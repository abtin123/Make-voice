#!/usr/bin/env python3
"""Static contract checks: nav_phrases.json <-> builder <-> Flutter cue mapping.

Usage: python tests/validate_single_voice_contract.py [path/to/flutter/project]
The Flutter checks are skipped when the project path does not exist.
"""
import json
import re
import sys
from pathlib import Path

builder = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(builder / "scripts"))
from voice_catalog import GENDERS, VOICE_LANGUAGES  # noqa: E402

LANGS = tuple(VOICE_LANGUAGES)
assert LANGS == ("fa", "en", "ar", "tr", "de", "fr", "es", "ru")
assert tuple(GENDERS) == ("female", "male")

data = json.loads((builder / "examples/nav_phrases.json").read_text(encoding="utf-8"))
single = (builder / "scripts/build_single_voicepack.py").read_text(encoding="utf-8")

# 1) every cue has every language, no leftover placeholders
for cue, texts in data.items():
    for lang in LANGS:
        text = texts.get(lang)
        assert isinstance(text, str) and text.strip(), f"{cue}.{lang} is empty"
        assert not re.search(r"[{}]", text), f"{cue}.{lang} still has a placeholder"
# 2) ordinals must be words (digits/suffixes like 1st, 1., 1ère, 1ª are read badly by Edge TTS)
for i in range(1, 21):
    for lang in LANGS:
        assert not re.search(r"\d", data[f"roundabout_take_exit_{i}"][lang]), f"digit in roundabout exit {i}/{lang}"
for lang in LANGS:  # Persian never contains digits
    for cue, texts in data.items():
        assert not re.search(r"\d", texts["fa"]), f"digit in fa text of {cue}"
# 3) cue families the app relies on
for i in range(1, 21):
    assert f"roundabout_take_exit_{i}" in data
for cue in ("roundabout_take_exit_next", "roundabout_enter", "turn_left", "turn_right", "u_turn",
            "approaching_destination", "arrived_destination", "police_checkpoint_ahead",
            "in_20m", "in_100m", "in_200m", "in_500m", "in_900m", "in_1km"):
    assert cue in data, cue
# 4) builder contract
assert "REQUIRED_CUES" in single and '"engine": "edge-neural"' in single
assert '"schema_version": 5' in single and "DISTANCE_CUE_PREFIXES" not in single
assert 'output = out_dir / f"{language.code}_{gender}.abv"' in single
assert 'MAGIC = b"ABV1"' in (builder / "scripts/abv_format.py").read_text(encoding="utf-8")

# 5) Flutter side (optional)
project = Path(sys.argv[1]) if len(sys.argv) > 1 else builder.parent / "work"
if project.exists():
    fa = (project / "lib/features/voice_settings/data/voice_pack_fa.dart").read_text(encoding="utf-8")
    svc = (project / "lib/features/voice_settings/data/voice_service.dart").read_text(encoding="utf-8")
    home = (project / "lib/features/map/presentation/home_screen.dart").read_text(encoding="utf-8")
    for cue in re.findall(r"'((?:turn|keep|roundabout|merge|exit|destination|approaching|arrived|continue|route|start|in)_[a-z_0-9]*|u_turn)'", fa):
        assert cue in data or cue.endswith("_"), f"Dart uses unknown cue: {cue}"
    assert "cueChainForManeuver" in fa and "distancePrefixCue" in fa
    assert "playGuidance" in svc and "_cueDone" in svc
    assert "playGuidance(" in home
print("single_voice_contract_ok")
