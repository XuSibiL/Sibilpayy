# ۱۸ — وصل کردن یک بات به webhook چندمقصدی

یک ربات، مثلا «میرزا» یا «سیبیل‌پنل»، فقط کلید API فروشگاه و یک آدرس https دارد. این سند نشان می‌دهد چطور مقصد webhook خودش را ثبت کند، بدون توکن ادمین، بدون دست زدن به اتصال بات‌های دیگر، و طوری که هر فاکتور فقط به همان مقصدی برود که از آن ساخته شده است.

## ۰) دو نوع مسیر، دو نوع دسترسی

| مسیر | دسترسی | برای چه کسی |
|---|---|---|
| `/api/v1/admin/stores/{store}/webhooks` | `X-Admin-Token` | اپراتور پلتفرم، پنل ادمین |
| `/api/v1/hooks/self` | `Authorization: Bearer <کلید_API همین فروشگاه>` | خود اتصال، یعنی بات یا سایت یا فروشگاه |

مسیرهای ادمین به همه کلیدها و مقصدهای یک فروشگاه دسترسی دارند. مسیرهای `hooks/self` فقط روی مقصدهای همان کلیدی کار می‌کنند که توکنش را فرستاده، نه کلید دیگر و نه فروشگاه دیگر. اگر بخواهی به مقصد یک کلید دیگر دست بزنی پاسخ `404 UNKNOWN_ENDPOINT` است، نه ۴۰۳، تا حتی وجود آن مقصد هم لو نرود.

## ۱) فهرست مقصدهای همین کلید

```http
GET /api/v1/hooks/self
Authorization: Bearer sp_live_…
```

```json
{"success": true, "data": {
  "key": "pk_ab12",
  "max": 3,
  "count": 1,
  "endpoints": [
    {"id": "ep1", "label": "mirza", "url": "https://mirza.example/hook",
     "enabled": true, "secret_masked": "whsec_afab…", "bound": true,
     "last": {"event": "invoice.paid", "status": "delivered", "code": 200,
              "attempts": 1, "at": "2026-11-17T12:40:11+00:00", "error": null}}
  ]
}}
```

`secret_masked` تنها شکلی است که secret در آن دیده می‌شود. `last` آخرین تحویل همان آدرس است و `null` یعنی هنوز چیزی نرفته.

## ۲) ثبت مقصد خودش، بدون توکن ادمین و بدون تخریب

```http
PUT /api/v1/hooks/self
Content-Type: application/json

{"url": "https://mirza.example/hook", "label": "mirza"}
```

قواعد دقیق:

| حالت | رفتار |
|---|---|
| آدرس تازه و کمتر از سه مقصد | مقصد ساخته می‌شود با `created: true` و secret کامل فقط در همین پاسخ |
| همان آدرس دوباره | همان مقصد برمی‌گردد با `created: false`؛ نه مقصد تکراری و نه secret تازه |
| `{"id": "ep2", "url": "…"}` | آدرس همان مقصد عوض می‌شود و secret دست‌نخورده می‌ماند با `secret_unchanged: true` |
| سه مقصد پر است و آدرس چهارم می‌آید | `409 LIMIT_REACHED` و هیچ مقصدی خودکار حذف نمی‌شود |
| `{"id": "ep9"}` که مال این کلید نیست | `404 UNKNOWN_ENDPOINT` |
| آدرس `http://` غیر لوکال | `400 INVALID_URL` |
| دو درخواست هم‌زمان | یک بار تکرار خودکار؛ اگر باز هم برخورد بود `409 CONCURRENT_UPDATE` و همان درخواست را دوباره بفرست |

پاسخ ساخت:

```json
{"success": true, "data": {
  "created": true, "id": "ep1", "url": "https://mirza.example/hook",
  "secret": "whsec_afab5b7561b673caa07e300117597c24b7caeac4720529f3",
  "secret_note": "این secret دیگر نمایش داده نمی‌شود؛ گم شد → rotate",
  "count": 1, "max": 3
}}
```

این مسیر هیچ‌وقت کل فهرست را جایگزین نمی‌کند. `PUT` روی مسیرهای ادمین یعنی «همه را با این فهرست عوض کن»، ولی اینجا `PUT` یعنی «این یکی را بساز یا پیدا کن». پس بات تازه نمی‌تواند اتصال بات دیگر را پاک کند.

## ۳) کدام مقصد برای کدام فاکتور

هنگام ساخت فاکتور، مقصد به این ترتیب انتخاب و روی خود فاکتور ثبت می‌شود:

1. اگر بدنه فاکتور فیلد `webhook_endpoint` را داشته باشد و آن مقصد متعلق به همان کلید باشد، همان.
2. وگرنه اولین مقصد همان کلید.
3. فاکتورهای قدیمی که این فیلد را ندارند، اولین مقصد فروشگاه را می‌گیرند؛ همان رفتار قبلی بدون قطعی.

```http
POST /api/v1/invoices
Authorization: Bearer sp_live_…
Content-Type: application/json

{
  "amount_rial": 500000,
  "order_id": "ORD-1001",
  "webhook_endpoint": "ep2"
}
```

