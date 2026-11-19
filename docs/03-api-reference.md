# ۰۳ — مرجع API

`SERVER` یعنی آدرس سرور پرداخت. آدرس API با `SERVER/api/v1` شروع می‌شود و آدرس درگاه با `SERVER/g/<slug>`؛ این دو یکی نیستند و در [سند ۱۵](15-address-map.md) توضیح داده شده‌اند.

## قاعده‌های کلی

احراز هویت در همه مسیرهای این سند با `Authorization` است:

```
Authorization: Bearer sibil_pay_live_XXXXXXXX
```

همه مبالغ به ریال هستند و ۱ تومان برابر ۱۰ ریال است.

شکل پاسخ همه درخواست‌ها یکی است:

```json
{ "success": true,  "data": { }, "error": null }
{ "success": false, "data": null, "error": { "code": "INVALID_TOKEN", "message": "…" } }
```

پس اول `success` را بررسی کن، بعد `data` یا `error` را.

مسیر پایه `/api/v1` است.

`order_id` نقش idempotency را دارد: اگر `order_id` بفرستی و برای همان فروشگاه فاکتور باز یا پرداخت‌شده‌ای با همان `order_id` وجود داشته باشد، فاکتور تکراری ساخته نمی‌شود و همان فاکتور با `200` و `"idempotent_replay": true` برمی‌گردد. جزئیات در [۱۰ — تلاش ناموفق و idempotency](10-retries-and-idempotency.md) است.

برای بازیابی نتیجه نامشخص:

```http
GET /api/v1/invoices/by-order/{order_id}
```

`200` یعنی فاکتور هست و `404` یعنی مطمئنی ساخته نشده و می‌توانی دوباره تلاش کنی.

## فهرست اندپوینت‌ها

| متد | مسیر | کار |
|---|---|---|
| `POST` | `/invoices` | ساخت فاکتور |
| `GET` | `/invoices` | فهرست فاکتورها |
| `GET` | `/invoices/{id}` | یک فاکتور با جزئیات |
| `GET` | `/invoices/{id}/status` | فقط وضعیت، سبک برای polling |
| `GET` | `/invoices/{id}/history` | تاریخچه تغییر وضعیت |
| `POST` | `/invoices/{id}/cancel` | لغو |
| `POST` | `/invoices/{id}/verify` | تأیید و گرفتن رسید |
| `POST` | `/invoices/{id}/confirm-deposit` | تأیید دستی واریزی دیررسیده |
| `GET` | `/cards` · `POST /cards` · `PATCH /cards/{id}` | کارت‌ها |
| `GET` | `/store` · `PATCH /store` | تنظیمات فروشگاه؛ `webhook_url` همیشه در پاسخ هست و `null` یعنی خالی |
| `GET` | `/webhooks` · `/webhooks?invoice_id=…` | ارسال‌های webhook با `status` و `attempts` و `response_status` و `last_error` و `next_attempt_at` |
| `POST` | `/webhook-test` | ارسال یک webhook نمونه |
| `GET` | `/gateways` | مسیرهای پرداخت فعال |
| `GET` | `/devices` | گوشی‌های وصل‌شده |
| `POST` | `/devices/pairing-code` | کد اتصال گوشی تازه |
| `POST` | `/test/invoices/{id}/simulate-payment` | شبیه‌سازی واریز، فقط با کلید test |

## ساخت فاکتور

```
POST /api/v1/invoices
```

| فیلد | نوع | الزامی | توضیح |
|---|---|---|---|
| `amount_rial` | int | بله | مبلغ به ریال، بیشتر از صفر |
| `order_id` | string | خیر | شماره سفارش خودت، حداکثر ۱۲۰ کاراکتر |
| `description` | string | خیر | توضیح کوتاه برای مشتری |
| `callback_url` | string | خیر | آدرس بازگشت مشتری، باید `http(s)://` داشته باشد |
| `expiry_minutes` | int | خیر | اعتبار بین ۲ تا ۱۸۰ دقیقه |
| `customer_name` | string | خیر | نام خریدار |
| `customer_phone` | string | خیر | موبایل خریدار |
| `metadata` | object | خیر | هر داده خودت، همان‌طور برمی‌گردد |

نمونه:

```bash
curl -X POST https://SERVER/api/v1/invoices \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_rial": 2500000,
    "order_id": "ORDER-1042",
    "description": "اشتراک ماهانه",
    "callback_url": "https://mysite.com/pay/return",
    "expiry_minutes": 30,
    "metadata": {"plan": "pro"}
  }'
```

