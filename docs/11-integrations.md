# ۱۱. اتصال از هر زبان، هر سایت، هر ربات، هر اپ

SIBILPAY هیچ SDK نمی‌خواهد. قرارداد یک **HTTP + JSON** ساده است، پس هر چیزی که بتواند
یک `POST` بفرستد وصل می‌شود: PHP 5.6 قدیمی، ASP.NET، اندروید، Go، وردپرس، رباتِ
آماده‌ای که فقط «کلید + آدرس» می‌گیرد.

این سند برای هر زبان همان سه کار را می‌نویسد: **ساختِ فاکتور**، **فرستادنِ کاربر به
درگاه**، **تأییدِ امن**.

---

## ۱) جریان در یک نگاه

```
┌──────────────┐   ① POST /api/v1/invoices         ┌───────────────────┐
│  سایت / ربات │ ────────────────────────────────▶ │      SIBILPAY      │
│   / اپِ تو   │ ◀──────────────────────────────── │  (فاکتور می‌سازد)  │
└──────┬───────┘   ② payment_url + payable_rial     └─────────┬─────────┘
       │                                                       │
       │ ③ کاربر را به payment_url بفرست                        │ ④ خریدار
       ▼                                                       ▼  کارت‌به‌کارت
┌──────────────┐   (صفحهٔ پرداخت: کارت، شبا، مبلغِ دقیق)  ┌───────────────┐
│    خریدار    │ ───────────────────────────────────────▶ │ کارتِ فروشنده │
└──────────────┘                                          └───────┬───────┘
                                                                  │ پیامکِ بانک
                                                                  ▼
┌──────────────┐   ⑤ POST به webhookِ تو (امضاشده)      ┌───────────────────┐
│  سایت / اپِ  │ ◀──────────────────────────────────── │  تطبیقِ خودکار     │
│  تو: تحویل!  │    event=invoice.paid                  │  مبلغ → تأیید      │
└──────────────┘                                        └───────────────────┘
```

| گام | کار | نتیجه |
|---|---|---|
| ۱ | `POST /api/v1/invoices` با `amount_rial` و `order_id` | `id`، `payment_url`، `payable_rial` |
| ۲ | کارت‌به‌کارتِ خریدار به کارتِ فروشنده | پیامکِ بانک در اپِ فروشنده |
| ۳ | تطبیقِ خودکار مبلغ | فاکتور `paid` و وب‌هوک `invoice.paid` |
| ۴ | تحویلِ تو | فقط بعد از `paid` |

---

## ۲) آدرس‌ها

| چیز | مقدار |
|---|---|
| پایهٔ API | `https://SERVER/api/v1` |
| احراز | `Authorization: Bearer <کلید_API>` |
| درگاهِ فروشگاه (لینکِ ثابت) | `https://SERVER/g/<store-slug>` |
| لینکِ پرداخت | همان `payment_url` که API می‌دهد: `https://SERVER/pay/<id>` |
| وضعیتِ عمومیِ فاکتور (بدونِ کلید) | `https://SERVER/api/v1/public/invoices/<id>` |

> ⚠️ **قانونِ طلایی:** لینکِ پرداخت را خودت نساز؛ همیشه `payment_url` را از پاسخِ API
> بردار. **API و درگاه روی یک پورت‌اند** (قانونِ PORT-ONE): آدرسی که
> `/api/v1/…` رویش JSON می‌دهد، همان آدرسی است که `/pay/…` رویش باز می‌شود.
> جزئیات و آزمونِ پذیرش: [۱۳ — یک پورت برای API و درگاه](13-one-port.md).

---

## ۳) قاعده‌های مشترک (برای همهٔ زبان‌ها یکی است)