- `webhook_endpoint` اختیاری است و بقیه بدنه همان قبلی است.
- مقصدی که متعلق به این کلید نباشد فاکتور را رد نمی‌کند. نادیده گرفته می‌شود و فاکتور با مقصد پیش‌فرض همین کلید ساخته می‌شود؛ پاسخ همان `201` است.
- هنگام تأیید پرداخت فقط همان یک آدرس فراخوانی می‌شود، با secret همان مقصد.
- اگر کلید عوض شود یا مقصد پاک شود، فاکتورهای قبلی همان مقصدی که ثبت کرده‌اند را نگه می‌دارند؛ اگر آن مقصد دیگر وجود نداشته باشد به اولین مقصد فروشگاه برمی‌گردند.

## ۴) امضای webhook، یک قاعده نه دو تا

هدر:

```
X-SIBILPAY-Signature: t=1763380800,v1=e3ad64aa…
X-SIBILPAY-Event: invoice.paid
X-SIBILPAY-Delivery: whd_…
```

قاعده:

```
string_to_sign = f"{t}." + raw_body
v1             = HMAC_SHA256(secret_of_that_endpoint, string_to_sign).hexdigest()
```

- `secret` همان مقصدی است که پیام به آن می‌رود (`whsec…`)، نه secret فروشگاه.
- `raw_body` بایت‌های خام بدنه است، پیش از هر پارس یا بازچینش. اگر بدنه را دوباره `json.dumps` کنی امضا نمی‌خواند.
- برای جلوگیری از replay مقدار `t` را با ساعت خودت مقایسه کن و اختلاف بیش از ۳۰۰ ثانیه را رد کن. `X-SIBILPAY-Delivery` را هم نگه دار، چون تحویل دوباره همان شناسه را دارد.

نمونه تست با secret آزمایشی:

```
secret = "whsec_test_123"
body   = {"event":"invoice.paid","data":{"id":"inv_9001","status":"paid"}}
t      = 1763380800
v1     = e3ad64aa1f8e55a9db83cce8862ada3804abf7d8ee64d2a25bbd3f26c532bfd2
header = t=1763380800,v1=e3ad64aa1f8e55a9db83cce8862ada3804abf7d8ee64d2a25bbd3f26c532bfd2
```

```python
import hmac, hashlib
expected = hmac.new(secret.encode(), f"{t}.".encode() + raw_body, hashlib.sha256).hexdigest()
assert hmac.compare_digest(expected, v1)
```

## ۵) گرفتن secret و چرخش آن

- secret فقط یک بار برمی‌گردد: در پاسخ ساخت (`PUT`) و در پاسخ چرخش.
- `GET` همیشه `secret_masked` می‌دهد و راهی برای خواندن دوباره secret کهنه نیست.
- اگر پاسخ ساخت وسط راه قطع شد و secret را نگرفتی:

```http
POST /api/v1/hooks/self/rotate
{"id": "ep1"}
```

```json
{"success": true, "data": {"id": "ep1", "url": "https://mirza.example/hook",
  "secret": "whsec_a85b7323…", "note": "فقط همین یک بار نمایش داده می‌شود"}}
```

بعد از چرخش امضاهای قبلی معتبر نیستند؛ مقصد همان است و آدرس عوض نمی‌شود. secret مقصدهای دیگر هرگز در این پاسخ‌ها نمی‌آید.

## ۶) تست و دیدن وضعیت

```http
POST /api/v1/hooks/self/test          # یک رویدادِ hook.test به مقصدِ همین کلید
{"id": "ep1"}                          # اختیاری
```

```json
{"success": true, "data": {"queued": true, "delivery_id": "whd_a5388440c6",
  "url": "https://mirza.example/hook", "endpoint_id": "ep1"}}
```

وضعیت تحویل:

```http
GET /api/v1/hooks/self/deliveries?limit=10
```

```json
{"success": true, "data": {"count": 1, "items": [
  {"id": "whd_a5388440c6", "event": "hook.test", "status": "delivered",
   "code": 200, "attempts": 1, "url": "https://mirza.example/hook",
   "at": "2026-11-17T12:41:02+00:00", "error": null}
]}}
```

این فهرست فقط تحویل‌های مقصدهای همین کلید را نشان می‌دهد.

## ۷) رواداری ۱۰ ریالی، کجا هست و کجا نیست

رواداری فقط در تطبیق واریزی اعمال می‌شود، یعنی از پیامک بانک به فاکتور، چون بانک مبلغ را به تومان گِرد می‌کند. روی وضعیت `paid` و پاسخ‌های `GET` و `verify` هیچ محاسبه تازه‌ای انجام نمی‌شود؛ آن‌ها فقط واقعیت ثبت‌شده را برمی‌گردانند.

نمونه: فاکتور با `amount_rial = 300000` و `payable_rial = 300075` و واریزی `300070`، یعنی ۵ ریال کم چون بانک گِرد کرده:

