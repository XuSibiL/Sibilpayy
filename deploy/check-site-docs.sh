#!/usr/bin/env bash
# check-site-docs.sh — آیا صفحهٔ مستنداتِ سایتِ فعال، نسخهٔ تازه را نشان می‌دهد؟
#
#   bash check-site-docs.sh                       # پیش‌فرض: https://pay.mrsibilman.ir/docs
#   bash check-site-docs.sh https://x.tld/docs    # آدرسِ دیگر
#
# اگر صفحهٔ قدیمی بود، همین اسکریپت نشان می‌دهد چه چیزی سرو می‌شود، کدام فایل روی
# دیسک مستندات است، کدام پروسه/پورت آن را می‌دهد و از کدام فایل/مسیر می‌خواند.
set -uo pipefail

URL="${1:-https://pay.mrsibilman.ir/docs}"
APP="${SIBILPAY_DIR:-/opt/sibilpay}"
OUT=/tmp/_site_docs_check.html

echo "=== ۱) صفحهٔ عمومی ==="
CODE=$(curl -sSL -o "$OUT" -w "%{http_code}" --max-time 25 "$URL" || echo 000)
SIZE=$(wc -c < "$OUT" 2>/dev/null || echo 0)
echo "  $URL → $CODE ($SIZE بایت)"

mark() { grep -q -- "$1" "$OUT" 2>/dev/null && echo "  ✔ $1" || echo "  ✗ $1"; }
mark "webhook_url"
mark 'id="cancel"'
mark "X-SIBILPAY-Delivery"
mark "لغو، رد کردن"

NEW=0
grep -q "X-SIBILPAY-Delivery" "$OUT" 2>/dev/null && grep -q 'id="cancel"' "$OUT" 2>/dev/null && NEW=1
if [ "$NEW" = 1 ]; then
  echo ""
  echo "✅ صفحهٔ فعال، نسخهٔ تازه است. کاری لازم نیست."
  exit 0
fi

echo ""
echo "⏳ صفحهٔ فعال نسخهٔ قدیمی است؛ علت را پیدا می‌کنم…"

echo ""
echo "=== ۲) سرویس‌ها و پورت‌های شنونده ==="
(ss -lntp 2>/dev/null || netstat -lntp 2>/dev/null) | head -15

echo ""
echo "=== ۳) پروسه‌های سیبیل‌پی ==="
ps aux 2>/dev/null | grep -Ei "uvicorn|gunicorn|hypercorn|sibilpay" | grep -v grep | head -8

echo ""
echo "=== ۴) تنظیمِ nginx برای این دامنه ==="
HOST=$(echo "$URL" | sed -e 's#https\?://##' -e 's#/.*##')
if command -v nginx >/dev/null 2>&1; then
  nginx -T 2>/dev/null | awk -v h="$HOST" '
    /server[[:space:]]*\{/ {buf=""; inside=1}
    inside {buf=buf $0 "\n"}
    /server_name/ && index($0, h) {found=1}
    /^[[:space:]]*\}[[:space:]]*$/ {if(inside && found){print buf; found=0} inside=0}
  ' | grep -E "server_name|proxy_pass|root|alias|listen|location|try_files" | head -20
  echo "  --- فایل‌های تنظیمات:"
  nginx -T 2>/dev/null | grep -E "^# configuration file" | grep -iE "sibil|pay|mrsibilman" | head -5
else
  echo "  nginx نصب نیست"
  if command -v docker >/dev/null 2>&1; then
    echo "  --- کانتینرها:"
    docker ps --format '  {{.Names}}  {{.Image}}  {{.Ports}}' 2>/dev/null | head -10
  fi
fi

echo ""
echo "=== ۵) نسخه‌های docs.html روی دیسک ==="
find /opt /srv /var/www /root /home -name "docs.html" -path "*templates*" 2>/dev/null | while read -r f; do
  s=$(wc -c < "$f" 2>/dev/null || echo 0)
  t=$(stat -c %y "$f" 2>/dev/null | cut -d. -f1)
  m="قدیمی"
  grep -q "X-SIBILPAY-Delivery" "$f" 2>/dev/null && m="تازه"
  echo "  $m | $s بایت | $t | $f"
done

echo ""
echo "=== ۶) نتیجه ==="
echo "  اگر فایلِ «تازه» در مسیرِ دیگری جز $APP/backend/app/templates/docs.html بود،"
echo "  همان مسیر را در فرمانِ بعدی بده:"
echo "    SIBILPAY_DIR=<مسیرِ آن نصب> sudo -E bash /tmp/update-site-docs.sh"
echo "  اگر فایلی «تازه» نبود، اول این را بزن:"
echo "    sudo bash /tmp/update-site-docs.sh"
echo ""
echo "  خروجیِ همین چهار بخش را بفرست تا دقیقاً همان چیزی را که سرو می‌شود درست کنم."
