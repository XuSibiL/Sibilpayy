<div dir="rtl" align="right">

# ۰۴ — وب‌هوک: خبرِ «پرداخت شد»

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
| `invoice.paid` | **پرداخت تأیید شد** ← مهم‌ترین |
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
