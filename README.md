# tts-sync

Text → natural voice audio + word-synced JSON → single compact bundle, for navigation-app playback. ElevenLabs `eleven_multilingual_v2`, 20+ languages, one continuous audio stream per phrase (no chunking) for smooth playback.

## Setup

```
pip install -r requirements.txt
export ELEVENLABS_API_KEY=xxx
export ELEVENLABS_VOICE_ID=xxx   # optional, defaults to a multilingual voice
```

## Single phrase

```
python scripts/generate.py --text "به مقصد نزدیک شدید" --lang fa --out out/route1
```

Outputs:
- `out/route1.mp3` — 64kbps compact audio
- `out/route1.json` — word + character level timestamps
- `out/route1.bundle.zip` — both packed together for app download

## Many languages at once

```
python scripts/batch.py --input examples/texts.json --out out/route1
```

Outputs one folder per language plus `manifest.zip` containing every mp3+json.

## JSON shape

```json
{
  "version": 1,
  "lang": "fa",
  "text": "...",
  "duration": 2.14,
  "words": [{"word": "به", "start": 0.0, "end": 0.18}, ...],
  "characters": [{"c": "ب", "s": 0.0, "e": 0.05}, ...]
}
```
`words` is what the nav app should use for sync highlighting; `characters` is kept for finer-grained needs.

## GitHub Actions

Add repo secrets `ELEVENLABS_API_KEY` (and optionally `ELEVENLABS_VOICE_ID`), then run the `generate-tts` workflow manually (Actions tab → Run workflow), pointing `input_json` at any `{lang: text}` file in the repo. Download the `tts-output` artifact when it finishes.
