# ۲۰ — مرجع API

> برای انتشار در محیط واقعی، [تلاش ناموفق، نتیجه نامشخص و idempotency](10-retries-and-idempotency.md) را بخوان: با `order_id` فاکتور تکراری ساخته نمی‌شود و با `GET /api/v1/invoices/by-order/{order_id}` می‌شود نتیجه نامشخص را تعیین تکلیف کرد.

همین مسیرها در چند قالب هم منتشر می‌شوند:

| قالب | فایل | کاربرد |
|---|---|---|
| OpenAPI 3.1 (JSON) | `api/openapi.json` | تولید کلاینت، CI، ابزارهای کدسازی |
| OpenAPI 3.1 (YAML) | `api/openapi.yaml` | خوانایی و بازبینی در PR |
| Postman Collection v2.1 | `api/postman_collection.json` | تست دستی و اشتراک با تیم |
| Swagger UI | `<BASE_URL>/docs` | اجرای زنده درخواست‌ها |
| ReDoc | `<BASE_URL>/redoc` | مرور خوانا |

جدول پایین فهرست کامل مسیرهای سرور است که از خود کد برداشته شده. مسیرهای پنل وب (`/panel/…` و `/admin/…`) در آن نیستند چون فرم HTML‌اند و برای اتصال برنامه‌نویسی به کار نمی‌آیند. احراز هویت دو طرح دارد: `StoreApiKey` برای فروشگاه و `AdminToken` برای ادمین.

## قالب پاسخ

```json
{"success": true, "data": { … }, "error": null}
{"success": false, "data": null, "error": {"code": "INVOICE_NOT_PAYABLE", "message": "…"}}
```

مبلغ‌ها همیشه ریال و عدد صحیح‌اند. `payable_rial` مبلغی است که مشتری باید واریز کند؛ آن را گرد نکن.

## مسیرها

هر مسیری که در کد هست، با احراز هویت همان مسیر. گروه «عمومی» کلید نمی‌خواهد و گروه «دستگاه» با `device_id` و `device_secret` احراز می‌شود.

