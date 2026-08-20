# آبتین‌مپ — سازندهٔ صوت یک‌تکه

هر گویندهٔ فارسی یک فایل `.nvb` دانلودی تولید می‌کند. این فایل شامل یک MP3
یک‌تکه و نقشهٔ زمانی فرمان‌ها است؛ اپ فقط با حرکت به ابتدای cue و توقف در
انتهای آن فرمان دلخواه را پخش می‌کند. فایل جمله‌ای جداگانه، چسباندن فایل در
اپ و اعلام فاصله وجود ندارد.

## پیش‌نیاز

در Secrets مخزن GitHub، مقدار `AVASHO_GATEWAY_TOKEN` را با gateway-token سرویس
Avasho قرار دهید. این کلید هرگز در سورس یا فایل خروجی ذخیره نمی‌شود.

```bash
pip install -r requirements.txt
export AVASHO_GATEWAY_TOKEN='...'
```

## ساخت محلی

```bash
python scripts/build_single_voicepack.py \
  --input examples/nav_phrases.json \
  --out out/shahrzad \
  --speaker shahrzad \
  --speed 1.0
```

گوینده‌های پشتیبانی‌شدهٔ Avasho عبارت‌اند از:

```text
kiani nourai dara parviz bahman farhad shahriyar ariya
sara pune bahar shahrzad sheyda shirin
```

## انتشار

از Actions، workflow `build-and-publish-single-voicepacks` را اجرا کنید. ورودی
`speakers` می‌تواند یک یا چند گوینده باشد؛ مثلاً `shahrzad sara`. خروجی release
دارای `manifest.json` و یک `.nvb` مستقل برای هر گوینده است، مانند:

```text
fa_shahrzad.nvb
fa_sara.nvb
manifest.json
```

## فرمت NVB

```text
magic 4B "NVB1" | json_len u32 | audio_len u32 | gzip(json) | gzip(mp3)
```

فرادادهٔ نسخهٔ ۲ شامل `cues` است. هر cue دارای `start`، `end` و `text` است و
به زمان ثانیه در MP3 یک‌تکه اشاره می‌کند. cueهای فاصله‌دار عمداً در فهرست ساخت
نیامده‌اند؛ فاصله فقط روی رابط نقشه نمایش داده می‌شود.
