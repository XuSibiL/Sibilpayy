#!/usr/bin/env bash
# update-site-docs.sh — مستنداتِ خودِ سایتِ سیبیل‌پی را روی سرورِ فعال به آخرین نسخه می‌برد.
#
# اجرای خودکار:
#   curl -fsSL https://raw.githubusercontent.com/XuSibiL/Sibilpayy/main/deploy/update-site-docs.sh | sudo bash
#
# یا با دانلود:
#   curl -fsSLO https://raw.githubusercontent.com/XuSibiL/Sibilpayy/main/deploy/update-site-docs.sh
#   sudo bash update-site-docs.sh
#
# مسیرِ نصبِ غیرِ پیش‌فرض:
#   SIBILPAY_DIR=/srv/sibilpay sudo -E bash update-site-docs.sh
#
# فقط یک فایلِ قالب (app/templates/docs.html) جای‌گزین می‌شود، از قبلی پشتیبان
# گرفته می‌شود و سرویس ری‌استارت می‌شود. به کد، دیتابیس، وبهوک و بات‌ها دست نمی‌زند.
set -euo pipefail

APP="${SIBILPAY_DIR:-/opt/sibilpay}"
if [ ! -d "$APP/backend/app/templates" ]; then
  APP="$(ls -d /opt/*/backend/app /root/*/backend/app /srv/*/backend/app /home/*/backend/app 2>/dev/null | head -1 | sed 's#/backend/app##' || true)"
fi
if [ ! -d "$APP/backend/app/templates" ]; then
  echo "✗ مسیرِ نصبِ سیبیل‌پی پیدا نشد. مسیر را با SIBILPAY_DIR بده:"
  echo "   SIBILPAY_DIR=/path/to/sibilpay sudo -E bash update-site-docs.sh"
  exit 1
fi

PY="$APP/venv/bin/python"
[ -x "$PY" ] || PY="$APP/.venv/bin/python"
[ -x "$PY" ] || PY="$APP/env/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

TPL="$APP/backend/app/templates/docs.html"
BAK="$APP/backend/_sibi_bak_$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BAK"
[ -f "$TPL" ] && cp -f "$TPL" "$BAK/docs.html"
echo "APP=$APP"
echo "قبل: $(wc -c < "$TPL" 2>/dev/null || echo 0) بایت — پشتیبان: $BAK/docs.html"

