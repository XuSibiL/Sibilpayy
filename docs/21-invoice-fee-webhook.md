# ۲۱ — ساخت فاکتور، کارمزد و webhook

این سند رفتار کد ۱.۵.۹.۸۲ است. هر بندش با آزمون خودکار همان نسخه سنجیده شده. اگر جایی کد و سند اختلاف داشتند، کد درست است.

## کارمزد در لحظه ساخت

کارمزد در همان لحظه ساخت فاکتور از کیف پول فروشگاه کم می‌شود. اگر کیف پول کم باشد فاکتور ساخته نمی‌شود؛ نه بعدا کم می‌شود، نه بدهکار می‌شوی، نه فاکتور نیمه‌کاره می‌مانی.

ترتیب کارها در `POST /api/v1/invoices`:

1. مبلغ بررسی می‌شود: بزرگ‌تر از صفر و کمتر از ۵۰٬۰۰۰٬۰۰۰٬۰۰۰ ریال (`400 INVALID_AMOUNT`).
2. کارت فعال همان فروشگاه انتخاب می‌شود؛ اگر نبود `409 NO_CARD_AVAILABLE` و هیچ مبلغی کم نمی‌شود.
3. کارمزد همان فروشگاه حساب می‌شود: `fee_flat_rial`. فروشگاه اپراتور و طرح رایگان صفر است.
4. کارمزد صفر یعنی بدون دروازه و بدون کسر، فاکتور ساخته می‌شود.
5. کارمزد بزرگ‌تر از صفر و `wallet_balance_rial` کمتر از آن یعنی `402 WALLET_INSUFFICIENT`، فاکتور ساخته نمی‌شود و به فروشنده در ربات پیام شارژ می‌رود. متن خطا برای مشتری بی‌طرفانه است («درگاه پرداخت این فروشگاه موقتا در دسترس نیست») تا کیف پول فروشنده لو نرود.
6. موجودی کافی: کارمزد کم می‌شود، یک ردیف `wallet_transactions` با `kind = 'fee'` و `invoice_id` همان فاکتور نوشته می‌شود و بعد فاکتور ساخته می‌شود. اگر ساخت فاکتور شکست بخورد همان تراکنش برمی‌گردد.
7. مسیر پرداخت کارمزد نمی‌گیرد. وقتی پرداخت تأیید شد، `wallet.charge_fee` ردیف `fee` همان فاکتور را می‌بیند و بدون کسری برمی‌گرداند؛ کمیسیون نماینده هم بر اساس همان ردیف پرداخت می‌شود. آزمون K همین را می‌سنجد: موجودی بعد از تأیید پرداخت دست‌نخورده می‌ماند و ردیف `fee` همان فاکتور یکی است.

نتیجه: کارمزد یک بار گرفته می‌شود، قبل از اینکه فاکتور وجود داشته باشد.

## انتخاب کارت

| وضعیت فروشگاه | رفتار |
|---|---|
| کارت فعال دارد | فاکتور با کارت خود همین فروشگاه ساخته می‌شود |
| کارت دارد ولی غیرفعال است | `409 NO_CARD_AVAILABLE`، فاکتور ساخته نمی‌شود، کارمزد کم نمی‌شود |
| هیچ کارتی ندارد | `409 NO_CARD_AVAILABLE`، فاکتور ساخته نمی‌شود، کارمزد کم نمی‌شود |

کارت فروشگاه دیگر هیچ‌وقت استفاده نمی‌شود؛ شرط همیشه «همان فروشگاه و فعال» است. کارت غیرفعال یعنی «به این حساب پرداخت نکن»، پس ساخت فاکتور هم معنا ندارد. کارت فروشگاه اپراتور با همان قاعده سنجیده می‌شود و فقط چون کارمزدش صفر است دروازه کیف پول ندارد.

## `POST /api/v1/invoices`

