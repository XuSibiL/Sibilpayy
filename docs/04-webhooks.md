<div dir="rtl" align="right">

# ۰۴ — وب‌هوک: خبرِ «پرداخت شد»

> **اگر وب‌هوک نرسید:** سندِ [۱۴ — وبهوک و تأیید دستی](14-webhooks-and-manual-confirm.md)
> شش علتِ رایج، ابزارِ `/hooks` در ربات و زنجیرهٔ کامل را دارد.

این مهم‌ترین بخشِ اتصال است. سایت/اپ/رباتِ تو با وب‌هوک **خودش** خبردار می‌شود.

---

## چطور فعال می‌شود؟

یک آدرس ثبت می‌کنی (باید با `http://` یا `https://` شروع شود — عملاً **https**، چون
امضا در مسیرِ رمزنگاری‌نشده محافظت نمی‌شود):

```bash
curl -X PATCH https://SERVER/api/v1/store \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url":"https://mysite.com/sibilpay/callback"}'
```

آزمایش:

```bash
curl -X POST https://SERVER/api/v1/webhook-test \
  -H "Authorization: Bearer sibil_pay_live_XXXXXXXX"
```

جواب می‌گوید سرورِ تو چه کدی برگرداند — اگر `2xx` نبود، همان‌جا مشکل را می‌بینی.

---

## رویدادها

| رویداد | کِی می‌آید |
|---|---|
| `invoice.created` | فاکتور ساخته شد |
| `invoice.paid` | **پرداخت تأیید شد** ← مهم‌ترین. هم پرداختِ خودکار و هم تأییدِ دستیِ فروشنده (حتی روی فاکتورِ منقضی یا لغو‌شده) این رخداد را می‌فرستد |
| `invoice.partially_paid` | بخشی از مبلغ واریز شد |
| `invoice.verified` | رسید/تأیید صادر شد |
| `deposit.unmatched` | واریزی به هیچ فاکتوری نخورد («نیازمندِ بررسی») |
| `transaction.detected` | تراکنشِ بانکی شناسایی شد |
| `transaction.review_required` | نیاز به تأییدِ دستی |

---

## شکلِ درخواست

```
POST https://mysite.com/sibilpay/callback
Content-Type: application/json
X-SIBILPAY-Signature: t=1767225000,v1=8f14e45fceea167a5a36dedd4bea2543…
X-SIBILPAY-Event: invoice.paid
X-SIBILPAY-Delivery: whd_7c1f2a
User-Agent: SIBILPAY/1.0 (+webhook)
```

بدنه:

```json
{
  "event": "invoice.paid",
  "created_at": "2026-01-01T12:12:41+00:00",
  "livemode": true,
  "data": {
    "id": "inv_9f2c1a7b3d",
    "object": "invoice",
    "status": "paid",
    "amount_rial": 2500000,
    "payable_rial": 2500137,
    "paid_amount_rial": 2500137,
    "order_id": "ORDER-1042",
    "description": "اشتراک ماهانه",
    "short_code": "AB12CD",
    "test_mode": false,
    "created_at": "2026-01-01T12:00:00+00:00",
    "paid_at": "2026-01-01T12:12:41+00:00",
    "verified_at": "2026-01-01T12:12:41+00:00",
    "expires_at": "2026-01-01T12:30:00+00:00",
    "store": { "id": "str_…", "slug": "myshop", "name": "فروشگاه من" },
    "card": { "bank": "mellat", "last4": "5678", "holder": "علی رضایی" },
    "payment_url": "https://SERVER/pay/inv_9f2c1a7b3d"
  }
}
```

`order_id` کلیدِ اتصال به سفارشِ خودت است.

---

## تأییدِ امضا (الزامی)

```
X-SIBILPAY-Signature: t=<timestamp>,v1=<hex>
```

قاعده: `hex = HMAC_SHA256(secret, "<t>." + raw_body)`

