# ۲۹ — هر باتی چطور خبرِ «پرداخت شد» را دریافت کند

این سند برای هر ربات و هر سایتی است: تلگرام، PHP، Node، پایتون، هرچه. مهم نیست با چه
زبانی نوشته شده؛ فقط سه چیز لازم است. اگر هر سه نباشد، خبرِ پرداخت یا نمی‌رسد یا
می‌رسد و پردازش نمی‌شود — که از بیرون شبیهِ «سیبیل‌پی تأیید نکرد» به‌نظر می‌رسد.

امضای دقیق و حالت‌های قدیمی‌تر در [سند ۲۱](21-invoice-fee-webhook.md) آمده؛ اینجا همان
قراردادِ اصلی («modern») پیاده می‌شود و دو حالتِ قدیمی فقط برای سازگاری نام برده شده‌اند.

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
  "created_at": "2026-11-20T02:05:11+00:00",
  "livemode": true,
  "data": {
    "id": "inv_6cdkskwhnk1m9ph2tegjby",
    "object": "invoice",
    "status": "paid",
    "amount_rial": 900000,
    "paid_amount_rial": 900000,
    "payable_rial": 902050,
    "order_id": "sp-7d0ed39aee3fd25a3b32c50c",
    "description": "تمدید سرویس",
    "short_code": "179794",
    "test_mode": false,
    "created_at": "2026-11-20T01:39:00+00:00",
    "paid_at": "2026-11-20T02:05:11+00:00",
    "verified_at": "2026-11-20T02:05:11+00:00",
    "expires_at": "2026-11-20T03:39:00+00:00",
    "store": {"id": "st_…", "slug": "vpn", "name": "Sibil Vpn Fast"},
    "card": {"bank": "melli", "last4": "1289", "holder": "…"},
    "payment_url": "https://SERVER/pay/inv_…"
  }
}
```

فهرستِ کاملِ رخدادها در [سند ۰۴](04-webhooks.md) است. سه قاعدهٔ عملی:

- **فقط `event == "invoice.paid"` سفارش را نهایی می‌کند.** `invoice.partially_paid`
  یعنی پول کم رسیده و هنوز باید منتظر ماند.
- **همهٔ فیلدهای فاکتور داخلِ `data` هستند** (`data.order_id`, `data.amount_rial`).
  اگر در نصبِ قدیمی خبرِ تخت (بدونِ `data`) دیدی، به‌صورتِ
  `data.order_id ?? order_id` بخوان.
- **مبلغِ سفارش `data.amount_rial` است.** `data.paid_amount_rial` در پرداختِ کامل و
  در «تأیید دستی» دقیقاً برابرِ همان است. `data.payable_rial` مبلغ + عددِ یکتا برای
  تشخیصِ واریز است و **نباید** با مبلغِ سفارش مقایسه شود.

## ۳) امضا: قاعدهٔ واحد

```
X-SIBILPAY-Signature: t=<unix>,v1=<hex>
hex = HMAC_SHA256(secret, "<t>" + "." + raw_body)
```

- `secret` کلیدِ امضای همان **مقصد** است (نه کلیدِ API؛ در پنل یا در پاسخِ
  `PUT /api/v1/hooks/self` فقط یک‌بار نشان داده می‌شود).
- `raw_body` یعنی بایت‌های خامِ درخواست؛ اگر بعد از `json_decode` دوباره بسازی، امضا
  نمی‌خورد.
- اختلافِ `t` با ساعتِ خودت بیش از **۵ دقیقه** → رد کن (ضدِ replay).
- امضا **الزامی** است: بدونِ امضای درست، پاسخ `401` است و هیچ پرداختی پذیرفته نمی‌شود.

دو حالتِ قدیمی‌تر ([سند ۲۱](21-invoice-fee-webhook.md)) فقط اگر با آن‌ها سروکار داری:
`legacy-store` = `HMAC_SHA256(secret, raw_body)` بدونِ `t`، و `legacy-token` =
`HMAC_SHA256(token, raw_body)` با توکنِ داخلِ آدرس. برای اتصالِ تازه، همان «modern» را
پیاده کن؛ هر دو قالب را هم‌زمان «قبول» نکن — اولویت باید روشن و ثبت‌شده باشد.

## ۴) پردازش درست، در هفت خط

| گام | کار |
|---|---|
| ۱ | بدنهٔ خام را بخوان (`php://input`)، امضا را با قاعدهٔ بالا بررسی کن، بعد JSON پارس کن |
| ۲ | اگر `event` چیزی جز `invoice.paid` بود، `200` بده و برو |
| ۳ | سفارش را با `data.order_id` پیدا کن (نه با `data.id` سیبیل‌پی) |
| ۴ | اگر سفارش از قبل پرداخت‌شده است، `{"ok":true,"state":"already"}` بده و هیچ‌کاری نکن |
| ۵ | اگر مبلغ جور نیست، `200` با `{"ok":false,"error":"amount_mismatch"}` بده (نه `5xx`) |
| ۶ | سفارش را پرداخت‌شده کن، سرویس را فعال/تمدید کن، مشتری را خبر کن |
| ۷ | پاسخ را زودتر ببند (`fastcgi_finish_request()`) و کارِ سنگین را در صف انجام بده |

## ۵) قواعدِ پاسخ