پاسخ (۲۰۱):

```json
{
  "success": true,
  "data": {
    "id": "inv_9f2c1a7b3d",
    "status": "pending",
    "amount_rial": 2500000,
    "payable_rial": 2500137,
    "paid_amount_rial": 0,
    "order_id": "ORDER-1042",
    "description": "اشتراک ماهانه",
    "short_code": "AB12CD",
    "created_at": "2026-01-01T12:00:00+00:00",
    "expires_at": "2026-01-01T12:30:00+00:00",
    "paid_at": null,
    "verified_at": null,
    "test_mode": false,
    "payment_url": "https://SERVER/pay/card/inv_9f2c1a7b3d",
    "short_payment_url": "https://SERVER/pay/inv_9f2c1a7b3d",
    "gateway_url": "https://SERVER/g/shop046806",
    "card": { "bank": "mellat", "last4": "5678", "holder": "علی رضایی" }
  },
  "error": null
}
```

`payable_rial` را به مشتری نشان بده، نه `amount_rial` را. اختلاف چند ریالی عمدی و یکتاست تا واریزی‌ها با هم قاطی نشوند.

## وضعیت فاکتور

```
GET /api/v1/invoices/{id}/status
GET /api/v1/invoices/{id}
```

`status` یکی از `pending`، `paid`، `partially_paid`، `expired` یا `cancelled` است.

نمونه پاسخ `/status`:

```json
{
  "success": true,
  "data": {
    "id": "inv_9f2c1a7b3d",
    "status": "paid",
    "amount_rial": 2500000,
    "payable_rial": 2500137,
    "paid_amount_rial": 2500137,
    "remaining_rial": 0,
    "verified": true,
    "expires_at": "2026-01-01T12:30:00+00:00"
  },
  "error": null
}
```

فهرست:

```bash
curl "https://SERVER/api/v1/invoices?status=paid&limit=50" \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"
```

## تأیید و رسید

```
POST /api/v1/invoices/{id}/verify
```

اگر پرداخت تأیید شده باشد، رسید قابل ارائه می‌دهد:

```json
{
  "success": true,
  "data": {
    "invoice_id": "inv_9f2c1a7b3d",
    "verified": true,
    "verified_at": "2026-01-01T12:12:41+00:00",
    "receipt_token": "rcp_…",
    "receipt_url": "https://SERVER/receipt/rcp_…"
  },
  "error": null
}
```

`receipt_url` یک صفحه رسید امضاشده است؛ می‌توانی لینکش را به مشتری بدهی تا اثبات پرداخت داشته باشد.

## لغو

```
POST /api/v1/invoices/{id}/cancel
```

فقط فاکتور `pending` یا `partially_paid` لغو می‌شود.

## تأیید دستی واریزی دیررسیده

```
POST /api/v1/invoices/{id}/confirm-deposit
```

برای وقتی است که پول رسیده ولی فاکتور منقضی شده بود، یا واریزی نیازمند بررسی است. معمولا از پنل یا ربات هم انجام می‌شود و این مسیر برای خودکارسازی است.

شاهد اجباری است: بدنه باید یا `sms_id` یعنی شناسه پیامک واریز ذخیره‌شده را داشته باشد یا `amount_rial` را. بدون یکی از این دو پاسخ `422 EVIDENCE_REQUIRED` است. این کار عمدی است، چون تأیید دستی یعنی انسان پول را دیده، نه یک «paid کن».

```bash
curl -X POST https://SERVER/api/v1/invoices/inv_XXXX/confirm-deposit \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{"amount_rial": 500868, "note": "پیامکِ واریز را دیدم"}'
```

وضعیت‌های پذیرفته‌شده: `pending`، `partially_paid`، `under_review`، `expired`، `cancelled`.

یعنی فاکتور منقضی و لغو‌شده هم با تأیید دستی به `paid` می‌رود و این راه رسمی باز کردن قفل «پول آمده ولی فاکتور مرده» است. بلافاصله پس از تأیید:

- وضعیت فاکتور `paid` می‌شود و `paid_amount_rial` پر می‌شود،
- رویداد `invoice.paid` برای webhook فروشگاه صف می‌شود،
- کارمزد از کیف پول کسر می‌شود و واقعه با `actor` ثبت می‌شود، پس قابل حسابرسی است.