```json
{
  "amount_rial": 150000,
  "order_id": "order-1001",
  "description": "سفارش ۱۰۰۱",
  "customer_name": "مشتری",
  "callback_url": "https://shop.example/cb",
  "webhook_endpoint": "ep_xxxxxxxx",
  "webhook_key_id": null
}
```

| فیلد | اجباری | توضیح |
|---|---|---|
| `amount_rial` | بله | ریال، بزرگ‌تر از صفر |
| `order_id` | خیر | با همان `order_id` همان فاکتور با `200` و `idempotent_replay: true` برمی‌گردد و کارمزد تازه کسر نمی‌شود |
| `webhook_endpoint` | خیر | شناسه یا آدرس یکی از مقصدهای همین کلید؛ اگر مال کلید دیگری باشد نادیده گرفته می‌شود |
| `webhook_key_id` | خیر | شناسه کلید، اگر مقصد به کلید بسته شده باشد |
| `callback_url` | خیر | بازگشت مرورگر مشتری پس از پرداخت |

`payable_rial` معمولا همان `amount_rial` است. اگر همان مبلغ روی همان کارت در فاکتور باز دیگری گرفته شده باشد، نزدیک‌ترین مبلغ آزاد (حداکثر ۹٬۹۹۹ ریال بیشتر) انتخاب می‌شود تا دو واریز با هم اشتباه نشوند. مبلغ نهایی همیشه در `payable_rial` برمی‌گردد و در `payment_url` هم همان است.

## خطاها

| کد | HTTP | کی |
|---|---|---|
| `INVALID_API_KEY` | 401 | کلید نامعتبر یا غیرفعال |
| `INVALID_AMOUNT` | 400 | مبلغ صفر یا منفی یا بیش از ۵۰ میلیارد ریال |
| `WALLET_INSUFFICIENT` | 402 | کیف پول کارمزد همین فروشگاه کمتر از یک کارمزد است |
| `NO_CARD_AVAILABLE` | 409 | فروشگاه کارت فعال ندارد |
| `AMOUNT_POOL_EXHAUSTED` | 409 | همه مبلغ‌های آزاد آن کارت پر شده؛ فاکتورهای باز را ببند |

شکل پاسخ خطا مثل بقیه مسیرهاست: `{"success": false, "data": null, "error": {...}}`.

## webhook مقصد همان فاکتور

`webhook_endpoint` روی خود فاکتور ذخیره می‌شود، در ستون `invoices.webhook_endpoint`. رویداد `invoice.created` و بقیه رویدادهای همان فاکتور فقط به همان مقصد می‌رود و با کلید همان مقصد امضا می‌شود، نه با کلید فروشگاه. اگر مقصدی انتخاب نشده باشد، مقصد اول فروشگاه و در نبود آن `stores.webhook_secret` به کار می‌رود.

### سه مسیر امضا

هر تلاش با یکی از این سه شکل امضا می‌شود تا مقصد یکی را قبول کند. مقصد فقط باید یکی را بپذیرد و بقیه را نادیده بگیرد.

| ترتیب | مسیر | مقدار `X-SIBILPAY-Signature` | کلید | برای چه کسی |
|---|---|---|---|---|
| ۱، اگر آدرس توکن دارد | `legacy-token` | `hex(HMAC_SHA256(token, raw_body))` | توکن داخل آدرس مقصد (`?hook=` یا `?token=` یا `?secret=` یا `?key=` یا `?sig=` یا `?signature=`) | پیاده‌سازی‌های رایج PHP و Node |
| ۲ | `modern` | `t=<unix>,v1=<hex(HMAC_SHA256(secret, "<unix>." + raw_body))>` | کلید همان مقصد | روش مستند و امن |
| ۳ | `legacy-store` | `hex(HMAC_SHA256(secret, raw_body))` | کلید همان مقصد | نسخه‌های قدیمی |

هدرهای همراه هر درخواست:

