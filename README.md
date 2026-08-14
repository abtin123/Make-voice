# tts-sync — GitHub-hosted voice packs for a nav app

Free engine (edge-tts, no key) → one small `.nvb` file per phrase/language/
gender (audio + word-timing JSON packed, gzip-compressed) → published as
GitHub Release assets → app fetches `catalog.json` first, shows a language
picker (male/female, like a map-style picker), downloads only the `.nvb`
files the user actually picks.

## Setup

```
pip install -r requirements.txt
```

## Build everything

```
python scripts/batch.py --input examples/nav_phrases.json --out out
```

Produces:
```
out/turn_left/fa_female.nvb
out/turn_left/fa_male.nvb
out/turn_left/en_female.nvb
...
out/catalog.json
```

`examples/nav_phrases.json` ships ~25 core nav phrases in `fa en ar tr de fr
es ru`, each with a male + female voice (`scripts/tts_client.py` → `VOICES`,
20 languages mapped, add more the same way).

## Publish to GitHub (the "hosted, download-only" part)

Push the repo, then run the `build-and-publish-voicepacks` workflow (Actions
tab → Run workflow). It builds all `.nvb` files and `catalog.json`, then
publishes them as assets on a GitHub Release (`voicepacks-latest` by
default). No server needed — the app downloads straight from the release's
asset URLs.

## `.nvb` format (the "one file, small, proprietary" bundle)

```
magic 4B "NVB1" | json_len u32 | audio_len u32 | gzip(json) | gzip(mp3)
```
One file per phrase+lang+gender. Gzip roughly halves size again on top of
the already-compressed mp3+short-JSON. Read it with:
```
python scripts/extract_nvb.py out/turn_left/fa_female.nvb
```

## App flow

1. On first launch (or language-settings screen), fetch **only**
   `catalog.json` from the release — a few KB, instant.
2. Render language + gender picker from `catalog["languages"]`
   (`{"fa": {"genders": ["male","female"]}, ...}`) — same UX pattern as a
   map-style/theme picker.
3. When the user picks e.g. `fa` + `female`, download just the `.nvb` files
   listed under each phrase for that lang/gender (`catalog["phrases"][id][lang][gender]["file"]`).
4. To play: read the `.nvb` (magic → lengths → gunzip json → gunzip audio),
   decode the mp3, and use `words[].start/end` for sync-highlighted text
   during playback — timestamps are real engine word-boundary events, not
   estimated.

`catalog.json`:
```json
{
  "version": 1,
  "languages": {"fa": {"genders": ["male","female"]}, "en": {"genders": ["male","female"]}},
  "phrases": {
    "turn_left": {
      "fa": {
        "male":   {"file": "turn_left/fa_male.nvb",   "size_bytes": 9832},
        "female": {"file": "turn_left/fa_female.nvb", "size_bytes": 9510}
      }
    }
  }
}
```

## Single file, ad hoc

```
python scripts/generate.py --text "به مقصد نزدیک شدید" --lang fa --gender female --out out/route1
```

## Notes

- edge-tts calls a Microsoft-operated streaming endpoint at generation
  time (build-time only, in CI) — free and keyless, but not literally
  offline. The *published* `.nvb` files are fully static/offline for the app.
- If Microsoft changes the endpoint internals, bump the pinned version in
  `requirements.txt` (`pip install -U edge-tts`) — it's a reverse-engineered
  client, not a stability-guaranteed API.
