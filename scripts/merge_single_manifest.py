#!/usr/bin/env python3
"""Merge per-speaker manifests after one-file Neural TTS packs are built."""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    voices = []
    for raw_path in args.inputs:
        doc = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        for voice in doc.get("voices", []):
            voice = dict(voice)
            voice["download_url"] = voice["name"]
            voices.append(voice)
    names = [voice["name"] for voice in voices]
    if not voices or len(names) != len(set(names)):
        raise SystemExit("Manifest has no voices or duplicate names")
    Path(args.out).write_text(json.dumps({"schema_version": 3, "voices": voices}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
