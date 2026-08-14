#!/usr/bin/env python3
"""Extract an .nvb bundle back into .mp3 + .json (for testing/debugging)."""
import argparse
import json
from pathlib import Path

from nvb_format import read_nvb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("nvb_file")
    ap.add_argument("--out", default=None, help="Output basename, default = same as input without .nvb")
    args = ap.parse_args()

    src = Path(args.nvb_file)
    out_base = Path(args.out) if args.out else src.with_suffix("")

    meta, audio_bytes = read_nvb(src)

    mp3_path = out_base.with_suffix(".mp3")
    json_path = out_base.with_suffix(".json")
    mp3_path.write_bytes(audio_bytes)
    json_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"extracted: {mp3_path}  {json_path}")
    print(f"lang={meta['lang']} gender={meta['gender']} voice={meta['voice']} duration={meta['duration']}s words={len(meta['words'])}")


if __name__ == "__main__":
    main()