| موضوع | قاعده |
|---|---|
| **مبلغ** | همیشه **ریال**، همیشه `amount_rial`. برای تومان در ۱۰ ضرب کن. چیزی که باید به کاربر نشان بدهی `payable_rial` است (چند تومان بیشتر، برای یکتاییِ تطبیق). |
| **`order_id`** | برای هر سفارش یکتا و ثابت. درخواستِ دوباره با همان `order_id` فاکتورِ تکراری نمی‌سازد و همان فاکتور را با `200` + `idempotent_replay: true` برمی‌گرداند. |
| **نتیجهٔ نامشخص** | `timeout` یا `5xx` یعنی «نمی‌دانم ساخته شد یا نه». `GET /invoices/by-order/{order_id}`: `200` = ساخته شده، `404` = مطمئنی ساخته نشده → تلاشِ تازه مجاز. |
| **امضای وب‌هوک** | `X-SIBILPAY-Signature: t=<ts>,v1=<hex>` که `hex = HMAC_SHA256(secret, "<ts>." + body)`. امضا + `t` را چک کن (پنجرهٔ ۵ دقیقه). |
| **تحویل** | فقط با `invoice.paid` یا وضعیتِ `paid`. بازگشتِ کاربر به سایت هیچ چیزی را اثبات نمی‌کند. |
| **یدمپوتنسی** | وب‌هوک ممکن است دوبار برسد؛ تحویل را با `order_id`/`invoice.id` یکتا کن. |
| **فاکتورِ مرده** | اگر پول رسید ولی فاکتور منقضی/لغو شد: `POST /invoices/{id}/confirm-deposit` با `amount_rial` یا `sms_id` (شاهد اجباری) → `paid` + وب‌هوک. این راهِ رسمی است. |

---

## ۴) کدِ آماده — زبان‌به‌زبان

### ۴.۱ PHP خالص (۵.۶ به بالا، بدونِ کتابخانه)

```php
<?php
const SERVER = 'https://SERVER';
const KEY    = 'کلید_API';

function sibilpay_invoice($amount_rial, $order_id, $name = null) {
    $body = ['amount_rial' => (int)$amount_rial, 'order_id' => (string)$order_id];
    if ($name) $body['customer_name'] = $name;

    $ch = curl_init(SERVER . '/api/v1/invoices');
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_HTTPHEADER     => ['Content-Type: application/json',
                                   'Authorization: Bearer ' . KEY],
        CURLOPT_POSTFIELDS     => json_encode($body, JSON_UNESCAPED_UNICODE),
    ]);
    $raw  = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);                       // 0 = شبکه قطع شد → نتیجه نامشخص

    $json = json_decode($raw, true);
    if ($code >= 200 && $code < 300) return $json['data'];
    throw new RuntimeException('SIBILPAY ' . $code . ' ' . ($json['error']['code'] ?? ''));
}

$inv = sibilpay_invoice(500000, 'order-1042', 'علی رضایی');
header('Location: ' . $inv['payment_url']);   // پورت و دامنه از خودِ پاسخ می‌آید
exit;
```

```php
// webhook.php — آدرسش را در ربات ثبت کن: 🔗 درگاه‌ها و API
$secret = 'whsec_...';
$body   = file_get_contents('php://input');
$header = $_SERVER['HTTP_X_SIBILPAY_SIGNATURE'] ?? '';

parse_str(str_replace(',', '&', $header), $p);
$expect = hash_hmac('sha256', $p['t'] . '.' . $body, $secret);
if (!hash_equals($expect, $p['v1'] ?? '') || abs(time() - (int)$p['t']) > 300) {
    http_response_code(400); exit('bad signature');
}

$event = json_decode($body, true);
if ($event['event'] === 'invoice.paid') {
    mark_order_paid($event['data']['order_id'], $event['data']['paid_amount_rial']);
}
http_response_code(200); echo 'ok';   // 2xx = تحویل شد
```

### ۴.۲ وردپرس / ووکامرس

