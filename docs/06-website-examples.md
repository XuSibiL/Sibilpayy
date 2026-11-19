# ۰۶ — نمونه‌های سایت

اگر زبان دیگری لازم داری، مثل PHP یا وردپرس یا Node یا Python یا جاوا یا C# یا Go یا Ruby، یا حتی بدون کد، بخش ۱۱ همین را با کد آماده و نمودار جریان دارد: [اتصال از هر زبان، هر سایت، هر ربات](11-integrations.md).

سه الگو در این سند هست: PHP برای وردپرس یا اسکریپت قدیمی، Node.js، و Python با Django یا FastAPI. هر سه یک کار می‌کنند: ساخت فاکتور، هدایت کاربر، و تأیید پرداخت با webhook.

`SERVER` یعنی آدرس سرور پرداخت و کلید API فقط در سرور سایت نگه داشته می‌شود.

## ۱) PHP بدون فریم‌ورک

فایل `sibilpay.php` با توابع مشترک:

```php
<?php
const SIBIL_SERVER = 'https://SERVER';
const SIBIL_KEY    = 'sibil_pay_live_XXXXXXXX';
const SIBIL_SECRET = 'کلیدِ-امضای-وب‌هوک';

function sibil_request(string $method, string $path, ?array $body = null): array {
    $ch = curl_init(SIBIL_SERVER . $path);
    curl_setopt_array($ch, [
        CURLOPT_CUSTOMREQUEST  => $method,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 15,
        CURLOPT_HTTPHEADER     => [
            'Authorization: Bearer ' . SIBIL_KEY,
            'Content-Type: application/json',
        ],
    ]);
    if ($body !== null) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($body, JSON_UNESCAPED_UNICODE));
    }
    $res = json_decode(curl_exec($ch), true);
    curl_close($ch);
    if (empty($res['success'])) {
        throw new RuntimeException($res['error']['message'] ?? 'خطای ارتباط با درگاه');
    }
    return $res['data'];
}

function sibil_create_invoice(int $toman, string $orderId, string $returnUrl): array {
    return sibil_request('POST', '/api/v1/invoices', [
        'amount_rial'    => $toman * 10,
        'order_id'       => $orderId,
        'description'    => 'سفارش ' . $orderId,
        'callback_url'   => $returnUrl,
        'expiry_minutes' => 30,
    ]);
}
```

فایل `pay.php` برای شروع پرداخت:

```php
<?php
require __DIR__ . '/sibilpay.php';

$orderId = 'ORD-' . time();          // در واقعیت: شمارهٔ سفارشِ خودت
$inv = sibil_create_invoice(250000, $orderId, 'https://mysite.com/return.php');

// ذخیرهٔ اتصالِ order → invoice (در دیتابیسِ خودت)
save_order_invoice($orderId, $inv['id']);

header('Location: ' . $inv['payment_url']);   // کاربر به صفحهٔ پرداخت می‌رود
exit;
```

فایل `callback.php` برای webhook:

```php
<?php
require __DIR__ . '/sibilpay.php';

$raw    = file_get_contents('php://input');
$header = $_SERVER['HTTP_X_SIBILPAY_SIGNATURE'] ?? '';
parse_str(str_replace(',', '&', $header), $p);
$ts  = (int)($p['t'] ?? 0);
$mac = $p['v1'] ?? '';

if (abs(time() - $ts) > 300 ||
    !hash_equals(hash_hmac('sha256', $ts . '.' . $raw, SIBIL_SECRET), $mac)) {
    http_response_code(401); exit;
}

$event = json_decode($raw, true);
if (($event['event'] ?? '') === 'invoice.paid') {
    $orderId = $event['data']['order_id'];
    if (!is_paid($orderId)) {          // یدمپوتنت
        mark_paid($orderId);
        send_receipt_email($orderId);  // فقط یک بار
    }
}
http_response_code(200);
echo '{"ok":true}';
```

در PHP برای گرفتن بدنه خام تنظیم خاصی لازم نیست؛ `php://input` همان بایت‌ها را می‌دهد.

## ۲) Node.js با Express

```js
// sibilpay.js
const crypto = require("crypto");
const SERVER = "https://SERVER";
const KEY    = process.env.SIBILPAY_KEY;
const SECRET = process.env.SIBILPAY_WEBHOOK_SECRET;

async function createInvoice({ toman, orderId, returnUrl }) {
  const r = await fetch(`${SERVER}/api/v1/invoices`, {
    method: "POST",
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      amount_rial: toman * 10,
      order_id: orderId,
      description: `سفارش ${orderId}`,
      callback_url: returnUrl,
      expiry_minutes: 30,
    }),
  });
  const json = await r.json();
  if (!json.success) throw new Error(json.error.message);
  return json.data;               // { id, payment_url, payable_rial, ... }
}

function verifySignature(raw, header, tolerance = 300) {
  const parts = Object.fromEntries(header.split(",").map(p => p.split("=")));
  const ts = Number(parts.t || 0);
  if (Math.abs(Date.now() / 1000 - ts) > tolerance) return false;
  const expected = crypto.createHmac("sha256", SECRET)
    .update(`${ts}.`).update(raw).digest("hex");
  const got = Buffer.from(parts.v1 || "", "hex");
  return got.length === expected.length &&
         crypto.timingSafeEqual(got, Buffer.from(expected, "hex"));
}

module.exports = { createInvoice, verifySignature };
```

