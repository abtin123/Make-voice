# Abtin Voice Tool
Builds AbtinMaps .abv voice packs (Microsoft Edge neural TTS, male/female, multi-language).

    pip install -r requirements.txt     # + ffmpeg on PATH
    python make_voice_pack.py --lang all --out voicepacks --base-url <release URL>
    python make_voice_pack.py --lang tr az --gender male
    python make_voice_pack.py --lang en --voice en_male=en-GB-RyanNeural
    python make_voice_pack.py --list-voices ar

Langs: fa en ar tr az ru de fr es. Output: <lang>_<gender>.abv + manifest.json.
Phrases live in dicts T / N at the top of make_voice_pack.py.
