#!/usr/bin/env python3
"""
Text -> Audio + Sync JSON -> single compact bundle for navigation apps.
Engine: ElevenLabs (multilingual v2, natural voice).
Usage:
  python scripts/generate.py --text "متن" --lang fa --out out/route1
  python scripts/generate.py --text-file input.txt --lang en --out out/route1
Env:
  ELEVENLABS_API_KEY (required)
  ELEVENLABS_VOICE_ID (optional, default below)
"""
import argparse
import base64
import json
import os
import struct
import sys
import zipfile
from pathlib import Path

import requests

API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel, multilingual
MODEL_ID = "eleven_multilingual_v2"


def synthesize(text: str, voice_id: str, api_key: str, output_format: str = "mp3_44100_64"):
    """Single-shot TTS call with char-level timestamps. One continuous audio stream (no chunking) for smooth, uninterrupted playback."""
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
        "output_format": output_format,
    }
    r = requests.post(
        API_URL.format(voice_id=voice_id),
        headers=headers,
        params={"output_format": output_format},
        json=payload,
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    audio_bytes = base64.b64decode(data["audio_base64"])
    chars = data["alignment"]["characters"]
    starts = data["alignment"]["character_start_times_seconds"]
    ends = data["alignment"]["character_end_times_seconds"]
    return audio_bytes, chars, starts, ends


def chars_to_words(text: str, chars, starts, ends):
    """Collapse char-level timestamps into word-level timing for nav-app sync."""
    words = []
    cur = ""
    cur_start = None
    for ch, s, e in zip(chars, starts, ends):
        if ch.strip() == "":
            if cur:
                words.append({"word": cur, "start": round(cur_start, 3), "end": round(prev_end, 3)})
                cur = ""
                cur_start = None
        else:
            if cur_start is None:
                cur_start = s
            cur = cur + ch
            prev_end = e
    if cur:
        words.append({"word": cur, "start": round(cur_start, 3), "end": round(prev_end, 3)})
    return words


def build_sync_json(text: str, lang: str, chars, starts, ends, duration: float):
    words = chars_to_words(text, chars, starts, ends)
    return {
        "version": 1,
        "lang": lang,
        "text": text,
        "duration": round(duration, 3),
        "words": words,
        "characters": [
            {"c": c, "s": round(s, 3), "e": round(e, 3)} for c, s, e in zip(chars, starts, ends)
        ],
    }


def mp3_duration_seconds(path: Path) -> float:
    """Cheap MP3 duration probe via mutagen if present, else estimate from bitrate header; falls back to last timestamp from alignment (caller supplies)."""
    try:
        from mutagen.mp3 import MP3
        return MP3(str(path)).info.length
    except Exception:
        return 0.0


def bundle(audio_path: Path, json_path: Path, out_zip: Path):
    """Pack audio+json together, low overhead, deflate compression, for single-file download in the app."""
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(audio_path, arcname=audio_path.name)
        zf.write(json_path, arcname=json_path.name)


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="Raw text input")
    src.add_argument("--text-file", help="Path to a UTF-8 text file")
    ap.add_argument("--lang", required=True, help="Language code, e.g. fa, en, ar, tr, de ... (20+ supported by eleven_multilingual_v2)")
    ap.add_argument("--voice-id", default=DEFAULT_VOICE_ID)
    ap.add_argument("--out", required=True, help="Output basename (no extension), e.g. out/route1")
    ap.add_argument("--format", default="mp3_44100_64", help="ElevenLabs output_format; 64kbps mono-ish for small size")
    args = ap.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    text = args.text if args.text else Path(args.text_file).read_text(encoding="utf-8")
    text = text.strip()
    if not text:
        print("ERROR: empty text", file=sys.stderr)
        sys.exit(1)

    out_base = Path(args.out)
    out_base.parent.mkdir(parents=True, exist_ok=True)

    audio_bytes, chars, starts, ends = synthesize(text, args.voice_id, api_key, args.format)

    audio_path = out_base.with_suffix(".mp3")
    audio_path.write_bytes(audio_bytes)

    duration = ends[-1] if ends else mp3_duration_seconds(audio_path)
    sync = build_sync_json(text, args.lang, chars, starts, ends, duration)

    json_path = out_base.with_suffix(".json")
    json_path.write_text(json.dumps(sync, ensure_ascii=False, indent=None, separators=(",", ":")), encoding="utf-8")

    zip_path = out_base.with_suffix(".bundle.zip")
    bundle(audio_path, json_path, zip_path)

    print(f"OK: {audio_path}  {json_path}  {zip_path}")
    print(f"duration={duration:.2f}s words={len(sync['words'])} chars={len(chars)}")


if __name__ == "__main__":
    main()