| گروه | متد | مسیر | احراز هویت | کار |
|---|---|---|---|---|
| فروشگاه | `GET` | `/api/v1/hooks/self` | `Authorization: Bearer sibil_pay_…` | مقصدهای webhook همین کلید |
| فروشگاه | `PUT` | `/api/v1/hooks/self` | `Authorization: Bearer sibil_pay_…` | ساخت یا پیدا کردن مقصد همین کلید |
| فروشگاه | `POST` | `/api/v1/hooks/self/rotate` | `Authorization: Bearer sibil_pay_…` | چرخش کلید امضای مقصد |
| فروشگاه | `POST` | `/api/v1/hooks/self/test` | `Authorization: Bearer sibil_pay_…` | ارسال آزمایشی به مقصد خودت |
| فروشگاه | `GET` | `/api/v1/hooks/self/deliveries` | `Authorization: Bearer sibil_pay_…` | تاریخچه ارسال‌های همین کلید |
| فروشگاه | `POST` | `/api/v1/invoices` | `Authorization: Bearer sibil_pay_…` | ساخت فاکتور |
| فروشگاه | `GET` | `/api/v1/invoices/by-order/{order_id}` | `Authorization: Bearer sibil_pay_…` | فاکتور با شماره سفارش خودت |
| فروشگاه | `GET` | `/api/v1/invoices` | `Authorization: Bearer sibil_pay_…` | فهرست فاکتورها |
| فروشگاه | `GET` | `/api/v1/invoices/{invoice_id}` | `Authorization: Bearer sibil_pay_…` | یک فاکتور با جزئیات |
| فروشگاه | `GET` | `/api/v1/invoices/{invoice_id}/status` | `Authorization: Bearer sibil_pay_…` | فقط وضعیت، سبک برای polling |
| فروشگاه | `POST` | `/api/v1/invoices/{invoice_id}/cancel` | `Authorization: Bearer sibil_pay_…` | لغو فاکتور |
| فروشگاه | `POST` | `/api/v1/invoices/{invoice_id}/verify` | `Authorization: Bearer sibil_pay_…` | تأیید یک‌بارمصرف و رسید |
| فروشگاه | `GET` | `/api/v1/invoices/{invoice_id}/history` | `Authorization: Bearer sibil_pay_…` | تاریخچه تغییر وضعیت |
| فروشگاه | `POST` | `/api/v1/test/invoices/{invoice_id}/simulate-payment` | `Authorization: Bearer sibil_pay_…` | شبیه‌سازی واریز، فقط با کلید test |
| فروشگاه | `GET` | `/api/v1/cards` | `Authorization: Bearer sibil_pay_…` | فهرست کارت‌های فروشگاه |
| فروشگاه | `POST` | `/api/v1/cards` | `Authorization: Bearer sibil_pay_…` | افزودن کارت |
| فروشگاه | `PATCH` | `/api/v1/cards/{card_id}` | `Authorization: Bearer sibil_pay_…` | ویرایش یا فعال کردن کارت |
| فروشگاه | `POST` | `/api/v1/devices/pairing-code` | `Authorization: Bearer sibil_pay_…` | ساخت کد اتصال گوشی تازه |
| فروشگاه | `GET` | `/api/v1/devices` | `Authorization: Bearer sibil_pay_…` | گوشی‌های وصل‌شده |
| فروشگاه | `DELETE` | `/api/v1/devices/{device_id}` | `Authorization: Bearer sibil_pay_…` | جدا کردن گوشی |
| فروشگاه | `GET` | `/api/v1/gateways` | `Authorization: Bearer sibil_pay_…` | مسیرهای پرداخت این فروشگاه |
| فروشگاه | `POST` | `/api/v1/gateways/{gateway_key}/enable` | `Authorization: Bearer sibil_pay_…` | روشن یا خاموش کردن یک مسیر پرداخت |
| فروشگاه | `POST` | `/api/v1/webhook-test` | `Authorization: Bearer sibil_pay_…` | ارسال webhook نمونه به آدرس ثبت‌شده |
| فروشگاه | `POST` | `/api/v1/invoices/{invoice_id}/confirm-deposit` | `Authorization: Bearer sibil_pay_…` | تأیید دستی واریزی دیررسیده |
| فروشگاه | `GET` | `/api/v1/store` | `Authorization: Bearer sibil_pay_…` | تنظیمات فروشگاه |
| فروشگاه | `PATCH` | `/api/v1/store` | `Authorization: Bearer sibil_pay_…` | به‌روزرسانی تنظیمات و آدرس webhook |
| فروشگاه | `GET` | `/api/v1/wallet` | `Authorization: Bearer sibil_pay_…` | موجودی کیف کارمزد |
| فروشگاه | `GET` | `/api/v1/stats/summary` | `Authorization: Bearer sibil_pay_…` | خلاصه آماری |
| فروشگاه | `GET` | `/api/v1/stats/export.xlsx` | `Authorization: Bearer sibil_pay_…` | خروجی اکسل |
| فروشگاه | `GET` | `/api/v1/stats/export.csv` | `Authorization: Bearer sibil_pay_…` | خروجی CSV |
| فروشگاه | `GET` | `/api/v1/stats/export.pdf` | `Authorization: Bearer sibil_pay_…` | خروجی PDF |
| فروشگاه | `GET` | `/api/v1/matches` | `Authorization: Bearer sibil_pay_…` | تطبیق‌های نیازمند بررسی |
| فروشگاه | `POST` | `/api/v1/matches/{match_id}/resolve` | `Authorization: Bearer sibil_pay_…` | تعیین تکلیف یک تطبیق |
| فروشگاه | `GET` | `/api/v1/strays` | `Authorization: Bearer sibil_pay_…` | واریزی‌های بی‌صاحب با پیشنهاد نزدیک‌ترین فاکتور |
| فروشگاه | `POST` | `/api/v1/strays/{sms_id}/ignore` | `Authorization: Bearer sibil_pay_…` | کنار گذاشتن واریزی بی‌صاحب |
| فروشگاه | `POST` | `/api/v1/strays/{sms_id}/claim` | `Authorization: Bearer sibil_pay_…` | وصل کردن واریزی بی‌صاحب به فاکتور |
| دستگاه | `POST` | `/api/v1/device/pair` | `device_id` و `device_secret` | جفت‌سازی گوشی با کد شش‌رقمی |
| دستگاه | `POST` | `/api/v1/device/sms` | `device_id` و `device_secret` | فرستادن پیامک یا اعلان بانکی |
| دستگاه | `POST` | `/api/v1/device/heartbeat` | `device_id` و `device_secret` | زنده بودن گوشی |
| دستگاه | `POST` | `/api/v1/device/gateway-choice` | `device_id` و `device_secret` | انتخاب دائمی گوشی و سیم‌کارت گیت‌وی |
| دستگاه | `POST` | `/api/v1/device/bank-unit` | `device_id` و `device_secret` | تعیین واحد پول یک بانک |
| دستگاه | `GET` | `/api/v1/device/banks` | `device_id` و `device_secret` | کاتالوگ بانک‌ها برای اپ |
| دستگاه | `POST` | `/api/v1/device/bootstrap` | `device_id` و `device_secret` | وضعیت اولیه اپ بعد از باز شدن |
| دستگاه | `POST` | `/api/v1/device/transactions` | `device_id` و `device_secret` | فرستادن فهرست تراکنش گوشی |
| دستگاه | `POST` | `/api/v1/device/card-toggle` | `device_id` و `device_secret` | فعال یا غیرفعال کردن کارت از گوشی |
| دستگاه | `POST` | `/api/v1/device/events` | `device_id` و `device_secret` | رویدادهای اپ مثل تغییر وضعیت سرویس |
| بانک‌ها | `GET` | `/api/v1/banks` | عمومی | فهرست بانک‌ها با واحد پیش‌فرض و نمونه پیامک |
| بانک‌ها | `POST` | `/api/v1/banks/parse` | عمومی | آزمودن یک پیامک، بدون ذخیره |
| عمومی | `GET` | `/mini` | عمومی | مینی‌اپ |
| عمومی | `GET` | `/mini/go` | عمومی | ورود مینی‌اپ با توکن |
| عمومی | `GET` | `/mini/{store_id}/{token}` | عمومی | مینی‌اپ فروشگاه |
| عمومی | `GET` | `/mini/health` | عمومی | سلامت مینی‌اپ |
| عمومی | `POST` | `/api/v1/mini/me` | عمومی | فروشگاه و فاکتورهای همین توکن مینی‌اپ |
| عمومی | `GET` | `/pay/{invoice_id}` | عمومی | صفحه پرداخت فاکتور |
| عمومی | `GET` | `/pay/{gateway_key}/{invoice_id}` | عمومی | صفحه پرداخت فاکتور با مسیر مشخص |
| عمومی | `GET` | `/g/{slug}/{invoice_id}` | عمومی | صفحه پرداخت فاکتور در درگاه فروشگاه |
| عمومی | `GET` | `/downloads/sibilpay.apk` | عمومی | دانلود اپ اندروید |
| عمومی | `GET` | `/docs/integration` | عمومی | راهنمای اتصال روی همان سرور |
| عمومی | `GET` | `/docs` | عمومی | مستندات تعاملی اگر فعال باشد |
| عمومی | `GET` | `/g/{slug}` | عمومی | درگاه فروشگاه، ساخت فاکتور با مبلغ دستی |
| عمومی | `GET` | `/@{slug}` | عمومی | همان درگاه با آدرس کوتاه |
| عمومی | `GET` | `/@{slug}/{invoice_id}` | عمومی | صفحه پرداخت با آدرس کوتاه |
| عمومی | `GET` | `/api/v1/public/invoices/{invoice_id}` | عمومی | وضعیت فاکتور بدون کلید |
| عمومی | `GET` | `/api/v1/public/invoices/{invoice_id}/events` | عمومی | جریان زنده وضعیت با SSE |
| عمومی | `GET` | `/r/{token}.png` | عمومی | رسید به‌صورت تصویر |
| عمومی | `GET` | `/r/{token}` | عمومی | صفحه رسید |
| عمومی | `GET` | `/api/v1/public/receipts/{token}` | عمومی | رسید به‌صورت JSON |
| رمزارز | `GET` | `/crypto/{invoice_id}` | عمومی | صفحه پرداخت رمزارزی فاکتور |
| رمزارز | `GET` | `/api/v1/public/crypto/{invoice_id}` | عمومی | اطلاعات رمزارزی فاکتور به‌صورت JSON |
| رمزارز | `POST` | `/api/v1/public/crypto/{invoice_id}/hash` | عمومی | ثبت هش تراکنش برای تأیید |
| رمزارز | `GET` | `/crypto/{invoice_id}/receipt` | عمومی | رسید رمزارزی |
| ادمین | `POST` | `/api/v1/admin/stores` | `X-Admin-Token` | ساخت فروشگاه |
| ادمین | `GET` | `/api/v1/admin/stores` | `X-Admin-Token` | فهرست فروشگاه‌ها |
| ادمین | `POST` | `/api/v1/admin/stores/{store_id}/wallet/topup` | `X-Admin-Token` | شارژ کیف کارمزد فروشگاه |
| ادمین | `POST` | `/api/v1/admin/stores/{store_id}/api-keys` | `X-Admin-Token` | صدور کلید API |
| ادمین | `POST` | `/api/v1/admin/stores/{store_id}/webhook` | `X-Admin-Token` | ثبت مقصد webhook فروشگاه |
| ادمین | `GET` | `/api/v1/admin/overview` | `X-Admin-Token` | خلاصه کل پلتفرم |
| ادمین | `GET` | `/api/v1/admin/devices` | `X-Admin-Token` | همه دستگاه‌ها |
| پشتیبانی | `GET` | `/support/t/{store_id}/{token}` | توکن در مسیر | فهرست تیکت‌های فروشگاه |
| پشتیبانی | `POST` | `/support/t/{store_id}/{token}/new` | توکن در مسیر | تیکت تازه |
| پشتیبانی | `GET` | `/support/t/{store_id}/{token}/t/{ticket_id}` | توکن در مسیر | یک تیکت |
| پشتیبانی | `POST` | `/support/t/{store_id}/{token}/t/{ticket_id}/reply` | توکن در مسیر | پاسخ به تیکت |
| پشتیبانی | `GET` | `/support/admin/{token}` | توکن در مسیر | فهرست تیکت‌ها برای پشتیبانی |
| پشتیبانی | `GET` | `/support/admin/{token}/t/{ticket_id}` | توکن در مسیر | یک تیکت در پنل پشتیبانی |
| پشتیبانی | `POST` | `/support/admin/{token}/t/{ticket_id}/reply` | توکن در مسیر | پاسخ پشتیبانی |
| سلامت | `GET` | `/health` | عمومی | سلامت سرویس |
| سلامت | `GET` | `/api/v1/net/ping` | عمومی | تست شبکه و پورت |

