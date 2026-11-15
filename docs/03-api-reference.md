<div dir="rtl" align="right">

# ۰۳ — مرجعِ API

> **`SERVER`** = آدرسِ سرورِ پرداختِ شما.

---

## قاعده‌های کلی

**احرازِ هویت:** در همهٔ مسیرهای زیر `Authorization` لازم است:

```
Authorization: Bearer sibil_pay_live_XXXXXXXX
```

**واحدِ پول:** همهٔ مبالغ **ریال** هستند (۱ تومان = ۱۰ ریال).

**پاسخِ همهٔ درخواست‌ها یک شکل دارد:**

```json
{ "success": true,  "data": { }, "error": null }
{ "success": false, "data": null, "error": { "code": "INVALID_TOKEN", "message": "…" } }
```

پس همیشه اول `success` را چک کن، بعد `data` یا `error` را.

**مسیرِ پایه:** `/api/v1`

**`order_id` = idempotency:** اگر `order_id` بفرستی و برای همان فروشگاه فاکتورِ
باز/پرداخت‌شده‌ای با همان `order_id` وجود داشته باشد، فاکتورِ تکراری ساخته
نمی‌شود؛ همان فاکتور با `200` و `"idempotent_replay": true` برمی‌گردد.
جزئیات: [۱۰ — تلاشِ ناموفق و idempotency](10-retries-and-idempotency.md)

**بازیابیِ نتیجهٔ نامشخص:**

```http
GET /api/v1/invoices/by-order/{order_id}
```

`200` = فاکتور هست · `404` = مطمئنی ساخته نشده و می‌توانی دوباره تلاش کنی.

---

## فهرستِ endpointها

| متد | مسیر | کار |
|---|---|---|
| `POST` | `/invoices` | ساختِ فاکتور |
| `GET` | `/invoices` | فهرستِ فاکتورها |
| `GET` | `/invoices/{id}` | یک فاکتور با جزئیات |
| `GET` | `/invoices/{id}/status` | فقط وضعیت (سبک، برای polling) |
| `GET` | `/invoices/{id}/history` | تاریخچهٔ تغییرِ وضعیت |
| `POST` | `/invoices/{id}/cancel` | لغو |
| `POST` | `/invoices/{id}/verify` | تأیید و گرفتنِ رسید |
| `POST` | `/invoices/{id}/confirm-deposit` | تأییدِ دستیِ واریزیِ دیررسیده |
| `GET` | `/cards` · `POST /cards` · `PATCH /cards/{id}` | کارت‌ها |
| `GET` | `/store` · `PATCH /store` | تنظیماتِ فروشگاه (از جمله `webhook_url`) |
| `POST` | `/webhook-test` | ارسالِ یک وب‌هوکِ نمونه |
| `GET` | `/gateways` | مسیرهای پرداختِ فعال |
| `GET` | `/devices` | گوشی‌های وصل‌شده |
| `POST` | `/devices/pairing-code` | کدِ اتصالِ گوشیِ تازه |
| `POST` | `/test/invoices/{id}/simulate-payment` | شبیه‌سازیِ واریز (فقط کلیدِ test) |

---

## ساختِ فاکتور

```
POST /api/v1/invoices
```

| فیلد | نوع | الزامی | توضیح |
|---|---|---|---|
| `amount_rial` | int | ✅ | مبلغ، ریال، بیشتر از صفر |
| `order_id` | string | — | شمارهٔ سفارشِ خودت (حداکثر ۱۲۰ کاراکتر) |
| `description` | string | — | توضیحِ کوتاه برای مشتری |
| `callback_url` | string | — | آدرسِ بازگشتِ مشتری (باید `http(s)://`) |
| `expiry_minutes` | int | — | اعتبار، بین ۲ تا ۱۸۰ دقیقه |
| `customer_name` | string | — | نامِ خریدار |
| `customer_phone` | string | — | موبایلِ خریدار |
| `metadata` | object | — | هر دادهٔ خودت؛ همان‌طور برمی‌گردد |

**نمونه:**

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

