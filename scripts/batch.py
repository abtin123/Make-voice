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
    ap.add_argument(
        "--languages", nargs="+", default=None,
        help="Only build these language codes (e.g. fa en). Default: all "
             "languages present in --input.",
    )
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument(
        "--max-failure-rate",
        type=float,
        default=0.02,
        help="Fraction of items allowed to fail (after retries) before the "
             "job exits non-zero. Default 0.02 (2%%) tolerates rare edge-tts "
             "flakiness so a couple of failures don't block publishing.",
    )
    args = ap.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    is_nested = all(isinstance(v, dict) for v in raw.values())
    phrases = raw if is_nested else {"phrase": raw}

    catalog = {"version": 1, "languages": {}, "phrases": {}}
    failures = []
    pending = []  # (phrase_id, lang, gender, text, out_path) needing a catalog entry once resolved
    total_items = 0

    def attempt(phrase_id, lang, gender, text, out_path):
        print(f"--- {phrase_id} / {lang} / {gender} ---", flush=True)
        try:
            generate_one(text, lang, gender, out_path, rate=args.rate)
            return True, None
        except TTSError as e:
            print(f"  FAILED: {e}", file=sys.stderr, flush=True)
            return False, str(e)

    for phrase_id, lang_map in phrases.items():
        phrase_dir = out_dir / phrase_id
        catalog["phrases"][phrase_id] = {}
        for lang, text in lang_map.items():
            if args.languages and lang not in args.languages:
                continue
            catalog["languages"].setdefault(lang, {"genders": []})
            catalog["phrases"][phrase_id][lang] = {}
            for gender in args.genders:
                if gender not in VOICES.get(lang, {}):
                    continue
                total_items += 1
                out_path = phrase_dir / f"{lang}_{gender}.nvb"
                if args.skip_existing and out_path.exists():
                    print(f"skip: {phrase_id}/{lang}_{gender}")
                else:
                    ok, err = attempt(phrase_id, lang, gender, text, out_path)
                    if not ok:
                        pending.append((phrase_id, lang, gender, text, out_path, err))
                        continue

                if gender not in catalog["languages"][lang]["genders"]:
                    catalog["languages"][lang]["genders"].append(gender)
                catalog["phrases"][phrase_id][lang][gender] = {
                    "file": f"{phrase_id}/{lang}_{gender}.nvb",
                    "size_bytes": out_path.stat().st_size if out_path.exists() else None,
                }

    # Second pass: retry whatever failed once the rest of the batch is done —
    # transient edge-tts hiccups (e.g. "No audio was received") often clear
    # up a few minutes later.
    if pending:
        print(f"\nRetrying {len(pending)} failed item(s) after full pass...", flush=True)
        still_failing = []
        for phrase_id, lang, gender, text, out_path, _prev_err in pending:
            ok, err = attempt(phrase_id, lang, gender, text, out_path)
            if ok:
                if gender not in catalog["languages"][lang]["genders"]:
                    catalog["languages"][lang]["genders"].append(gender)
                catalog["phrases"][phrase_id][lang][gender] = {
                    "file": f"{phrase_id}/{lang}_{gender}.nvb",
                    "size_bytes": out_path.stat().st_size if out_path.exists() else None,
                }
            else:
                still_failing.append(f"{phrase_id}/{lang}/{gender}: {err}")
        failures = still_failing

    catalog_path = out_dir / "catalog.json"
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    n_langs = len(catalog["languages"])
    n_phrases = len(catalog["phrases"])
    print(f"\ncatalog -> {catalog_path}  ({n_phrases} phrases x {n_langs} languages x male/female)")

    if failures:
        rate = len(failures) / total_items if total_items else 1.0
        print(f"\n{len(failures)} failure(s) out of {total_items} ({rate:.2%}):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        if rate > args.max_failure_rate:
            print(
                f"\nFailure rate {rate:.2%} exceeds --max-failure-rate "
                f"{args.max_failure_rate:.2%} -> failing the build.",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            print(
                f"\nFailure rate {rate:.2%} is within --max-failure-rate "
                f"{args.max_failure_rate:.2%} -> continuing so catalog.json "
                "and the successful .nvb files still get published. Missing "
                "phrases are simply absent from catalog.json for that "
                "lang/gender.",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