- `secret` = کلیدِ امضای وب‌هوکِ فروشگاه (از پنل بگیر).
- **raw_body** یعنی بدنهٔ خامِ درخواست، دقیقاً همان بایت‌ها (بعد از پارس‌کردنِ JSON
  دوباره بسازی، امضا نمی‌خورد).
- اختلافِ `t` با ساعتِ خودت بیشتر از ۵ دقیقه باشد → رد کن (ضدِ بازپخش/replay).

### پایتون (FastAPI)

```python
import hashlib, hmac, time
from fastapi import FastAPI, Request, HTTPException

SECRET = "کلیدِ-امضای-وب‌هوک"
app = FastAPI()

def verify(raw: bytes, header: str, tolerance: int = 300) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    ts, mac = int(parts.get("t", "0")), parts.get("v1", "")
    if abs(time.time() - ts) > tolerance:
        return False
    expected = hmac.new(SECRET.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, mac)

@app.post("/sibilpay/callback")
async def callback(request: Request):
    raw = await request.body()
    if not verify(raw, request.headers.get("X-SIBILPAY-Signature", "")):
        raise HTTPException(401, "bad signature")
    event = await request.json()
    if event["event"] == "invoice.paid":
        data = event["data"]
        # ۱) سفارش را با data["order_id"] پیدا کن
        # ۲) اگر قبلاً paid شده، هیچ کاری نکن (idempotent)
        # ۳) سفارش را paid کن و به کاربر پیام بده
    return {"ok": True}          # حتماً 2xx و سریع
```

### Node.js (Express)

```js
const crypto = require("crypto");
const express = require("express");
const app = express();

const SECRET = process.env.SIBILPAY_WEBHOOK_SECRET;

app.post("/sibilpay/callback",
  express.raw({ type: "application/json" }),   // بدنهٔ خام، نه json()
  (req, res) => {
    const header = req.get("X-SIBILPAY-Signature") || "";
    const parts = Object.fromEntries(header.split(",").map(p => p.split("=")));
    const ts = Number(parts.t || 0);
    const expected = crypto.createHmac("sha256", SECRET)
      .update(`${ts}.`).update(req.body).digest("hex");

    const got = Buffer.from(parts.v1 || "", "hex");
    const ok  = got.length === expected.length &&
                crypto.timingSafeEqual(got, Buffer.from(expected, "hex"));

    if (Math.abs(Date.now() / 1000 - ts) > 300 || !ok) {
      return res.status(401).send("bad signature");
    }

    const event = JSON.parse(req.body.toString("utf8"));
    if (event.event === "invoice.paid") {
      // markPaid(event.data.order_id)  ← یدمپوتنت بنویس
    }
    res.json({ ok: true });
  });
```

> ⚠️ در Express حتماً `express.raw` (یا `bodyParser.raw`) برای همین مسیر بگذار؛
> `express.json()` بدنه را تغییر می‌دهد و امضا نمی‌خورد.

### PHP

```php
<?php
$secret = getenv('SIBILPAY_WEBHOOK_SECRET');
$raw    = file_get_contents('php://input');
$header = $_SERVER['HTTP_X_SIBILPAY_SIGNATURE'] ?? '';

parse_str(str_replace(',', '&', $header), $parts);   // t=…&v1=…
$ts  = (int)($parts['t'] ?? 0);
$mac = $parts['v1'] ?? '';

$expected = hash_hmac('sha256', $ts . '.' . $raw, $secret);
if (abs(time() - $ts) > 300 || !hash_equals($expected, $mac)) {
    http_response_code(401);
    exit('bad signature');
}

$event = json_decode($raw, true);
if (($event['event'] ?? '') === 'invoice.paid') {
    $orderId = $event['data']['order_id'];
    // سفارش را paid کن — قبل از تغییر چک کن قبلاً paid نشده باشد
}
http_response_code(200);
echo json_encode(['ok' => true]);
```

---

## قواعدِ تحویل

