<div dir="rtl" align="right">

# ۱۶ — سه دامنه، یک فروشگاه: وب‌هوکِ چندمقصدی

> **مسئله‌ای که این سند جواب می‌دهد:** «سه بات دارم، هر کدام روی دامنهٔ خودش؛ ولی
> فقط یکی از آن‌ها خبرِ پرداخت را می‌گیرد — یا هر سه، سه بار خبر می‌گیرند.»
> فروشگاه یکی است، دامنه‌ها سه‌اند.

---

## ۰) چرا قبلاً نمی‌شد

هر فروشگاه فقط **یک** `webhook_url` داشت. پس سه باتِ سه دامنه ناچار بودند یک آدرسِ
مشترک بدهند؛ نتیجه یکی از این دو بود:

- فقط یکی از بات‌ها خبر می‌گرفت و دو تای دیگر منتظر می‌ماندند، یا
- هر سه به یک آدرس می‌زدند و پیامِ «پرداخت تأیید شد» سه بار می‌آمد،
- یا بدتر: امضای یک بات برای باتِ دیگر معنی نداشت و هر سه «امضای نامعتبر» می‌گرفتند.

## ۱) حالا: تا سه مقصد، هر کدام مستقل

- هر فروشگاه می‌تواند تا **۳ مقصدِ وب‌هوک** داشته باشد؛ هر مقصد برچسب، آدرس و
  **کلیدِ امضای خودش** (`whsec_…`) را دارد.
- هر **کلیدِ API** به یکی از این مقصدها بسته می‌شود.
- هر **فاکتور** موقعِ ساخت ثبت می‌کند از کدام مقصد آمده (`webhook_endpoint`).
- هنگامِ تأیید، فقط **همان یک آدرس** فراخوانی می‌شود؛ بقیه هیچ پیامی نمی‌گیرند.
- امضا با کلیدِ همان مقصد ساخته می‌شود، پس هر بات فقط امضای خودش را می‌پذیرد.

> سازگاری: اگر از قبل `webhook_url` داشتی، همان **خودکار** مقصدِ اول می‌شود. لازم
> نیست چیزی را دستی مهاجرت بدهی و هیچ اتصالی قطع نمی‌شود.

## ۲) API

همهٔ این مسیرها با هدرِ `X-Admin-Token` کار می‌کنند.

### دیدنِ مقصدها

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
     "$SERVER/api/v1/admin/stores/$STORE_ID/webhooks"
```

```json
{"success": true, "data": {
  "max": 3,
  "endpoints": [
    {"id": "ep1", "label": "mirza", "url": "https://mirza.example/hook",
     "enabled": true, "secret_masked": "whsec_ab12…"}
  ]
}}
```

### ثبت یا جایگزینیِ مقصدها (حداکثر ۳)

```bash
curl -X PUT -H "X-Admin-Token: $ADMIN_TOKEN" -H "Content-Type: application/json" \
     -d '{"endpoints":[{"label":"mirza","url":"https://mirza.example/hook"},
                       {"label":"sibilpay-bot","url":"https://bot.example/hook"},
                       {"label":"site","url":"https://shop.example/hook"}]}' \
     "$SERVER/api/v1/admin/stores/$STORE_ID/webhooks"
```

- فهرستِ تازه **جایگزین** فهرستِ قبلی می‌شود.
- هر مقصدی که کلید نداشته باشد، یک `whsec_…` تازه می‌گیرد؛ کلیدِ قبلی دست‌نخورده می‌ماند.
- بیشتر از سه مورد پذیرفته نمی‌شود؛ `enabled:false` مقصد را ساکت می‌کند.
- `url` باید با `http://` یا `https://` شروع شود.

### دیدنِ کلیدهای API و اینکه هر کدام به کدام مقصد بسته است

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
     "$SERVER/api/v1/admin/stores/$STORE_ID/api-keys"
```

### بستنِ یک کلید به یک مقصد

```bash
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" -H "Content-Type: application/json" \
     -d '{"endpoint":"ep2"}' \
     "$SERVER/api/v1/admin/api-keys/$KEY_ID/webhook"
```

از این لحظه، هر فاکتوری که با این کلید ساخته شود، فقط به همان مقصد خبر می‌دهد.
`{"endpoint": null}` کلید را آزاد می‌کند و برمی‌گردد به مقصدِ اول.

## ۳) آنچه در وب‌هوک می‌رسد

هدرها:

```
X-SIBILPAY-Signature: <HMAC-SHA256 با کلیدِ همان مقصد>
X-SIBILPAY-Event: invoice.paid
X-SIBILPAY-Delivery: whd_…
```

بدنه همان بدنهٔ همیشگی است؛ فقط برای اینکه بدانی این پیام از کدام مقصد آمده،
شناسهٔ مقصد داخلِ مسیرِ ارسال (`webhook_deliveries.endpoint_id`) ثبت می‌شود و در
پنل/دیتابیس قابلِ بررسی است.

## ۴) بررسیِ امضا

```python
import hmac, hashlib
expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
ok = hmac.compare_digest(expected, request.headers["X-SIBILPAY-Signature"])
```

## ۵) خطاهای رایج

| کد | معنی | کار |
|---|---|---|
| `UNKNOWN_ENDPOINT` | مقصدی که می‌خواهی کلید را به آن ببندی، در این فروشگاه ثبت نشده | اول `PUT .../webhooks` |
| `STORE_NOT_FOUND` | شناسهٔ فروشگاه غلط | `GET /api/v1/admin/stores` |
| `KEY_NOT_FOUND` | شناسهٔ کلید غلط | `GET .../api-keys` |

## ۶) کارمزد: فقط فروشگاهِ اصلی

هر مالک یک «فروشگاهِ اصلی» دارد (اولین فروشگاهی که ساخته، مثل `MR SIBIL`) و
فقط همان کارمزد دارد؛ بقیهٔ فروشگاه‌ها فروشگاهِ معمولی‌اند و `fee_bps = 0`.
کارتِ کیف پولِ کارمزد هم همان کارتِ فروشگاهِ اصلی است، پس پولِ کارمزد و پولِ
فروش، دو کارتِ جدا دارند و قاطی نمی‌شوند.

</div>