## کدهای خطا

| کد | HTTP | معنا |
|---|---|---|
| `DEPOSIT_ALREADY_USED` | — | این واریز قبلاً به فاکتوری وصل شده است |
| `DEPOSIT_NOT_FOUND` | — | پیامک واریز پیدا نشد |
| `EMAIL_TAKEN` | — | ایمیل قبلاً برای فروشگاه دیگری ثبت شده |
| `EVIDENCE_REQUIRED` | — | برای تأیید دستی، مدرک (sms_id یا مبلغ) لازم است |
| `GATEWAY_DISABLED` | — | درگاه برای این فروشگاه فعال نیست |
| `INVALID_AMOUNT` | — | مبلغ نامعتبر |
| `INVALID_EMAIL` | — | ایمیل معتبر نیست |
| `INVALID_TRANSITION` | — | گذار وضعیت غیرمجاز |
| `INVOICE_ALREADY_VERIFIED` | — | این فاکتور قبلاً تأیید و تحویل شده است |
| `INVOICE_NOT_FOUND` | — | فاکتور پیدا نشد (یا مال این فروشگاه نیست) |
| `INVOICE_NOT_PAYABLE` | — | وضعیت اجازه پرداخت نمی‌دهد (لغو یا منقضی بدون تأیید دستی) |
| `MANUAL_CONFIRM_REJECTED` | — | تأیید دستی مجاز نیست (پرداخت‌شده، لغو‌شده یا وضعیت نامناسب) |
| `NO_CARD_AVAILABLE` | — | کارت فعالی برای صدور فاکتور نیست |
| `REPORT_ENGINE_UNAVAILABLE` | — | تولید PDF در این سرور فعال نیست |
| `UNKNOWN_GATEWAY` | — | درگاه ناشناخته |

