#!/usr/bin/env python3
"""Free TTS via edge-tts. No key. Male+female voice per language."""
import asyncio
from typing import List, Optional, Tuple

import edge_tts

VOICES = {
    "fa": {"male": "fa-IR-FaridNeural", "female": "fa-IR-DilaraNeural"},
    "en": {"male": "en-US-AndrewNeural", "female": "en-US-AvaNeural"},
    "ar": {"male": "ar-SA-HamedNeural", "female": "ar-SA-ZariyahNeural"},
    "tr": {"male": "tr-TR-AhmetNeural", "female": "tr-TR-EmelNeural"},
    "de": {"male": "de-DE-ConradNeural", "female": "de-DE-KatjaNeural"},
    "fr": {"male": "fr-FR-HenriNeural", "female": "fr-FR-DeniseNeural"},
    "es": {"male": "es-ES-AlvaroNeural", "female": "es-ES-ElviraNeural"},
    "ru": {"male": "ru-RU-DmitryNeural", "female": "ru-RU-SvetlanaNeural"},
    "it": {"male": "it-IT-DiegoNeural", "female": "it-IT-ElsaNeural"},
    "pt": {"male": "pt-BR-AntonioNeural", "female": "pt-BR-FranciscaNeural"},
    "zh": {"male": "zh-CN-YunxiNeural", "female": "zh-CN-XiaoxiaoNeural"},
    "hi": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural"},
    "ur": {"male": "ur-PK-AsadNeural", "female": "ur-PK-UzmaNeural"},
    "az": {"male": "az-AZ-BabekNeural", "female": "az-AZ-BanuNeural"},
    "ja": {"male": "ja-JP-KeitaNeural", "female": "ja-JP-NanamiNeural"},
    "ko": {"male": "ko-KR-InJoonNeural", "female": "ko-KR-SunHiNeural"},
    "nl": {"male": "nl-NL-MaartenNeural", "female": "nl-NL-ColetteNeural"},
    "pl": {"male": "pl-PL-MarekNeural", "female": "pl-PL-ZofiaNeural"},
    "sv": {"male": "sv-SE-MattiasNeural", "female": "sv-SE-SofieNeural"},
}


class TTSError(RuntimeError):
    pass


def resolve_voice(lang: str, gender: str, voice: Optional[str] = None) -> str:
    if voice:
        return voice
    entry = VOICES.get(lang)
    if not entry or gender not in entry:
        raise TTSError(f"No voice for lang='{lang}' gender='{gender}'. Pass --voice-id explicitly.")
    return entry[gender]


async def _run(text: str, voice: str, rate: str):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio = bytearray()
    boundaries = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            boundaries.append(chunk)
    return bytes(audio), boundaries


def synthesize(text: str, lang: str, gender: str = "female", voice: str = None, rate: str = "+0%") -> Tuple[bytes, List[dict]]:
    resolved = resolve_voice(lang, gender, voice)
    try:
        audio_bytes, boundaries = asyncio.run(_run(text, resolved, rate))
    except Exception as e:
        raise TTSError(f"edge-tts failed (voice={resolved}): {e}") from e
    if not audio_bytes:
        raise TTSError(f"edge-tts returned no audio for voice={resolved}")
    alignment = [
        {"word": b["text"], "start": b["offset"] / 10_000_000, "end": (b["offset"] + b["duration"]) / 10_000_000}
        for b in boundaries
    ]
    return audio_bytes, alignment
