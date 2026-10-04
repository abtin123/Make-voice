# Make-Voice

[English](#english) · [فارسی](#فارسی)

---

## English

A tool for building **navigation Voice Packs** for Abtin Maps using Microsoft Edge Neural TTS.

The project converts the fixed navigation-guidance phrases into binary `.abv` files for multiple languages and voices, so the app can download one Voice Pack per language/gender and play the cues inside it offline.

### Features

- Audio generation with `edge-tts` and Microsoft Edge Neural voices
- Female and male voices
- One `.abv` file per language and gender
- Start/end time of every cue stored in the manifest
- TTS output caching to avoid regenerating identical audio
- Automatic `manifest.json` generation
- Automatic publishing of Voice Packs to GitHub Releases
- Extract an `.abv` back to MP3 and JSON for testing and debugging
- Contract validation between the Voice Packs and the related parts of the app

### Languages and voices

| Code | Language | Female voice | Male voice |
|---|---|---|---|
| `fa` | Persian | `fa-IR-DilaraNeural` | `fa-IR-FaridNeural` |
| `en` | English | `en-US-AvaNeural` | `en-US-AndrewNeural` |
| `ar` | Arabic | `ar-SA-ZariyahNeural` | `ar-SA-HamedNeural` |
| `tr` | Turkish | `tr-TR-EmelNeural` | `tr-TR-AhmetNeural` |
| `de` | German | `de-DE-KatjaNeural` | `de-DE-ConradNeural` |
| `fr` | French | `fr-FR-DeniseNeural` | `fr-FR-HenriNeural` |
| `es` | Spanish | `es-ES-ElviraNeural` | `es-ES-AlvaroNeural` |
| `ru` | Russian | `ru-RU-SvetlanaNeural` | `ru-RU-DmitryNeural` |

By default all 8 languages × 2 genders are built, i.e. **16 ABV files**.

### Project structure

```text
Make-voice-main/
├── .github/
│   └── workflows/
│       ├── Extract.yml
│       ├── Fixmanifest.yml
│       ├── build-and-publish-voicepacks.yml
│       └── flatten-repo.yml
├── examples/
│   └── nav_phrases.json
├── scripts/
│   ├── abv_format.py
│   ├── build_single_voicepack.py
│   ├── extract_abv.py
│   ├── merge_single_manifest.py
│   ├── neural_tts_client.py
│   └── voice_catalog.py
├── tests/
│   └── validate_single_voice_contract.py
├── requirements.txt
└── README.md
```

### Installation

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
```

#### Linux / macOS

```bash
source .venv/bin/activate
```

#### Windows

```powershell
.venv\Scripts\activate
```

Then install the dependencies:

```bash
pip install -r requirements.txt
```

Main dependencies:

- `edge-tts` for Neural voice generation
- `mutagen` for detecting MP3 duration

> Generating audio requires network access to the Edge TTS service.

### Building Voice Packs

Build all languages and genders:

```bash
python scripts/build_single_voicepack.py \
  --input examples/nav_phrases.json \
  --out out \
  --languages all \
  --genders all \
  --speed 1.0 \
  --cache-dir out/.voice_build_cache
```

The output looks roughly like this:

```text
out/
├── fa_female.abv
├── fa_male.abv
├── en_female.abv
├── en_male.abv
├── ...
├── ru_female.abv
├── ru_male.abv
└── manifest.json
```

#### Building a specific language or gender

Persian only:

```bash
python scripts/build_single_voicepack.py \
  --languages fa \
  --genders all
```

Several languages:

```bash
python scripts/build_single_voicepack.py \
  --languages fa,en,tr \
  --genders female
```

Valid genders:

```text
female
male
all
```

Language codes:

```text
fa,en,ar,tr,de,fr,es,ru
```

#### Speed

The `--speed` parameter defaults to `1.0`.

Allowed range:

```text
0.5 to 1.8
```

Example:

```bash
python scripts/build_single_voicepack.py --speed 1.1
```

### Cues and phrases

The phrase source is:

```text
examples/nav_phrases.json
```

Example:

```json
{
  "turn_left": {
    "fa": "به چپ بپیچید",
    "en": "Turn left"
  }
}
```

The build script only includes fixed cues in a Voice Pack.

Cues containing variables such as the following are skipped, because they cannot be turned into fixed audio directly:

```text
{distance}
{number}
{street}
{time}
```

Cues for dynamic distances, such as `turn_left_in_...`, are also deliberately left out of the fixed Voice Pack.

The minimum required cues are:

```text
route_found
recalculating_route
off_route
arrived_destination
gps_signal_lost
gps_signal_restored
speed_camera_ahead
speed_bump_ahead
```

If any of these cues is missing for a language, the build for that language stops with an error.

### Full `nav_phrases.json` (169 cues × 8 languages)

The file is generated with `python scripts/gen_nav_phrases.py` (to change the phrases, edit that script and run it again).

- **Roundabouts:** `roundabout_take_exit_1..20` + `roundabout_take_exit_next` + `roundabout_enter` + `roundabout_continue` + `roundabout_u_turn`. Ordinals are written out **as words** everywhere (not `1st` / `1.` / `1ère` / `1ª` / `1-м`) because Edge reads those unreliably.
- **Distance:** there is no longer a full "In N meters turn left" cue. Short cues `in_20m … in_900m`, `in_1km`, `in_2km`, `in_100ft …`, `in_1mi` are played before the maneuver cue ("In two hundred meters," + "At the roundabout, take the second exit").
- **Highway:** `take_exit_1..15`, `take_exit_next`, `merge_onto_highway`, `exit_highway`, `highway_splits_*`.
- **Warnings:** speed camera, speed bump, police checkpoint (`police_checkpoint_ahead`), traffic, accident, fog, ice, flooding, and more.
- **Speed limits:** `speed_limit_30kmh … 130kmh` and `speed_limit_20mph … 70mph`.
- **Persian without digits:** all numbers in Persian text are written as words.

#### Pronunciation: voice-only override
Each cue can have an optional `tts` key. The `fa` text stays the clean card/display text, and only what is **spoken** changes:

```json
"roundabout_take_exit_2": {
  "fa": "در میدان، از خروجی دوم خارج شوید",
  "tts": { "fa": "در میدان، از خروجیِ دوم خارج شوید" }
}
```

Before changing the JSON, use `scripts/pronunciation_lab.py` to compare diacritics / half-spaces / elongation, etc.

### ABV format

An `.abv` file is a simple compressed container that keeps metadata and audio in a single file.

General structure:

```text
ABV1
├── json_len
├── audio_len
├── gzip(JSON metadata)
└── gzip(MP3 audio)
```

The metadata contains information such as:

```json
{
  "version": 2,
  "engine": "edge-neural",
  "lang": "fa",
  "locale": "fa-IR",
  "speaker": "دیلارا",
  "gender": "female",
  "voice_name": "fa-IR-DilaraNeural",
  "duration": 12.345,
  "cue_format": "seconds",
  "cues": {}
}
```

Each cue has a `start` and `end` in seconds, so the app can locate the wanted cue inside a single audio file.

### Manifest

After a build, this file is generated:

```text
out/manifest.json
```

Current schema:

```text
schema_version = 5
```

Each Voice Pack entry includes:

- file name
- display name
- language
- language code
- gender
- Edge TTS voice name
- file size
- download URL

If `--download-base` is given, the download URL of each file is built automatically.

Example:

```bash
python scripts/build_single_voicepack.py \
  --download-base "https://github.com/OWNER/REPO/releases/download/voicepacks-latest"
```

### Cache

To reduce time and the number of TTS requests, the result of each cue is cached.

The cache key is built from:

```text
cue + text + voice + speed
```

So if the text, voice or speed changes, the previous result is automatically not reused.

In GitHub Actions, the cache is kept at:

```text
out/.voice_build_cache
```

### Extracting and inspecting an ABV

To convert an `.abv` to MP3 and JSON:

```bash
python scripts/extract_abv.py out/fa_female.abv
```

Or choose the output path:

```bash
python scripts/extract_abv.py \
  out/fa_female.abv \
  --out debug/fa_female
```

Output:

```text
debug/fa_female.mp3
debug/fa_female.json
```

This tool is for testing and debugging Voice Packs.

### Running the contract test

To check the static contract:

```bash
python tests/validate_single_voice_contract.py
```

This test checks things such as Neural voices, the workflow structure, required cues and the Voice Pack file contract.

> Note: the existing test also references files from the `work/` part of the main app project. If that structure does not exist in your environment, the full test may not run.

### GitHub Actions

#### Build and Publish

This workflow builds and publishes the Voice Packs:

```text
.github/workflows/build-and-publish-voicepacks.yml
```

It runs via `workflow_dispatch` and has these inputs:

- `speed` — audio speed, default `1.0`
- `release_tag` — GitHub Release tag, default `voicepacks-latest`

Overall flow:

```text
Checkout
   ↓
Install Python dependencies
   ↓
Restore TTS cache
   ↓
Build all languages/genders
   ↓
Generate manifest.json
   ↓
Publish .abv + manifest.json
   ↓
GitHub Release
```

To run it from GitHub:

```text
Actions → build-and-publish-neural-voicepacks → Run workflow
```

#### Fix Manifest

File:

```text
.github/workflows/Fixmanifest.yml
```

Used to recover assets and rebuild the manifest from existing Releases; draft Releases are taken into account too.

#### Extract

File:

```text
.github/workflows/Extract.yml
```

Designed to extract a ZIP and commit the extracted files to the repository.

#### Flatten

File:

```text
.github/workflows/flatten-repo.yml
```

Used to move the contents of a nested folder up to the repository root.

### Publishing to a GitHub Release

To build and publish automatically:

1. Open the repository on GitHub.
2. Go to **Actions**.
3. Select the `build-and-publish-neural-voicepacks` workflow.
4. Click **Run workflow**.
5. Set the speed and `release_tag`.
6. Run the workflow.

On success, these files are placed in the Release:

```text
manifest.json
fa_female.abv
fa_male.abv
en_female.abv
en_male.abv
...
```

### Important notes

- Voice Packs are designed for fixed cues; distance, numbers, street names and time are not generated dynamically inside them.
- Changing `nav_phrases.json` changes the cache key of the changed cue.
- Before publishing, run a local build and the contract test.
- Files generated in `out/` should not be committed into the source code without a reason; they are published through GitHub Releases.
- `manifest.json` must match the actual Release files.
- The voice names in `voice_catalog.py` are the reference point for choosing the speaker of each language and gender.

### Quick summary

```bash
# Install
pip install -r requirements.txt

# Build all Voice Packs
python scripts/build_single_voicepack.py \
  --input examples/nav_phrases.json \
  --out out \
  --languages all \
  --genders all \
  --speed 1.0 \
  --cache-dir out/.voice_build_cache

# Inspect one ABV
python scripts/extract_abv.py out/fa_female.abv

# Run the test
python tests/validate_single_voice_contract.py
```

At its core this project is a pipeline that turns **fixed navigation phrases → Edge Neural TTS → cue-based MP3s → compressed ABV files → manifest → GitHub Release**.

---

<div dir="rtl">

## فارسی

ابزار ساخت **Voice Packهای ناوبری** برای Abtin Maps با استفاده از Microsoft Edge Neural TTS.

این پروژه متن‌های ثابت راهنمای مسیریابی را در زبان‌ها و صداهای مختلف به فایل‌های باینری `.abv` تبدیل می‌کند تا اپلیکیشن بتواند برای هر زبان/جنسیت یک Voice Pack واحد دریافت و به‌صورت آفلاین از cueهای داخل آن استفاده کند.

### قابلیت‌ها

- تولید صدا با `edge-tts` و Microsoft Edge Neural voices
- پشتیبانی از صدای زن و مرد
- ساخت یک فایل `.abv` برای هر زبان و جنسیت
- نگهداری زمان شروع/پایان هر cue داخل manifest
- cache کردن خروجی TTS برای جلوگیری از تولید مجدد صداهای یکسان
- تولید خودکار `manifest.json`
- انتشار خودکار Voice Packها به GitHub Releases
- امکان استخراج دوباره `.abv` به MP3 و JSON برای تست و دیباگ
- اعتبارسنجی قرارداد بین Voice Packها و بخش‌های مرتبط اپلیکیشن

### زبان‌ها و صداها

| کد | زبان | صدای زن | صدای مرد |
|---|---|---|---|
| `fa` | فارسی | `fa-IR-DilaraNeural` | `fa-IR-FaridNeural` |
| `en` | English | `en-US-AvaNeural` | `en-US-AndrewNeural` |
| `ar` | العربية | `ar-SA-ZariyahNeural` | `ar-SA-HamedNeural` |
| `tr` | Türkçe | `tr-TR-EmelNeural` | `tr-TR-AhmetNeural` |
| `de` | Deutsch | `de-DE-KatjaNeural` | `de-DE-ConradNeural` |
| `fr` | Français | `fr-FR-DeniseNeural` | `fr-FR-HenriNeural` |
| `es` | Español | `es-ES-ElviraNeural` | `es-ES-AlvaroNeural` |
| `ru` | Русский | `ru-RU-SvetlanaNeural` | `ru-RU-DmitryNeural` |

در حالت پیش‌فرض، تمام ۸ زبان × ۲ جنسیت ساخته می‌شوند؛ یعنی **۱۶ فایل ABV**.

### ساختار پروژه

```text
Make-voice-main/
├── .github/
│   └── workflows/
│       ├── Extract.yml
│       ├── Fixmanifest.yml
│       ├── build-and-publish-voicepacks.yml
│       └── flatten-repo.yml
├── examples/
│   └── nav_phrases.json
├── scripts/
│   ├── abv_format.py
│   ├── build_single_voicepack.py
│   ├── extract_abv.py
│   ├── merge_single_manifest.py
│   ├── neural_tts_client.py
│   └── voice_catalog.py
├── tests/
│   └── validate_single_voice_contract.py
├── requirements.txt
└── README.md
```

### نصب

Python 3.11 یا جدیدتر پیشنهاد می‌شود.

```bash
python -m venv .venv
```

#### Linux / macOS

```bash
source .venv/bin/activate
```

#### Windows

```powershell
.venv\Scripts\activate
```

سپس dependencyها را نصب کنید:

```bash
pip install -r requirements.txt
```

وابستگی‌های اصلی:

- `edge-tts` برای تولید صدای Neural
- `mutagen` برای تشخیص مدت فایل MP3

> تولید صدا نیازمند دسترسی شبکه به سرویس Edge TTS است.

### تولید Voice Pack

ساخت همه زبان‌ها و جنسیت‌ها:

```bash
python scripts/build_single_voicepack.py \
  --input examples/nav_phrases.json \
  --out out \
  --languages all \
  --genders all \
  --speed 1.0 \
  --cache-dir out/.voice_build_cache
```

خروجی تقریباً به این شکل خواهد بود:

```text
out/
├── fa_female.abv
├── fa_male.abv
├── en_female.abv
├── en_male.abv
├── ...
├── ru_female.abv
├── ru_male.abv
└── manifest.json
```

#### ساخت زبان یا جنسیت خاص

مثلاً فقط فارسی:

```bash
python scripts/build_single_voicepack.py \
  --languages fa \
  --genders all
```

چند زبان:

```bash
python scripts/build_single_voicepack.py \
  --languages fa,en,tr \
  --genders female
```

جنسیت‌های قابل استفاده:

```text
female
male
all
```

کدهای زبان:

```text
fa,en,ar,tr,de,fr,es,ru
```

#### تنظیم سرعت

پارامتر `--speed` به‌صورت پیش‌فرض `1.0` است.

محدوده مجاز:

```text
0.5 تا 1.8
```

مثلاً:

```bash
python scripts/build_single_voicepack.py --speed 1.1
```

### Cueها و متن‌ها

منبع متن‌ها در این فایل قرار دارد:

```text
examples/nav_phrases.json
```

نمونه:

```json
{
  "turn_left": {
    "fa": "به چپ بپیچید",
    "en": "Turn left"
  }
}
```

اسکریپت build فقط cueهای ثابت را وارد Voice Pack می‌کند.

Cueهای دارای متغیرهایی مثل موارد زیر برای تولید مستقیم صوت ثابت کنار گذاشته می‌شوند:

```text
{distance}
{number}
{street}
{time}
```

همچنین cueهای مربوط به فاصله‌های داینامیک، مانند `turn_left_in_...`، عمداً وارد Voice Pack ثابت نمی‌شوند.

حداقل cueهای موردنیاز عبارت‌اند از:

```text
route_found
recalculating_route
off_route
arrived_destination
gps_signal_lost
gps_signal_restored
speed_camera_ahead
speed_bump_ahead
```

اگر یکی از این cueها برای یک زبان وجود نداشته باشد، build همان زبان با خطا متوقف می‌شود.

### نسخهٔ کامل `nav_phrases.json` (۱۶۹ cue × ۸ زبان)

فایل با `python scripts/gen_nav_phrases.py` ساخته می‌شود (برای تغییر متن‌ها، همان اسکریپت را ویرایش و دوباره اجرا کنید).

- **میدان:** `roundabout_take_exit_1..20` + `roundabout_take_exit_next` + `roundabout_enter` + `roundabout_continue` + `roundabout_u_turn`. ترتیبی‌ها همه‌جا به‌صورت **حروف** نوشته شده‌اند (نه `1st` / `1.` / `1ère` / `1ª` / `1-м`) چون Edge آن‌ها را ناپایدار می‌خواند.
- **فاصله:** دیگر cue کامل «در N متر دیگر به چپ بپیچید» نداریم. cueهای کوتاه `in_20m … in_900m`، `in_1km`، `in_2km`، `in_100ft …`، `in_1mi` قبل از cue مانور پخش می‌شوند («در دویست متر دیگر،» + «در میدان، از خروجی دوم خارج شوید»).
- **بزرگراه:** `take_exit_1..15`، `take_exit_next`، `merge_onto_highway`، `exit_highway`، `highway_splits_*`.
- **هشدارها:** دوربین، سرعت‌گیر، ایست بازرسی (`police_checkpoint_ahead`)، ترافیک، تصادف، مه، یخ، آب‌گرفتگی و …
- **سرعت مجاز:** `speed_limit_30kmh … 130kmh` و `speed_limit_20mph … 70mph`.
- **فارسی بدون رقم:** همهٔ عددها در متن فارسی با حروف نوشته می‌شوند.

#### تلفظ: override فقط برای صدا
برای هر cue می‌توان کلید اختیاری `tts` گذاشت. متن `fa` همان متن تمیزِ کارت/نمایش می‌ماند و فقط چیزی که **خوانده می‌شود** عوض می‌شود:

```json
"roundabout_take_exit_2": {
  "fa": "در میدان، از خروجی دوم خارج شوید",
  "tts": { "fa": "در میدان، از خروجیِ دوم خارج شوید" }
}
```

برای مقایسهٔ حرکات/نیم‌فاصله/کشیده و … قبل از تغییر JSON از `scripts/pronunciation_lab.py` استفاده کنید.

### فرمت ABV

فایل `.abv` یک container ساده و فشرده است که metadata و audio را در یک فایل نگه می‌دارد.

ساختار کلی:

```text
ABV1
├── json_len
├── audio_len
├── gzip(JSON metadata)
└── gzip(MP3 audio)
```

Metadata شامل اطلاعاتی مانند این موارد است:

```json
{
  "version": 2,
  "engine": "edge-neural",
  "lang": "fa",
  "locale": "fa-IR",
  "speaker": "دیلارا",
  "gender": "female",
  "voice_name": "fa-IR-DilaraNeural",
  "duration": 12.345,
  "cue_format": "seconds",
  "cues": {}
}
```

هر cue دارای `start` و `end` بر حسب ثانیه است؛ بنابراین اپلیکیشن می‌تواند cue موردنظر را از یک فایل صوتی واحد پیدا کند.

### Manifest

پس از build، فایل زیر تولید می‌شود:

```text
out/manifest.json
```

Schema فعلی:

```text
schema_version = 5
```

هر Voice Pack شامل اطلاعاتی مانند:

- نام فایل
- نام نمایشی
- زبان
- کد زبان
- جنسیت
- نام voice در Edge TTS
- حجم فایل
- آدرس دانلود

اگر `--download-base` مشخص شود، آدرس دانلود برای هر فایل به‌صورت خودکار ساخته می‌شود.

مثال:

```bash
python scripts/build_single_voicepack.py \
  --download-base "https://github.com/OWNER/REPO/releases/download/voicepacks-latest"
```

### Cache

برای کاهش زمان و تعداد درخواست‌های TTS، نتیجه هر cue در cache ذخیره می‌شود.

کلید cache بر اساس این موارد ساخته می‌شود:

```text
cue + text + voice + speed
```

بنابراین اگر متن، voice یا سرعت تغییر کند، نتیجه قبلی به‌صورت خودکار قابل استفاده نخواهد بود.

در GitHub Actions، cache در مسیر زیر نگهداری می‌شود:

```text
out/.voice_build_cache
```

### استخراج و بررسی یک ABV

برای تبدیل `.abv` به MP3 و JSON:

```bash
python scripts/extract_abv.py out/fa_female.abv
```

یا تعیین مسیر خروجی:

```bash
python scripts/extract_abv.py \
  out/fa_female.abv \
  --out debug/fa_female
```

خروجی:

```text
debug/fa_female.mp3
debug/fa_female.json
```

این ابزار برای تست و دیباگ کردن Voice Packها کاربرد دارد.

### اجرای تست قرارداد

برای بررسی static contract:

```bash
python tests/validate_single_voice_contract.py
```

این تست مواردی مانند voiceهای Neural، ساختار workflow، cueهای ضروری و قرارداد فایل‌های Voice Pack را بررسی می‌کند.

> توجه: تست موجود به فایل‌های بخش `work/` از پروژه اصلی اپلیکیشن نیز reference دارد. بنابراین اگر آن ساختار در محیط شما وجود نداشته باشد، ممکن است تست کامل قابل اجرا نباشد.

### GitHub Actions

#### Build و Publish

Workflow زیر برای ساخت و انتشار Voice Packها استفاده می‌شود:

```text
.github/workflows/build-and-publish-voicepacks.yml
```

این workflow با `workflow_dispatch` اجرا می‌شود و ورودی‌های زیر را دارد:

- `speed` — سرعت تولید صدا، پیش‌فرض `1.0`
- `release_tag` — تگ GitHub Release، پیش‌فرض `voicepacks-latest`

فرآیند کلی:

```text
Checkout
   ↓
Install Python dependencies
   ↓
Restore TTS cache
   ↓
Build all languages/genders
   ↓
Generate manifest.json
   ↓
Publish .abv + manifest.json
   ↓
GitHub Release
```

برای اجرای آن از GitHub:

```text
Actions → build-and-publish-neural-voicepacks → Run workflow
```

#### Fix Manifest

فایل:

```text
.github/workflows/Fixmanifest.yml
```

برای بازیابی assetها و بازسازی manifest از Releaseهای موجود استفاده می‌شود و Releaseهای draft را نیز در نظر می‌گیرد.

#### Extract

فایل:

```text
.github/workflows/Extract.yml
```

برای extract کردن ZIP و commit کردن فایل‌های استخراج‌شده در repository طراحی شده است.

#### Flatten

فایل:

```text
.github/workflows/flatten-repo.yml
```

برای خارج کردن محتوای یک پوشه تو‌در‌تو و انتقال آن به root repository استفاده می‌شود.

### انتشار در GitHub Release

برای build و انتشار خودکار:

1. repository را در GitHub باز کنید.
2. وارد بخش **Actions** شوید.
3. workflow مربوط به `build-and-publish-neural-voicepacks` را انتخاب کنید.
4. گزینه **Run workflow** را بزنید.
5. سرعت و `release_tag` را تنظیم کنید.
6. workflow را اجرا کنید.

در صورت موفقیت، فایل‌های زیر در Release قرار می‌گیرند:

```text
manifest.json
fa_female.abv
fa_male.abv
en_female.abv
en_male.abv
...
```

### نکات مهم

- Voice Packها برای cueهای ثابت طراحی شده‌اند؛ فاصله، شماره، نام خیابان و زمان به‌صورت داینامیک داخل آن‌ها تولید نمی‌شود.
- تغییر `nav_phrases.json` باعث تغییر کلید cache مربوط به cue تغییرکرده می‌شود.
- قبل از انتشار، بهتر است build محلی و تست contract اجرا شود.
- فایل‌های تولیدشده در `out/` نباید بدون دلیل داخل source code commit شوند؛ انتشار آن‌ها از طریق GitHub Release انجام می‌شود.
- `manifest.json` باید با فایل‌های واقعی Release هماهنگ باشد.
- نام voiceها در `voice_catalog.py` نقطه مرجع انتخاب speaker برای هر زبان و جنسیت است.

### خلاصه سریع

```bash
# نصب
pip install -r requirements.txt

# ساخت همه Voice Packها
python scripts/build_single_voicepack.py \
  --input examples/nav_phrases.json \
  --out out \
  --languages all \
  --genders all \
  --speed 1.0 \
  --cache-dir out/.voice_build_cache

# بررسی یک ABV
python scripts/extract_abv.py out/fa_female.abv

# اجرای تست
python tests/validate_single_voice_contract.py
```

این پروژه در اصل یک pipeline برای تبدیل **متن‌های ثابت ناوبری → Edge Neural TTS → MP3های cue-based → فایل‌های فشرده ABV → manifest → GitHub Release** است.

</div>