تطبیق خودکار هرگز سراغ فاکتور منقضی یا لغو‌شده نمی‌رود؛ فقط همین مسیر دستی و با شاهد. پس هیچ واریزی اشتباهی خودش فاکتور را paid نمی‌کند.

## تفاوت `payment_url` و `gateway_url`

هر دو در پاسخ فاکتور هستند ولی دو چیز متفاوت‌اند:

| فیلد | معنی | برای چه کسی |
|---|---|---|
| `payment_url` | لینک همین فاکتور، `/pay/<gateway>/<id>` | مشتری؛ ریدایرکت کن و تمام |
| `short_payment_url` | همان لینک بدون نام درگاه، `/pay/<id>` | لینک‌های قدیمی یا کوتاه |
| `gateway_url` | آدرس درگاه فروشگاه، `/g/<slug>` | فیلد آدرس درگاه در پنل‌های دیگر، نه لینک یک خرید خاص |

`payment_url` و `short_payment_url` را همان‌طور که می‌آید مصرف کن و خودت از `SERVER` نساز. آدرس API و آدرس صفحه پرداخت روی یک پورت هستند؛ اگر پورت صریحی در `BASE_URL` باشد همان پورت باید مسیر `/api/v1/…` را هم سرو کند. آزمون سریع و جدول خطاها در [۱۳ — یک پورت برای API و درگاه](13-one-port.md) است.

## کارت‌ها

```bash
# فهرست
curl https://SERVER/api/v1/cards -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"

# افزودن
curl -X POST https://SERVER/api/v1/cards \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{"card_number":"6104337812345678","bank":"mellat","holder_name":"علی رضایی"}'

# فعال/غیرفعال یا اولویت
curl -X PATCH https://SERVER/api/v1/cards/card_XXXX \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

## تنظیمات فروشگاه

```bash
# خواندن
curl https://SERVER/api/v1/store -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"

# ثبتِ آدرسِ وب‌هوک (مهم‌ترین تنظیم برای اتصال)
curl -X PATCH https://SERVER/api/v1/store \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url":"https://mysite.com/sibilpay/callback"}'
```

اگر آدرس با `http://` یا `https://` شروع نشود خطای `INVALID_WEBHOOK_URL` با کد ۴۲۲ می‌گیری.

## گوشی‌ها

```bash
# فهرستِ گوشی‌های وصل‌شده
curl https://SERVER/api/v1/devices -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"

# کدِ اتصال برای گوشیِ تازه (۶ رقمی، چند دقیقه اعتبار)
curl -X POST https://SERVER/api/v1/devices/pairing-code \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"
```

کد را در اپ Forwarder وارد می‌کنی. از لحظه اتصال پیامک‌های تازه خوانده می‌شوند و پیامک‌های قدیمی گوشی هیچ‌وقت واریزی حساب نمی‌شوند.

## شبیه‌سازی واریز، فقط test

```
POST /api/v1/test/invoices/{id}/simulate-payment
```

موتور تطبیق واقعی با یک پیامک ساختگی اجرا می‌شود، برای تست کامل webhook و منطق سفارش بدون یک ریال پول.

بدنه که همه فیلدهایش اختیاری است:

```json
{ "amount_rial": 2500137, "bank": "mellat", "payer_last4": "1234" }
```

روی سرور production فقط با کلید تست (`sibil_pay_test_…`) کار می‌کند، وگرنه `INVOICE_NOT_PAYABLE` می‌گیری. فاکتور هم باید `pending` یا `partially_paid` باشد.

## اندپوینت‌های تکمیلی

| متد | مسیر | کار |
|---|---|---|
| `DELETE` | `/devices/{id}` | جدا کردن گوشی متصل |
| `GET` | `/wallet` | موجودی کیف کارمزد |
| `GET` | `/stats/summary` | خلاصه آماری فروشگاه |
| `GET` | `/stats/export.xlsx` · `.csv` · `.pdf` | خروجی گزارش |
| `GET` | `/matches` | واریزی‌های نیازمند بررسی |
| `POST` | `/matches/{match_id}/resolve` | تعیین تکلیف یک تطبیق |

## مستندات تعاملی

اگر روی سرورت فعال باشد، `SERVER/docs` همه اندپوینت‌ها را با Try it out نشان می‌دهد. مرجع نهایی همین سند است.

بعدی: [webhook](04-webhooks.md)
