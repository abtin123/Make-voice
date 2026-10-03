#!/usr/bin/env python3
"""
.abv (Abtin Voice Bundle) — one small binary file = mp3 + json packed and
gzip-compressed. App downloads exactly one file per phrase+lang+gender.

Layout (all integers little-endian uint32):
  magic        4 bytes   b"ABV1"
  json_len     4 bytes
  audio_len    4 bytes
  json_bytes   json_len bytes   (gzip-compressed UTF-8 JSON)
  audio_bytes  audio_len bytes  (gzip-compressed mp3)
"""
import gzip
import json
import struct
from pathlib import Path

MAGIC = b"ABV1"


def write_abv(path: Path, meta: dict, audio_bytes: bytes):
    json_gz = gzip.compress(json.dumps(meta, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), compresslevel=9)
    audio_gz = gzip.compress(audio_bytes, compresslevel=9)
    with open(path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<I", len(json_gz)))
        f.write(struct.pack("<I", len(audio_gz)))
        f.write(json_gz)
        f.write(audio_gz)


def read_abv(path: Path):
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError(f"not an .abv file: {path}")
        json_len, audio_len = struct.unpack("<II", f.read(8))
        json_gz = f.read(json_len)
        audio_gz = f.read(audio_len)
    meta = json.loads(gzip.decompress(json_gz).decode("utf-8"))
    audio_bytes = gzip.decompress(audio_gz)
    return meta, audio_bytes


# نام‌های داخلی نسخهٔ قبلی فقط برای اسکریپت‌های قدیمی باقی مانده‌اند؛ خروجی و
# قرارداد عمومی آبتین‌مپ از این نسخه ABV است.
write_nvb = write_abv
read_nvb = read_abv
