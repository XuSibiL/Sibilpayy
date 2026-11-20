# ۲۲ — اتصال پروژه‌های بیرونی

SIBILPAY یک API معمولی JSON روی HTTPS است و SDK اجباری ندارد. هر چیزی که بتواند `curl` بزند می‌تواند درگاه بسازد: PHP، Laravel، وردپرس، ووکامرس، Node، Go یا اسکریپت bash. کد اجرایی نمونه در `examples/php/` هست.

## پیش‌نیازها

| چیز | مقدار |
|---|---|
| آدرس پایه | همان `BASE_URL` سرور، مثلا `https://pay.mrsibilman.ir:19055` |
| کلید API | `sp_live_...` یا `sp_test_...` که یک‌بار در پنل یا ربات ساخته می‌شود |
| هدر احراز هویت | `Authorization: Bearer <کلید>` |
| قالب پاسخ | `{"success": true, "data": {...}}` و در خطا `{"success": false, "error": {"code","message"}}` |
| مبلغ | همیشه ریال (۱۰ ریال = ۱ تومان) |

PHP فقط به `curl` و `json` نیاز دارد:

```bash
php -m | grep -E '^(curl|json)$'
```

## ۱) ساخت فاکتور

```bash
curl -X POST https://pay.mrsibilman.ir:19055/api/v1/invoices \
  -H "Authorization: Bearer $SIBIL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"amount_rial": 2500000, "order_id": "A-1043", "customer_name": "علی"}'
```

پاسخ:

```json
{
  "success": true,
  "data": {
    "id": "inv_...",
    "status": "pending",
    "amount_rial": 2500000,
    "payable_rial": 2500473,
    "payment_url": "https://pay.mrsibilman.ir:19055/pay/inv_...",
    "expires_at": "2026-11-12T19:40:00+03:30",
    "short_code": "483920"
  }
}
```

`payable_rial` مبلغی است که مشتری باید واریز کند. چند ریال با `amount_rial` فرق دارد تا هر واریزی یکتا شناسایی شود؛ همان را به مشتری بده و همان را در صفحه خودت نشان بده.

`payment_url` صفحه پرداخت است (کارت و مبلغ دقیق). لینک را در پروژه خودت به مشتری بده؛ نمایش لینک قابل‌کپی داخل ربات SIBILPAY ممنوع است.

## ۲) خواندن وضعیت

```bash
curl https://pay.mrsibilman.ir:19055/api/v1/invoices/inv_.../status \
  -H "Authorization: Bearer $SIBIL_KEY"
```

`status` یکی از این‌هاست: `pending`، `partially_paid`، `paid`، `expired`، `cancelled`، `under_review`.

## ۳) تأیید یک‌بارمصرف و رسید

```bash
curl -X POST https://pay.mrsibilman.ir:19055/api/v1/invoices/inv_.../verify \
  -H "Authorization: Bearer $SIBIL_KEY"
```

بار اول `200` با `receipt_url`، `receipt_token` و `png_url` (رسید تصویری) برمی‌گردد. بار دوم `409` با کد `INVOICE_ALREADY_VERIFIED`؛ این عمدی است تا سفارش دوبار تحویل داده نشود.

## ۴) webhook پرداخت

```bash
curl -X PATCH https://pay.mrsibilman.ir:19055/api/v1/store \
  -H "Authorization: Bearer $SIBIL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://shop.example.ir/sibilpay/callback"}'
```

پاسخ شامل `webhook_secret` است. هر تحویل یک درخواست `POST` با این هدرهاست:

```
X-SIBILPAY-Signature: t=1763158800,v1=<64 hex>
X-SIBILPAY-Event: invoice.paid
X-SIBILPAY-Delivery: whd_...
Content-Type: application/json
```

کلید امضا همان کلید مقصد webhook است (اگر مقصدی ثبت نشده باشد: `webhook_secret` فروشگاه). هدر `X-SIBILPAY-Signature-Mode` می‌گوید همین درخواست با کدام مسیر امضا شده:

| مسیر | مقدار `X-SIBILPAY-Signature` | کلید |
|---|---|---|
| `modern` | `t=<unix>,v1=<hex>` | کلید مقصد |
| `legacy-store` | `<hex>` روی بدنه | کلید مقصد |
| `legacy-token` | `<hex>` روی بدنه | توکن داخل آدرس مقصد |