```php
// wp-content/plugins/my-shop-sibilpay/my-shop-sibilpay.php
<?php
/* Plugin Name: SIBILPAY gateway for my shop */

add_action('woocommerce_thankyou', function ($order_id) {
    $order = wc_get_order($order_id);
    if (!$order || $order->get_status() !== 'pending') return;

    $res = wp_remote_post('https://SERVER/api/v1/invoices', [
        'timeout' => 20,
        'headers' => ['Content-Type'  => 'application/json',
                      'Authorization' => 'Bearer ' . get_option('sibilpay_key')],
        'body' => wp_json_encode([
            'amount_rial'   => (int) round($order->get_total() * 10),  // تومان → ریال
            'order_id'      => 'wc-' . $order_id,                      // یکتا و ثابت
            'customer_name' => $order->get_billing_first_name(),
            'description'   => 'سفارش #' . $order_id,
        ]),
    ]);

    if (is_wp_error($res)) return;                    // نامشخص → by-order
    $data = json_decode(wp_remote_retrieve_body($res), true)['data'] ?? null;
    if ($data) { wp_redirect($data['payment_url']); exit; }
});

add_action('rest_api_init', function () {
    register_rest_route('my-shop/v1', '/sibilpay', [
        'methods' => 'POST', 'permission_callback' => '__return_true',
        'callback' => function (WP_REST_Request $r) {
            $body = $r->get_body();
            parse_str(str_replace(',', '&', (string) $r->get_header('x-sibilpay-signature')), $p);
            $ok = hash_equals(hash_hmac('sha256', $p['t'] . '.' . $body,
                                        get_option('sibilpay_secret')), $p['v1'] ?? '');
            if (!$ok) return new WP_REST_Response(['error' => 'sig'], 400);

            $e = json_decode($body, true);
            if (($e['event'] ?? '') === 'invoice.paid') {
                $order = wc_get_order(str_replace('wc-', '', $e['data']['order_id']));
                if ($order && !$order->is_paid()) $order->payment_complete();
            }
            return new WP_REST_Response(['ok' => true], 200);
        },
    ]);
});
```

### ۴.۳ Node.js (Express ۱۸+)

```js
import express from 'express';
import crypto from 'node:crypto';

const SERVER = 'https://SERVER';
const KEY    = process.env.SIBILPAY_KEY;
const SECRET = process.env.SIBILPAY_SECRET;
const app = express();

app.post('/checkout', express.json(), async (req, res) => {
  const orderId = `ord-${Date.now()}`;            // یکتا برای هر تلاش
  const r = await fetch(`${SERVER}/api/v1/invoices`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${KEY}` },
    body: JSON.stringify({ amount_rial: req.body.total_rial, order_id: orderId,
                           customer_name: req.body.name }),
    signal: AbortSignal.timeout(20000),
  });
  if (r.status >= 400) return res.status(502).send('پرداخت آماده نشد');
  const { data } = await r.json();
  res.redirect(303, data.payment_url);            // ← لینکِ خودِ API
});

app.post('/sibilpay/webhook', express.raw({ type: '*/*' }), (req, res) => {
  const parts = Object.fromEntries((req.get('X-SIBILPAY-Signature') || '')
                    .split(',').map(p => p.split('=')));
  const expect = crypto.createHmac('sha256', SECRET)
                       .update(`${parts.t}.${req.body}`).digest('hex');
  const safe = expect.length === (parts.v1 || '').length &&
               crypto.timingSafeEqual(Buffer.from(expect), Buffer.from(parts.v1 || ''));
  if (!safe || Math.abs(Date.now() / 1000 - Number(parts.t)) > 300)
    return res.status(400).send('bad signature');

  const event = JSON.parse(req.body.toString('utf8'));
  if (event.event === 'invoice.paid') markPaid(event.data.order_id);  // یدمپوتنت
  res.json({ ok: true });
});
```

### ۴.۴ Python (Flask / Django / FastAPI)

```python
import hmac, hashlib, time, requests
from flask import Flask, request, redirect, abort

