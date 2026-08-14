#!/usr/bin/env python3
"""
Batch: phrases.json {phrase_id: {lang: text}} -> one .nvb per
phrase/lang/gender, hosted flat on GitHub, plus catalog.json the app uses to
render a language+gender picker and download only what's chosen.

Usage:
  python scripts/batch.py --input examples/nav_phrases.json --out out

Output:
  out/<phrase_id>/<lang>_<gender>.nvb
  out/catalog.json
"""
import argparse
import json
import sys
from pathlib import Path

from generate import generate_one
from tts_client import TTSError, VOICES

GENDERS = ["male", "female"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--genders", nargs="+", choices=GENDERS, default=GENDERS)
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    is_nested = all(isinstance(v, dict) for v in raw.values())
    phrases = raw if is_nested else {"phrase": raw}

    catalog = {"version": 1, "languages": {}, "phrases": {}}
    failures = []

    for phrase_id, lang_map in phrases.items():
        phrase_dir = out_dir / phrase_id
        catalog["phrases"][phrase_id] = {}
        for lang, text in lang_map.items():
            catalog["languages"].setdefault(lang, {"genders": []})
            catalog["phrases"][phrase_id][lang] = {}
            for gender in args.genders:
                if gender not in VOICES.get(lang, {}):
                    continue
                out_path = phrase_dir / f"{lang}_{gender}.nvb"
                if args.skip_existing and out_path.exists():
                    print(f"skip: {phrase_id}/{lang}_{gender}")
                else:
                    print(f"--- {phrase_id} / {lang} / {gender} ---", flush=True)
                    try:
                        _, meta = generate_one(text, lang, gender, out_path, rate=args.rate)
                    except TTSError as e:
                        print(f"  FAILED: {e}", file=sys.stderr, flush=True)
                        failures.append(f"{phrase_id}/{lang}/{gender}: {e}")
                        continue

                if gender not in catalog["languages"][lang]["genders"]:
                    catalog["languages"][lang]["genders"].append(gender)

                catalog["phrases"][phrase_id][lang][gender] = {
                    "file": f"{phrase_id}/{lang}_{gender}.nvb",
                    "size_bytes": out_path.stat().st_size if out_path.exists() else None,
                }

    catalog_path = out_dir / "catalog.json"
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    n_langs = len(catalog["languages"])
    n_phrases = len(catalog["phrases"])
    print(f"\ncatalog -> {catalog_path}  ({n_phrases} phrases x {n_langs} languages x male/female)")
    if failures:
        print(f"\n{len(failures)} failure(s):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
