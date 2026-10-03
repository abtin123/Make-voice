#!/usr/bin/env python3
"""Catalog of the verified Edge Neural voices used by Abtin Maps voice packs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceLanguage:
    code: str
    locale: str
    display_name: str
    voices: dict[str, str]
    speaker_names: dict[str, str]

    def voice_for(self, gender: str) -> str:
        try:
            return self.voices[gender]
        except KeyError as error:
            raise ValueError(f"Unsupported gender '{gender}' for language '{self.code}'") from error

    def speaker_for(self, gender: str) -> str:
        try:
            return self.speaker_names[gender]
        except KeyError as error:
            raise ValueError(f"Unsupported gender '{gender}' for language '{self.code}'") from error


# Each pair was verified from the current Edge voice catalog. One explicit
# female and one explicit male Neural voice are published per phrase language.
VOICE_LANGUAGES: dict[str, VoiceLanguage] = {
    "fa": VoiceLanguage("fa", "fa-IR", "فارسی", {"female": "fa-IR-DilaraNeural", "male": "fa-IR-FaridNeural"}, {"female": "دیلارا", "male": "فرید"}),
    "en": VoiceLanguage("en", "en-US", "English", {"female": "en-US-AvaNeural", "male": "en-US-AndrewNeural"}, {"female": "Ava", "male": "Andrew"}),
    "ar": VoiceLanguage("ar", "ar-SA", "العربية", {"female": "ar-SA-ZariyahNeural", "male": "ar-SA-HamedNeural"}, {"female": "Zariyah", "male": "Hamed"}),
    "tr": VoiceLanguage("tr", "tr-TR", "Türkçe", {"female": "tr-TR-EmelNeural", "male": "tr-TR-AhmetNeural"}, {"female": "Emel", "male": "Ahmet"}),
    "de": VoiceLanguage("de", "de-DE", "Deutsch", {"female": "de-DE-KatjaNeural", "male": "de-DE-ConradNeural"}, {"female": "Katja", "male": "Conrad"}),
    "fr": VoiceLanguage("fr", "fr-FR", "Français", {"female": "fr-FR-DeniseNeural", "male": "fr-FR-HenriNeural"}, {"female": "Denise", "male": "Henri"}),
    "es": VoiceLanguage("es", "es-ES", "Español", {"female": "es-ES-ElviraNeural", "male": "es-ES-AlvaroNeural"}, {"female": "Elvira", "male": "Alvaro"}),
    "ru": VoiceLanguage("ru", "ru-RU", "Русский", {"female": "ru-RU-SvetlanaNeural", "male": "ru-RU-DmitryNeural"}, {"female": "Svetlana", "male": "Dmitry"}),
}

GENDERS = ("female", "male")
