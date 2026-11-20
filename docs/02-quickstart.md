# ۰۲ — شروع سریع، ۱۵ دقیقه تا اولین پرداخت

هدف: ساختِ یک فاکتور، باز کردنِ لینکِ پرداخت و مشاهدهٔ مسیرِ تأییدِ آن.

`SERVER` یعنی آدرس سرور پرداخت، مثلا `https://pay.example.com`.

## گام ۱، کلید API

بعد از ساخت فروشگاه دو کلید داری:

| کلید | شکل | کاربرد |
|---|---|---|
| live | `sibil_pay_live_…` | پرداخت واقعی با پول واقعی |
| test | `sibil_pay_test_…` | تمرین بدون پول واقعی |

کلید را فقط در سرور خودت نگه دار. داخل اپ موبایل، جاوااسکریپت صفحه یا مخزن عمومی نگذار.

کلیدهای قدیمی‌تر با پیشوند `sp_live_` و `sp_test_` هم کار می‌کنند.

## گام ۲، ثبت کارت بانکی

کارت فروشنده باید ثبت شده و فعال باشد، وگرنه فاکتور ساخته نمی‌شود.

```bash
curl -X POST https://SERVER/api/v1/cards \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{
    "card_number": "6104337812345678",
    "bank": "mellat",
    "holder_name": "علی رضایی"
  }'
```

لیست کارت‌ها:

```bash
curl https://SERVER/api/v1/cards -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"
```

## گام ۳، اولین فاکتور

```bash
curl -X POST https://SERVER/api/v1/invoices \
  -H "Authorization: Bearer sibil_pay_test_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_rial": 2500000,
    "order_id": "ORDER-1042",
    "description": "اشتراک ماهانه",
    "expiry_minutes": 30
  }'
```

جواب، خلاصه:

```json
{
  "success": true,
  "data": {
    "id": "inv_9f2c1a7b3d",
    "status": "pending",
    "amount_rial": 2500000,
    "payable_rial": 2500137,
    "short_code": "AB12CD",
    "payment_url": "https://SERVER/pay/inv_9f2c1a7b3d",
    "expires_at": "2026-01-01T12:30:00+00:00",
    "test_mode": true,
    "card": { "bank": "mellat", "last4": "5678", "holder": "علی رضایی" }
  },
  "error": null
}
```

**تفکیکِ دو مبلغ:**

- `amount_rial` مبلغِ اسمیِ سفارش است و هرگز تغییر نمی‌کند؛ همین عدد مبنای گزارش‌ها و وبوک است.
- `payable_rial` مبلغی است که خریدار باید واریز کند: `amount_rial` به‌علاوهٔ چند ریال عددِ یکتا (کمتر از ۱۰۰۰ ریال) تا واریزی‌ها در صورت‌حساب قابلِ تفکیک باشند.

در نمونهٔ بالا `amount_rial = 2,500,000` و `payable_rial = 2,500,137` ریال است. به خریدار همیشه `payable_rial` را نشان بده. تومان فقط واحدِ نمایش است (`تومان = ریال ÷ ۱۰`) و چون عددِ یکتا مضربی از ۱۰ نیست، تومانِ معادل ممکن است اعشار داشته باشد؛ در نمایش، ریال را دقیق نگه دار.

## گام ۴، چک کردن وضعیت

```bash
curl https://SERVER/api/v1/invoices/inv_9f2c1a7b3d/status \
  -H "Authorization: Bearer sibil_pay_test_XXXXXXXX"
```

```json
{
  "success": true,
  "data": {
    "id": "inv_9f2c1a7b3d",
    "status": "pending",
    "amount_rial": 2500000,
    "payable_rial": 2500137,
    "paid_amount_rial": 0,
    "remaining_rial": 2500000,
    "verified": false,
    "expires_at": "2026-01-01T12:30:00+00:00"
  },
  "error": null
}
```

وقتی `status` به `paid` رسید یعنی پرداخت تأیید شده است.

## گام ۵، تست بدون پول واقعی

با کلید test دو راه داری.

الف) شبیه‌سازیِ واریز: این مسیر یک پیامک بانکیِ نمونه در جدولِ پیامک‌ها ثبت می‌کند و **همان موتورِ تطبیقِ محیطِ واقعی** را روی آن اجرا می‌کند (تطبیقِ مبلغِ یکتا، کارت و زمان، سپس تأییدِ فاکتور). هیچ مبلغی جابه‌جا نمی‌شود و فاکتور باید `paid` شود:

```bash
curl -X POST https://SERVER/api/v1/test/invoices/inv_9f2c1a7b3d/simulate-payment \
  -H "Authorization: Bearer sibil_pay_test_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{"bank": "mellat", "payer_last4": "1234"}'
```

بعد دوباره `status` را بگیر؛ باید `paid` شده باشد.

ب) پرداختِ واقعیِ ۱۰۰ تومانی: فاکتوری با `amount_rial: 1000` (یعنی ۱۰۰ تومان) بساز و خودت مبلغ را واریز کن. این روش، چرخهٔ کاملِ «پیامک بانک → تطبیق → تأیید → وبوک» را با کمترین هزینه نشان می‌دهد.

## گام ۶، وصل کردن webhook

```bash
curl -X PATCH https://SERVER/api/v1/store \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://mysite.com/sibilpay/callback"}'
```

برای آزمونِ مقصد، یک رویدادِ نمونهٔ امضاشده به همان آدرس فرستاده می‌شود و پاسخِ سرورِ تو گزارش می‌شود:

```bash
curl -X POST https://SERVER/api/v1/webhook-test \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"
```

جزئیات امضا و بدنه در [۰۴ — webhook](04-webhooks.md) است.

## چک‌لیست رفتن به محیط واقعی

- [ ] کلید live در سرور است و کلید test فقط برای تست
- [ ] `webhook_url` با https ثبت شده
- [ ] امضای webhook در کد بررسی می‌شود
- [ ] پردازش سفارش در برابر دریافتِ تکراریِ وبوک مقاوم است؛ یک رویدادِ تکراری نباید سفارش یا پرداختِ دوم بسازد
- [ ] به صفحه بازگشت (`callback_url`) به‌تنهایی اعتماد نمی‌کنی
- [ ] مبلغ نمایش‌داده‌شده به مشتری همان `payable_rial` است
- [ ] گوشی فروشنده به سرور وصل است و پیامک می‌فرستد
- [ ] کیف پول کارمزد شارژ دارد

بعدی: [مرجع API](03-api-reference.md)
