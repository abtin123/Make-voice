#!/usr/bin/env python3
"""Static contract checks for Neural TTS one-file voice packs and Flutter cues."""

import json
import sys
from pathlib import Path


builder = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(builder / "scripts"))
from voice_catalog import GENDERS, VOICE_LANGUAGES

project = builder.parent / "work"
neural = (builder / "scripts/neural_tts_client.py").read_text(encoding="utf-8")
single = (builder / "scripts/build_single_voicepack.py").read_text(encoding="utf-8")
workflow = (builder / ".github/workflows/build-and-publish-voicepacks.yml").read_text(encoding="utf-8")
phrases = (builder / "examples/nav_phrases.json").read_text(encoding="utf-8")
service = (project / "lib/features/voice_settings/data/voice_service.dart").read_text(encoding="utf-8")
catalog = (project / "lib/features/voice_settings/data/voice_pack_catalog.dart").read_text(encoding="utf-8")
voice_map = (project / "lib/features/voice_settings/data/voice_pack_fa.dart").read_text(encoding="utf-8")
home = (project / "lib/features/map/presentation/home_screen.dart").read_text(encoding="utf-8")
routing = (project / "lib/features/routing/data/routing_service.dart").read_text(encoding="utf-8")
offline_routing = (project / "lib/features/routing/data/abtinmap_routing_provider.dart").read_text(encoding="utf-8")

assert "fa-IR-DilaraNeural" in neural and "fa-IR-FaridNeural" in neural
assert "edge_tts.Communicate" in neural and "WordBoundary" in neural
assert "Neural TTS failed after" in neural and "attempts: int = 5" in neural
assert "NeuralTtsClient" in single and "voice=voice" in single
assert '"engine": "edge-neural"' in single
assert '"display_name"' in single and "_write_manifest" in single
assert '"schema_version": 5' in single
phrase_data = json.loads(phrases)
required_cues = {"route_found", "recalculating_route", "off_route", "arrived_destination", "gps_signal_lost", "gps_signal_restored", "speed_camera_ahead", "speed_bump_ahead"}
spoken_static = {
    cue for cue, value in phrase_data.items()
    if isinstance(value, dict)
    and isinstance(value.get("fa"), str)
    and value["fa"].strip()
    and not cue.startswith(("turn_left_in_", "turn_right_in_", "exit_highway_in_", "arrive_in_"))
    and not any(marker in value["fa"] for marker in ("{distance}", "{number}", "{street}", "{time}"))
}
assert "REQUIRED_CUES" in single and "DISTANCE_CUE_PREFIXES" in single and '"distance_speech": False' in single
assert "speed_bump_ahead" in single and '"speed_bump_ahead"' in phrases
assert {"route_found", "off_route", "gps_signal_lost", "speed_bump_ahead"}.issubset(spoken_static)
assert all(f"roundabout_take_exit_{exit_number}" in spoken_static for exit_number in range(1, 21))
assert "all female and male" in workflow
assert "actions/cache@v4" in workflow and "voice_build_cache" in workflow
assert "merge_single_manifest.py" not in workflow
assert "--languages all" in workflow and "--genders all" in workflow
assert 'output = out_dir / f"{language.code}_{gender}.abv"' in single
catalogue = (builder / "scripts/voice_catalog.py").read_text(encoding="utf-8")
for locale in ("fa-IR", "en-US", "ar-SA", "tr-TR", "de-DE", "fr-FR", "es-ES", "ru-RU"):
    assert locale in catalogue
assert tuple(VOICE_LANGUAGES) == ("fa", "en", "ar", "tr", "de", "fr", "es", "ru")
assert tuple(GENDERS) == ("female", "male")
for language_code, language in VOICE_LANGUAGES.items():
    assert set(language.voices) == set(GENDERS)
    assert set(language.speaker_names) == set(GENDERS)
    language_static = {
        cue for cue, value in phrase_data.items()
        if isinstance(value, dict)
        and isinstance(value.get(language_code), str)
        and value[language_code].strip()
        and not cue.startswith(("turn_left_in_", "turn_right_in_", "exit_highway_in_", "arrive_in_"))
        and not any(marker in value[language_code] for marker in ("{distance}", "{number}", "{street}", "{time}"))
    }
    assert required_cues.issubset(language_static)
assert 'MAGIC = b"ABV1"' in (builder / "scripts/abv_format.py").read_text(encoding="utf-8")
assert "'.abv'" in catalog and "'ABV1'" in catalog
assert "playCue(String cue)" in service
assert "_player.seek(cue.start)" in service
assert "playSequence(" not in service
assert "final Map<String, VoiceCue> cues" in catalog
assert "_readCues(meta['cues'])" in catalog
assert "displayName" in catalog
assert "distance(" not in voice_map
assert "cueForManeuver" in voice_map
assert "textForCue" in voice_map
assert "exit <= 20" in voice_map
assert "voice.playCue(VoicePackFa.cueForManeuver(" in home
assert "voice.playCue('off_route')" in home
assert "distanceMeters: distToNext" not in home
assert "voice.playSequence(" not in home
assert "_player.positionStream.listen(_stopAtCueBoundary)" in service
assert "_activeCueEnd = cue.end" in service
assert "_finishCueAtBoundary" in service
assert "VoicePackFa.textForCue(VoicePackFa.cueForManeuver(" in routing
assert "VoicePackFa.textForCue(VoicePackFa.cueForManeuver(" in offline_routing

print("single_voice_contract_ok")