| کد | معنی برای سیبیل‌پی | رفتار |
|---|---|---|
| `200` / `201` / `204` | رسید | تحویل تمام؛ تکرار نمی‌شود |
| `401` | امضا نامعتبر | تحویل **ناموفق** حساب می‌شود و تکرار می‌شود؛ ریشه را درست کن |
| `4xx` دیگر | ردِ قطعی | دوباره تلاش نمی‌کند |
| `5xx` یا تایم‌اوت | خطای موقت | تا ۸ بار، ۵ ثانیه تا ۱ ساعت دوباره تلاش می‌کند |

پس برای «خطای منطقی» (سفارش پیدا نشد، مبلغ جور نبود) `500` نده؛ `200` با `ok:false`
برگردان تا تلاشِ بی‌پایان نشود.

## ۶) تکرارپذیری: یک کلید

```sql
create table if not exists sibilpay_seen (
  delivery_id text primary key,      -- X-SIBILPAY-Delivery
  invoice_id  text,
  seen_at     timestamp default current_timestamp
);
```

اگر `X-SIBILPAY-Delivery` را دیده‌ای، `200` بده و پردازش نکن. اگر هدر نبود،
`(data.id, event)` را کلید بگیر.

## ۷) آزمونِ پذیرش (قبل از این‌که بگویی تمام شد)

```bash
SECRET='whsec_…'
URL='https://shop.example/payment/sibilpay_webhook.php'
RAW='{"event":"invoice.paid","data":{"id":"inv_test","order_id":"sp_test","status":"paid","amount_rial":900000,"paid_amount_rial":900000}}'
TS=$(date +%s)
SIG=$(printf '%s.%s' "$TS" "$RAW" | openssl dgst -sha256 -hmac "$SECRET" -r | cut -d' ' -f1)

# الف) بدونِ امضا → باید ۴۰۱ باشد (نه ۲۰۰)
curl -sS -i -X POST "$URL" -H 'Content-Type: application/json' \
  -H 'X-SIBILPAY-Event: invoice.paid' -d "$RAW" | head -3

# ب) با امضای درست → باید ۲۰۰ و JSON باشد، نه HTML
curl -sS -i -X POST "$URL" -H 'Content-Type: application/json' \
  -H 'X-SIBILPAY-Event: invoice.paid' \
  -H "X-SIBILPAY-Signature: t=$TS,v1=$SIG" -d "$RAW" | head -8

# ج) همان درخواستِ امضاشده دوباره → {"ok":true,"state":"already"} و سفارش دست‌نخورده
# د) order_id ناموجود → 200 با {"ok":false,"error":"unknown_order"} (نه ۵۰۰)
# ه) امضای درست ولی t قدیمی‌تر از ۵ دقیقه → ۴۰۱
```

از طرفِ سیبیل‌پی هم می‌توانی پاسخِ سرورِ خودت را ببینی:

```bash
curl -X POST https://SERVER/api/v1/webhook-test -H "Authorization: Bearer sibil_pay_live_XXXX"
```

## ۸) اسکلتِ مرجعِ PHP

```php
<?php
// payment/sibilpay_webhook.php
$SECRET = getenv('SIBILPAY_WEBHOOK_SECRET') ?: 'CHANGE_ME';
$raw = file_get_contents('php://input');
$hdr = $_SERVER['HTTP_X_SIBILPAY_SIGNATURE'] ?? '';
$log = function (string $m) {
    @file_put_contents(__DIR__ . '/../logs/sibilpay_webhook.log',
        date('c') . ' ' . $m . PHP_EOL, FILE_APPEND);
};

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') { http_response_code(405); exit; }

parse_str(str_replace(',', '&', $hdr), $parts);
$ts  = (int) ($parts['t'] ?? 0);
$mac = $parts['v1'] ?? '';
$expected = hash_hmac('sha256', $ts . '.' . $raw, $SECRET);
if (!$ts || abs(time() - $ts) > 300 || !hash_equals($expected, $mac)) {
    $log('bad signature ts=' . $ts);
    http_response_code(401);
    echo '{"ok":false,"error":"bad_signature"}';
    exit;
}

$d      = json_decode($raw, true) ?: [];
$event  = $d['event'] ?? '';
$data   = $d['data'] ?? [];
$order  = $data['order_id'] ?? '';
$amount = (int) ($data['amount_rial'] ?? 0);
$inv    = $data['id'] ?? '';
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

## ۹) نشانه‌ها و علت‌ها

| نشانه | علت | راه |
|---|---|---|
| همیشه بدنهٔ HTML برمی‌گردد | آدرس، صفحهٔ بازگشت است نه webhook | یک فایلِ جدا برای webhook بساز |
| `401` روی خبرِ واقعی | امضا روی `raw` حساب شده، نه `t.raw`؛ یا بدنه بعد از پارس دوباره ساخته شده | قاعدهٔ بخش ۳ و بدنهٔ خام |
| `401` فقط بعضی وقت‌ها | ساعتِ سرور جلو/عقب است | اختلافِ `t` را ببند (NTP) یا پنجره را دقیق ۳۰۰ ثانیه بگذار |
| خبر در `/hooks` سبز است ولی سفارش تأیید نمی‌شود | پردازش به `amount_rial` یا `status` شرط بسته یا استثنا می‌خورد | فقط `invoice.paid` را مبنا بگیر، `data` را بخوان، خطاها را لاگ کن |
| یک سفارش دو بار تأیید می‌شود | `2xx` نمی‌دهی یا تکرارپذیر نیستی | `X-SIBILPAY-Delivery` را ذخیره کن |
| هیچ خبری نمی‌رسد و آدرس در پنل سبز است | مقصد ثبت نشده یا آدرس در `callback_url` مانده | `PUT /api/v1/hooks/self` یا فرستادنِ `webhook_url` |
