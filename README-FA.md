# LectureFlow — اپ اندروید (TWA)

[English](README.md) | فارسی

اپ اندروید [LectureFlow](https://lf.kiaashkan.workers.dev/) که به‌صورت
**Trusted Web Activity (TWA)** ساخته شده: یک پوسته‌ی رسمی و سبک گوگل دور
وب‌اپ LectureFlow (PWA). اپ هیچ منطق تکراری از سایت ندارد — سایت زنده را
تمام‌صفحه باز می‌کند، پس **هر به‌روزرسانی سایت فوراً به‌روزرسانی اپ است**.
یک کدبیس، یک دیپلوی.

- پکیج: `ir.kiaashkan.lectureflow`
- نسخه: 1.0.6 (versionCode 7)
- حداقل اندروید: 5.0 (API 21)
- ساخته‌شده با [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap)
  از روی مانیفست وب‌اپ سایت؛ تنظیمات در `twa-manifest.json` است.
- دانلود: فایل APK امضاشده ضمیمه‌ی هر
  [ریلیز گیت‌هاب](https://github.com/kiaashkan/LectureFlow-app/releases)
  است (آخرین: v1.0.6). صفحه‌ی شروع اپ از حالت روشن/تیره‌ی سیستم پیروی می‌کند.

## پیش‌نیاز تمام‌صفحه (Digital Asset Links)

برای اینکه اپ بدون نوار آدرس مرورگر باز شود، سایت باید فایل
`/.well-known/assetlinks.json` را سرو کند و دامنه را به کلید امضای این اپ
وصل کند. این اندپوینت در نسخه‌ی **v3.9.2** ورکر LectureFlow اضافه شد، با
اثر انگشت SHA-256 گواهی انتشار:

```
CD:CF:5E:C4:01:1E:15:88:BC:3A:16:17:F4:D1:15:89:D3:79:3F:E1:C8:1B:85:DC:ED:A9:1F:42:9B:B5:9E:3A
```

اگر کلید امضا روزی عوض شود، اثر انگشت داخل ورکر (و این اپ) هم باید به‌روز
شود، وگرنه اپ به Custom Tab برمی‌گردد.

## کلید امضا

کی‌استور انتشار **در این ریپو نیست**. بیرون از پروژه نگه داشته می‌شود
(پوشه‌ی کلیدهای KiA، آلیاس `lectureflow`، گواهی CN=KiA, O=LectureFlow) —
همان الگوی EditNote. هیچ‌وقت کی‌استور را کامیت نکنید.

## بیلد

مسیر معمول (هر ماشینی با JDK 17 + Android SDK):

```bash
npm i -g @bubblewrap/cli
bubblewrap build        # reads twa-manifest.json, produces signed APK + AAB
```

فایل APK ریلیز v1.0.0 با پایپ‌لاین دستی داخل `manual-build/` ساخته شد
(`build_manual.py`: ‏aapt2 + javac + d8 + apksigner و `resolve_deps.py`
برای گرفتن گراف وابستگی‌های AndroidX) چون دیمون Gradle روی ماشین بیلد
اجرا نمی‌شد. خروجی یک APK انتشار استاندارد است که با `apksigner verify`
راستی‌آزمایی شده (اثر انگشت گواهی در بالا).

### بیلد از همین ریپو (پایپ‌لاین دستی)

پیش‌نیازها: JDK 17، ‏Android SDK (پلتفرم 36، بیلدتولز 36.1.0) و
Python 3 با Pillow. کی‌استور انتشار در این ریپو نیست (بخش «کلید امضا» در
بالا)؛ قبل از بیلد، `KS`/`PWFILE` را در `manual-build/build_manual.py`
به کی‌استور خودتان اشاره دهید.

```bash
python3 manual-build/resolve_deps.py   # downloads the AndroidX deps (manual-build/deps/)
python3 manual-build/build_manual.py   # produces the signed LectureFlow-vX.Y.Z.apk
```

همه‌ی تصاویر لانچر، آداپتیو، اسپلش (روشن و شب) و نوتیفیکیشن را خود بیلد
از روی فایل‌های اصلی آیکون در `icons/` می‌سازد، پس هیچ تصویر آماده‌ای در
گیت نگه داشته نمی‌شود. خود فایل‌های APK هم دارایی ریلیزند، نه فایل ریپو
(نگاه کنید به `.gitignore`).

## نکته برای کاربرانی که از اپ قدیمی (قبل از ۲۰۲۶) ارتقا می‌دهند

اپ قدیمی LectureFlow با کلید دیگری امضا شده بود، پس اندروید اجازه نمی‌دهد
این نسخه رویش نصب شود. اول اپ قدیمی را حذف کنید، بعد این APK را نصب کنید.