| `AMOUNT_POOL_EXHAUSTED` | 409 | بازه مبلغ یکتا پر شده (هر کارت ۹۹۹ عدد در گردش) |
| `INVALID_RECEIPT` | 404 | توکن رسید معتبر نیست (دستکاری‌شده) |
| `INVOICE_ERROR` | 400 | خطای عمومی دامنه |
| `NOTHING_TO_UPDATE` | 422 | بدنه PATCH خالی است |
| `SLUG_TAKEN` | 409 | شناسه فروشگاه تکراری است |
| `STORE_NOT_FOUND` | 404 | فروشگاه پیدا نشد |
| `VALIDATION_ERROR` | 422 | ورودی با طرح تعریف‌شده نمی‌خواند |

## واریزی بی‌صاحب، بانک‌ها و سیم‌کارت گیت‌وی

هر واریزی که به هیچ فاکتور بازی نخورد ذخیره می‌شود و با برچسب واریزی بی‌صاحب در ربات، در داشبورد روی `/panel/strays` و در اپ دیده می‌شود. وصل کردنش به فاکتور باز یا منقضی همان مسیر تأیید دستی است با همان قواعد: واریز دو بار مصرف نمی‌شود، فاکتور دوبار پرداخت نمی‌شود، کارمزد از کیف پول کم می‌شود و رخداد `late_deposit_accepted` در تاریخچه فاکتور ثبت می‌شود.

