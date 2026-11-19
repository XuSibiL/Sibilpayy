# ۲۹ — هر باتی چطور خبرِ «پرداخت شد» را دریافت کند

این سند برای هر ربات و هر سایتی است: تلگرام، PHP، Node، پایتون، هرچه. مهم نیست با چه
زبانی نوشته شده؛ فقط سه چیز لازم است. اگر هر سه نباشد، خبرِ پرداخت یا نمی‌رسد یا
می‌رسد و پردازش نمی‌شود — که از بیرون شبیهِ «سیبیل‌پی تأیید نکرد» به‌نظر می‌رسد.

## سه چیزی که هر بات باید داشته باشد

| # | لازم | چرا |
|---|---|---|
| ۱ | **یک آدرس عمومیِ https که `POST` JSON را قبول کند** | سیبیل‌پی خبر را با `POST` می‌فرستد؛ اگر آدرس صفحهٔ HTML باشد، خبر در راه می‌میرد |
| ۲ | **ثبتِ همان آدرس به‌عنوان مقصدِ همین بات** | با `PUT /api/v1/hooks/self` (بدون توکن ادمین) یا با فرستادنِ `webhook_url` هنگامِ ساختِ فاکتور |
| ۳ | **پاسخِ سریع `2xx` + پردازشِ تکرارپذیر** | `5xx` یعنی «دوباره بفرست»، `4xx` یعنی «هرگز»؛ تکرار هم نباید سفارش را دوباره تأیید کند |

## ۰) خطای گران‌قیمت: صفحهٔ بازگشت جای webhook نیست

دو آدرس متفاوت‌اند و جابه‌جا کردنشان رایج‌ترین دلیلِ «پرداخت شد ولی سفارش تأیید نشد» است:

| آدرس | مخاطبش | چه چیزی می‌فهمد |
|---|---|---|
| `callback_url` مثل `https://shop.example/payment/sibilpay_return.php` | **مرورگر مشتری** | صفحهٔ HTML؛ `POST` JSON را نمی‌فهمد |
| `webhook_url` مثل `https://shop.example/payment/sibilpay_webhook.php` | **سرور سیبیل‌پی** | `POST` JSON + هدرهای امضا |

اگر آدرسِ بازگشت در جای webhook بگذاری، هر بار کد `200` با بدنهٔ HTML برمی‌گردد،
پنل هم سبز می‌شود، ولی هیچ خبری پردازش نمی‌شود. آزمونِ تشخیص، در بخش ۶ آمده است.

## ۱) ثبتِ مقصد، بدون توکن ادمین

هر بات با کلیدِ API خودِ فروشگاه، مقصدش را یک‌بار ثبت می‌کند. این کار اتصالِ بات‌های
دیگر را دست نمی‌زند و با سقفِ سه مقصد ([سند ۱۶](16-multi-webhook.md)) جور است.

```http
PUT /api/v1/hooks/self
Authorization: Bearer sibil_pay_live_XXXX
Content-Type: application/json

{"url": "https://shop.example/payment/sibilpay_webhook.php", "label": "shop-bot"}
```

فهرست و وضعیتِ همان مقصدها:

```http
GET /api/v1/hooks/self
Authorization: Bearer sibil_pay_live_XXXX
```

اگر به `PUT` دسترسی نداشتی، جایگزین این است که هنگامِ ساختِ فاکتور همان آدرس را
بفرستی؛ سیبیل‌پی آن را به‌عنوان مقصدِ همان فاکتور به‌کار می‌برد:

```json
{
  "amount_rial": 900000,
  "order_id": "sp-123456",
  "callback_url": "https://shop.example/payment/sibilpay_return.php",
  "webhook_url":  "https://shop.example/payment/sibilpay_webhook.php"
}
```

مسیرِ دومی روشِ رایج در ربات‌های آماده است؛ اولی تمیزتر است چون یک‌بار انجام می‌شود
و همهٔ فاکتورهای بعدی خودکار همان مقصد را می‌گیرند.

## ۲) آناتومی خبر

```http
POST /payment/sibilpay_webhook.php HTTP/1.1
Content-Type: application/json
X-SIBILPAY-Event: invoice.paid
X-SIBILPAY-Delivery: whd_7c1f2a
X-SIBILPAY-Signature: t=1767225000,v1=8f14e45fceea167a5a36dedd4bea2543…
```

