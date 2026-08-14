#!/usr/bin/env python3
"""
Merge multiple per-language catalog.json files (produced by running
batch.py separately per language, e.g. in a GitHub Actions matrix) into
a single catalog.json covering all languages.

Usage:
  python scripts/merge_catalogs.py --inputs out-fa/catalog.json out-en/catalog.json ... --out out/catalog.json
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    merged = {"version": 1, "languages": {}, "phrases": {}}

    for input_path in args.inputs:
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))

        for lang, info in data.get("languages", {}).items():
            existing = merged["languages"].setdefault(lang, {"genders": []})
            for g in info.get("genders", []):
                if g not in existing["genders"]:
                    existing["genders"].append(g)

        for phrase_id, lang_map in data.get("phrases", {}).items():
            merged_phrase = merged["phrases"].setdefault(phrase_id, {})
            for lang, gender_map in lang_map.items():
                merged_phrase.setdefault(lang, {}).update(gender_map)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    n_langs = len(merged["languages"])
    n_phrases = len(merged["phrases"])
    print(f"merged catalog -> {out_path}  ({n_phrases} phrases x {n_langs} languages)")


if __name__ == "__main__":
    main()