| موضوع | رفتار |
|---|---|
| موفقیت | هر پاسخِ `2xx` در ۱۰ ثانیه = تحویل شد |
| تلاشِ مجدد | تا **۸ بار**، با فاصلهٔ ۵، ۱۰، ۲۰، ۴۰ … ثانیه (حداکثر ۱ ساعت) |
| ترتیب | ممکن است جابه‌جا برسد؛ به `created_at` و وضعیتِ فعلی تکیه کن، نه به ترتیب |
| تکرار | ممکن است یک رویداد دو بار بیاید → **یدمپوتنت** بنویس |
| شناسهٔ تحویل | `X-SIBILPAY-Delivery` — برای حذفِ تکرارها کلیدِ یکتا بگذار |

**قاعدهٔ طلایی:** در وب‌هوک کارِ سنگین نکن. سریع `200` بده، بعد در صف/بک‌گراند
سفارش را کامل کن.

---

## اگر وب‌هوک نرسید؟

1. `POST /api/v1/webhook-test` را بزن و ببین جوابِ سرورت چه بود.
2. مطمئن شو آدرس از اینترنت **قابلِ دسترس** است (نه `localhost`، نه پشتِ فایروال).
3. `GET /api/v1/invoices/{id}/status` همیشه مرجعِ نهایی است؛ اگر `paid` بود و وب‌هوک
   نیامده، با یک jobِ زمان‌بندی‌شده وضعیت را sync کن (fallbackِ سالم).

---

بعدی: [رباتِ تلگرام →](05-telegram-bot.md)

</div>

---

## وضعیتِ وب‌هوک را از API بخوان (قبل از هر ثبتِ خودکار)

هر فروشگاه **یک** آدرسِ وب‌هوک دارد. `webhook_url` در پاسخِ `GET /api/v1/store`
**همیشه** هست؛ اگر آدرسی ثبت نشده باشد مقدارش `null` است — کلید حذف نمی‌شود.
پس اتصالِ خودکار (ربات، سایت، اپ) می‌تواند بدونِ حدس تصمیم بگیرد:

```http
GET /api/v1/store
Authorization: Bearer sibil_pay_live_XXXXXXXX
```

```json
{
  "success": true,
  "data": {
    "id": "st_9f2c…", "slug": "shop", "name": "فروشگاهِ من",
    "webhook_url": null,
    "webhook_configured": false,
    "webhook_secret_configured": false,
    "webhook_single_url_per_store": true,
    "webhook_events": ["invoice.created", "invoice.paid", "invoice.partially_paid",
                       "invoice.verified", "invoice.cancelled", "invoice.expired", "invoice.error"],
    "webhook_last_delivery": null
  },
  "error": null
}
```

| کلید | معنی |
|---|---|
| `webhook_url` | آدرسِ فعلی؛ **`null` = ثبت نشده** |
| `webhook_configured` | همان، به‌صورتِ بولی (برای شرط‌های ساده) |
| `webhook_secret_configured` | آیا کلیدِ امضا تنظیم شده |
| `webhook_single_url_per_store` | **محدودیتِ صریح:** هر فروشگاه فقط یک آدرس |
| `webhook_events` | رویدادهایی که واقعاً فرستاده می‌شوند (از خودِ کد، نه از مستندات) |
| `webhook_last_delivery` | آخرین ارسال: `status`, `attempts`, `response_status`, `last_error`, `next_attempt_at` |

### قانونِ طلایی برای اتصالِ خودکار

```
GET /store  →  webhook_url خالی است؟        →  PATCH بگذار (ثبتِ خودکار)
            →  همان آدرسِ من است؟           →  کاری نکن
            →  آدرسِ دیگری است؟             →  بازنویسی نکن؛ از فروشنده بپرس
```

وقتی `PATCH` می‌زنی، پاسخ می‌گوید چه چیزی جایگزین شد:

```json
{"success": true, "data": {
  "webhook_url": "https://mine.example.ir/hook",
  "webhook_configured": true,
  "webhook_previous_url": "https://old.example.ir/hook",
  "webhook_replaced": true
}, "error": null}
```