| فراخوانی | نتیجه |
|---|---|
| `GET /api/v1/invoices/{id}` | `status: "paid"` و `payable_rial: 300075` و `paid_amount_rial: 300070` |
| `GET /api/v1/invoices/{id}/status` | `paid` |
| `POST /api/v1/invoices/{id}/verify` | `{"verified": true, "verified_at": "…", "receipt_token": "…"}` |

مبنای مبلغ وصول‌شده `paid_amount_rial` است و مبنای طلب سفارش `amount_rial`. `payable_rial` فقط مبلغ دقیق قابل پرداخت با دنباله یکتاست و مبنای حسابداری نیست. ۱۰ ریال رواداری مجوز نادیده گرفتن کسری واقعی نیست: اگر واریزی بیش از ۱۰ ریال کم باشد فاکتور `partial` می‌شود و در نیازمند بررسی می‌ماند.

## ۸) کارمزد و کیف اعتبار

| چه کسی | کارمزد | اگر کیف کافی نباشد |
|---|---|---|
| فروشگاه‌های کاربران | نرخ پلتفرم، مثلا ۲۰۰۰ تومان، بابت هر فاکتور، همان لحظه ساخت | فاکتور ساخته نمی‌شود (`402 WALLET_INSUFFICIENT`) و همان لحظه به خود فروشنده در ربات پیام می‌رود |
| فروشگاه‌های مالک سرویس و فروشگاه پلتفرم | صفر | هیچ‌وقت بلاک نمی‌شوند |

قاعده‌ها:

- کارمزد از کیف کارمزد فروشگاه کم می‌شود، نه از پول فروش، و موجودی منفی نمی‌شود.
- مبلغ در همان لحظه ساخت فاکتور کسر می‌شود و فاکتور منقضی یا لغوشده کارمزدی ندارد.
- هشدارهای موجودی برای فروشنده: رسیدن به ۲۰٬۰۰۰ تومان و ۱۰٬۰۰۰ تومان و کمتر از یک کارمزد. هر سطح یک بار پیام می‌دهد، نه یکی برای هر فاکتور.
- پیام «مشتری‌ات فاکتور خواست»: وقتی مشتری فاکتور می‌خواهد و کیف فروشنده کافی نیست، به فروشنده در ربات خبر می‌رسد با فروشگاه و مبلغ درخواستی و کارمزد و موجودی و این نکته که فاکتور ساخته نشد. برای جلوگیری از رگبار، حداکثر هر ۳۰ دقیقه یک پیام.
- پیامی که مشتری می‌بیند عمدا خنثی است، مثل «درگاه موقتا در دسترس نیست»، و دلیل واقعی فقط به فروشنده گفته می‌شود.
- بعد از شارژ کیف، ساخت فاکتور بدون کار اضافه برمی‌گردد و مشتری لازم نیست دوباره پرداخت کند، چون فاکتور ردشده اصلا ساخته نشده است.

## ۹) چک‌لیست اتصال یک بات تازه

1. `GET /api/v1/hooks/self` بزن و ببین از سه مقصد چند تا پر است.
2. `PUT /api/v1/hooks/self` با آدرس https خودت بزن و secret را همان‌جا ذخیره کن.
3. `POST /api/v1/hooks/self/test` بزن و تحویل را در `/deliveries` ببین.
4. در ساخت فاکتور اگر لازم شد `webhook_endpoint` را بده، وگرنه مقصد همین کلید خودکار انتخاب می‌شود.
5. امضا را با `t.<body>` و secret همان مقصد بررسی کن و بیش از ۳۰۰ ثانیه را رد کن.

## ۱۰) الگوی امن در کد ربات

سه خط زیر جلوی بیشتر خطاهای گزارش‌شده را می‌گیرد: `order_id` ثابت برای هر سفارش، تلاش دوباره روی `503` و `429`، و نفرستادن `webhook_endpoint` دستی.

```python
import asyncio, httpx

async def create_invoice(base, key, order_id, amount_rial):
    payload = {"amount_rial": amount_rial, "order_id": order_id}
    for attempt in range(5):
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(f"{base}/api/v1/invoices", json=payload,
                             headers={"Authorization": f"Bearer {key}"})
        if r.status_code in (200, 201):
            return r.json()["data"]
        if r.status_code in (429, 503) or r.status_code >= 500:
            await asyncio.sleep(min(3, 0.3 * 2 ** attempt))
            continue
        raise RuntimeError(r.json()["error"])
    got = await c.get(f"{base}/api/v1/invoices/by-order/{order_id}",
                      headers={"Authorization": f"Bearer {key}"})
    if got.status_code == 200:
        return got.json()["data"]
    raise RuntimeError("سرویس پرداخت جواب نداد")
```

- `order_id` تکراری فاکتور تکراری نمی‌سازد، پس تلاش دوباره بی‌خطر است.
- `200` با `idempotent_replay: true` یعنی این سفارش از قبل فاکتور دارد و همان برگشته است.
- `503 DB_BUSY` و `429` را با تأخیر کوتاه دوباره بفرست، نه با خطا به کاربر.
