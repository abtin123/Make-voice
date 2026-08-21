#!/usr/bin/env python3
"""Build one downloadable, cue-addressable ABV voice file using Avasho."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from avasho_client import AvashoClient, AvashoError
from abv_format import write_abv

try:
    from mutagen.mp3 import MP3
except Exception:
    MP3 = None


# همهٔ عبارت‌های ثابتِ مناسب گفتار تولید می‌شوند؛ فقط عبارت‌های مسافتی یا
# دارای متغیر لحظه‌ای کنار گذاشته می‌شوند. بنابراین افزودن یک هشدار جدید به
# JSON، بدون تغییر کد سازنده، آن را وارد همان فایل صوتی می‌کند.
REQUIRED_CUES = {
    "route_found", "recalculating_route", "off_route", "arrived_destination",
    "gps_signal_lost", "gps_signal_restored", "speed_camera_ahead", "speed_bump_ahead",
}
TEMPLATE_MARKERS = ("{distance}", "{number}", "{street}", "{time}")
DISTANCE_CUE_PREFIXES = (
    "turn_left_in_", "turn_right_in_", "exit_highway_in_", "arrive_in_",
)

SPEAKERS = {
    "kiani": ("male", "کیانی"),
    "nourai": ("male", "نورایی"),
    "dara": ("male", "دارا"),
    "parviz": ("male", "پرویز"),
    "bahman": ("male", "بهمن"),
    "farhad": ("male", "فرهاد"),
    "shahriyar": ("male", "شهریار"),
    "ariya": ("male", "آریا"),
    "sara": ("female", "سارا"),
    "pune": ("female", "پونه"),
    "bahar": ("female", "بهار"),
    "shahrzad": ("female", "شهرزاد"),
    "sheyda": ("female", "شیدا"),
    "shirin": ("female", "شیرین"),
}


def _duration_seconds(audio: bytes, timestamps: list[dict]) -> float:
    if timestamps:
        latest = max((float(item.get("end_time", 0.0)) for item in timestamps), default=0.0)
        if latest > 0:
            return latest
    if MP3:
        try:
            return float(MP3(io.BytesIO(audio)).info.length)
        except Exception:
            pass
    raise AvashoError("Avasho did not return usable timestamps or readable MP3 duration")


def _load_texts(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    phrases: dict[str, str] = {}
    for cue, phrase in raw.items():
        text = phrase.get("fa") if isinstance(phrase, dict) else None
        speaksDistance = cue.startswith(DISTANCE_CUE_PREFIXES)
        hasTemplate = isinstance(text, str) and any(marker in text for marker in TEMPLATE_MARKERS)
        if isinstance(cue, str) and isinstance(text, str) and text.strip() and not speaksDistance and not hasTemplate:
            phrases[cue] = text.strip()
    missing = sorted(REQUIRED_CUES - phrases.keys())
    if missing:
        raise ValueError(f"Missing Persian cue text: {', '.join(missing)}")
    return phrases


def _cached_result(cache_dir: Path, cue: str, text: str, speaker: str, speed: float) -> tuple[Path, Path]:
    key = hashlib.sha256(f'{cue}\0{text}\0{speaker}\0{speed}'.encode('utf-8')).hexdigest()
    return cache_dir / f'{key}.mp3', cache_dir / f'{key}.json'


def build_pack(*, input_path: Path, out_dir: Path, speaker: str, speed: float,
               token: str, csrf_token: str, session_cookie: str, cache_dir: Path) -> Path:
    if speaker not in SPEAKERS:
        raise ValueError(f"Unsupported Avasho speaker '{speaker}'. Choose: {', '.join(SPEAKERS)}")
    gender, voice_name = SPEAKERS[speaker]
    client = AvashoClient(token, csrf_token=csrf_token, session_cookie=session_cookie)
    phrases = _load_texts(input_path)
    cache_dir.mkdir(parents=True, exist_ok=True)
    audio_parts: list[bytes] = []
    cues: dict[str, dict[str, float | str]] = {}
    cursor = 0.0
    for cue, text in phrases.items():
        audio_path, meta_path = _cached_result(cache_dir, cue, text, speaker, speed)
        if audio_path.exists() and meta_path.exists():
            try:
                cached = json.loads(meta_path.read_text(encoding='utf-8'))
                result = type('CachedResult', (), {
                    'audio': audio_path.read_bytes(),
                    'timestamps': cached['timestamps'],
                })()
                print(f"Using cached {cue} with {speaker}...", flush=True)
            except (OSError, ValueError, KeyError, TypeError):
                audio_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                result = None
        else:
            result = None
        if result is None:
            print(f"Synthesizing {cue} with {speaker}...", flush=True)
            result = client.synthesize(text, speaker=speaker, speed=speed)
            audio_path.write_bytes(result.audio)
            meta_path.write_text(json.dumps({'timestamps': result.timestamps}, ensure_ascii=False), encoding='utf-8')
        duration = _duration_seconds(result.audio, result.timestamps)
        cues[cue] = {"start": round(cursor, 3), "end": round(cursor + duration, 3), "text": text}
        cursor += duration
        audio_parts.append(result.audio)

    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"fa_{speaker}.abv"
    output = out_dir / name
    meta = {
        "version": 2,
        "engine": "avasho-large",
        "lang": "fa",
        "speaker": speaker,
        "gender": gender,
        "voice_name": voice_name,
        "duration": round(cursor, 3),
        "cue_format": "seconds",
        "cues": cues,
        "distance_speech": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    # MPEG frames concatenate into one playable MP3 stream.  The app seeks only
    # within cue start/end boundaries and never downloads individual phrases.
    write_abv(output, meta, b"".join(audio_parts))
    return output


def _update_manifest(*, path: Path, output: Path, gender: str, voice_name: str,
                     download_base: str) -> None:
    """Add or replace one voice without discarding packs built earlier."""
    existing: dict = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except (OSError, ValueError):
            pass
    voices = existing.get("voices", [])
    voices = voices if isinstance(voices, list) else []
    gender_label = "زن" if gender == "female" else "مرد"
    entry = {
        "name": output.name,
        "display_name": f"فارسی — {voice_name} ({gender_label})",
        "language": "فارسی",
        "language_code": "fa",
        "gender_label": gender_label,
        "voice_name": voice_name,
        "size": output.stat().st_size,
        "download_url": f"{download_base.rstrip('/')}/{output.name}" if download_base else output.name,
    }
    by_name = {
        item.get("name"): item
        for item in voices
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    by_name[output.name] = entry
    manifest = {
        "schema_version": 4,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "voices": [by_name[name] for name in sorted(by_name)],
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="examples/nav_phrases.json")
    parser.add_argument("--out", default="out")
    parser.add_argument("--speaker", required=True, choices=sorted(SPEAKERS))
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--token-env", default="AVASHO_GATEWAY_TOKEN")
    parser.add_argument("--csrf-env", default="AVASHO_CSRF_TOKEN",
                        help="نام متغیر محیطی CSRF اجباری برای POST")
    parser.add_argument("--session-cookie-env", default="AVASHO_SESSION_COOKIE",
                        help="نام متغیر محیطی کوکی نشست معتبر Avasho")
    parser.add_argument("--cache-dir", default=".voice_build_cache")
    parser.add_argument("--download-base", default="")
    args = parser.parse_args()
    token = os.environ.get(args.token_env, "")
    csrf_token = os.environ.get(args.csrf_env, "")
    session_cookie = os.environ.get(args.session_cookie_env, "")
    output = build_pack(
        input_path=Path(args.input),
        out_dir=Path(args.out),
        speaker=args.speaker,
        speed=args.speed,
        token=token,
        csrf_token=csrf_token,
        session_cookie=session_cookie,
        cache_dir=Path(args.cache_dir),
    )
    gender, voice_name = SPEAKERS[args.speaker]
    manifest_path = Path(args.out) / "manifest.json"
    _update_manifest(
        path=manifest_path,
        output=output,
        gender=gender,
        voice_name=voice_name,
        download_base=args.download_base,
    )
    print(f"Built {output} ({output.stat().st_size} bytes) and {manifest_path}")


if __name__ == "__main__":
    main()