SERVER = "https://SERVER"
KEY    = "کلید_API"
SECRET = "whsec_..."
app = Flask(__name__)

def create_invoice(amount_rial: int, order_id: str, name: str | None = None) -> dict:
    payload = {"amount_rial": amount_rial, "order_id": order_id}
    if name:
        payload["customer_name"] = name
    r = requests.post(f"{SERVER}/api/v1/invoices", json=payload,
                      headers={"Authorization": f"Bearer {KEY}"}, timeout=20)
    if r.status_code >= 400:                  # قطعی: فاکتور ساخته نشد
        raise RuntimeError(f"SIBILPAY {r.status_code} {r.text[:200]}")
    return r.json()["data"]

@app.get("/checkout/<int:order_id>")
def checkout(order_id: int):
    inv = create_invoice(500_000, f"shop-{order_id}")
    return redirect(inv["payment_url"], code=303)

@app.post("/sibilpay/webhook")
def webhook():
    body  = request.get_data()                # خام، نه form
    parts = dict(p.split("=", 1) for p in
                 request.headers.get("X-SIBILPAY-Signature", "").split(","))
    expect = hmac.new(SECRET.encode(), f"{parts.get('t')}.".encode() + body,
                      hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, parts.get("v1", "")):
        abort(400)
    if int(time.time()) - int(parts["t"]) > 300:
        abort(400)

    event = request.get_json(force=True)
    if event["event"] == "invoice.paid":
        deliver(event["data"]["order_id"])    # یدمپوتنت
    return {"ok": True}
```

### ۴.۵ Kotlin / Java (اندروید، Spring، هر JVM)

```kotlin
val SERVER = "https://SERVER"
val KEY    = "کلید_API"

fun createInvoice(amountRial: Long, orderId: String, onUrl: (String) -> Unit) {
    val body = """{"amount_rial":$amountRial,"order_id":"$orderId"}"""
        .toRequestBody("application/json".toMediaType())

    val req = Request.Builder()
        .url("$SERVER/api/v1/invoices")
        .header("Authorization", "Bearer $KEY")
        .post(body).build()

    OkHttpClient().newCall(req).enqueue(object : Callback {
        override fun onResponse(c: Call, r: Response) = r.use {
            if (!it.isSuccessful) return          // 4xx = قطعاً ساخته نشد
            val url = JSONObject(it.body!!.string())
                .getJSONObject("data").getString("payment_url")
            onUrl(url)                            // ← کاربر را اینجا بفرست
        }
        override fun onFailure(c: Call, e: IOException) {
            // نتیجه نامشخص → GET /api/v1/invoices/by-order/$orderId
        }
    })
}
// startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
```

### ۴.۶ C# / .NET

```csharp
using System.Net.Http.Json;

static readonly HttpClient http = new();
const string Server = "https://SERVER";
const string Key    = "کلید_API";

public static async Task<string> CreateInvoiceAsync(long amountRial, string orderId)
{
    using var req = new HttpRequestMessage(HttpMethod.Post, $"{Server}/api/v1/invoices")
    {
        Content = JsonContent.Create(new { amount_rial = amountRial, order_id = orderId })
    };
    req.Headers.Authorization = new("Bearer", Key);

    using var res = await http.SendAsync(req);
    if (!res.IsSuccessStatusCode)
        throw new Exception($"SIBILPAY {(int)res.StatusCode}");   // قطعی

    var json = await res.Content.ReadFromJsonAsync<JsonElement>();
    return json.GetProperty("data").GetProperty("payment_url").GetString()!;
}