cat > "$TPL" <<'DOCS_EOF'
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SIBILPAY — راهنمای کامل درگاه و API</title>
<style>
  @font-face{font-family:'Vazirmatn';font-style:normal;font-weight:400;font-display:swap;
    src:url('/static/fonts/Vazirmatn-Regular.ttf') format('truetype')}
  @font-face{font-family:'Vazirmatn';font-style:normal;font-weight:700;font-display:swap;
    src:url('/static/fonts/Vazirmatn-Bold.ttf') format('truetype')}
  :root{
    --bg:#070d18;--bg2:#0b1424;--card:rgba(255,255,255,.045);--line:rgba(255,255,255,.09);
    --ink:#eef4ff;--ink2:#b9c8de;--muted:#7f92ae;--sky:#22c3ff;--sky2:#0a84d8;--violet:#7a5cff;
    --ok:#2fd39a;--warn:#ffc24b;--err:#ff6b6b;--code:#0a1526;
  }
  @media (prefers-color-scheme:light){
    :root{--bg:#f1f6fc;--bg2:#e8f0fa;--card:#fff;--line:#dbe6f3;--ink:#0b1728;--ink2:#33455e;
      --muted:#5f7189;--sky:#0091d6;--sky2:#0069a8;--violet:#5b45d6;--code:#0f2033}
  }
  *{box-sizing:border-box}
  body{
    margin:0;background:
      radial-gradient(1000px 520px at 90% -10%, rgba(34,195,255,.15), transparent 60%),
      radial-gradient(760px 420px at 0% 110%, rgba(122,92,255,.13), transparent 62%), var(--bg);
    color:var(--ink);font-family:'Vazirmatn',Tahoma,system-ui,sans-serif;line-height:1.95;
    font-size:15px;-webkit-font-smoothing:antialiased;
  }
  header{padding:34px 18px 30px;border-bottom:1px solid var(--line)}
  .head{max-width:1000px;margin:0 auto;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
  .mark{width:52px;height:52px;border-radius:16px;display:grid;place-items:center;font-weight:800;
    font-size:22px;color:#03121f;background:linear-gradient(150deg,var(--sky),var(--sky2));
    box-shadow:0 18px 34px -18px rgba(34,195,255,.95)}
  header h1{margin:0;font-size:23px;letter-spacing:-.3px}
  header p{margin:3px 0 0;color:var(--muted);font-size:13px}
  nav{max-width:1000px;margin:0 auto;padding:12px 18px;display:flex;gap:8px;flex-wrap:wrap;
    border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5;
    background:color-mix(in srgb, var(--bg) 88%, transparent);backdrop-filter:blur(12px)}
  nav a{font-size:12px;color:var(--ink2);text-decoration:none;border:1px solid var(--line);
    border-radius:999px;padding:5px 11px;white-space:nowrap}
  nav a:hover{border-color:var(--sky);color:var(--sky)}
  .wrap{max-width:1000px;margin:0 auto;padding:22px 18px 70px}
  section{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:20px 20px 22px;
    margin-bottom:16px;box-shadow:0 26px 54px -44px rgba(0,0,0,.9)}
  h2{font-size:18px;margin:0 0 12px;letter-spacing:-.2px}
  h3{font-size:14px;margin:20px 0 8px;color:var(--sky)}
  p,li{font-size:13.6px;color:var(--ink2)}
  p{margin:8px 0}
  code{
    font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.2px;
    background:rgba(34,195,255,.12);color:var(--sky);border-radius:6px;padding:1px 6px;
    direction:ltr;unicode-bidi:embed;white-space:nowrap;display:inline-block;max-width:100%;
    overflow-wrap:anywhere;vertical-align:middle;
  }
  pre{
    background:var(--code);color:#d9f1ff;border:1px solid var(--line);border-radius:14px;
    padding:14px 16px;overflow-x:auto;direction:ltr;text-align:left;font-size:12.3px;
    line-height:1.85;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;margin:12px 0;
  }
  pre b{color:#7fd8ff;font-weight:600}
  pre.code{background:linear-gradient(180deg,#0b1b2b,#08131f);border-color:#1d3350}
  pre.diagram{background:#0e1a12;color:#bff3c8;border-color:#1e3826;line-height:1.55;
    font-size:11.8px;text-align:center}
  details.lang{border:1px solid var(--line);border-radius:16px;margin:10px 0;
    background:rgba(255,255,255,.025);overflow:hidden}
  details.lang summary{cursor:pointer;padding:12px 14px;font-size:13.3px;font-weight:700;
    color:var(--sky);list-style:none}
  details.lang summary::-webkit-details-marker{display:none}
  details.lang[open] summary{border-bottom:1px solid var(--line);background:rgba(34,195,255,.07)}
  details.lang > pre{margin:0;border:0;border-radius:0}
  .rows{display:grid;gap:10px;margin:12px 0}
  .r{display:grid;grid-template-columns:minmax(120px,180px) 1fr;gap:12px;align-items:start;
    border:1px solid var(--line);border-radius:14px;padding:11px 13px;background:rgba(255,255,255,.02)}
  .r .k{font-size:12.5px;color:var(--muted);font-weight:700}
  .r .v{font-size:13px;color:var(--ink);min-width:0;overflow-wrap:anywhere}
  .steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:14px 0}
  .step{border:1px solid var(--line);border-radius:16px;padding:13px 14px;background:rgba(255,255,255,.025)}
  .step b{display:block;color:var(--sky);font-size:13px;margin-bottom:4px}
  .step span{font-size:12.3px;color:var(--ink2)}
  .note{border-radius:14px;padding:11px 14px;font-size:12.6px;margin:12px 0;border:1px solid}
  .note.i{background:rgba(34,195,255,.09);border-color:rgba(34,195,255,.3);color:var(--ink2)}
  .note.w{background:rgba(255,194,75,.1);border-color:rgba(255,194,75,.32);color:var(--warn)}
  .note.e{background:rgba(255,107,107,.1);border-color:rgba(255,107,107,.32);color:var(--err)}
  .badge{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:700;
    border-radius:999px;padding:3px 10px;border:1px solid var(--line);color:var(--muted)}
  .ep{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap;
    border-bottom:1px solid var(--line);padding:10px 0;font-size:13px}
  .ep:last-child{border-bottom:0}
  .ep .m{font-size:10.5px;font-weight:800;border-radius:7px;padding:2px 7px;color:#03121f;
    background:var(--sky);min-width:44px;text-align:center}
  .ep .m.post{background:#7ae0b6}
  .ep .m.get{background:#8fc0ff}
  .ep .m.del{background:#ff9b9b}
  .ep .p{font-family:ui-monospace,monospace;direction:ltr;font-size:12px;color:var(--ink);
    flex:1 1 auto;min-width:0;overflow-wrap:anywhere}
  .ep .d{font-size:12px;color:var(--muted);flex:0 1 46%}
  .cta{display:inline-flex;align-items:center;gap:8px;background:linear-gradient(135deg,var(--sky),var(--sky2));
    color:#03121f;text-decoration:none;border-radius:13px;padding:10px 18px;font-size:13px;font-weight:800;
    margin-top:8px;box-shadow:0 16px 30px -20px rgba(34,195,255,.95)}
  footer{text-align:center;color:var(--muted);font-size:12px;padding:26px 16px 40px}
  @media (max-width:620px){
    .r{grid-template-columns:1fr}
    .ep .d{flex-basis:100%}
    header h1{font-size:20px}
    section{padding:16px 15px 18px;border-radius:18px}
  }
</style>
</head>
<body>

<header>
  <div class="head">
    <div class="mark">S</div>
    <div>
      <h1>راهنمای SIBILPAY</h1>
      <p>یک قرارداد عمومی برای همه: یک آدرس درگاه، یک آدرس API، یک شکل کلید — برای هر سایت، ربات، اپ و فروشگاه.</p>
    </div>
  </div>
</header>

<nav>
  <a href="#start">شروع سریع</a>
  <a href="#one">آدرس و کلید</a>
  <a href="#pay">دو راه پرداخت</a>
  <a href="#invoice">ساخت فاکتور</a>
  <a href="#status">وضعیت</a>
  <a href="#verify">تأیید</a>
  <a href="#endpoints">همهٔ مسیرها</a>
  <a href="#errors">خطاها</a>
  <a href="#integrate">اتصال هر زبان</a>
  <a href="#panel">پنل و مینی‌اپ</a>
  <a href="#backup">پشتیبان</a>
  <a href="#multi">چند فاکتور هم‌زمان</a>
  <a href="#port">پورتِ API و درگاه</a>
  <a href="#cancel">لغو و رد کردن</a>
  <a href="#hooks">وبهوک</a>
  <a href="#faq">پرسش‌ها</a>
</nav>

<div class="wrap">

<!-- The one thing a seller needs from this page. Everything else is reference. -->
<div class="card" style="text-align:center;padding:22px 16px;margin:14px 0 18px;border-radius:20px;background:linear-gradient(160deg,#0f7b6c,#0a5c50);color:#fff">
  <div style="font-size:19px;font-weight:800;margin-bottom:6px">درگاه اختصاصی و کلید API خودت را بگیر</div>
  <div style="font-size:13px;line-height:1.9;opacity:.92;margin-bottom:14px">
    لازم نیست چیزی کپی کنی. دکمهٔ زیر را بزن؛ ربات کلید API و لینک درگاه
    <b>همان فروشگاه</b> تو را تحویل می‌دهد.
  </div>
  <a href="https://t.me/{{ bot_username }}?start=api"
     style="display:inline-block;background:#fff;color:#0a5c50;text-decoration:none;font-weight:800;
            padding:13px 22px;border-radius:14px;font-size:15px">
     🔑 دریافت API و لینک درگاه اختصاصی من
  </a>
  <div style="font-size:11.5px;opacity:.8;margin-top:10px">
    تا سه فروشگاه، هر کدام با کلید و لینک جدا.
  </div>
</div>

<section id="start">
  <h2>۱. در سه قدم</h2>
  <p>SIBILPAY درگاه کارت‌به‌کارت است: خریدار مبلغ را به کارت فروشنده واریز می‌کند،
     اپ SIBILPAY روی گوشی فروشنده پیامک بانک را می‌خواند، مبلغ را با فاکتور تطبیق می‌دهد و
     فاکتور را خودکار «پرداخت‌شده» می‌کند. هیچ پولی وارد حساب SIBILPAY نمی‌شود.</p>
  <div class="steps">
    <div class="step"><b>۱) فاکتور</b><span>از ربات یا با API یک فاکتور بساز و لینک پرداخت بگیر.</span></div>
    <div class="step"><b>۲) پرداخت</b><span>خریدار لینک را باز می‌کند و مبلغ دقیق را کارت‌به‌کارت می‌کند.</span></div>
    <div class="step"><b>۳) تأیید</b><span>اپ، پیامک بانک را می‌خواند و فاکتور همان لحظه تأیید می‌شود.</span></div>
  </div>
  <div class="note i">مبلغی که خریدار واریز می‌کند چند تومان بیشتر از مبلغ فاکتور است تا تطبیق
     خودکار قطعی شود؛ همین عدد در صفحهٔ پرداخت به خریدار نشان داده می‌شود.</div>
</section>

<section id="one">
  <h2>۲. درگاه و API با هم، برای همه یکسان</h2>
  <p>در SIBILPAY یک قرارداد عمومی وجود دارد و همه — سایت تو، ربات تو، اپلیکیشن تو،
     و هر فروشگاه دیگری — از همان یک قرارداد استفاده می‌کنند. هیچ فروشگاهی آدرس
     اختصاصی یا دامنهٔ جدا ندارد؛ فقط <b>کلید</b> اختصاصی است.</p>
  <div class="rows">
    <div class="r"><div class="k">🔗 درگاه</div>
      <div class="v"><code>{{ pay_base }}/g/{store_slug}</code><br>
      لینکِ پایهٔ فروشگاه؛ آخرِ آن شناسهٔ فاکتور می‌آید:
      <code>{{ pay_base }}/g/{store_slug}/{invoice_id}</code><br>
      <span style="opacity:.75">لینکِ پرداخت روی پورتِ خودش سرو می‌شود و همیشه از
      <code>payment_url</code> بیاید — نه دست‌ساز.</span></div></div>
    <div class="r"><div class="k">🛠 API</div>
      <div class="v"><code>{{ base_url }}/api/v1</code></div></div>
    <div class="r"><div class="k">🔑 کلید</div>
      <div class="v"><code>Authorization: Bearer &lt;کلید&gt;</code></div></div>
  </div>
  <div class="note i"><b>درگاه و API همیشه با هم تحویل داده می‌شوند.</b> در صفحهٔ پرداخت
     (همان <code>/pay/…</code>) مشتری دو دکمهٔ شیشه‌ای می‌بیند: «پرداخت از طریق درگاه» و
     «پرداخت از طریق ربات». هیچ‌کدام آدرس جدا یا دامنهٔ ثالث ندارد؛ رباتِ معرفی‌شده
     فقط <code>@{{ bot_username }}</code> است و فاکتور را به‌صورت <b>متن</b> می‌فرستد.</div>
  <div class="note i"><b>تلاشِ ناموفق ≠ نتیجهٔ نامشخص.</b> اگر پاسخِ ساختِ فاکتور
     به ربات/سایتِ تو نرسید (timeout، قطعِ شبکه، ۵xx)، قاعده این است: <b>قبل از
     هر درخواستِ تازه، با <code>{{ base_url }}/api/v1/invoices/by-order/{order_id}</code>
     استعلام بگیر</b> — <code>200</code> یعنی فاکتور هست، <code>404</code> یعنی مطمئنی
     ساخته نشده. با فرستادنِ <code>order_id</code> هم فاکتورِ تکراری ساخته نمی‌شود
     (پاسخِ تکراری: <code>200</code> + <code>idempotent_replay: true</code>).
     فهرستِ کاملِ کدهایی که «تضمین می‌کنند فاکتوری ساخته نشده» در صفحهٔ
     <a href="{{ base_url }}/docs#errors">خطاها</a> است.</div>
  <div class="note e"><b>چرا «درگاه با API من کار نمی‌کند»؟</b> یا کلید مال فروشگاه
     دیگری است، یا آدرس را با <code>http</code>/بدون <code>/api/v1</code> زده‌ای.
     با کلید همین فروشگاه و آدرس بالا، همیشه کار می‌کند — فرقی نمی‌کند از سایت
     صدا بزنی یا از ربات یا از اپ.</div>
</section>

<section id="pay">
  <h2>۳. دو راه پرداخت، یک نتیجه</h2>
  <div class="steps">
    <div class="step"><b>💳 از طریق درگاه</b><span>صفحهٔ <code>/pay/{id}</code>: کارت فروشنده،
      مبلغ دقیق به ریال و تومان، دکمه‌های کپی. مبلغ دقیق را واریز کن.</span></div>
    <div class="step"><b>🤖 از طریق ربات</b><span>همان فاکتور در
      <code>@{{ bot_username }}</code> به‌صورت متن می‌آید: شمارهٔ کارت ثبت‌شدهٔ فروشنده،
      مبلغ دقیق به ریال و تومان، و چهار دکمهٔ «کپی شماره کارت»، «کپی شماره شبا»،
      «کپی مبلغ به ریال» و «کپی مبلغ به تومان» (مبلغ روی دکمه نوشته نمی‌شود،
      فقط کپی می‌شود).</span></div>
    <div class="step"><b>✅ تأیید</b><span>پیامک واریز → تطبیق دقیق مبلغ → تأیید.
      بعد از تأیید، ربات ثبت‌شدهٔ فروشنده دکمهٔ «▶️ استارت» برای همان خریدار می‌گیرد.</span></div>
  </div>
  <div class="note i"><b>چه چیزی خودکار تأیید نمی‌شود:</b> مبلغ رندشده (بدون رقم‌های
     یکتای آخر)، واریزی نیازمند بررسی، واریزی بعد از انقضا. این‌ها فقط با تأیید دستی
     صاحب فروشگاه تأیید می‌شوند — و همان لحظه دکمهٔ استارت به ربات خودش می‌رود.</div>
  <p>اعلان‌ها سه مسیر دارند و از «📣 محل دریافت اعلان‌ها» در ربات تنظیم می‌شوند:
     ربات تلگرام خودت، آدرس سایت/وبه‌وک، و اپلیکیشن متصل. هیچ‌کدام بدون تأیید
     واریز پیام «پرداخت شد» نمی‌فرستد.</p>
</section>

<section id="invoice">
  <h2>۴. ساخت فاکتور</h2>
  <p>بات/سایت/اپ فقط یک درخواست می‌فرستد؛ مبلغِ نهایی، کارت، کدِ کوتاه و لینک را
     <b>سرورِ سیبیل‌پی</b> می‌سازد:</p>
  <pre>curl -X POST {{ base_url }}/api/v1/invoices \
  -H "Authorization: Bearer <b>کلید_API</b>" \
  -H "Content-Type: application/json" \
  -d '{
        "amount_rial": 2500000,
        "order_id": "order-1234",
        "description": "سفارش ۱۲۳۴",
        "customer_name": "علی",
        "webhook_url": "https://shop.example.com/payment/sibilpay_webhook.php"
      }'</pre>
  <p>پاسخ:</p>
  <pre>{
  "success": true,
  "data": {
    "id": "inv_9f2c1a",
    "short_code": "483920",
    "status": "pending",
    "amount_rial": 2500000,
    "payable_rial": 2500030,
    "order_id": "order-1234",
    "webhook_url": "https://shop.example.com/payment/sibilpay_webhook.php",
    "gateway": "card",
    "expires_at": "2026-11-11T10:30:00+00:00",
    "payment_url": "{{ base_url }}/pay/card/inv_9f2c1a",
    "short_payment_url": "{{ base_url }}/pay/inv_9f2c1a"
  }
}</pre>
  <div class="rows">
    <div class="r"><div class="k">amount_rial</div><div class="v">مبلغ فاکتور به ریال — اجباری</div></div>
    <div class="r"><div class="k">order_id</div><div class="v">شناسهٔ سفارشِ خودت؛ در خبرِ پرداخت برمی‌گردد</div></div>
    <div class="r"><div class="k">webhook_url</div><div class="v">آدرسِ تأییدیهٔ <b>همین فاکتور</b> — اختیاری، ولی توصیه‌شده (نامِ <code>webhook</code> و <code>callback_url</code> هم همین معنی را دارند)</div></div>
    <div class="r"><div class="k">gateway</div><div class="v"><code>card</code> یا <code>deposit_ref</code>؛ پیش‌فرض همان درگاهِ کلیدِ API</div></div>
    <div class="r"><div class="k">expiry_minutes</div><div class="v">بین ۲ تا ۱۸۰ دقیقه (پیش‌فرض ۳۰)</div></div>
    <div class="r"><div class="k">customer_name / customer_phone / description</div><div class="v">فقط برای گزارش و فاکتورِ چاپی</div></div>
    <div class="r"><div class="k">payment_url</div><div class="v">لینکِ پرداخت؛ بعد از انقضا سخت بسته می‌شود</div></div>
  </div>
  <p class="hint">فیلدِ ناشناخته هیچ‌وقت ساختِ فاکتور را نمی‌شکند؛ ولی دو شرطِ سرور هست:
     کارتِ فعالِ همان فروشگاه (<code>409 NO_CARD_AVAILABLE</code>) و موجودیِ کیف پول برای
     کارمزدِ همان فاکتور (<code>402 WALLET_INSUFFICIENT</code>). این‌ها سمتِ کلاینت
     دور زده نمی‌شوند.</p>
  <p class="hint"><b>اگر فاکتور ساخته نمی‌شود</b> اول کدِ پاسخ را ببین: <code>402</code> یعنی
     کیف پول، <code>409</code> یعنی کارت، <code>401</code> یعنی کلیدِ API.
     <code>422</code> یعنی نوعِ داده غلط است (مثلاً مبلغِ صفر یا رشته).</p>
</section>

<section id="status">
  <h2>۵. وضعیت فاکتور</h2>
  <p>وضعیت‌ها: <code>pending</code> در انتظار · <code>paid</code> پرداخت‌شده ·
     <code>partially_paid</code> ناقص · <code>expired</code> منقضی · <code>cancelled</code> لغو ·
     <code>under_review</code> در بررسی.</p>
  <pre>curl {{ base_url }}/api/v1/invoices/<b>inv_9f2c1a</b>/status \
  -H "Authorization: Bearer <b>کلید_API</b>"</pre>
</section>

<section id="verify">
  <h2>۶. تأیید و تحویل سفارش (فقط یک‌بار)</h2>
  <pre>curl -X POST {{ base_url }}/api/v1/invoices/<b>inv_9f2c1a</b>/verify \
  -H "Authorization: Bearer <b>کلید_API</b>"</pre>
  <p>بار اول <code>200</code> و سفارش تحویل می‌شود؛ هر بار بعد <code>409</code>.
     یعنی حتی اگر سایت و ربات و اپ هر سه تأیید را صدا بزنند، سفارش دوبار تحویل نمی‌شود.</p>
</section>

<section id="endpoints">
  <h2>۷. همهٔ مسیرها</h2>
  <div class="ep"><span class="m post">POST</span><span class="p">/api/v1/invoices</span><span class="d">ساخت فاکتور + لینک پرداخت</span></div>
  <div class="ep"><span class="m get">GET</span><span class="p">/api/v1/invoices</span><span class="d">فهرست فاکتورها (فیلتر <code>?status=</code>)</span></div>
  <div class="ep"><span class="m get">GET</span><span class="p">/api/v1/invoices/{id}</span><span class="d">جزئیات یک فاکتور</span></div>
  <div class="ep"><span class="m get">GET</span><span class="p">/api/v1/invoices/{id}/status</span><span class="d">فقط وضعیت، سبک</span></div>
  <div class="ep"><span class="m post">POST</span><span class="p">/api/v1/invoices/{id}/cancel</span><span class="d">لغو فاکتور باز</span></div>
  <div class="ep"><span class="m post">POST</span><span class="p">/api/v1/invoices/{id}/confirm-deposit</span><span class="d">تأیید دستی واریز</span></div>
  <div class="ep"><span class="m get">GET</span><span class="p">/api/v1/invoices/{id}/history</span><span class="d">تاریخچهٔ رویدادها</span></div>
  <div class="ep"><span class="m get">GET</span><span class="p">/api/v1/cards</span><span class="d">کارت‌های واریز فروشگاه</span></div>
  <div class="ep"><span class="m post">POST</span><span class="p">/api/v1/cards</span><span class="d">افزودن کارت</span></div>
  <div class="ep"><span class="m get">GET</span><span class="p">/api/v1/devices</span><span class="d">دستگاه‌های متصل</span></div>
  <div class="ep"><span class="m post">POST</span><span class="p">/api/v1/devices/pairing-code</span><span class="d">کد اتصال اپ</span></div>
  <div class="ep"><span class="m get">GET</span><span class="p">/api/v1/store</span><span class="d">اطلاعات فروشگاه</span></div>
  <div class="ep"><span class="m get">GET</span><span class="p">/api/v1/wallet</span><span class="d">کیف پول و تراکنش‌ها</span></div>
  <div class="ep"><span class="m get">GET</span><span class="p">/api/v1/stats/summary</span><span class="d">آمار (اکسل/CSV/PDF هم دارد)</span></div>
  <div class="ep"><span class="m get">GET</span><span class="p">/api/v1/meta · /health</span><span class="d">نسخه و سلامت، بدون کلید</span></div>
  <p style="margin-top:14px"><a class="cta" href="/api/docs" target="_blank" rel="noopener">مرجع تعاملی برای برنامه‌نویس ↗</a></p>
</section>

<section id="errors">
  <h2>۸. خطاها</h2>
  <div class="rows">
    <div class="r"><div class="k">401 invalid_api_key</div><div class="v">کلید غلط یا مال فروشگاه دیگر</div></div>
    <div class="r"><div class="k">403 app_signature_required</div><div class="v">هدر <code>X-App-Cert</code> نیست (قفل امضای اپ روشن است)</div></div>
    <div class="r"><div class="k">404 invoice_not_found</div><div class="v">شناسهٔ فاکتور غلط است</div></div>
    <div class="r"><div class="k">409 invoice_closed</div><div class="v">فاکتور قبلاً بسته شده</div></div>
    <div class="r"><div class="k">422 validation_error</div><div class="v">مبلغ یا فیلد اجباری درست نیست</div></div>
    <div class="r"><div class="k">429 rate_limited</div><div class="v">درخواست زیاد؛ چند ثانیه صبر کن</div></div>
    <div class="r"><div class="k">503 no_active_card</div><div class="v">فروشگاه کارت فعال ندارد</div></div>
  </div>
</section>

<section id="panel">
  <h2>۹. پنل و مینی‌اپ</h2>
  <p><b>پنل وب:</b> <code>{{ base_url }}/panel</code> — با ایمیل و کد یک‌بارمصرف، بدون رمز.</p>
  <p><b>مینی‌اپ:</b> با دکمهٔ <b>Open</b> پایین چت ربات باز می‌شود (همان که در BotFather فعال شد).
     اگر باز نشد، در BotFather مسیر
     <code>Bot Settings → Configure Mini App</code> باید روی <b>Enable</b> باشد.</p>
  <p><b>تیکت:</b> فروشنده از ربات و خریدار از صفحهٔ پرداخت تیکت می‌فرستد؛ هر تیکت در گروه گزارش‌ها
     تاپیک خودش را دارد.</p>
</section>

{% include "_integrations.html" %}

<section id="backup">
  <h2>۱۰. پشتیبان‌گیری</h2>
  <p>ربات هر ۲۴ ساعت دیتابیس را فشرده می‌کند و در تاپیک «🗄 پشتیبان‌گیری» می‌فرستد.
     نسخهٔ فوری: پنل مدیریت → «🗄 پشتیبان‌گیری روزانه» → «📥 همین حالا پشتیبان بگیر».</p>
  <pre>sudo systemctl stop sibilpay-api sibilpay-bot
cd /opt/sibilpay
sudo cp backend/sibilpay.db backend/sibilpay.db.bak-$(date +%F)
sudo gunzip -c /path/to/sibilpay-YYYYMMDD-HHMM.db.gz | sudo tee backend/sibilpay.db &gt; /dev/null
sudo chown sibilpay:sibilpay backend/sibilpay.db
sudo systemctl start sibilpay-api sibilpay-bot</pre>
</section>

<section id="multi">
  <h2>۱۱. چند فاکتور هم‌زمان — و دامِ «صفِ تک‌فاکتوری»</h2>
  <p>هر <code>POST /api/v1/invoices</code> یک <b>فاکتورِ تازه</b> است با مبلغ و لینکِ
     پرداختِ خودش. سیبیل‌پی صف ندارد؛ اگر خریدارها پشتِ سرِ هم می‌مانند، آن صف را
     <b>کدِ فروشگاه</b> ساخته است. <!-- MULTI-INVOICE-DOC-V1 --></p>

  <h3>ظرفیتِ واقعی</h3>
  <table>
    <tr><th>موضوع</th><th>عدد</th><th>توضیح</th></tr>
    <tr><td>ساختِ فاکتور هم‌زمان</td><td>نامحدود در عمل</td><td>هر درخواست شناسه و لینکِ جدا دارد</td></tr>
    <tr><td>فاکتورِ باز با همان مبلغ روی یک کارت</td><td>۹۹۹</td><td>هر فاکتور دنبالهٔ ریالیِ یکتا می‌گیرد</td></tr>
    <tr><td>مبلغِ متفاوت</td><td>بدون تداخل</td><td>۵۰۰٬۰۰۰ و ۷۵۰٬۰۰۰ رقابتی ندارند</td></tr>
    <tr><td>چند کارت</td><td>چرخشِ خودکار</td><td>بر اساس اولویت و حجمِ روز</td></tr>
  </table>
  <p class="hint">مبلغ‌ها چند ریال فرق دارند چون پیامکِ بانکی شناسهٔ پرداخت ندارد و تنها
     سرنخ «مبلغِ دقیق» است. همیشه <code>payable_rial</code> را بفرست، گردش نکن.</p>

  <h3>اگه این‌جوری کنی، این‌جوری می‌شه</h3>
  <table>
    <tr><th>کاری که کدِ فروشگاه می‌کند</th><th>نتیجه‌ای که می‌بینی</th></tr>
    <tr><td><code>order_id</code> ثابت برای همهٔ تلاش‌ها</td><td>تا وقتی فاکتورِ اول باز است، همه همان لینک را می‌گیرند — «یک فاکتور، همه در صف»</td></tr>
    <tr><td>قفلِ «تا نتیجهٔ قبلی روشن نشود، فاکتور ممنوع»</td><td>کاربر پول داده، پیامک نرسیده، و تا ابد «منتظر بررسی» می‌ماند</td></tr>
    <tr><td><code>pending</code> را رها می‌کنی</td><td>فاکتور بعد از ۳۰ دقیقه منقضی می‌شود ولی کاربر قفل است</td></tr>
    <tr><td>مبلغ را گرد می‌کنی</td><td>واریز با <code>payable_rial</code> یکی نیست → هرگز تطبیق نمی‌شود</td></tr>
  </table>

  <h3>سه خطی که مشکل را حل می‌کند</h3>
  <p>قبل از ساختِ فاکتور، از درگاه بپرس:</p>
  <pre>GET /api/v1/invoices/by-order/{order_id}</pre>
  <table>
    <tr><th>پاسخ</th><th>کارِ درست</th></tr>
    <tr><td><code>pending</code></td><td>همان <code>payment_url</code> را دوباره بفرست، فاکتورِ تازه نساز</td></tr>
    <tr><td><code>paid</code></td><td>سفارش را تحویل بده؛ دوباره پول نگیر</td></tr>
    <tr><td><code>404</code></td><td>فاکتورِ تازه با همان <code>order_id</code> بساز</td></tr>
    <tr><td><code>expired</code> / <code>cancelled</code></td><td>با <code>order_id</code> <b>جدید</b> فاکتور بساز</td></tr>
  </table>
  <pre>order_id = f"{cart.id}-{int(time.time())}"                     # یکتا برای هر تلاش
inv = await sibil_get(f"/api/v1/invoices/by-order/{order_id}")  # ۳ خط
if not inv or inv["status"] in ("expired", "cancelled"):
    inv = await sibil_post("/api/v1/invoices",
                           {"amount_rial": rial, "order_id": order_id})
send(inv["payment_url"], inv["payable_rial"])</pre>

  <p class="hint">ربات‌های فروشِ آماده که «یک پرداختِ معلق برای هر کاربر» را قفل می‌کنند،
     با همین سه خط سازگار می‌شوند. پیامِ «نتیجهٔ درخواست قبلی هنوز مشخص نیست»
     از سیبیل‌پی نیست — سیبیل‌پی هیچ‌وقت به‌خاطرِ یک فاکتورِ باز، درخواستِ بعدی را رد نمی‌کند.</p>
</section>

<section id="port">
  <h2>۱۲. یک پورت برای API و درگاه</h2>
  <!-- ONE-PORT-DOC-V1 -->
  <p>لینکِ API و لینکِ صفحهٔ پرداخت باید روی <b>یک پورت</b> باشند. این یک سلیقه نیست،
     یک شرطِ فنی است: مرورگرِ خریدار، اپِ متصل و ربات همه یک آدرس می‌شناسند و
     ریدایرکت‌های سایت هم به همان پورت برمی‌گردند.</p>

  <h3>هر لینک از کدام آدرس ساخته می‌شود</h3>
  <table>
    <tr><th>لینک</th><th>از کدام تنظیم</th></tr>
    <tr><td>API، سایت، مستندات، APK، وب‌هوک</td><td><code>BASE_URL</code></td></tr>
    <tr><td>صفحهٔ پرداخت <code>/pay/…</code></td><td><code>PAYMENT_BASE_URL</code> (پیش‌فرض: همان <code>BASE_URL</code>)</td></tr>
    <tr><td>مینی‌اپ <code>/mini</code></td><td><code>MINI_BASE_URL</code> — تنها استثنا، روی ۴۴۳ بدون پورت</td></tr>
  </table>

  <h3>اگه پورت‌ها یکی نباشند</h3>
  <table>
    <tr><th>اتفاق</th><th>نتیجه</th></tr>
    <tr><td>صفحهٔ پرداخت روی پورتِ دیگر</td><td>خریدار لینکی باز می‌کند که سشن/کوکیِ همان پورت را ندارد → «فاکتور پیدا نشد»</td></tr>
    <tr><td>API روی ۴۴۳، درگاه روی ۲۰۵۳</td><td>رباتِ فروش یک آدرس را می‌شناسد و آدرسِ دیگری می‌گیرد → «نتیجهٔ ساخت فاکتور نامشخص»</td></tr>
    <tr><td>هیچ‌کدام روی پورتِ اعلام‌شده سرو نشود</td><td>درخواست به هیچ‌جا نمی‌رسد؛ فاکتوری ساخته نمی‌شود</td></tr>
  </table>

  <p>برای همین، از نسخهٔ 1.5.9.22 قانون <b>PORT-ONE</b> اعمال می‌شود: اگر
     <code>PAYMENT_BASE_URL</code> پورتِ دیگری بدهد، نادیده گرفته می‌شود و لینک‌ها
     از پورتِ <code>BASE_URL</code> ساخته می‌شوند (هشدار در لاگ ثبت می‌شود).
     برای جداکردنِ عمدی، <code>STRICT_ONE_PORT=false</code> را در <code>.env</code> بگذار.</p>

  <h3>بررسیِ سریع</h3>
  <pre>curl -s -o /dev/null -w "%{http_code}\n" https://pay.example.com/api/v1/invoices/by-order/probe</pre>
  <p>معیار، <b>مسیرِ API</b> است: <code>401</code> (یا <code>404</code> با کلید) درست است؛ <code>302</code> یعنی این آدرس به API نمی‌رسد. <code>200</code> روی <code>/health</code> به‌تنهایی چیزی را ثابت نمی‌کند.</p>
  <p>اگر <code>200</code> آمد، همان پورت را هم برای <code>BASE_URL</code> و هم برای
     <code>PAYMENT_BASE_URL</code> بگذار. در ربات، فرمانِ <code>/diag</code> خطِ
     «پورتِ درگاه» را نشان می‌دهد.</p>

  <h3>اگر <code>302</code> گرفتی <!-- ONE-PORT-302-V1 --></h3>
  <p><code>302</code>/<code>301</code> با هدرِ <code>Location</code> یعنی درخواست به API نرسیده و
     جایی (وب‌سرور یا پراکسی) آن را به پورتِ دیگر پرتاب کرده است. پاسخِ سالمِ API
     همیشه <b>JSON</b> است: <code>401</code> بدونِ کلید، <code>404</code> با کدِ
     <code>INVOICE_NOT_FOUND</code> برای شناسهٔ ناموجود.</p>
  <pre>curl -sS -o /dev/null -D - https://pay.example.com/api/v1/invoices/by-order/probe | head -5
curl -sS -o /dev/null -w "%{http_code} %{redirect_url}\n" https://pay.example.com/api/v1/invoices/by-order/probe</pre>
  <table>
    <tr><th>خروجی</th><th>یعنی</th></tr>
    <tr><td><code>401</code> + JSON</b></td><td>مسیرِ API مستقیم جواب می‌دهد ✔</td></tr>
    <tr><td><code>404</code> + <code>INVOICE_NOT_FOUND</code></td><td>با کلیدِ معتبر، شناسهٔ ناموجود — درست است ✔</td></tr>
    <tr><td><code>302</code> + <code>Location</code> به پورتِ دیگر</td><td>آدرسِ اشتباه؛ یا وب‌سرور ریدایرکت می‌کند یا <code>BASE_URL</code> با پورتِ سرو یکی نیست ✘</td></tr>
  </table>
  <p>نکتهٔ مهم: <code>200</code> روی <code>/health</code> سلامتِ مسیرِ API را ثابت نمی‌کند؛
     فقط می‌گوید سرویس زنده است. آزمونِ واقعی همان <code>/api/v1/…</code> است.</p>
</section>

<section id="cancel">
  <h2>۱۳. لغو، رد کردن، و تأییدِ دستی</h2>
  <!-- DOCS-SITE-V8 -->
  <p>«رد کردن» سه معنیِ جدا دارد؛ هر کدام مسیرِ خودش را دارد و هیچ‌کدام فاکتور را
     دستی «پرداخت‌شده» نمی‌کند مگر مسیرِ تأیید.</p>

  <h3>لغو کردنِ فاکتور (منصرف شد، سفارش باطل شد)</h3>
  <pre>curl -X POST {{ base_url }}/api/v1/invoices/<b>inv_9f2c1a</b>/cancel \
  -H "Authorization: Bearer <b>کلید_API</b>"</pre>
  <p>وضعیت به <code>cancelled</code> می‌رود، لینکِ پرداخت بسته می‌شود و هیچ وبهوکی
     فرستاده نمی‌شود. فقط فاکتورِ <code>pending</code> یا <code>expired</code> لغو می‌شود؛
     فاکتورِ پرداخت‌شده لغو نمی‌شود (باید بازگشتِ وجه جدا ثبت شود).</p>

  <h3>رد کردنِ واریزیِ بی‌صاحب (پول آمده، ولی مالِ این فاکتور نیست)</h3>
  <pre>curl -X POST {{ base_url }}/api/v1/matches/<b>match_id</b>/resolve \
  -H "Authorization: Bearer <b>کلید_API</b>" \
  -H "Content-Type: application/json" \
  -d '{"action": "reject"}'</pre>
  <p>واریزی از صفِ «نیازمندِ بررسی» بیرون می‌رود، به هیچ فاکتوری نمی‌چسبد و پرداختی
     ثبت نمی‌شود. اگر بعداً معلوم شد مالِ همان فاکتور بود، با
     <code>{"action": "confirm", "invoice_id": "inv_…"}</code> می‌چسبد.</p>

  <h3>تأییدِ دستی (پول آمده و صاحبش پیدا شد)</h3>
  <p>همان مسیرِ بالا با <code>confirm</code>، یا از ربات: «🔍 نیازمندِ بررسی» → انتخابِ
     فاکتور → تأیید. نتیجهٔ هر دو یکی است: فاکتور <code>paid</code> می‌شود، مبلغِ ثبت‌شده
     <b>مبلغِ خودِ فاکتور</b> است (<code>amount_rial</code>) و همان وبهوکِ
     <code>invoice.paid</code> به همان مقصد می‌رود.</p>

  <h3>واریزیِ ناقص (`deposit_ref`)</h3>
  <pre>curl -X POST {{ base_url }}/api/v1/invoices/<b>inv_9f2c1a</b>/confirm-deposit \
  -H "Authorization: Bearer <b>کلید_API</b>"</pre>
  <p>برای درگاهِ «کدِ واریز» وقتی خریدار مبلغِ کمتری واریز کرده و فروشنده می‌پذیرد.</p>

  <p class="hint">قاعدهٔ طلایی: <b>هیچ‌وقت</b> بر اساسِ پارامترِ URL یا پیامِ کاربر فاکتور را
     تأیید نکن. تأیید فقط روی سرورِ سیبیل‌پی و با وبهوکِ امضاشده اعلام می‌شود.</p>
</section>

<section id="hooks">
  <h2>۱۴. وبهوک: از تأیید تا رسیدنِ خبر</h2>
  <!-- HOOKS-DOC-V1 -->
  <p>«فاکتور را تأیید کردم ولی سایت/ربات/اپم خبر نشد.» خبررسانی <b>سه</b> جای مستقل
     دارد و هر کدام می‌تواند جدا بترکد:</p>
  <table>
    <tr><th>گیرنده</th><th>شرطِ ارسال</th></tr>
    <tr><td>رباتِ سیبیل‌پی (خودِ فروشنده)</td><td>همیشه</td></tr>
    <tr><td>سایت / اپ / رباتِ فروشگاه</td><td><b>فقط</b> اگر «آدرس سایت من» ثبت شده باشد</td></tr>
    <tr><td>مشتری</td><td>فقط اگر فروشنده دکمهٔ پیام را بزند</td></tr>
  </table>
  <p class="hint">اگر آدرس ثبت نشده باشد، فاکتور پرداخت‌شده <b>می‌شود</b> ولی هیچ
     وبهوکی فرستاده نمی‌شود. این دو را از هم جدا بدان.</p>

  <!-- SIGN-DOC-V1 -->
  <h3>امضای وبهوک</h3>
  <p>هر درخواست این هدر را دارد:</p>
  <p dir="ltr"><code>X-SIBILPAY-Signature: t=1763380800,v1=&lt;hex&gt;</code></p>
  <p>با secretِ همان مقصد و <b>بدنهٔ خام</b> (قبل از هر پارس‌کردن) بررسی کن:</p>
  <p dir="ltr"><code>v1 = HMAC_SHA256(secret, t + "." + raw_body)</code></p>
  <p class="hint">اگر <code>t</code> بیشتر از ۳۰۰ ثانیه قدیمی باشد درخواست را رد کن.
     پاسخِ <code>401</code> با <code>{"status":"bad_signature"}</code> یعنی همین محاسبه
     سمتِ شما جور دیگری انجام شده؛ نه اینکه پلتفرم خبر نفرستاده باشد.</p>
  <p>هر کلیدِ API تا <b>۳</b> مقصدِ جدا دارد: <code>PUT /api/v1/hooks/self</code> با
     <code>{"url":"https://…"}</code>؛ <code>GET</code> همان مسیر فهرست و شمارِ مقصدها را
     می‌دهد.</p>

  <h3>مقصدِ خبر کدام است؟</h3>
  <ol>
    <li><code>webhook_url</code> که <b>همان فاکتور</b> هنگامِ ساخت فرستاده است؛</li>
    <li>مقصدِ بسته‌شده به همان کلیدِ API (<code>webhook_key_id</code>)؛</li>
    <li>مقصدِ ذخیره‌شدهٔ همان دامنه (فاکتورهای قدیمی؛ همان رفتارِ قبل).</li>
  </ol>
  <p>یعنی خبر همیشه به <b>همان</b> سایت/اپ/باتی می‌رود که فاکتور را ساخته — نه به
     اولین مقصدِ فروشگاه.</p>

  <h3>بدنهٔ خبر</h3>
  <pre>{
  "event": "invoice.paid",
  "created_at": "2026-11-11T10:00:00+00:00",
  "livemode": true,
  "data": {
    "id": "inv_9f2c1a", "object": "invoice", "status": "paid",
    "amount_rial": 2500000, "paid_amount_rial": 2500000, "payable_rial": 2500030,
    "order_id": "order-1234", "short_code": "483920", "test_mode": false,
    "paid_at": "2026-11-11T10:00:00+00:00",
    "store": {"id": "str_…", "slug": "shop", "name": "فروشگاه"}
  }
}</pre>
  <p>مبلغِ معتبر <code>data.amount_rial</code> است. هدرِ <code>X-SIBILPAY-Delivery</code>
     را برای تکرارناپذیری نگه دار و تأییدِ سفارش را روی <code>data.order_id</code> بزن.</p>

  <h3>پاسخ‌های تو و تکرارِ ارسال</h3>
  <table>
    <tr><th>پاسخِ شما</th><th>معنی برای سیبیل‌پی</th></tr>
    <tr><td><code>200/201/202/204</code></td><td>تحویل شد؛ دیگر تکرار نمی‌شود</td></tr>
    <tr><td><code>401</code> / <code>403</code></td><td>امضا رد شد → تا ۸ تلاشِ دوباره (۵ ثانیه تا ۱ ساعت)</td></tr>
    <tr><td><code>4xx</code> دیگر</td><td>اشتباهِ دائمی → توقف تا اصلاحِ مقصد</td></tr>
    <tr><td><code>5xx</code> / تایم‌اوت</td><td>تا ۸ تلاشِ دوباره</td></tr>
    <tr><td><code>200 {"ok":false}</code></td><td>خطای منطقی؛ بدنه را برای پشتیبانی نگه دار</td></tr>
  </table>

  <h3>شش دلیلی که «خبر نرسید»</h3>
  <table>
    <tr><th>نشانه</th><th>علت</th><th>راهِ درست</th></tr>
    <tr><td>هیچ درخواستی به سایت نرسید</td><td>آدرس ثبت نشده</td><td>«بیشتر» → «🌐 آدرس سایت من»</td></tr>
    <tr><td>آدرس هست، لاگ خالی است</td><td><code>http</code> یا پورتِ اشتباه</td><td><code>https</code> و همان پورتِ مسیر</td></tr>
    <tr><td><code>404</code></td><td>مسیرِ آدرس اشتباه</td><td>مسیرِ واقعیِ سایتِ خودت</td></tr>
    <tr><td><code>401</code>/<code>500</code></td><td>بررسیِ امضا یا خطای داخلی</td><td>اول <code>200</code> بده، بعد پردازش</td></tr>
    <tr><td>تکراری می‌آید</td><td>پاسخِ دیرتر از ۱۰ ثانیه</td><td>پاسخِ سریع + صف</td></tr>
    <tr><td>سایت «پرداخت نشد» مانده</td><td><code>order_id</code> ذخیره نشده</td><td>تحویلِ idempotent با <code>order_id</code></td></tr>
  </table>

  <h3><code>/hooks</code> در ربات</h3>
  <p>فرمانِ <code>/hooks</code> آدرسِ ثبت‌شده و آخرین ۸ ارسال را با وضعیت
     (<code>✅ delivered</code> / <code>⏳ pending</code> / <code>✘ failed</code>)،
     تعدادِ تلاش و کدِ HTTPِ سایتِ شما نشان می‌دهد؛ به‌همراهِ
     «🔁 ارسالِ دوبارهٔ ناموفق‌ها» و «🧪 ارسالِ آزمایشی».
     پیامِ «تأیید دستی» هم دیگر ادعا نمی‌کند؛ همان نتیجه را می‌نویسد.</p>

  <h3>تأیید خودکار و قاعدهٔ «دامنه#کد»</h3>
  <p>تطبیقِ خودکار وقتی کار می‌کند که پیامکِ بانک از اپ به سرور برسد. ربات کدِ اتصال را
     این‌طور می‌دهد: <code>pay.mrsibilman.ir#135381</code> — سمتِ چپ آدرسِ سرور،
     سمتِ راست کد. <b>همیشه رشتهٔ کامل را پیست کن</b>؛ با کدِ تنها، اپ روی آدرسِ
     پیش‌فرضِ زمانِ build می‌ماند و «تأیید خودکار» هیچ‌وقت رخ نمی‌دهد.</p>
</section>

<section id="faq">
  <h2>۱۵. پرسش‌های رایج</h2>
  <!-- FEE-DOC-V1 -->
  <h3>کارمزد چطور حساب می‌شود؟</h3>
  <p>هر فروشگاه بابت هر فاکتورِ موفق کارمزد می‌دهد؛ مبلغی ثابت (نه درصد) که از کیف پولِ
     همان فروشگاه کم می‌شود.</p>
  <p>اگر موجودیِ کیف پول کافی نباشد فاکتور <b>ساخته نمی‌شود</b> (پاسخ <code>402</code> با کدِ
     <code>WALLET_INSUFFICIENT</code>) و همان لحظه در رباتِ فروشنده پیام می‌آید که کاربرش
     فاکتور خواسته و موجودی ندارد. موجودی هرگز منفی نمی‌شود و با شارژ، ساختِ فاکتور
     بلافاصله برمی‌گردد.</p>
  <h3>واریز رسیده ولی فاکتور پرداخت نشده</h3>
  <p>اپ باز و متصل است؟ بانک همان کارت تیک خورده؟ مبلغ دقیقاً <code>payable_rial</code> بود؟
     اگر مبلغ فرق داشت، از «🔍 نیازمند بررسی» به فاکتور وصلش کن.</p>
  <h3>پول کجا می‌رود؟</h3>
  <p>مستقیم به کارت خود فروشنده؛ SIBILPAY واسطهٔ پول نیست.</p>
</section>

<footer>SIBILPAY v{{ version }} · <span style="direction:ltr;display:inline-block">{{ base_url }}</span></footer>
</div>

<section id="address-map" dir="rtl" style="font-family:Tahoma,sans-serif;line-height:1.9">
  <!-- ADDRESS-MAP-V1 -->
  <h2>کدام آدرس، کجا؟ (درگاه ≠ API)</h2>
  <p>این سه آدرس با هم فرق دارند و جای هرکدام جداست:</p>
  <table>
    <thead><tr><th>آدرس</th><th>برای چه کسی</th><th>نمونه</th></tr></thead>
    <tbody>
      <tr><td><b>آدرسِ درگاهِ فروشگاه</b></td>
          <td>به مشتری بده؛ در پنل‌های دیگر (فروشگاه‌ساز، وردپرس، رباتِ دیگر) هم
              داخلِ فیلدِ «آدرس درگاه» همین می‌رود</td>
          <td dir="ltr"><code>https://pay.mrsibilman.ir/g/shop046806</code></td></tr>
      <tr><td><b>آدرسِ پرداختِ فاکتور</b></td>
          <td>لینکِ همان خرید؛ آن را API در <code>payment_url</code> می‌دهد — خودت نساز</td>
          <td dir="ltr"><code>https://pay.mrsibilman.ir/pay/inv_…</code></td></tr>
      <tr><td><b>آدرسِ API</b></td>
          <td><b>فقط داخلِ کد</b> (سایت/ربات/اپ). هرگز آن را به‌جای آدرسِ درگاه نگذار</td>
          <td dir="ltr"><code>https://pay.mrsibilman.ir/api/v1</code></td></tr>
    </tbody>
  </table>
  <p style="background:#fff6e5;border:1px solid #f0c36d;border-radius:8px;padding:10px">
    ⚠️ اگر جایی فیلدِ «آدرس درگاه» را با <code>/api/v1</code> پر کنی، کاربرِ نهایی
    صفحهٔ JSON می‌بیند نه صفحهٔ پرداخت. آن آدرس فقط برای برنامه‌نویس است.
  </p>
  <p>پورت همیشه <b>۴۴۳</b> است و در آدرس نوشته نمی‌شود؛ نه برای درگاه و نه برای API.</p>
</section>


<section id="connect-facts" dir="rtl" style="font-family:Tahoma,sans-serif;line-height:1.9">
  <!-- CONNECT-FACTS-V1 — چیزهایی که برای اتصال لازم است، جای درستش -->
  <h2>اتصال در یک نگاه</h2>
  <table>
    <tbody>
      <tr><th>آدرسِ درگاهِ فروشگاه</th><td dir="ltr"><code>{{ pay_base }}/g/&lt;store-slug&gt;</code></td></tr>
      <tr><th>لینکِ پرداختِ هر فاکتور</th><td dir="ltr"><code>{{ pay_base }}/pay/&lt;gateway&gt;/&lt;invoice_id&gt;</code>
          — همان <code>payment_url</code> که API می‌دهد؛ خودت نساز</td></tr>
      <tr><th>آدرسِ API</th><td dir="ltr"><code>{{ base_url }}/api/v1</code> + هدرِ
          <code>Authorization: Bearer &lt;کلید&gt;</code></td></tr>
      <tr><th>پورت</th><td><b>۴۴۳</b> — برای درگاه و API یکی است و در آدرس نوشته نمی‌شود</td></tr>
      <tr><th>وبهوک</th><td dir="ltr"><code>PUT /api/v1/hooks/self</code> — تا ۳ مقصد برای
          هر کلید؛ امضا در هدرِ <code>X-SIBILPAY-Signature</code></td></tr>
    </tbody>
  </table>
  <h3>کدهای خطای ساختِ فاکتور</h3>
  <table>
    <thead><tr><th>کد</th><th>HTTP</th><th>معنی</th></tr></thead>
    <tbody>
      <tr><td dir="ltr"><code>WALLET_INSUFFICIENT</code></td><td>402</td><td>موجودیِ کیف پولِ کارمزد کافی نیست — فاکتور ساخته نشد و به فروشنده در رباتش اطلاع داده شد</td></tr>
      <tr><td dir="ltr"><code>NO_CARD_AVAILABLE</code></td><td>409</td><td>هیچ کارتِ فعالی برای این فروشگاه ثبت نشده</td></tr>
      <tr><td dir="ltr"><code>AMOUNT_POOL_EXHAUSTED</code></td><td>409</td><td>مبلغِ یکتا برای این کارت پیدا نشد</td></tr>
      <tr><td dir="ltr"><code>GATEWAY_DISABLED</code></td><td>409</td><td>این درگاه برای فروشگاه خاموش است</td></tr>
      <tr><td dir="ltr"><code>UNKNOWN_GATEWAY</code></td><td>404</td><td>درگاه تعریف نشده است</td></tr>
      <tr><td dir="ltr"><code>INVALID_AMOUNT</code></td><td>400</td><td>مبلغ نامعتبر است</td></tr>
    </tbody>
  </table>
</section>

</body>
</html>
DOCS_EOF

echo "بعد: $(wc -c < "$TPL") بایت"

echo ""
echo "=== ۱) بررسیِ قالب ==="
"$PY" - "$TPL" <<'PYEOF'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
need = ("webhook_url", 'id="cancel"', "X-SIBILPAY-Delivery", "لغو، رد کردن", "ساخت فاکتور")
try:
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(p.parent)))
    out = env.get_template(p.name).render(base_url="https://x", pay_base="https://x",
                                          bot_username="b", version="1")
    print("  حالت: رندرِ کامل")
except Exception as exc:                      # noqa: BLE001
    out = p.read_text(encoding="utf-8")
    print("  حالت: بررسیِ متن (%s)" % type(exc).__name__)
missing = [k for k in need if k not in out]
for k in need:
    print(("  ✔ " if k not in missing else "  ✗ ") + k)
raise SystemExit(0 if not missing else 1)
PYEOF

echo ""
echo "=== ۲) ری‌استارتِ سرویس ==="
SVC=""
for u in sibilpay-api sibilpay sibilpay-backend sibil-api sibil; do
  if systemctl restart "$u" 2>/dev/null; then SVC="$u"; echo "  سرویسِ $u ری‌استارت شد"; break; fi
done
if [ -z "$SVC" ] && command -v docker >/dev/null 2>&1 && [ -f "$APP/docker-compose.yml" ]; then
  docker compose -f "$APP/docker-compose.yml" restart 2>/dev/null && echo "  کانتینرها ری‌استارت شدند" || true
fi
[ -n "$SVC" ] || echo "  ! سرویسِ سیستمی پیدا نشد — سرویسِ خودت را ری‌استارت کن"
sleep 3

echo ""
echo "=== ۳) آزمونِ صفحهٔ /docs از داخلِ سرور ==="
for P in 8000 80 8080 5000; do
  CODE=$(curl -s -o /tmp/_docs_site.html -w "%{http_code}" "http://127.0.0.1:$P/docs" || echo 000)
  if [ "$CODE" = "200" ]; then
    echo "  /docs روی پورتِ $P → 200 ($(wc -c < /tmp/_docs_site.html) بایت)"
    grep -q "swagger-ui" /tmp/_docs_site.html 2>/dev/null && echo "  ! این پورت Swagger است نه صفحهٔ مستندات"
    for k in webhook_url "id=\"cancel\"" X-SIBILPAY-Delivery; do
      if grep -q -- "$k" /tmp/_docs_site.html; then echo "  ✔ $k"; else echo "  ✗ $k"; fi
    done
    break
  fi
done

echo ""
echo "=== ۴) آدرسِ رسمیِ سایت ==="
BASE=$("$PY" -c "from app.config import settings; print(settings.base_url)" 2>/dev/null || true)
if [ -n "$BASE" ]; then
  echo "  base_url = $BASE"
  BC=$(curl -s -o /tmp/_docs_site2.html -w "%{http_code}" "$BASE/docs" || echo 000)
  echo "  $BASE/docs → $BC ($(wc -c < /tmp/_docs_site2.html 2>/dev/null || echo 0) بایت)"
  for k in webhook_url "id=\"cancel\"" X-SIBILPAY-Delivery; do
    if grep -q -- "$k" /tmp/_docs_site2.html 2>/dev/null; then echo "  ✔ $k"; else echo "  ✗ $k"; fi
  done
else
  echo "  base_url خوانده نشد — دستی چک کن"
fi

echo ""
echo "✔ تمام شد. مستنداتِ سایت روی همین سرور به آخرین نسخه رسید."
echo "  اگر نسخهٔ قدیمی دیدی، کشِ مرورگر/پروکسی را پاک کن یا سرویس را دوباره ری‌استارت کن."
