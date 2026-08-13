#!/usr/bin/env python3
"""
Batch mode: one input JSON with {lang: text} pairs -> generates all languages,
each as its own audio+json+bundle.zip, plus one combined manifest.zip for the app.

Usage:
  python scripts/batch.py --input texts.json --out out/route1

texts.json example:
{
  "fa": "به مقصد نزدیک شدید",
  "en": "You have arrived at your destination",
  "ar": "لقد وصلت إلى وجهتك",
  "tr": "Hedefinize ulaştınız"
}
"""
import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSON file: {lang_code: text, ...}")
    ap.add_argument("--out", required=True, help="Output directory base")
    ap.add_argument("--voice-id", default=None)
    ap.add_argument("--format", default="mp3_44100_64")
    args = ap.parse_args()

    entries = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    produced = []
    for lang, text in entries.items():
        base = out_dir / lang
        cmd = [
            sys.executable, str(HERE / "generate.py"),
            "--text", text,
            "--lang", lang,
            "--out", str(base),
            "--format", args.format,
        ]
        if args.voice_id:
            cmd += ["--voice-id", args.voice_id]
        print(f"--- {lang} ---")
        subprocess.run(cmd, check=True)
        produced.append(base)

    manifest_zip = out_dir / "manifest.zip"
    with zipfile.ZipFile(manifest_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for base in produced:
            for ext in (".mp3", ".json"):
                p = base.with_suffix(ext)
                if p.exists():
                    zf.write(p, arcname=f"{base.name}/{p.name}")

    print(f"\nAll languages done -> {manifest_zip}")


if __name__ == "__main__":
    main()