**پاسخ (۲۰۱):**

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
    "payment_url": "https://SERVER/pay/inv_9f2c1a7b3d",
    "card": { "bank": "mellat", "last4": "5678", "holder": "علی رضایی" }
  },
  "error": null
}
```

> 🔑 **`payable_rial` را به مشتری نشان بده، نه `amount_rial` را.**
> اختلافِ چند ریالی، عمدی و یکتاست تا واریزی‌ها با هم قاطی نشوند.

---

## وضعیتِ فاکتور

```
GET /api/v1/invoices/{id}/status
GET /api/v1/invoices/{id}
```

`status` یکی از: `pending` · `paid` · `partially_paid` · `expired` · `cancelled`

نمونهٔ پاسخِ `/status`:

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

**فهرست:**

```bash
curl "https://SERVER/api/v1/invoices?status=paid&limit=50" \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"
```

---

## تأیید و رسید

```
POST /api/v1/invoices/{id}/verify
```

اگر پرداخت تأیید شده باشد، رسیدِ قابلِ ارائه می‌دهد:

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

`receipt_url` یک صفحهٔ رسیدِ امضاشده است؛ می‌توانی لینکش را به مشتری بدهی (اثباتِ پرداخت).

---

## لغو

```
POST /api/v1/invoices/{id}/cancel
```

فقط فاکتورِ `pending` (یا `partially_paid`) لغو می‌شود. کارمزدی ندارد.

---

## تأییدِ دستیِ واریزیِ دیررسیده

```
POST /api/v1/invoices/{id}/confirm-deposit
```

برای وقتی که پول رسیده ولی فاکتور منقضی شده بود، یا واریزی «نیازمندِ بررسی» است.
(معمولاً از پنل/ربات هم انجام می‌شود؛ برای خودکارسازی در دسترس است.)

---

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

---

## تنظیماتِ فروشگاه

```bash
# خواندن
curl https://SERVER/api/v1/store -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"

# ثبتِ آدرسِ وب‌هوک (مهم‌ترین تنظیم برای اتصال)
curl -X PATCH https://SERVER/api/v1/store \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url":"https://mysite.com/sibilpay/callback"}'
```

اگر آدرس با `http://` یا `https://` شروع نشود → خطای `INVALID_WEBHOOK_URL` (کد ۴۲۲).

---

## گوشی‌ها (دستگاه‌ها)

```bash
# فهرستِ گوشی‌های وصل‌شده
curl https://SERVER/api/v1/devices -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"

# کدِ اتصال برای گوشیِ تازه (۶ رقمی، چند دقیقه اعتبار)
curl -X POST https://SERVER/api/v1/devices/pairing-code \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"
```

کد را در اپِ Forwarder وارد می‌کنی. **از لحظهٔ اتصال** پیامک‌های تازه خوانده می‌شوند؛
پیامک‌های قدیمیِ گوشی هیچ‌وقت واریزی حساب نمی‌شوند.

---

## شبیه‌سازیِ واریز (فقط test)

```
POST /api/v1/test/invoices/{id}/simulate-payment
```

موتورِ تطبیقِ **واقعی** با یک پیامکِ ساختگی اجرا می‌شود؛ برای تستِ کاملِ وب‌هوک و
منطقِ سفارش، بدونِ یک ریال پول.

بدنه (همه اختیاری):

```json
{ "amount_rial": 2500137, "bank": "mellat", "payer_last4": "1234" }
```

> روی سرورِ production فقط با **کلیدِ تست** (`sibil_pay_test_…`) کار می‌کند؛ وگرنه
> `INVOICE_NOT_PAYABLE` می‌گیری. فاکتور هم باید `pending` یا `partially_paid` باشد.

---

## endpointهای تکمیلی

| متد | مسیر | کار |
|---|---|---|
| `DELETE` | `/devices/{id}` | جدا کردنِ گوشیِ متصل |
| `GET` | `/wallet` | موجودیِ کیفِ کارمزد |
| `GET` | `/stats/summary` | خلاصهٔ آماری فروشگاه |
| `GET` | `/stats/export.xlsx` · `.csv` · `.pdf` | خروجیِ گزارش |
| `GET` | `/matches` | واریزی‌های نیازمندِ بررسی |
| `POST` | `/matches/{match_id}/resolve` | تعیینِ تکلیفِ یک تطبیق |

---

## مستنداتِ تعاملی

اگر روی سرورت فعال باشد، `SERVER/docs` همهٔ endpointها را با امکانِ «Try it out» نشان
می‌دهد. اما مرجعِ نهایی همین سند است.

---

بعدی: [وب‌هوک →](04-webhooks.md)

</div>