```
Content-Type: application/json
X-SIBILPAY-Event: invoice.created
X-SIBILPAY-Delivery: whd_xxxxxxxx        ← شناسهٔ همین تحویل (برای حذفِ تکرار)
X-SIBILPAY-Signature-Mode: modern        ← همین تلاش با کدام مسیر امضا شده
X-SIBILPAY-Signature: …                  ← مقدارِ همان مسیر (جدولِ بالا)
X-SIBILPAY-Signature-Hex: <hex>          ← همان HMAC به‌صورتِ hex خالی
X-Signature: <hex>
X-Hub-Signature-256: sha256=<hex>
User-Agent: SIBILPAY/1.0 (+webhook)
```

هدر `X-SIBILPAY-Signature-Mode` می‌گوید همین درخواست با کدام کلید و کدام قالب امضا شده. اگر مقصدت چند شکل را می‌پذیرد، بر اساس همین هدر تصمیم بگیر.

### تلاش‌ها

- مهلت هر درخواست ۸ ثانیه است و ارسال در پس‌زمینه انجام می‌شود، پس پاسخ ساخت فاکتور کند نمی‌شود.
- تا ۸ تلاش با فاصله `5 × 2^(n-1)` ثانیه و سقف یک ساعت. هر تلاش مسیر بعدی امضا را امتحان می‌کند، پس مقصدی که فقط `modern` را قبول می‌کند در تلاش دوم به نتیجه می‌رسد.
- پاسخ 2xx یعنی `delivered` و پایان. پاسخ غیر 2xx یعنی تلاش بعدی.
- تحویل «حداقل یک بار» است: ممکن است یک رویداد دو بار برسد، با تلاش موازی یا قطع اتصال بعد از دریافت. مصرف‌کننده باید با `X-SIBILPAY-Delivery` یا `id` فاکتور تکرار را حذف کند. رویداد گم‌شده بدتر از رویداد تکراری است.
- هر تلاش با کد پاسخش در `GET /api/v1/hooks/self/deliveries` ثبت می‌شود.

## تأیید امضا

بدنه خام را امضا کن، یعنی همان بایت‌هایی که رسیده، نه JSON بازسازی‌شده. مقایسه را هم زمان‌ثابت انجام بده.

### PHP

```php
<?php
$raw  = file_get_contents('php://input');
$mode = $_SERVER['HTTP_X_SIBILPAY_SIGNATURE_MODE'] ?? 'modern';
$head = $_SERVER['HTTP_X_SIBILPAY_SIGNATURE'] ?? '';

if ($mode === 'modern') {
    // t=...,v1=...
    parse_str(str_replace(',', '&', $head), $parts);
    $signed = $parts['t'] . '.' . $raw;
    $ok = hash_equals(hash_hmac('sha256', $signed, $endpointSecret), $parts['v1']);
} else {
    // legacy-token یا legacy-store: hex خالی روی بدنه
    $ok = hash_equals(hash_hmac('sha256', $raw, $mode === 'legacy-token' ? $urlToken : $endpointSecret),
                      $head);
}
if (!$ok) { http_response_code(401); exit; }
echo 'ok';        // 2xx = تحویل موفق
```

### Node و JavaScript

```js
const crypto = require('crypto');

function verify({ rawBody, header, mode, secret, urlToken }) {
  const hmac = (key, data) =>
    crypto.createHmac('sha256', key).update(data).digest('hex');

  if (mode === 'modern') {
    const parts = Object.fromEntries(header.split(',').map((p) => p.split('=')));
    const expected = hmac(secret, `${parts.t}.` + rawBody);
    return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(parts.v1));
  }
  const key = mode === 'legacy-token' ? urlToken : secret;
  const expected = hmac(key, rawBody);
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(header));
}
// Express: app.use(express.raw({ type: 'application/json' })) تا rawBody خام بماند
```

### Python

