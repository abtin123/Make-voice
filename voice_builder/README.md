# آبتین‌مپ — سازندهٔ صوت یک‌تکه

هر گویندهٔ فارسی یک فایل `.abv` دانلودی تولید می‌کند. این فایل شامل یک MP3
یک‌تکه و نقشهٔ زمانی فرمان‌ها است؛ اپ فقط با حرکت به ابتدای cue و توقف در
انتهای آن فرمان دلخواه را پخش می‌کند. فایل جمله‌ای جداگانه، چسباندن فایل در
اپ و اعلام فاصله وجود ندارد.

هر اجرای سازنده، گویندهٔ ساخته‌شده را به `manifest.json` اضافه یا همان ورودی
را به‌روزرسانی می‌کند؛ ساخت گویندهٔ بعدی، گوینده‌های قبلی را حذف نمی‌کند.
فیلد `display_name` نام قابل‌نمایش گوینده است و اپ همین نام را به‌جای نام فنی
فایل در فهرست دانلود و انتخاب صوت نشان می‌دهد.

## پیش‌نیاز

در Secrets مخزن GitHub فقط مقدار `AVASHO_GATEWAY_TOKEN` را قرار دهید. سازنده
پیش از درخواست `POST /request` یک نشست موقت ایجاد می‌کند و CSRF متناظر را از
header، پاسخ یا cookie درگاه می‌خواند. این نشست و توکن فقط در حافظهٔ همان اجرا
هستند و در سورس یا فایل خروجی ذخیره نمی‌شوند.

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
دارای `manifest.json` و یک `.abv` مستقل برای هر گوینده است، مانند:

```text
fa_shahrzad.abv
fa_sara.abv
manifest.json
```

## فرمت ABV

```text
magic 4B "ABV1" | json_len u32 | audio_len u32 | gzip(json) | gzip(mp3)
```

فرادادهٔ نسخهٔ ۲ شامل `cues` است. هر cue دارای `start`، `end` و `text` است و
به زمان ثانیه در MP3 یک‌تکه اشاره می‌کند. cueهای فاصله‌دار عمداً در فهرست ساخت
نیامده‌اند؛ فاصله فقط روی رابط نقشه نمایش داده می‌شود.