`webhook_replaced: true` یعنی یک اتصالِ دیگر (ربات/سایت/اپ) از قبل این آدرس را
داشته و تو عوضش کردی — همان چیزی که نباید بی‌اطلاع انجام شود.

### حذفِ وب‌هوک

```http
PATCH /api/v1/store      {"webhook_url": ""}
```
پاسخ: `webhook_url: null` و `webhook_configured: false`.

### پیگیریِ ارسال‌ها و تلاش‌های مجدد

```http
GET /api/v1/webhooks?limit=20
GET /api/v1/webhooks?invoice_id=inv_123&limit=5
```

```json
{"success": true, "data": {
  "webhook_url": "https://mine.example.ir/hook",
  "webhook_configured": true,
  "count": 1,
  "deliveries": [{
    "id": "whd_…", "event": "invoice.paid", "invoice_id": "inv_123",
    "url": "https://mine.example.ir/hook",
    "status": "delivered", "attempts": 1, "response_status": 200,
    "last_error": null,
    "created_at": "2026-11-16T00:10:00+00:00",
    "next_attempt_at": null
  }]
}, "error": null}
```

`status`: `pending` (در صف) · `delivered` (تحویل شد) · `failed` (پس از تلاش‌ها رد شد).

---

## نمونهٔ کدِ اتصال — همهٔ زبان‌ها

الگویِ مشترک: **بخوان → اگر خالی بود بنویس → امضا را بررسی کن → ۲xx برگردان**.

### ۱) PHP (خالص)

```php
<?php
$base  = 'https://pay.mrsibilman.ir';
$token = 'sibil_pay_live_XXXXXXXX';
$hook  = 'https://mysite.com/sibilpay/callback';

function api(string $method, string $url, string $token, ?array $body = null) {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_CUSTOMREQUEST  => $method,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER     => ["Authorization: Bearer $token", "Content-Type: application/json"],
        CURLOPT_POSTFIELDS     => $body === null ? null : json_encode($body),
    ]);
    $raw = curl_exec($ch); $code = curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
    return [$code, json_decode($raw, true)];
}

// ۱) خواندنِ وضعیت
[, $me] = api('GET', "$base/api/v1/store", $token);
$current = $me['data']['webhook_url'] ?? null;          // null = خالی

// ۲) فقط اگر خالی بود ثبت کن (اتصالِ قبلی را نسوزان)
if ($current === null) {
    api('PATCH', "$base/api/v1/store", $token, ['webhook_url' => $hook]);
} elseif ($current !== $hook) {
    error_log("وبهوک از قبل ثبت شده: $current — بازنویسی نکردم");
}

// ۳) گیرندهٔ وبهوک: امضا
$secret = getenv('SIBILPAY_WEBHOOK_SECRET');
$raw    = file_get_contents('php://input');
$sig    = $_SERVER['HTTP_X_SIBILPAY_SIGNATURE'] ?? '';
if (!hash_equals(hash_hmac('sha256', $raw, $secret), $sig)) { http_response_code(401); exit; }

$event = json_decode($raw, true);
if (($event['event'] ?? '') === 'invoice.paid') {
    mark_order_paid($event['data']['order_id'], $event['data']['paid_amount_rial']);
}
http_response_code(200); echo '{"ok":true}';
```

### ۲) وردپرس (بدونِ کتابخانه)