app.MapPost("/sibilpay/webhook", async (HttpRequest request, string secret) =>
{
    using var reader = new StreamReader(request.Body);
    var body   = await reader.ReadToEndAsync();                   // خام
    var parts  = request.Headers["X-SIBILPAY-Signature"].ToString()
                        .Split(',').Select(p => p.Split('=', 2))
                        .ToDictionary(p => p[0], p => p[1]);

    using var hmac = new System.Security.Cryptography.HMACSHA256(
        System.Text.Encoding.UTF8.GetBytes(secret));
    var hash = Convert.ToHexString(hmac.ComputeHash(
        System.Text.Encoding.UTF8.GetBytes($"{parts["t"]}.{body}"))).ToLowerInvariant();

    if (hash != parts["v1"]) return Results.BadRequest("bad signature");
    return Results.Ok();                                          // invoice.paid → تحویل
});
```

### ۴.۷ Go

```go
package main

import (
    "bytes"; "crypto/hmac"; "crypto/sha256"; "encoding/hex"
    "encoding/json"; "fmt"; "io"; "net/http"; "time"
)

const server = "https://SERVER"
const key    = "کلید_API"

type resp struct {
    Data struct {
        ID         string `json:"id"`
        PaymentURL string `json:"payment_url"`
        Payable    int64  `json:"payable_rial"`
    } `json:"data"`
}

func createInvoice(amountRial int64, orderID string) (string, error) {
    body, _ := json.Marshal(map[string]any{"amount_rial": amountRial, "order_id": orderID})
    req, _ := http.NewRequest("POST", server+"/api/v1/invoices", bytes.NewReader(body))
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Authorization", "Bearer "+key)

    res, err := (&http.Client{Timeout: 20 * time.Second}).Do(req)
    if err != nil { return "", err }              // نامشخص → by-order
    defer res.Body.Close()
    if res.StatusCode >= 400 { return "", fmt.Errorf("sibilpay %d", res.StatusCode) }

    var r resp
    json.NewDecoder(res.Body).Decode(&r)
    return r.Data.PaymentURL, nil                 // ← کاربر را همین‌جا بفرست
}

func webhook(secret string) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        body, _ := io.ReadAll(r.Body)
        var ts, sig string
        for _, p := range bytes.Split([]byte(r.Header.Get("X-SIBILPAY-Signature")), []byte(",")) {
            kv := bytes.SplitN(p, []byte("="), 2)
            if len(kv) != 2 { continue }
            switch string(kv[0]) {
            case "t":  ts = string(kv[1])
            case "v1": sig = string(kv[1])
            }
        }
        mac := hmac.New(sha256.New, []byte(secret))
        mac.Write([]byte(ts + ".")); mac.Write(body)
        if hex.EncodeToString(mac.Sum(nil)) != sig {
            http.Error(w, "bad signature", 400); return
        }
        w.Write([]byte(`{"ok":true}`))
    }
}
```

### ۴.۸ Ruby on Rails

```ruby
require 'net/http'; require 'json'; require 'openssl'

SERVER = 'https://SERVER'
KEY    = ENV['SIBILPAY_KEY']

def create_invoice(amount_rial:, order_id:)
  uri  = URI("#{SERVER}/api/v1/invoices")
  http = Net::HTTP.new(uri.host, uri.port)
  http.use_ssl = uri.scheme == 'https'
  http.open_timeout = http.read_timeout = 20

  req = Net::HTTP::Post.new(uri, 'Content-Type' => 'application/json',
                                 'Authorization' => "Bearer #{KEY}")
  req.body = { amount_rial: amount_rial, order_id: order_id }.to_json

  res = http.request(req)
  raise "SIBILPAY #{res.code}" if res.code.to_i >= 400    # قطعی
  JSON.parse(res.body)['data']                           # payment_url, ...
end

# کنترلر: redirect_to inv['payment_url']

class SibilpayController < ApplicationController
  skip_before_action :verify_authenticity_token
  def webhook
    body  = request.raw_post
    parts = request.headers['X-SIBILPAY-Signature'].to_s.split(',').to_h { |p| p.split('=', 2) }
    digest = OpenSSL::HMAC.hexdigest('SHA256', ENV['SIBILPAY_SECRET'], "#{parts['t']}.#{body}")
    return head :bad_request unless ActiveSupport::SecurityUtils.secure_compare(digest, parts['v1'].to_s)

    event = JSON.parse(body)
    Order.find_by!(code: event.dig('data', 'order_id')).mark_paid! if event['event'] == 'invoice.paid'
    head :ok
  end