```python
import hashlib
import hmac


def verify(raw_body: bytes, header: str, mode: str, secret: str, url_token: str = "") -> bool:
    if mode == "modern":
        parts = dict(part.split("=", 1) for part in header.split(","))
        expected = hmac.new(secret.encode(), f"{parts['t']}.".encode() + raw_body,
                            hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, parts["v1"])
    key = url_token if mode == "legacy-token" else secret
    expected = hmac.new(key.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)
```

### Go

```go
func verify(rawBody []byte, header, mode, secret, urlToken string) bool {
	if mode == "modern" {
		var ts, sig string
		for _, part := range strings.Split(header, ",") {
			kv := strings.SplitN(part, "=", 2)
			if len(kv) != 2 {
				return false
			}
			if kv[0] == "t" {
				ts = kv[1]
			} else if kv[0] == "v1" {
				sig = kv[1]
			}
		}
		mac := hmac.New(sha256.New, []byte(secret))
		mac.Write([]byte(ts + "."))
		mac.Write(rawBody)
		return hmac.Equal([]byte(hex.EncodeToString(mac.Sum(nil))), []byte(sig))
	}
	key := secret
	if mode == "legacy-token" {
		key = urlToken
	}
	mac := hmac.New(sha256.New, []byte(key))
	mac.Write(rawBody)
	return hmac.Equal([]byte(hex.EncodeToString(mac.Sum(nil))), []byte(header))
}
```

### Ruby

```ruby
require 'openssl'

def secure_compare(a, b)                     # مقایسهٔ زمان‌ثابت، بی‌نیاز از Rack
  return false unless a.bytesize == b.bytesize
  res = 0
  a.bytes.zip(b.bytes) { |x, y| res |= x ^ y }
  res.zero?
end

def verify(raw_body, header, mode, secret, url_token = nil)
  if mode == 'modern'
    parts = header.split(',').map { |p| p.split('=', 2) }.to_h
    expected = OpenSSL::HMAC.hexdigest('sha256', secret, "#{parts['t']}.#{raw_body}")
    secure_compare(expected, parts['v1'])
  else
    key = mode == 'legacy-token' ? url_token : secret
    secure_compare(OpenSSL::HMAC.hexdigest('sha256', key, raw_body), header)
  end
end
```

### Java

```java
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HashMap;
import java.util.Map;

static String hexMac(String key, byte[] data) throws Exception {
    Mac mac = Mac.getInstance("HmacSHA256");
    mac.init(new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
    byte[] out = mac.doFinal(data);
    StringBuilder sb = new StringBuilder();
    for (byte b : out) sb.append(String.format("%02x", b));
    return sb.toString();
}

static boolean verify(byte[] rawBody, String header, String mode,
                      String secret, String urlToken) throws Exception {
    if ("modern".equals(mode)) {
        Map<String, String> parts = new HashMap<>();
        for (String part : header.split(",")) {
            String[] kv = part.split("=", 2);
            parts.put(kv[0], kv[1]);
        }
        byte[] prefix = (parts.get("t") + ".").getBytes(StandardCharsets.UTF_8);
        byte[] signed = new byte[prefix.length + rawBody.length];
        System.arraycopy(prefix, 0, signed, 0, prefix.length);
        System.arraycopy(rawBody, 0, signed, prefix.length, rawBody.length);
        String expected = hexMac(secret, signed);
        byte[] a = expected.getBytes(StandardCharsets.UTF_8);
        byte[] b = parts.get("v1").getBytes(StandardCharsets.UTF_8);
        return MessageDigest.isEqual(a, b);
    }
    String key = "legacy-token".equals(mode) ? urlToken : secret;
    return MessageDigest.isEqual(hexMac(key, rawBody).getBytes(StandardCharsets.UTF_8),
                                 header.getBytes(StandardCharsets.UTF_8));
}
```

### C# و .NET

