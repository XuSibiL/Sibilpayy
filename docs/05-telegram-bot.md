<div dir="rtl" align="right">

# ۰۵ — افزودنِ روشِ پرداخت به رباتِ تلگرام

هدف: کاربر در رباتِ تو سفارش می‌دهد → لینکِ پرداخت می‌گیرد → بعد از واریز، ربات
**خودش** به کاربر پیام می‌دهد «پرداختت تأیید شد».

> **`SERVER`** = آدرسِ سرورِ پرداخت · `BOT_TOKEN` = توکنِ رباتِ خودت از @BotFather

---

## معماریِ ساده

```
کاربر → رباتِ تو → (۱) ساختِ فاکتور روی SERVER
                          ↓
                    لینکِ پرداخت → کاربر واریز می‌کند
                          ↓
      (۲) وب‌هوکِ invoice.paid  →  سرورِ تو  →  (۳) پیام به کاربر
```

نکتهٔ کلیدی: پیام به کاربر را **باتِ خودت** می‌فرستد؛ سیبیل‌پی فقط خبرِ معتبر می‌دهد.

---

## گام ۱ — فاکتور بساز و لینک بده

```python
import requests

SERVER   = "https://SERVER"
API_KEY  = "sibil_pay_live_XXXXXXXX"       # فقط در سرور

def create_invoice(amount_toman: int, order_id: str, description: str):
    r = requests.post(
        f"{SERVER}/api/v1/invoices",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "amount_rial": amount_toman * 10,   # همیشه ریال!
            "order_id": order_id,
            "description": description,
        },
        timeout=15,
    )
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(data["error"]["message"])
    return data["data"]          # id, payment_url, payable_rial, ...
```

در هندلرِ ربات:

```python
inv = create_invoice(250_000, order_id="ORD-1042", description="اشتراک ماهانه")
toman = inv["payable_rial"] // 10
await bot.send_message(
    chat_id,
    f"🧾 سفارش {inv['order_id']}\n"
    f"مبلغِ دقیقِ واریز: <b>{toman:,} تومان</b>\n\n"
    f"👉 {inv['payment_url']}",
    parse_mode="HTML",
)
```

> همیشه **`payable_rial`** را نشان بده (مبلغِ دقیقِ یکتا)، نه مبلغِ سفارش.

---

## گام ۲ — خبرِ تأیید را بگیر (وب‌هوک)

```python
from flask import Flask, request, abort
import hashlib, hmac, time, requests

app = Flask(__name__)
BOT_TOKEN     = "123456:ABC…"
WEBHOOK_SECRET = "کلیدِ-امضای-وب‌هوکِ-فروشگاه"

def tg_send(chat_id: int, text: str):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )

def signature_ok(raw: bytes, header: str) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    ts  = int(parts.get("t", "0"))
    mac = parts.get("v1", "")
    if abs(time.time() - ts) > 300:
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode(), f"{ts}.".encode() + raw,
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, mac)

@app.post("/sibilpay/callback")
def callback():
    raw = request.get_data()
    if not signature_ok(raw, request.headers.get("X-SIBILPAY-Signature", "")):
        abort(401)

    event = request.get_json(force=True)
    if event.get("event") != "invoice.paid":
        return {"ok": True}                       # بقیه را نادیده بگیر

    data = event["data"]
    order_id = data["order_id"]

    # ۳) یدمپوتنت: اگر این سفارش قبلاً paid شده، دوباره پیام نده
    if already_paid(order_id):
        return {"ok": True}
    mark_paid(order_id)

    chat_id = chat_of(order_id)                    # از دیتابیسِ خودت
    tg_send(chat_id, f"✅ پرداختِ سفارش <code>{order_id}</code> تأیید شد.\n"
                     f"مبلغ: {data['paid_amount_rial'] // 10:,} تومان")
    return {"ok": True}
```

اجرا و ثبتِ وبهوک روی همان سرور:

```bash
python app.py            # روی پورتِ عمومی، مثلاً 8080 پشتِ nginx https
```

---

## گام ۳ — اگر سرور نداری؟ (polling)

برای ربات‌های کوچک، بدونِ وب‌هوک هم می‌شود: بعد از ساختِ فاکتور، هر ۵ ثانیه وضعیت را بپرس.

```python
import time, requests

def wait_for_payment(invoice_id: str, timeout: int = 900) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(
            f"{SERVER}/api/v1/invoices/{invoice_id}/status",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=10,
        )
        status = r.json()["data"]["status"]
        if status == "paid":
            return True
        if status in ("expired", "cancelled"):
            return False
        time.sleep(5)
    return False
```

این روش ساده است ولی اگر ربات ری‌استارت شود، باید وضعیت را از دیتابیسِ خودت بازیابی کنی.
برای حجمِ واقعی، **وب‌هوک** بهتر است.

---

## گام ۴ — صفحهٔ بازگشت (اختیاری)

اگر `callback_url` بدهی، خریدار بعد از پرداخت به آن آدرس برمی‌گردد. برای دکمهٔ
«بازگشت به ربات» از لینکِ تلگرام استفاده کن:

```
https://t.me/YOUR_BOT?start=order_ORD-1042
```

و در ربات، با `/start order_…` وضعیت آن سفارش را نشان بده.

> یادت باشد: `callback_url` فقط تجربهٔ کاربر است؛ **مبنای تأیید، وب‌هوک یا status است.**

---

## چک‌لیست

- [ ] کلیدِ API فقط در سرورِ ربات (نه در اپِ موبایل)
- [ ] `amount_rial = تومان × ۱۰`
- [ ] به کاربر `payable_rial` نشان داده می‌شود
- [ ] امضای وب‌هوک چک می‌شود
- [ ] دوباره‌آمدنِ یک رویداد، پیامِ تکراری نمی‌فرستد
- [ ] فاکتورِ منقضی، وضعیتش به کاربر گفته می‌شود
- [ ] آدرسِ وب‌هوک https و از اینترنت قابلِ دسترس است

---

بعدی: [نمونه‌کدِ سایت →](06-website-examples.md)

</div>
