# ۱۶ — سه دامنه، یک فروشگاه: webhook چندمقصدی

این سند حالت سه بات روی سه دامنه را جواب می‌دهد، وقتی فقط یکی از آن‌ها خبر پرداخت را می‌گیرد یا هر سه سه بار خبر می‌گیرند. فروشگاه یکی است و دامنه‌ها سه‌اند.

## ۰) چرا قبلا نمی‌شد

هر فروشگاه فقط یک `webhook_url` داشت. پس سه بات سه دامنه ناچار بودند یک آدرس مشترک بدهند و نتیجه یکی از این‌ها بود:

- فقط یکی از بات‌ها خبر می‌گرفت و دو تای دیگر منتظر می‌ماندند،
- هر سه به یک آدرس می‌زدند و پیام پرداخت تأیید شد سه بار می‌آمد،
- یا بدتر: امضای یک بات برای بات دیگر معنی نداشت و هر سه خطای امضای نامعتبر می‌گرفتند.

## ۱) تا سه مقصد، هر کدام مستقل

- هر فروشگاه می‌تواند تا سه مقصد webhook داشته باشد و هر مقصد برچسب و آدرس و کلید امضای خودش (`whsec_…`) را دارد.
- هر کلید API به یکی از این مقصدها بسته می‌شود.
- هر فاکتور موقع ساخت هم کلید API را ثبت می‌کند (`webhook_key_id`) و هم مقصد را (`webhook_endpoint`)، پس فاکتور می‌داند از کدام بات آمده، نه فقط از کدام فروشگاه.
- هنگام تأیید فقط همان یک آدرس فراخوانی می‌شود و بقیه هیچ پیامی نمی‌گیرند.
- امضا با کلید همان مقصد ساخته می‌شود، پس هر بات فقط امضای خودش را می‌پذیرد.

اگر از قبل `webhook_url` داشتی همان خودکار مقصد اول می‌شود. لازم نیست چیزی را دستی مهاجرت بدهی و هیچ اتصالی قطع نمی‌شود.

ترتیب انتخاب مقصد این است: `invoices.webhook_endpoint`، بعد اولین مقصد کلیدی که فاکتور با آن ساخته شد، بعد اولین مقصد فروشگاه. فاکتورهای قدیمی که این ستون‌ها را خالی دارند همان مسیر قبلی را می‌روند، پس چیزی نمی‌شکند.

## ۲) API

همه این مسیرها با هدر `X-Admin-Token` کار می‌کنند.

### دیدن مقصدها

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
     "$SERVER/api/v1/admin/stores/$STORE_ID/webhooks"
```

```json
{"success": true, "data": {
  "max": 3,
  "endpoints": [
    {"id": "ep1", "label": "mirza", "url": "https://mirza.example/hook",
     "enabled": true, "secret_masked": "whsec_ab12…"}
  ]
}}
```

### ثبت یا جایگزینی مقصدها، حداکثر سه

```bash
curl -X PUT -H "X-Admin-Token: $ADMIN_TOKEN" -H "Content-Type: application/json" \
     -d '{"endpoints":[{"label":"mirza","url":"https://mirza.example/hook"},
                       {"label":"sibilpay-bot","url":"https://bot.example/hook"},
                       {"label":"site","url":"https://shop.example/hook"}]}' \
     "$SERVER/api/v1/admin/stores/$STORE_ID/webhooks"
```

- فهرست تازه جایگزین فهرست قبلی می‌شود.
- هر مقصدی که کلید نداشته باشد یک `whsec_…` تازه می‌گیرد و کلید قبلی دست‌نخورده می‌ماند.
- بیشتر از سه مورد پذیرفته نمی‌شود و `enabled:false` مقصد را ساکت می‌کند.
- `url` باید با `http://` یا `https://` شروع شود.

### دیدن کلیدهای API و اینکه هر کدام به کدام مقصد بسته است

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
     "$SERVER/api/v1/admin/stores/$STORE_ID/api-keys"
```

### بستن یک کلید به یک مقصد

```bash
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" -H "Content-Type: application/json" \
     -d '{"endpoint":"ep2"}' \
     "$SERVER/api/v1/admin/api-keys/$KEY_ID/webhook"
```

از این لحظه هر فاکتوری که با این کلید ساخته شود فقط به همان مقصد خبر می‌دهد. مقدار `{"endpoint": null}` کلید را آزاد می‌کند و به مقصد اول برمی‌گردد.

## ۲·۵) سه webhook روی هر API، نه فقط هر فروشگاه

اگر یک درگاه یا بات را روی چند دامنه بالا آورده‌ای، سه آدرس را به همان کلید API ببند، نه به فروشگاه:

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" "$SERVER/api/v1/admin/api-keys/$KEY_ID/webhooks"

curl -X PUT -H "X-Admin-Token: $ADMIN_TOKEN" -H "Content-Type: application/json" \
     -d '{"endpoints":[{"label":"iran","url":"https://ir.example/hook"},
                       {"label":"eu","url":"https://eu.example/hook"},
                       {"label":"backup","url":"https://b.example/hook"}]}' \
     "$SERVER/api/v1/admin/api-keys/$KEY_ID/webhooks"
```

- هر مقصد کلید امضای خودش را دارد.
- هر فاکتور کلید و مقصدش را موقع ساخت ثبت می‌کند و خبر تأیید فقط به همان یک آدرس می‌رود، نه به هر سه.
- اولویت این است: مقصدهای کلید، بعد اگر کلید مقصدی نداشت مقصدهای فروشگاه، بعد اگر آن هم نبود `webhook_url` قدیمی.