```bash
# ۱) چه پولی بی‌صاحب مانده؟ (به ترتیب نزدیک‌بودن به هر فاکتور باز/منقضی)
curl -s "$BASE/api/v1/strays?limit=20" -H "Authorization: Bearer $KEY"

# ۲) وصلش کن به فاکتور — فرقی نمی‌کند فاکتور باز باشد یا منقضی
curl -s -X POST "$BASE/api/v1/strays/sms_xxxx/claim" \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"invoice_id":"inv_yyyy"}'
```

پاسخ `GET /api/v1/strays`:

```json
{"success": true, "data": {"count": 1, "label": "واریزی بی‌صاحب", "total_rial": 450000,
 "strays": [{"sms_id": "sms_…", "amount_rial": 450000, "bank": "mellat", "sim_slot": "sim2",
             "payer_last4": "5678", "ref_no": "778899", "notified": true,
             "suggested_invoices": [{"invoice_id": "inv_…", "status": "expired",
                                     "remaining_rial": 450000, "exact": true, "gap_rial": 0}]}]},
 "error": null}
```

خطاها: `DEPOSIT_NOT_FOUND` 404 (پیامک نیست یا مال این فروشگاه نیست)، `DEPOSIT_ALREADY_USED` 409 (قبلاً وصل شده)، `INVOICE_NOT_PAYABLE` 409، `MANUAL_CONFIRM_REJECTED` 409.

### بانک‌ها و واحد پول

```bash
curl -s "$BASE/api/v1/banks"                                  # ۳۴ بانک + واحد + نمونه
curl -s -X POST "$BASE/api/v1/banks/parse" -H 'Content-Type: application/json' \
  -d '{"sender":"200033","body":"واریز 1,250,000 تومان به حساب 1234567890"}'
```

