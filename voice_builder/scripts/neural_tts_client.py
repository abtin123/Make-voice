#!/usr/bin/env python3
"""Reliable Microsoft Edge Neural TTS client for one-file ABV voice packs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import edge_tts


class NeuralTtsError(RuntimeError):
    pass


@dataclass(frozen=True)
class NeuralTtsResult:
    audio: bytes
    timestamps: list[dict[str, Any]]


class NeuralTtsClient:
    """Generate natural Persian speech with retry-safe Edge Neural voices."""

    _voice_by_gender = {
        "female": "fa-IR-DilaraNeural",
        "male": "fa-IR-FaridNeural",
    }

    def __init__(self, *, attempts: int = 5) -> None:
        self._attempts = attempts

    @staticmethod
    def _rate(speed: float) -> str:
        if not 0.5 <= speed <= 1.8:
            raise NeuralTtsError("Speed must be between 0.5 and 1.8")
        percent = round((speed - 1.0) * 100)
        return f"{percent:+d}%"

    async def _generate(self, text: str, gender: str, speed: float) -> NeuralTtsResult:
        voice = self._voice_by_gender.get(gender)
        if voice is None:
            raise NeuralTtsError(f"Unsupported Neural voice gender: {gender}")
        audio = bytearray()
        timestamps: list[dict[str, Any]] = []
        communicator = edge_tts.Communicate(text, voice=voice, rate=self._rate(speed))
        async for event in communicator.stream():
            kind = event.get("type")
            if kind == "audio":
                audio.extend(event["data"])
            elif kind == "WordBoundary":
                start = float(event.get("offset", 0)) / 10_000_000
                duration = float(event.get("duration", 0)) / 10_000_000
                timestamps.append({
                    "start_time": start,
                    "end_time": start + duration,
                    "text": event.get("text", ""),
                })
        if not audio:
            raise NeuralTtsError("Neural TTS returned no audio")
        return NeuralTtsResult(audio=bytes(audio), timestamps=timestamps)

    def synthesize(self, text: str, *, gender: str, speed: float) -> NeuralTtsResult:
        if not text.strip():
            raise NeuralTtsError("Cannot synthesize empty text")
        last_error: Exception | None = None
        for attempt in range(1, self._attempts + 1):
            try:
                return asyncio.run(self._generate(text, gender, speed))
            except Exception as error:  # network errors from Edge are transient
                last_error = error
                if attempt < self._attempts:
                    delay = min(20.0, 1.7 ** attempt)
                    print(
                        f"Neural TTS failed (attempt {attempt}/{self._attempts}); retrying in {delay:.1f}s",
                        flush=True,
                    )
                    import time
                    time.sleep(delay)
        raise NeuralTtsError(f"Neural TTS failed after {self._attempts} attempts: {last_error}") from last_error