اگر مقصدت فقط `legacy-store` را می‌شناسد همان را بپذیر و بقیه را نادیده بگیر؛ سامانه خودش مسیر درست را در تلاش‌های بعدی پیدا می‌کند.

### بررسی در PHP

```php
$raw    = file_get_contents('php://input');            // بدنهٔ خام، نه $_POST
$sig    = $_SERVER['HTTP_X_SIBILPAY_SIGNATURE'] ?? '';
$secret = 'whsec_...';                                 // از PATCH /api/v1/store

if (!Sibilpay::verifywebhook($raw, $sig, $secret)) {
    http_response_code(401);
    exit('bad signature');
}

$event = json_decode($raw, true);
if ($event['event'] === 'invoice.paid') {
    // $event['data']['order_id'] → سفارش را «پرداخت‌شده» کن
}
http_response_code(200);                               // 2xx = تحویل شد
```

چند نکته موقع پیاده‌سازی:

- بدنه خام را هش کن. اگر `json_decode` و دوباره `json_encode` کنی، امضا می‌شکند.
- مقدار `t` را اگر بیش از پنج دقیقه قدیمی باشد رد کن.
- تا وقتی 2xx برنگردانی SIBILPAY تا ۸ بار با فاصله فزاینده دوباره تلاش می‌کند. پس idempotent باش: اگر سفارش قبلا پرداخت شده، باز هم 200 بده.
- رخدادها: `invoice.created`، `invoice.paid`، `invoice.partially_paid`، `deposit.unmatched` (واریزی نیازمند بررسی)، `deposit.claimed`، `wallet.low`، `wallet.empty`، `webhook.test`.

### تست امضا

```bash
curl -X POST https://pay.mrsibilman.ir:19055/api/v1/webhook-test \
  -H "Authorization: Bearer $SIBIL_KEY"
```

این درخواست همان قالب امضای واقعی را می‌فرستد تا کد بررسی‌ات را یک‌بار تست کنی.

## ۵) وصل کردن واریزی نیازمند بررسی

```bash
curl "https://pay.mrsibilman.ir:19055/api/v1/strays?limit=25" \
  -H "Authorization: Bearer $SIBIL_KEY"

curl -X POST https://pay.mrsibilman.ir:19055/api/v1/strays/<sms_id>/claim \
  -H "Authorization: Bearer $SIBIL_KEY" -H "Content-Type: application/json" \
  -d '{"invoice_id": "inv_..."}'

curl -X POST https://pay.mrsibilman.ir:19055/api/v1/strays/<sms_id>/ignore \
  -H "Authorization: Bearer $SIBIL_KEY"
```

`claim` همان مسیر تأیید دستی را اجرا می‌کند: کارمزد از کیف پول، رسید، webhook و اعلان ربات و اپ، دقیقا مثل وقتی خودت در ربات دکمه را می‌زنی.

## ۶) کیف پول کارمزد

```bash
curl https://pay.mrsibilman.ir:19055/api/v1/wallet -H "Authorization: Bearer $SIBIL_KEY"
```

پول کارمزد و پول فروشگاه دو حساب جدا هستند: واریزی مشتری به کارت خودت می‌رود و کارمزد از کیف پول کم می‌شود. شارژ کیف پول با فاکتور `kind=wallet_topup` انجام می‌شود و در آمار فروشگاه شمرده نمی‌شود.

## ۷) آزمون اجراشده

```
$ php examples/php/smoke.php https://... sp_live_...
✅ فاکتور ساخته شد
✅ مبلغ قابل پرداخت برگشت
✅ وضعیت خوانده شد
✅ تأیید قبل از پرداخت رد شد (INVOICE_NOT_PAYABLE)
✅ لیست نیازمند بررسی خوانده شد
✅ کیف پول خوانده شد
✅ پرداخت ثبت شد
✅ رسید امضاشده صادر شد
✅ تأیید دوم رد شد (INVOICE_ALREADY_VERIFIED)
✅ امضای معتبر پذیرفته شد
✅ بدنهٔ دست‌کاری‌شده رد شد
✅ امضای منقضی رد شد
```

پس هر پروژه‌ای که `curl` دارد می‌تواند روی SIBILPAY درگاه بسازد.
