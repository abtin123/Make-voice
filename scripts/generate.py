#!/usr/bin/env python3
"""
Text -> single .nvb bundle (audio+json, gzip-packed, one small file).
Engine: edge-tts (free, no key). Male/female voice per language.

Usage:
  python scripts/generate.py --text "به مقصد نزدیک شدید" --lang fa --gender female --out out/route1
"""
import argparse
import sys
from pathlib import Path

from tts_client import synthesize, resolve_voice, TTSError
from nvb_format import write_nvb

try:
    from mutagen.mp3 import MP3
except Exception:
    MP3 = None


def mp3_duration_seconds(audio_bytes: bytes) -> float:
    if not MP3:
        return 0.0
    import io
    try:
        return MP3(io.BytesIO(audio_bytes)).info.length
    except Exception:
        return 0.0


def generate_one(text: str, lang: str, gender: str, out_path: Path, voice: str = None, rate: str = "+0%"):
    text = text.strip()
    if not text:
        raise ValueError("empty text")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    audio_bytes, alignment = synthesize(text, lang=lang, gender=gender, voice=voice, rate=rate)
    duration = mp3_duration_seconds(audio_bytes)
    words = [{"word": a["word"], "start": round(a["start"], 3), "end": round(a["end"], 3)} for a in alignment]
    if not duration and words:
        duration = words[-1]["end"]

    resolved_voice = resolve_voice(lang, gender, voice)

    meta = {
        "version": 1,
        "engine": "edge-tts",
        "voice": resolved_voice,
        "gender": gender,
        "lang": lang,
        "text": text,
        "duration": round(duration, 3),
        "timing_source": "engine",
        "words": words,
    }

    write_nvb(out_path, meta, audio_bytes)
    return out_path, meta


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text")
    src.add_argument("--text-file")
    ap.add_argument("--lang", required=True)
    ap.add_argument("--gender", choices=["male", "female"], default="female")
    ap.add_argument("--voice-id", default=None)
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--out", required=True, help="Output file path, e.g. out/route1.nvb")
    args = ap.parse_args()

    text = args.text if args.text else Path(args.text_file).read_text(encoding="utf-8")
    out_path = Path(args.out)
    if out_path.suffix != ".nvb":
        out_path = out_path.with_suffix(".nvb")

    try:
        path, meta = generate_one(text, args.lang, args.gender, out_path, voice=args.voice_id, rate=args.rate)
    except TTSError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"OK: {path} ({path.stat().st_size} bytes)  duration={meta['duration']:.2f}s words={len(meta['words'])}")


if __name__ == "__main__":
    main()