```csharp
using System;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

static string HexMac(string key, byte[] data)
{
    using var hmac = new HMACSHA256(Encoding.UTF8.GetBytes(key));
    return Convert.ToHexString(hmac.ComputeHash(data)).ToLowerInvariant();
}

static bool Verify(byte[] rawBody, string header, string mode, string secret, string urlToken)
{
    if (mode == "modern")
    {
        var parts = header.Split(',')
            .Select(p => p.Split('=', 2))
            .ToDictionary(p => p[0], p => p[1]);
        var prefix = Encoding.UTF8.GetBytes(parts["t"] + ".");
        var signed = prefix.Concat(rawBody).ToArray();      // پیشوند + بدنهٔ خام
        var expected = HexMac(secret, signed);
        return CryptographicOperations.FixedTimeEquals(
            Encoding.UTF8.GetBytes(expected), Encoding.UTF8.GetBytes(parts["v1"]));
    }
    var key = mode == "legacy-token" ? urlToken : secret;
    return CryptographicOperations.FixedTimeEquals(
        Encoding.UTF8.GetBytes(HexMac(key, rawBody)), Encoding.UTF8.GetBytes(header));
}
```

### هر زبان دیگری با openssl

```bash
# modern
printf 't=%s.v1=%s\n' "$TS" "$(printf '%s.%s' "$TS" "$RAW" \
  | openssl dgst -sha256 -hmac "$SECRET" -r | cut -d' ' -f1)"

# legacy-token / legacy-store
printf '%s' "$RAW" | openssl dgst -sha256 -hmac "$KEY" -r | cut -d' ' -f1
```

بدون کتابخانه و بدون SDK: بایت‌های خام، HMAC-SHA256 و hex.

نمونه‌های بالا با یک بردار مشترک اجرا شده‌اند: بدنه `{"a":1,"b":"x"}`، کلید `whsec_demo` و زمان `1700000000`. هر شش نمونه برای `modern`، `legacy-token` و `legacy-store` مقدار true و برای کلید اشتباه false داده‌اند. فایل‌های اجراشده در `docs/examples/webhook-verify/` هست.

## شکل پاسخ ساخت فاکتور

```json
{
  "success": true,
  "data": {
    "id": "inv_...",
    "status": "pending",
    "amount_rial": 150000,
    "payable_rial": 150000,
    "payment_url": "https://<host>/pay/card/inv_...",
    "short_payment_url": "https://<host>/pay/inv_...",
    "gateway_url": "https://<host>/g/<slug>",
    "store": { "...": "..." },
    "card": { "...": "..." },
    "idempotent_replay": false
  },
  "error": null
}
```

## چطور تست شده

آزمون ۱۳ حالته روی همان کد نصب‌شده و روی یک کپی از دیتابیس اجرا می‌شود و به دیتابیس اصلی دست نمی‌زند. اگر یکی قرمز شود نصب خودش به نسخه قبل برمی‌گردد.

| # | چه چیزی سنجیده می‌شود |
|---|---|
| A | کیف پول خالی: `402` و هیچ فاکتوری |
| B | کیف پول کافی: `201` و کارمزد کسر شد |
| C | فاکتور بعدی با کیف پول خالی: `402` |
| D | کارمزد صفر: `201` و هیچ کسری |
| E | کارت غیرفعال: `409` و بدون کسری |
| F | فروشگاه بی‌کارت: `409` و بدون کسری |
| G | ۳۰ فاکتور هم‌مبلغ: ۳۰ فاکتور و ۳۰ کارمزد |
| H | `webhook_endpoint` روی فاکتور ذخیره شد و تحویل به همان مقصد ثبت شد |
| I | فراخوانی دوباره کارمزد: بدون کسری و یک ردیف |
| J1 | مقصد با توکن: امضای `legacy-token` پذیرفته شد |
| J2 | مقصدی که فقط `modern` را می‌پذیرد: پذیرفته شد |
| J3 | سلسله‌مراتب سه‌مسیره: تلاش اول رد، تلاش دوم قبول |
| K | تأیید پرداخت: کارمزد دوم کم نشد |
