#!/usr/bin/env python3
"""Static contract checks for Avasho one-file voice packs and Flutter cues."""

import json
from pathlib import Path


builder = Path(__file__).resolve().parents[1]
project = builder.parent / "work"
avasho = (builder / "scripts/avasho_client.py").read_text(encoding="utf-8")
single = (builder / "scripts/build_single_voicepack.py").read_text(encoding="utf-8")
workflow = (builder / ".github/workflows/build-and-publish-voicepacks.yml").read_text(encoding="utf-8")
phrases = (builder / "examples/nav_phrases.json").read_text(encoding="utf-8")
service = (project / "lib/features/voice_settings/data/voice_service.dart").read_text(encoding="utf-8")
catalog = (project / "lib/features/voice_settings/data/voice_pack_catalog.dart").read_text(encoding="utf-8")
voice_map = (project / "lib/features/voice_settings/data/voice_pack_fa.dart").read_text(encoding="utf-8")
home = (project / "lib/features/map/presentation/home_screen.dart").read_text(encoding="utf-8")

assert '"/request"' in avasho and '"/track/{job_id}"' in avasho and '"/download/{job_id}"' in avasho
assert '"timestamp": True' in avasho
assert "max_words_per_request = 1000" in avasho
assert "at most 1000 words" in avasho and "_split_for_requests" in avasho
assert "csrf_token: str = \"\", session_cookie: str = \"\"" in avasho
assert '"x-csrf-token"' in avasho and '"x-xsrf-token"' in avasho
assert "_bootstrap_session" in avasho and "CookieJar" in avasho
assert 'for path in ("/download", "", "/", "/csrf", "/csrf-token")' in avasho
assert 'if self._session_cookie:' in avasho and 'headers["cookie"]' in avasho
assert 'if self._csrf_token:' in avasho
assert '"origin": self._origin' in avasho and '"referer": f"{self.base_url}/"' in avasho
assert 'if error.code in {401, 403}:' in avasho
assert '"--csrf-env"' in single and "override اختیاری CSRF" in single
assert '"--session-cookie-env"' in single and "override اختیاری کوکی نشست" in single
assert '"display_name"' in single and "_update_manifest" in single
assert '"schema_version": 4' in single
phrase_data = json.loads(phrases)
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
assert "AVASHO_GATEWAY_TOKEN" in workflow
assert "AVASHO_CSRF_TOKEN" not in workflow and "AVASHO_SESSION_COOKIE" not in workflow
assert 'test -n "$AVASHO_GATEWAY_TOKEN"' in workflow
assert "actions/cache@v4" in workflow and "voice_build_cache" in workflow
assert "edge-tts" not in workflow
assert "merge_single_manifest.py" not in workflow
assert 'name = f"fa_{speaker}.abv"' in single
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
assert "exit <= 20" in voice_map
assert "voice.playCue(VoicePackFa.cueForManeuver(" in home
assert "voice.playCue('off_route')" in home
assert "distanceMeters: distToNext" not in home
assert "voice.playSequence(" not in home

print("single_voice_contract_ok")