```json
{
  "event": "invoice.paid",
  "object": "invoice",
  "id": "inv_6cdkskwhnk1m9ph2tegjby",
  "invoice_id": "inv_6cdkskwhnk1m9ph2tegjby",
  "status": "paid",
  "order_id": "sp-7d0ed39aee3fd25a3b32c50c",
  "amount_rial": 900000,
  "paid_amount_rial": 900000,
  "amount_toman": 90000,
  "payable_rial": 902050,
  "short_code": "179794",
  "created_at": "2026-11-20T01:39:00+00:00",
  "paid_at": "2026-11-20T02:05:11+00:00",
  "store": {"id": "st_…", "slug": "vpn", "name": "Sibil Vpn Fast"},
  "card": {"bank": "melli", "last4": "1289", "holder": "…"},
  "payment_url": "https://SERVER/pay/inv_…"
}
```

فهرستِ کاملِ رخدادها در [سند ۰۴](04-webhooks.md) است. دو قاعدهٔ عملی:

- **فقط `event == "invoice.paid"` سفارش را نهایی می‌کند.** `invoice.partially_paid`
  یعنی پول کم رسیده و هنوز باید منتظر ماند.
- **مبلغِ سفارش `amount_rial` است.** `paid_amount_rial` در پرداختِ کامل و در
  «تأیید دستی» دقیقاً برابرِ همان است. `payable_rial` مبلغ + عددِ یکتا برای تشخیصِ
  واریز است و **نباید** با مبلغِ سفارش مقایسه شود.

## ۳) پردازش درست، در هفت خط

| گام | کار |
|---|---|
| ۱ | بدنهٔ خام را بخوان (`php://input`)، امضا را بررسی کن، بدنه را به آرایه تبدیل کن |
| ۲ | اگر `event` چیزی جز `invoice.paid` بود، `200` بده و برو |
| ۳ | سفارش را با `order_id` پیدا کن (نه با `id` سیبیل‌پی) |
| ۴ | اگر سفارش از قبل پرداخت‌شده است، `{"ok":true,"state":"already"}` بده و هیچ‌کاری نکن |
| ۵ | اگر مبلغ جور نیست، `200` با `{"ok":false,"error":"amount_mismatch"}` بده (نه `5xx`) |
| ۶ | سفارش را پرداخت‌شده کن، سرویس را فعال/تمدید کن، مشتری را خبر کن |
| ۷ | پاسخ را زودتر ببند (`fastcgi_finish_request()`) و کارِ سنگین را در صف انجام بده |

## ۴) قواعدِ پاسخ

| کد | معنی برای سیبیل‌پی | رفتار |
|---|---|---|
| `200` / `201` / `204` | رسید | تحویل تمام؛ تکرار نمی‌شود |
| `4xx` | ردِ قطعی | دوباره تلاش نمی‌کند |
| `5xx` یا تایم‌اوت | خطای موقت | با فاصلهٔ ۵ ثانیه تا ۱ ساعت دوباره تلاش می‌کند |

پس هرگز برای «خطای منطقی» (سفارش پیدا نشد، مبلغ جور نبود) `500` نده؛ آن را `200`
با `ok:false` برگردان تا تلاشِ بی‌پایان و صفِ خراب نشود.

## ۵) تکرارپذیری: یک کلید

درخواست‌ها تکرار می‌شوند (تایم‌اوت، یا `5xx`ِ خودت). یک جدولِ کوچک بگذار:

```sql
create table if not exists sibilpay_seen (
  delivery_id text primary key,      -- X-SIBILPAY-Delivery
  invoice_id  text,
  seen_at     timestamp default current_timestamp
);
```

اگر `X-SIBILPAY-Delivery` را دیده‌ای، `200` بده و پردازش نکن. اگر هدر نبود،
`(invoice_id, event)` را کلید بگیر.

## ۶) آزمونِ پذیرش (قبل از این‌که بگویی تمام شد)

```bash
# الف) پاسخ باید JSON باشد نه HTML، و کد ۲۰۰
curl -sS -i -X POST https://shop.example/payment/sibilpay_webhook.php \
  -H 'Content-Type: application/json' \
  -H 'X-SIBILPAY-Event: invoice.paid' \
  -H 'X-SIBILPAY-Signature: t=1767225000,v1=امضای-درست' \
  -d '{"event":"invoice.paid","id":"inv_test","order_id":"<یک سفارش واقعی>",
       "status":"paid","amount_rial":900000,"paid_amount_rial":900000}'
# انتظار: HTTP/1.1 200 و بدنه‌ای مثل {"ok":true}

# ب) همان درخواست دوباره → {"ok":true,"state":"already"} و سفارش دست‌نخورده
# ج) امضای غلط → 401
# د) order_id ناموجود → 200 با {"ok":false,"error":"unknown_order"} (نه ۵۰۰)
```