```php
add_action('init', function () {
    if ($_SERVER['REQUEST_URI'] !== '/sibilpay/callback') return;

    $raw   = file_get_contents('php://input');
    $sig   = $_SERVER['HTTP_X_SIBILPAY_SIGNATURE'] ?? '';
    $secret = get_option('sibilpay_webhook_secret');
    if (!hash_equals(hash_hmac('sha256', $raw, $secret), $sig)) { status_header(401); exit; }

    $event = json_decode($raw, true);
    if (($event['event'] ?? '') === 'invoice.paid') {
        $order = wc_get_order($event['data']['order_id']);
        if ($order && !$order->is_paid()) { $order->payment_complete($event['data']['payment_id']); }
    }
    status_header(200); echo '{"ok":true}'; exit;
});

// ثبتِ خودکار فقط وقتی خالی است
function sibilpay_ensure_hook() {
    $token = get_option('sibilpay_api_key');
    $res   = wp_remote_get('https://pay.mrsibilman.ir/api/v1/store',
                 ['headers' => ['Authorization' => "Bearer $token"]]);
    $me    = json_decode(wp_remote_retrieve_body($res), true);
    if (($me['data']['webhook_url'] ?? null) === null) {
        wp_remote_request('https://pay.mrsibilman.ir/api/v1/store', [
            'method'  => 'PATCH',
            'headers' => ['Authorization' => "Bearer $token", 'Content-Type' => 'application/json'],
            'body'    => wp_json_encode(['webhook_url' => home_url('/sibilpay/callback')]),
        ]);
    }
}
```

### ۳) Node.js (Express)

```js
const crypto = require('crypto');
const BASE = 'https://pay.mrsibilman.ir';
const TOKEN = process.env.SIBILPAY_TOKEN;
const HOOK = 'https://mysite.com/sibilpay/callback';
const H = { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'application/json' };

async function ensureWebhook() {
  const me = await (await fetch(`${BASE}/api/v1/store`, { headers: H })).json();
  const current = me.data.webhook_url;               // null = خالی
  if (current === null) {
    const r = await (await fetch(`${BASE}/api/v1/store`, {
      method: 'PATCH', headers: H, body: JSON.stringify({ webhook_url: HOOK }),
    })).json();
    console.log('ثبت شد:', r.data.webhook_url);
  } else if (current !== HOOK) {
    console.warn('آدرسِ دیگری ثبت است، دست نزدم:', current);
  }
}

app.post('/sibilpay/callback', express.raw({ type: '*/*' }), (req, res) => {
  const sig = crypto.createHmac('sha256', process.env.SIBILPAY_WEBHOOK_SECRET)
                    .update(req.body).digest('hex');
  if (sig !== req.get('X-SIBILPAY-SIGNATURE')) return res.status(401).end();
  const ev = JSON.parse(req.body.toString());
  if (ev.event === 'invoice.paid') { /* سفارش را پرداخت‌شده کن */ }
  res.json({ ok: true });
});
```

### ۴) Python (FastAPI)

```python
import hmac, hashlib, httpx
from fastapi import FastAPI, Request, HTTPException

BASE, TOKEN = "https://pay.mrsibilman.ir", "sibil_pay_live_XXXXXXXX"
HOOK = "https://mysite.com/sibilpay/callback"
H = {"Authorization": f"Bearer {TOKEN}"}

async def ensure_webhook():
    async with httpx.AsyncClient() as c:
        me = (await c.get(f"{BASE}/api/v1/store", headers=H)).json()["data"]
        if me["webhook_url"] is None:                       # خالی
            await c.patch(f"{BASE}/api/v1/store", headers=H, json={"webhook_url": HOOK})
        elif me["webhook_url"] != HOOK:
            print("ثبتِ قبلی حفظ شد:", me["webhook_url"])

app = FastAPI()

@app.post("/sibilpay/callback")
async def hook(request: Request):
    raw = await request.body()
    sig = hmac.new(b"WEBHOOK_SECRET", raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, request.headers.get("X-SIBILPAY-SIGNATURE", "")):
        raise HTTPException(401)
    ev = await request.json()
    if ev["event"] == "invoice.paid":
        ...
    return {"ok": True}
```

### ۵) Kotlin / Java (اندروید)

```kotlin
val base = "https://pay.mrsibilman.ir"
val hook = "https://mysite.com/sibilpay/callback"

// خواندن، بعد فقط در صورتِ خالی‌بودن نوشتن
val me = JSONObject(URL("$base/api/v1/store").openConnection().apply {
    setRequestProperty("Authorization", "Bearer $token")
}.getInputStream().bufferedReader().readText())
if (me.getJSONObject("data").isNull("webhook_url")) {
    val conn = URL("$base/api/v1/store").openConnection() as HttpURLConnection
    conn.requestMethod = "PATCH"
    conn.setRequestProperty("Authorization", "Bearer $token")
    conn.setRequestProperty("Content-Type", "application/json")
    conn.doOutput = true
    conn.outputStream.write("""{"webhook_url":"$hook"}""".toByteArray())
    conn.responseCode  // 200
}
```

