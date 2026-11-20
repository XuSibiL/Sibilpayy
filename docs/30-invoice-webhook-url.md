# ۳۰ — آدرسِ تأییدِ هر فاکتور: `webhook_url`

> این سند برای **هر** بات، سایت و اپ است؛ هیچ کتابخانهٔ خاصی لازم نیست.
> پیش‌نیازِ امضا در [۲۹ — دریافت خبر در هر بات](29-receive-a-webhook.md) آمده است.

## چرا

تا امروز خبرِ «پرداخت شد» فقط به دامنه‌ای می‌رفت که خودِ سیبیل‌پی آن را کشف می‌کرد.
از این نسخه، **سازندهٔ فاکتور** می‌تواند مستقیماً بگوید تأییدیه کجا برود:

```http
POST /api/v1/invoices
Authorization: Bearer sp_live_xxx
Content-Type: application/json

{
  "amount_rial": 900000,
  "order_id": "sp-1234",
  "description": "سفارش ۱۲۳۴",
  "webhook_url": "https://shop.example.com/payment/sibilpay_webhook.php"
}
```

`webhook_url` **اختیاری** است. فاکتور بدونِ آن دقیقاً مثلِ قبل ساخته می‌شود
(سازگاریِ کامل با همهٔ کدهای قدیمی). اگر فیلد ناشناخته‌ای بفرستید، سیبیل‌پی آن را
نادیده می‌گیرد و فاکتور باز هم ساخته می‌شود — ساختِ فاکتور هیچ‌وقت به‌خاطرِ فیلدِ
اضافه شکست نمی‌خورد.

نام‌های پذیرفته‌شده: `webhook_url` و `webhook`.

## اولویتِ مقصدِ تأیید

۱. `invoice.webhook_url` — اگر سازنده داده باشد.
۲. مقصدِ کشف/ذخیره‌شدهٔ همان دامنه (رفتارِ قبلی، برای فاکتورهای قدیمی).
۳. اگر هیچ‌کدام نبود، به صاحبِ فروشگاه اطلاع داده می‌شود.

## پاسخِ ساختِ فاکتور

```json
{
  "ok": true,
  "data": {
    "id": "inv_...",
    "status": "pending",
    "amount_rial": 900000,
    "payable_rial": 900137,
    "short_code": "7F3K9Q",
    "payment_url": "https://sibilpay.ir/pay/card/inv_...",
    "short_payment_url": "https://sibilpay.ir/pay/inv_...",
    "webhook_url": "https://shop.example.com/payment/sibilpay_webhook.php"
  }
}
```

`webhook_url` در پاسخ هم برمی‌گردد تا بتوانید مطمئن شوید همان چیزی است که خواستید.
مبلغی که در تأییدیه می‌آید `data.amount_rial` است (مبلغِ اسمیِ فاکتور) و
`payable_rial` فقط مبلغِ قابلِ واریز با عددِ یکتا است.

## سه کارِ اجباری در بات/سایت/اپ

۱. **امضا را چک کن** (سند ۲۹):

```
X-SIBILPAY-Signature: t=<unix>,v1=hex(HMAC_SHA256(secret, "<t>." + raw_body))
```

کلید = کلیدِ همان مقصد (endpoint secret)، پنجرهٔ زمانی ۳۰۰ ثانیه، مقایسهٔ
time-constant. اگر امضا نبود یا غلط بود: `401` بده، فاکتور را تأیید **نکن**.

۲. **تکرارناپذیر باش**: با `X-SIBILPAY-Delivery` یا `data.id` پرداخت را یک‌بار ثبت کن.

۳. **سریع جواب بده**: هر `2xx` زیرِ ۱۰ ثانیه = تحویل شد. کارِ سنگین را در صف بگذار.

## پاسخ‌ها و تلاشِ دوباره

| پاسخِ شما | معنی برای سیبیل‌پی |
|---|---|
| `200/201/202/204` | تحویل شد، تمام |
| `401` / `403` | امضا رد شد → تا ۸ بار دیگر تلاش می‌شود (۵ ثانیه تا ۱ ساعت) |
| `4xx` دیگر | اشتباهِ دائمی → توقف |
| `5xx` / تایم‌اوت | تا ۸ بار دیگر تلاش می‌شود |
| `200 {"ok":false}` | خطای منطقی؛ بدنه را برای پشتیبانی نگه دار |

همان فاکتور حداکثر یک‌بار «تحویل‌شده» ثبت می‌شود؛ تلاشِ ناموفق جلوی ارسالِ
بعدی را نمی‌گیرد.

## بدنهٔ تأییدیه (خلاصه)

```json
{
  "event": "invoice.paid",
  "created_at": "2026-11-11T10:00:00+00:00",
  "livemode": true,
  "data": {
    "id": "inv_...",
    "object": "invoice",
    "status": "paid",
    "amount_rial": 900000,
    "paid_amount_rial": 900000,
    "payable_rial": 900137,
    "order_id": "sp-1234",
    "short_code": "7F3K9Q",
    "test_mode": false,
    "paid_at": "2026-11-11T10:00:00+00:00",
    "store": {"id": "str_...", "slug": "shop", "name": "فروشگاه"}
  }
}
```

## تستِ سریع

```bash
curl -s -X POST "$BASE/api/v1/invoices" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"amount_rial":1000,"order_id":"sp-test","webhook_url":"https://your-host/hook.php"}'
```

بعد پرداخت را شبیه‌سازی کن (`/api/v1/invoices/{id}/simulate`) و ببین روی
`your-host/hook.php` چه می‌رسد. اگر `401` گرفتی، یعنی امضا/کلیدِ مقصد غلط است.
