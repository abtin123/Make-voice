#!/usr/bin/env python3
"""A/B lab for Edge TTS pronunciation (diacritics, ZWNJ, kashida, digits...).

    python scripts/pronunciation_lab.py --voice fa-IR-DilaraNeural --out lab

Edit VARIANTS, run, then listen to lab/*.mp3 back to back. Whatever sounds better
goes into nav_phrases.json under the cue's  "tts": {"fa": "..."}  override
(the displayed text stays clean).
"""
import argparse
import asyncio
from pathlib import Path

import edge_tts

# name -> text.   U+0650 kasra, U+064E fatha, U+0655 hamza-below, U+0640 tatweel
VARIANTS = {
    "plain": "در میدان، از خروجی دوم خارج شوید",
    "ezafe_kasra": "در میدان، از خروجیِ دوم خارج شوید",
    "hamza_below": "در میدان، از خروجی\u0655 دوم خارج شوید",
    "tatweel": "در میدان، از خروجـی دوم خارج شوید",
    "fatha_on_exit": "در میدان، از خُروجی دوم خارج شوید",
    "comma_pause": "در میدان، از خروجیِ دوم، خارج شوید",
    "digits": "در میدان، از خروجی 2 خارج شوید",
}


async def run(voice: str, out: Path, rate: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, text in VARIANTS.items():
        await edge_tts.Communicate(text, voice=voice, rate=rate).save(str(out / f"{name}.mp3"))
        print("saved", name)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="fa-IR-DilaraNeural")
    ap.add_argument("--out", default="lab")
    ap.add_argument("--rate", default="+0%")
    a = ap.parse_args()
    asyncio.run(run(a.voice, Path(a.out), a.rate))