از طرفِ سیبیل‌پی هم می‌توانی همین را بسنجی؛ پاسخِ سرورِ خودت را نشان می‌دهد:

```bash
curl -X POST https://SERVER/api/v1/webhook-test -H "Authorization: Bearer sibil_pay_live_XXXX"
```

## ۷) اسکلتِ مرجعِ PHP

```php
<?php
// payment/sibilpay_webhook.php
$SECRET = getenv('SIBILPAY_WEBHOOK_SECRET') ?: 'CHANGE_ME';
$raw = file_get_contents('php://input');
$sig = $_SERVER['HTTP_X_SIBILPAY_SIGNATURE'] ?? '';
$log = function (string $m) {
    @file_put_contents(__DIR__ . '/../logs/sibilpay_webhook.log',
        date('c') . ' ' . $m . PHP_EOL, FILE_APPEND);
};

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') { http_response_code(405); exit; }

// امضا: بخشِ v1 = hex HMAC-SHA256 از بدنهٔ خام با کلیدِ مقصد
preg_match('/v1=([0-9a-f]{64})/i', $sig, $m);
if (!hash_equals(hash_hmac('sha256', $raw, $SECRET), $m[1] ?? '')) {
    $log('bad signature');
    http_response_code(401);
    echo '{"ok":false,"error":"bad_signature"}';
    exit;
}

$d      = json_decode($raw, true) ?: [];
$event  = $d['event'] ?? '';
$order  = $d['order_id'] ?? '';
$amount = (int) ($d['amount_rial'] ?? 0);
$inv    = $d['id'] ?? '';
$deliv  = $_SERVER['HTTP_X_SIBILPAY_DELIVERY'] ?? '';
$log(sprintf('event=%s order=%s amount=%d inv=%s deliv=%s', $event, $order, $amount, $inv, $deliv));

header('Content-Type: application/json; charset=utf-8');

if ($event !== 'invoice.paid') { echo '{"ok":true,"state":"ignored"}'; exit; }

// ۱) تکرار
// if (seen($deliv)) { echo '{"ok":true,"state":"duplicate"}'; exit; }

// ۲) سفارش
$row = null;                       // $row = find_order_by_external_id($order);
if (!$row) { echo '{"ok":false,"error":"unknown_order"}'; exit; }
if (!empty($row['paid'])) { echo '{"ok":true,"state":"already"}'; exit; }
if ($amount !== (int) $row['amount_rial']) {
    $log('amount mismatch');
    echo '{"ok":false,"error":"amount_mismatch"}';
    exit;
}

// ۳) همان کاری که امروز بعد از تأیید دستی می‌کنی
// mark_order_paid($row['id']); notify_customer($row['user_id'], 'پرداخت تأیید شد');

echo '{"ok":true}';
```

## ۸) نشانه‌ها و علت‌ها

| نشانه | علت | راه |
|---|---|---|
| همیشه بدنهٔ HTML برمی‌گردد | آدرس، صفحهٔ بازگشت است نه webhook | یک فایلِ جدا برای webhook بساز |
| خبر در `/hooks` سبز است ولی سفارش تأیید نمی‌شود | پردازش به مبلغ یا `status` دیگری شرط بسته یا استثنا می‌خورد | فقط `invoice.paid` را مبنا بگیر و خطاها را لاگ کن |
| یک سفارش دو بار تأیید می‌شود | `2xx` نمی‌دهی یا تکرارپذیر نیستی | `X-SIBILPAY-Delivery` را ذخیره کن |
| هیچ خبری نمی‌رسد و آدرس در پنل سبز است | مقصد ثبت نشده یا آدرس در `callback_url` مانده | `PUT /api/v1/hooks/self` یا فرستادنِ `webhook_url` |
| فقط بعضی دامنه‌ها خبر می‌گیرند | هر دامنه باید مقصدِ خودش را ثبت کند | [سند ۱۶](16-multi-webhook.md) و [سند ۱۸](18-connect-a-bot.md) |