`/api/v1/banks/parse` چیزی ذخیره نمی‌کند؛ فقط می‌گوید واریز است یا نه، مبلغ ریالی چقدر می‌شود، و اگر نشد چرا. تنظیم دستی واحد یک بانک از سمت گوشی:

```bash
curl -s -X POST "$BASE/api/v1/device/bank-unit" -H 'Content-Type: application/json' \
  -d '{"device_id":"dev_…","device_secret":"dp_…","bank":"mellat","unit":"toman"}'
```

### پیامک هر دو سیم‌کارت و انتخاب گیت‌وی

`POST /api/v1/device/sms` هر پیامکی را می‌پذیرد. هر آیتم دو فیلد اختیاری دارد:

| فیلد | مقدار | معنا |
|---|---|---|
| `sim_slot` | `sim1` / `sim2` | پیامک روی کدام سیم‌کارت آمده |
| `channel` | `sms` / `push` | پیامک معمولی یا اعلان اپ بانک |

همه پیام‌ها ذخیره می‌شوند با `kind` برابر `deposit`، `otp` یا `other`. اگر فروشنده سیم‌کارت گیت‌وی را انتخاب کرده باشد، پیامک سیم‌کارت دیگر بایگانی می‌شود ولی پولی جابه‌جا نمی‌کند و پاسخش `{"status":"ignored","reason":"not_gateway_sim"}` است. انتخاب گیت‌وی:

```bash
curl -s -X POST "$BASE/api/v1/device/gateway-choice" -H 'Content-Type: application/json' \
  -d '{"device_id":"dev_…","device_secret":"dp_…",
       "gateway_device_id":"dev_…","gateway_sim_slot":"sim2"}'
```

`gateway_sim_slot` می‌تواند `sim1`، `sim2` یا `null` و `any` باشد. در `bootstrap` هم برمی‌گردد تا اپ بعد از ری‌استارت همان انتخاب را نشان دهد.

## نمونه جریان کامل با curl

```bash
KEY=sp_live_...
BASE=https://your-domain.example

# ۱) فاکتور بساز
INV=$(curl -s -X POST $BASE/api/v1/invoices \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"amount_rial":125000,"order_id":"WC-1042"}' | jq -r .data.id)

# ۲) لینک پرداخت را به مشتری بده
echo $BASE/pay/card/$INV

# ۳) پس از webhook معتبر، یک‌بار verify کن
curl -s -X POST $BASE/api/v1/invoices/$INV/verify -H "Authorization: Bearer $KEY" | jq .
```

## اتصال به زبان‌های دیگر

PHP، وردپرس و ووکامرس، Node.js، Python، Kotlin و Java، C#، Go، Ruby و حالت‌های بدون کد، همراه با کد آماده ساخت فاکتور، هدایت کاربر و تأیید امن webhook در [`11-integrations.md`](11-integrations.md) هست.

## ساخت فاکتور و کارمزد

- کارمزد در همان لحظه ساخت فاکتور از کیف پول فروشگاه کسر می‌شود.
- اگر موجودی کیف پول کمتر از یک کارمزد باشد فاکتور ساخته نمی‌شود و پاسخ `402 WALLET_INSUFFICIENT` است؛ فروشنده در ربات پیام شارژ می‌گیرد.
- فروشگاه اپراتور و هر فروشگاهی که `fee_flat_rial = 0` دارد کارمزد صفر دارد، بدون کسر و بدون دروازه.
- هنگام تأیید پرداخت کارمزد دوباره گرفته نمی‌شود.
- کارت باید فعال باشد؛ کارت غیرفعال یا فروشگاه بدون کارت `409 NO_CARD_AVAILABLE` می‌گیرد و فاکتور ساخته نمی‌شود.
- `webhook_endpoint` روی فاکتور ذخیره می‌شود و `invoice.created` فقط به همان مقصد می‌رود؛ سه مسیر امضا به ترتیب امتحان می‌شود: `legacy-token`، `modern`، `legacy-store`.

جزئیات در `21-invoice-fee-webhook.md`.