```js
// app.js
const express = require("express");
const { createInvoice, verifySignature } = require("./sibilpay");
const app = express();

app.get("/pay/:orderId", async (req, res) => {
  const inv = await createInvoice({
    toman: 250000,
    orderId: req.params.orderId,
    returnUrl: `https://mysite.com/pay/done/${req.params.orderId}`,
  });
  await db.saveInvoiceMapping(req.params.orderId, inv.id);
  res.redirect(inv.payment_url);
});

// ⚠️ raw body برای همین مسیر
app.post("/sibilpay/callback", express.raw({ type: "application/json" }), async (req, res) => {
  if (!verifySignature(req.body, req.get("X-SIBILPAY-Signature") || "")) {
    return res.status(401).send("bad signature");
  }
  const event = JSON.parse(req.body.toString("utf8"));
  res.json({ ok: true });                       // اول 200 بده

  if (event.event === "invoice.paid") {
    setImmediate(async () => {
      const { order_id, paid_amount_rial } = event.data;
      if (!(await db.isPaid(order_id))) {
        await db.markPaid(order_id, paid_amount_rial);
        await mail.sendReceipt(order_id);       // فقط یک بار
      }
    });
  }
});

app.listen(3000);
```

## ۳) Python با Django

```python
# shop/sibilpay.py
import hashlib, hmac, time, requests
from django.conf import settings

SERVER = settings.SIBIL_SERVER
HEADERS = {"Authorization": f"Bearer {settings.SIBIL_KEY}"}

def create_invoice(toman: int, order_id: str, return_url: str) -> dict:
    r = requests.post(f"{SERVER}/api/v1/invoices", headers=HEADERS, timeout=15, json={
        "amount_rial": toman * 10,
        "order_id": order_id,
        "description": f"سفارش {order_id}",
        "callback_url": return_url,
        "expiry_minutes": 30,
    })
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(data["error"]["message"])
    return data["data"]

def signature_ok(raw: bytes, header: str, tolerance: int = 300) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    ts, mac = int(parts.get("t", "0")), parts.get("v1", "")
    if abs(time.time() - ts) > tolerance:
        return False
    expected = hmac.new(settings.SIBIL_WEBHOOK_SECRET.encode(),
                        f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, mac)
```

```python
# shop/views.py
import json
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .sibilpay import create_invoice, signature_ok

def start_payment(request, order_id):
    inv = create_invoice(
        toman=250_000,
        order_id=order_id,
        return_url=request.build_absolute_uri(f"/pay/done/{order_id}/"),
    )
    Order.objects.filter(pk=order_id).update(invoice_id=inv["id"])
    return HttpResponseRedirect(inv["payment_url"])

@csrf_exempt
def sibilpay_callback(request):
    raw = request.body                                   # بایت‌های خام
    if not signature_ok(raw, request.headers.get("X-SIBILPAY-Signature", "")):
        return HttpResponse(status=401)

    event = json.loads(raw)
    if event.get("event") == "invoice.paid":
        order_id = event["data"]["order_id"]
        Order.objects.filter(pk=order_id, paid=False).update(paid=True)  # یدمپوتنت
    return JsonResponse({"ok": True})
```

## ۴) صفحه بازگشت

کاربر بعد از واریز به `callback_url` برمی‌گردد. آنجا تصمیم مالی نگیر و فقط نمایش بده:

```python
# GET /api/v1/invoices/{id}/status  را صدا بزن
# status == "paid"        → «پرداخت تأیید شد ✅»
# status == "pending"     → «در حالِ بررسی، چند لحظه…»
# status == "expired"     → «مهلت تمام شد، دوباره تلاش کن»
# status == "cancelled"   → «لغو شد»
```

اگر کاربر صفحه را بست، webhook باز هم سفارش را paid می‌کند. به «کاربر برگشت» اعتماد نکن؛ به وضعیت یا webhook اعتماد کن.

## تست محلی در دو دقیقه

1. یک فاکتور با کلید test یا فاکتور عادی بساز.
2. `POST /api/v1/test/invoices/{id}/simulate-payment` را بزن.
3. ببین webhook تو رسید، امضا درست بود و سفارش `paid` شد.

بدون این تست سراغ پول واقعی نرو.

بعدی: [امنیت](07-security.md)