end
```

---

## ۵) بدونِ کد: سایتِ آماده، رباتِ آماده، اپِ قدیمی

| حالت | راه |
|---|---|
| **سایتِ آماده / لینکِ ثابت** | لینکِ درگاهِ فروشگاه `https://SERVER/g/<slug>` را در دکمه یا پست بگذار. کاربر مبلغ را وارد می‌کند و فاکتور همان‌جا ساخته می‌شود. |
| **ربات/افزونهٔ آماده** | هر ربات یا افزونه‌ای که «کلید API + آدرسِ سرور» می‌گیرد، بدونِ تغییر کار می‌کند. آدرس = `https://SERVER/api/v1`. |
| **نسخه‌های قدیمی که قفل می‌شوند** | اگر افزونه با خطای `PREVIOUS_CHECKOUT_NEEDS_REVIEW` گیر کرد، رکوردِ نیمه‌کاره را با `GET /invoices/by-order/{order_id}` استعلام کن؛ `404` یعنی آزاد است. یا فروشنده از ربات «✅ تایید دستی» را می‌زند. |
| **اپِ بدونِ سرور** | اپ فقط `payment_url` را در WebView باز می‌کند و وضعیت را با `GET /api/v1/public/invoices/<id>` (بدونِ کلید) هر ۵ ثانیه می‌پرسد. |
| **فاکتورِ منقضی و پولِ رسیده** | `POST /invoices/<id>/confirm-deposit` با `amount_rial` یا `sms_id` → `paid` + وب‌هوک `invoice.paid`. |

> در همهٔ این حالت‌ها تحویلِ کالا/سرویس فقط با `paid` یا `invoice.paid` انجام می‌شود؛
> بازگشتِ کاربر به سایت هیچ چیزی را اثبات نمی‌کند.

---

## ۶) چک‌لیستِ ۶۰ ثانیه‌ای

- [ ] کلید را از «🔗 درگاه‌ها و API» گرفتم و در `.env` گذاشتم.
- [ ] آدرس `https://SERVER/api/v1` است (با `https`، با `/api/v1`).
- [ ] برای هر سفارش یک `order_id` یکتا می‌فرستم.
- [ ] کاربر را به `payment_url` می‌فرستم، نه لینکِ دست‌ساز.
- [ ] وب‌هوک را ثبت کردم و امضا + `t` را چک می‌کنم.
- [ ] تحویل را یدمپوتنت نوشتم (یک سفارش، یک تحویل).
- [ ] برای نتیجهٔ نامشخص، `by-order` را صدا می‌زنم.

---

## ۷) خطاهای رایج و معنی‌شان

| پاسخ | یعنی | کارِ تو |
|---|---|---|
| `401 INVALID_TOKEN` | کلید غلط/باطل | کلید تازه از «🔗 درگاه‌ها و API» |
| `403 STORE_INACTIVE` / `STORE_BLOCKED` | فروشگاه غیرفعال است | پشتیبانی |
| `422 INVALID_AMOUNT` | `amount_rial` نبود یا ≤ ۰ | مبلغ ریالی و مثبت |
| `409 WALLET_INSUFFICIENT` | کیف پولِ کارمزد کم است | شارژ از ربات |
| `409 NO_CARD_AVAILABLE` | کارتِ فعالی برای فروشگاه نیست | افزودن کارت |
| `404 INVOICE_NOT_FOUND` (در `by-order`) | مطمئنی ساخته نشده | تلاشِ تازه مجاز |
| `5xx` / timeout | **نامشخص** | `by-order` بعد تصمیم |