### ۶) C# (ASP.NET Core)

```csharp
// خواندن + ثبت فقط وقتی خالی است
var me = await http.GetFromJsonAsync<JsonElement>($"{baseUrl}/api/v1/store");
var current = me.GetProperty("data").GetProperty("webhook_url");
if (current.ValueKind == JsonValueKind.Null) {
    var res = await http.PatchAsJsonAsync($"{baseUrl}/api/v1/store",
        new { webhook_url = "https://mysite.com/sibilpay/callback" });
}

// گیرنده
app.MapPost("/sibilpay/callback", async (HttpRequest req) => {
    using var reader = new StreamReader(req.Body);
    var raw = await reader.ReadToEndAsync();
    var expected = Convert.ToHexString(
        HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), Encoding.UTF8.GetBytes(raw))).ToLowerInvariant();
    if (req.Headers["X-SIBILPAY-SIGNATURE"] != expected) return Results.Unauthorized();
    return Results.Ok(new { ok = true });
});
```

### ۷) Go (net/http)

```go
type storeResp struct {
    Data struct {
        WebhookURL *string `json:"webhook_url"`
        Configured bool    `json:"webhook_configured"`
    } `json:"data"`
}

func ensureWebhook() error {
    req, _ := http.NewRequest("GET", base+"/api/v1/store", nil)
    req.Header.Set("Authorization", "Bearer "+token)
    var sr storeResp
    // … اجرای درخواست و decode …
    if sr.Data.WebhookURL != nil {
        if *sr.Data.WebhookURL != hook { log.Printf("ثبتِ قبلی حفظ شد: %s", *sr.Data.WebhookURL) }
        return nil
    }
    body := strings.NewReader(`{"webhook_url":"` + hook + `"}`)
    pr, _ := http.NewRequest("PATCH", base+"/api/v1/store", body)
    pr.Header.Set("Authorization", "Bearer "+token)
    pr.Header.Set("Content-Type", "application/json")
    _, err := http.DefaultClient.Do(pr)
    return err
}
```

### ۸) Ruby (Sinatra/Rails)

```ruby
require "net/http"; require "json"; require "openssl"

def api(method, path, body = nil)
  uri = URI("https://pay.mrsibilman.ir#{path}")
  req = Net::HTTP.const_get(method.capitalize).new(uri)
  req["Authorization"] = "Bearer #{ENV['SIBILPAY_TOKEN']}"
  req["Content-Type"]  = "application/json"
  req.body = body.to_json if body
  JSON.parse(Net::HTTP.start(uri.host, uri.port, use_ssl: true) { |h| h.request(req) }.body)
end

me = api(:get, "/api/v1/store")["data"]
api(:patch, "/api/v1/store", { webhook_url: "https://mysite.com/sibilpay/callback" }) if me["webhook_url"].nil?

post "/sibilpay/callback" do
  raw = request.body.read
  expected = OpenSSL::HMAC.hexdigest("SHA256", ENV["SIBILPAY_WEBHOOK_SECRET"], raw)
  halt 401 unless Rack::Utils.secure_compare(expected, request.env["HTTP_X_SIBILPAY_SIGNATURE"].to_s)
  ev = JSON.parse(raw)
  # ev["event"] == "invoice.paid"
  { ok: true }.to_json
end
```

> **کلیدِ امضا** از ربات/تنظیماتِ فروشگاه گرفته می‌شود و **فقط** برای بررسیِ
> `X-SIBILPAY-SIGNATURE` استفاده می‌شود؛ هیچ‌جا در پاسخ‌های API چاپ نمی‌شود
> (`webhook_secret_configured` فقط بولی است).
