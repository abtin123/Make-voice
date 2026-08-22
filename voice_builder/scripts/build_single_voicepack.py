#!/usr/bin/env python3
"""Build cue-addressable one-file ABV packs for every navigation language and gender."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from abv_format import write_abv
from neural_tts_client import NeuralTtsClient, NeuralTtsError
from voice_catalog import GENDERS, VOICE_LANGUAGES, VoiceLanguage

try:
    from mutagen.mp3 import MP3
except Exception:
    MP3 = None


# Dynamic distance, street name and time phrases remain deliberately excluded.
# The app displays and speaks the same static cue key and seeks it in one ABV.
REQUIRED_CUES = {
    "route_found", "recalculating_route", "off_route", "arrived_destination",
    "gps_signal_lost", "gps_signal_restored", "speed_camera_ahead", "speed_bump_ahead",
}
TEMPLATE_MARKERS = ("{distance}", "{number}", "{street}", "{time}")
DISTANCE_CUE_PREFIXES = (
    "turn_left_in_", "turn_right_in_", "exit_highway_in_", "arrive_in_",
)


def _duration_seconds(audio: bytes, timestamps: list[dict]) -> float:
    timeline_duration = max((float(item.get("end_time", 0.0)) for item in timestamps), default=0.0)
    mp3_duration = 0.0
    if MP3:
        try:
            mp3_duration = float(MP3(io.BytesIO(audio)).info.length)
        except Exception:
            pass
    if timeline_duration > 0 and mp3_duration > 0:
        # Never allow a bad remote timestamp to swallow the following cue.
        return min(timeline_duration, mp3_duration)
    if timeline_duration > 0:
        return timeline_duration
    if mp3_duration > 0:
        return mp3_duration
    raise NeuralTtsError("Neural TTS did not return usable timestamps or readable MP3 duration")


def _load_texts(path: Path, language_code: str) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    phrases: dict[str, str] = {}
    for cue, phrase in raw.items():
        text = phrase.get(language_code) if isinstance(phrase, dict) else None
        speaks_distance = cue.startswith(DISTANCE_CUE_PREFIXES)
        has_template = isinstance(text, str) and any(marker in text for marker in TEMPLATE_MARKERS)
        if isinstance(cue, str) and isinstance(text, str) and text.strip() and not speaks_distance and not has_template:
            phrases[cue] = text.strip()
    missing = sorted(REQUIRED_CUES - phrases.keys())
    if missing:
        raise ValueError(f"Missing {language_code} cue text: {', '.join(missing)}")
    return phrases


def _cached_result(cache_dir: Path, cue: str, text: str, voice: str, speed: float) -> tuple[Path, Path]:
    key = hashlib.sha256(f"{cue}\0{text}\0{voice}\0{speed}".encode("utf-8")).hexdigest()
    return cache_dir / f"{key}.mp3", cache_dir / f"{key}.json"


def build_pack(
    *, input_path: Path, out_dir: Path, language: VoiceLanguage, gender: str,
    speed: float, cache_dir: Path,
) -> Path:
    if gender not in GENDERS:
        raise ValueError(f"Unsupported gender '{gender}'. Choose: {', '.join(GENDERS)}")
    voice = language.voice_for(gender)
    phrases = _load_texts(input_path, language.code)
    client = NeuralTtsClient()
    cache_dir.mkdir(parents=True, exist_ok=True)
    audio_parts: list[bytes] = []
    cues: dict[str, dict[str, float | str]] = {}
    cursor = 0.0
    for cue, text in phrases.items():
        audio_path, meta_path = _cached_result(cache_dir, cue, text, voice, speed)
        result = None
        if audio_path.exists() and meta_path.exists():
            try:
                cached = json.loads(meta_path.read_text(encoding="utf-8"))
                result = type("CachedResult", (), {"audio": audio_path.read_bytes(), "timestamps": cached["timestamps"]})()
                print(f"Using cached {language.code}/{gender}/{cue}", flush=True)
            except (OSError, ValueError, KeyError, TypeError):
                audio_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
        if result is None:
            print(f"Synthesizing {language.code}/{gender}/{cue} with {voice}", flush=True)
            result = client.synthesize(text, voice=voice, speed=speed)
            audio_path.write_bytes(result.audio)
            meta_path.write_text(json.dumps({"timestamps": result.timestamps}, ensure_ascii=False), encoding="utf-8")
        duration = _duration_seconds(result.audio, result.timestamps)
        cues[cue] = {"start": round(cursor, 3), "end": round(cursor + duration, 3), "text": text}
        cursor += duration
        audio_parts.append(result.audio)

    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{language.code}_{gender}.abv"
    meta = {
        "version": 2,
        "engine": "edge-neural",
        "lang": language.code,
        "locale": language.locale,
        "speaker": language.speaker_for(gender),
        "gender": gender,
        "voice_name": voice,
        "duration": round(cursor, 3),
        "cue_format": "seconds",
        "cues": cues,
        "distance_speech": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_abv(output, meta, b"".join(audio_parts))
    return output


def _manifest_entry(output: Path, language: VoiceLanguage, gender: str, download_base: str) -> dict[str, object]:
    gender_label = "زن" if gender == "female" else "مرد"
    speaker = language.speaker_for(gender)
    return {
        "name": output.name,
        "display_name": f"{language.display_name} — {speaker} ({gender_label})",
        "language": language.display_name,
        "language_code": language.code,
        "gender_label": gender_label,
        "voice_name": language.voice_for(gender),
        "size": output.stat().st_size,
        "download_url": f"{download_base.rstrip('/')}/{output.name}" if download_base else output.name,
    }


def _write_manifest(path: Path, packs: list[tuple[Path, VoiceLanguage, str]], download_base: str) -> None:
    manifest = {
        "schema_version": 5,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "voices": [
            _manifest_entry(output, language, gender, download_base)
            for output, language, gender in sorted(packs, key=lambda item: item[0].name)
        ],
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _select(value: str, available: dict[str, VoiceLanguage]) -> list[str]:
    if value.strip().lower() == "all":
        return list(available)
    selected = [part.strip() for part in value.split(",") if part.strip()]
    unknown = sorted(set(selected) - set(available))
    if unknown:
        raise ValueError(f"Unsupported language code(s): {', '.join(unknown)}")
    return selected


def _select_genders(value: str) -> list[str]:
    if value.strip().lower() == "all":
        return list(GENDERS)
    selected = [part.strip() for part in value.split(",") if part.strip()]
    unknown = sorted(set(selected) - set(GENDERS))
    if unknown:
        raise ValueError(f"Unsupported gender(s): {', '.join(unknown)}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="examples/nav_phrases.json")
    parser.add_argument("--out", default="out")
    parser.add_argument("--languages", default="all", help="Comma-separated codes or 'all' (default).")
    parser.add_argument("--genders", default="all", help="female,male or 'all' (default).")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--cache-dir", default=".voice_build_cache")
    parser.add_argument("--download-base", default="")
    args = parser.parse_args()

    input_path, out_dir, cache_dir = Path(args.input), Path(args.out), Path(args.cache_dir)
    packs: list[tuple[Path, VoiceLanguage, str]] = []
    for language_code in _select(args.languages, VOICE_LANGUAGES):
        language = VOICE_LANGUAGES[language_code]
        for gender in _select_genders(args.genders):
            output = build_pack(
                input_path=input_path,
                out_dir=out_dir,
                language=language,
                gender=gender,
                speed=args.speed,
                cache_dir=cache_dir / language_code / gender,
            )
            packs.append((output, language, gender))
    _write_manifest(out_dir / "manifest.json", packs, args.download_base)
    print(f"Built {len(packs)} ABV packs and {out_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
