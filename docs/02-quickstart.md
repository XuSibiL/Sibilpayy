# ۰۲ — شروع سریع، ۱۵ دقیقه تا اولین پرداخت

هدف: یک فاکتور بسازی، لینکش را باز کنی و ببینی پرداخت چطور تأیید می‌شود.

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

`payable_rial` همان چیزی است که مشتری باید واریز کند؛ در این نمونه ۲٬۵۰۰٬۱۳۷ ریال یعنی ۲۵۰٬۰۱۳ تومان. به کاربر همیشه همین را نشان بده، نه `amount_rial` را.

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

الف) شبیه‌سازی واریز؛ موتور تطبیق واقعی با یک پیامک ساختگی اجرا می‌شود:

```bash
curl -X POST https://SERVER/api/v1/test/invoices/inv_9f2c1a7b3d/simulate-payment \
  -H "Authorization: Bearer sibil_pay_test_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{"bank": "mellat", "payer_last4": "1234"}'
```

بعد دوباره `status` را بگیر؛ باید `paid` شده باشد.

ب) پرداخت واقعی یک‌ریالی؛ یک فاکتور با `amount_rial: 1000` بساز یعنی ۱۰۰ تومان و خودت واریز کن. برای دیدن چرخه کامل پیامک و فاکتور بهترین راه است.

## گام ۶، وصل کردن webhook

```bash
curl -X PATCH https://SERVER/api/v1/store \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://mysite.com/sibilpay/callback"}'
```

بعد با یک دکمه تستش کن؛ یک رویداد نمونه امضاشده می‌فرستد و می‌گوید سرور تو چه جوابی داد:

```bash
curl -X POST https://SERVER/api/v1/webhook-test \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"
```

جزئیات امضا و بدنه در [۰۴ — webhook](04-webhooks.md) است.

## چک‌لیست رفتن به محیط واقعی

- [ ] کلید live در سرور است و کلید test فقط برای تست
- [ ] `webhook_url` با https ثبت شده
- [ ] امضای webhook در کد بررسی می‌شود
- [ ] تحویل سفارش idempotent است، یعنی دو بار آمدن یک رویداد دو سفارش نمی‌سازد
- [ ] به صفحه بازگشت (`callback_url`) به‌تنهایی اعتماد نمی‌کنی
- [ ] مبلغ نمایش‌داده‌شده به مشتری همان `payable_rial` است
- [ ] گوشی فروشنده به سرور وصل است و پیامک می‌فرستد
- [ ] کیف پول کارمزد شارژ دارد

بعدی: [مرجع API](03-api-reference.md)