## ۳) آنچه در webhook می‌رسد

هدرها:

```
X-SIBILPAY-Signature: <HMAC-SHA256 با کلیدِ همان مقصد>
X-SIBILPAY-Event: invoice.paid
X-SIBILPAY-Delivery: whd_…
```

بدنه همان بدنه همیشگی است. برای اینکه بدانی پیام از کدام مقصد آمده، شناسه مقصد داخل مسیر ارسال (`webhook_deliveries.endpoint_id`) ثبت می‌شود و در پنل یا دیتابیس قابل بررسی است.

## ۴) بررسی امضا

هدر `X-SIBILPAY-Signature` به شکل `t=<unix>,v1=<hex>` است و امضا روی `t + "." + raw_body` با secret همان مقصدی ساخته می‌شود که پیام به آن می‌رود:

```python
import hmac, hashlib, time

def verify(raw_body: bytes, header: str, secret: str, tolerance: int = 300) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(","))   # t=...,v1=...
    ts, signature = int(parts["t"]), parts["v1"]
    if abs(time.time() - ts) > tolerance:                     # محافظت از بازپخش
        return False
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

`raw_body` بایت‌های خام بدنه است؛ اگر بدنه را دوباره `json.dumps` کنی امضا نمی‌خواند. نمونه کامل ساخت یک اتصال تازه با کلید API به‌جای توکن ادمین در [سند ۱۸](18-connect-a-bot.md) است.

## ۵) خطاهای رایج

| کد | معنی | کار |
|---|---|---|
| `UNKNOWN_ENDPOINT` | مقصدی که می‌خواهی کلید را به آن ببندی در این فروشگاه ثبت نشده | اول `PUT .../webhooks` |
| `STORE_NOT_FOUND` | شناسه فروشگاه غلط است | `GET /api/v1/admin/stores` |
| `KEY_NOT_FOUND` | شناسه کلید غلط است | `GET .../api-keys` |

## ۶) کارمزد

کارمزد از کیف کارمزد فروشگاه کسر می‌شود، نه از پول فروش. پول مشتری مستقیم روی کارت خودت می‌نشیند.

- نرخ روی هر فروشگاه تنظیم می‌شود (`fee_bps`) و در پنل دیده می‌شود.
- مبلغ در همان لحظه ساخت فاکتور از کیف کسر و در `wallet_transactions` ثبت می‌شود.
- کیف که خالی شود فاکتور ساخته نمی‌شود (`402 WALLET_INSUFFICIENT`) و همان لحظه به فروشنده در ربات پیام می‌رود که مشتری‌اش فاکتور خواسته و موجودی ندارد. موجودی منفی نمی‌شود، از ربات شارژ کن.
- فروشگاه‌های مالک سرویس و فروشگاه پلتفرم کارمزد ندارند و هیچ‌وقت بلاک نمی‌شوند.
- فاکتور منقضی یا لغوشده کارمزد ندارد.

## ۷) حذف فروشگاه

در «فروشگاه‌های من» و تنظیمات و جزئیات هر فروشگاه:

- فروشگاه اصلی، یعنی اولین فروشگاه مالک که ادمین تأیید کرده، دکمه حذف ندارد و از هر مسیری رد می‌شود.
- فروشگاه‌های دوم و سوم: دکمه حذف، بعد پیام هشدار، و باید کلمه بله را بنویسی.
- اگر فاکتور بازی داشته باشد حذف انجام نمی‌شود تا اول آن‌ها را لغو کنی.

## ۸) اتصال خودکار یک بات، بدون توکن ادمین

اگر خود بات می‌خواهد مقصدش را ثبت کند، مسیرهای `X-Admin-Token` به کارش نمی‌آید. با کلید API همین اتصال انجام می‌شود:

```http
GET  /api/v1/hooks/self
PUT  /api/v1/hooks/self          {"url": "https://mirza.example/hook", "label": "mirza"}
POST /api/v1/hooks/self/rotate   {"id": "ep1"}
POST /api/v1/hooks/self/test     {"id": "ep1"}
GET  /api/v1/hooks/self/deliveries
```

هر کلید فقط مقصدهای خودش را می‌بیند و می‌سازد؛ ثبت دوباره همان آدرس مقصد تکراری نمی‌سازد و secret را عوض نمی‌کند. جزئیات کامل و خطاها و قرارداد امضا در [سند ۱۸](18-connect-a-bot.md) است.

## ۹) «اتصالات» در ربات

در بخش «بیشتر» یک دکمه «اتصالات» هست که همان سؤال را جواب می‌دهد:

```
🔌 اتصالات — MR SIBIL

🌐 وبوکِ فروشگاه: ۲ از ۳ وصل
  ۱) مقصد اصلی — panel.example.com ✅
  ۲) بکاپ — backup.example.com ✅
  ۳) —

🔑 کلیدهای API (هر کدام تا ۳ مقصدِ جدا):
  • pk_ab12… · bot-1 — ۲ از ۳
  ۱) iran — ir.example.com ✅
  ۲) eu — eu.example.com ✅
  ۳) —

✅ آخرین ارسال: invoice.paid · 200 · 11-17 14:02
```

دکمه «جزئیات و ارسال آزمایشی» همان صفحه `/hooks` را باز می‌کند.
