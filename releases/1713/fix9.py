"""fix9 — تأیید دستی یعنی «این فاکتور تسویه شد».

واریزیِ بی‌صاحب ۳۹۰٬۰۰۰ تومان به فاکتورِ ۳٬۹۰۲٬۵۹۶ ریالی چسبانده شده بود؛ مبلغی
که به رباتِ فروشنده گزارش می‌شد همان واریزی بود، نه مبلغِ فاکتور. اینجا هنگامِ
تأیید دستی، ماندهٔ فاکتور (تا سقفِ مبلغِ خودِ فاکتور) به‌عنوانِ پرداخت ثبت می‌شود
و مبلغِ واقعیِ واریزی فقط در یادداشت و خلاصهٔ همان تأیید می‌ماند.
"""
import pathlib
import subprocess
import sys
import tarfile
import time

APP = pathlib.Path(sys.argv[1])
PY = sys.argv[2] if len(sys.argv) > 2 else sys.executable
EXT = "." + "py"
MANUAL = APP / "backend" / "app" / "services" / ("manual" + EXT)
if not MANUAL.exists():
    raise SystemExit("فایل پیدا نشد: %s" % MANUAL)

BACKUP = APP / ".sp1713-backup" / ("v4-" + time.strftime("%Y%m%d-%H%M%S") + ".tar.gz")
BACKUP.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(BACKUP, "w:gz") as tar:
    tar.add(MANUAL, arcname=str(MANUAL.relative_to(APP)))
print("بکاپ: %s" % BACKUP)

src = MANUAL.read_text(encoding="utf-8")
if "MANUAL-FULL-V1" in src:
    print("  • manual — از قبل درست است")
else:
    anchor = '''    was_expired = invoice.status == "expired"'''
    inject = '''    # MANUAL-FULL-V1 — تأیید دستی یعنی «این فاکتور تسویه شد». پس مبلغی که ثبت و
    # به رباتِ فروشنده گزارش می‌شود ماندهٔ همان فاکتور است، نه مبلغِ واریزیِ
    # بی‌صاحب. مبلغِ واقعیِ واریزی در یادداشت می‌ماند تا حساب و کتاب گم نشود.
    _deposit = int(amount)
    _target = int(invoice.amount_rial or invoice.payable_rial or 0)
    _settle = max(_target - int(invoice.paid_amount_rial or 0), 0) or _deposit
    _note = (note or ("manual confirmation of an expired invoice"
                      if invoice.status == "expired" else "manual confirmation"))
    _note = "%s · deposit_rial=%d" % (_note, _deposit)

'''
    if anchor not in src:
        raise SystemExit("بلوکِ was_expired پیدا نشد")
    src = src.replace(anchor, inject + anchor, 1)

    old_call = "        amount_rial=amount,"
    if old_call not in src:
        raise SystemExit("فراخوانیِ apply_payment پیدا نشد")
    src = src.replace(old_call, "        amount_rial=_settle,          # MANUAL-FULL-V1", 1)

    old_note = ('        note=note or ("manual confirmation of an expired invoice" if was_expired '
                'else "manual confirmation"),')
    if old_note in src:
        src = src.replace(old_note, "        note=_note,", 1)

    old_meta = 'meta={"sms_id": sms.id if sms else None, "amount_rial": amount},'
    if old_meta in src:
        src = src.replace(old_meta,
                          'meta={"sms_id": sms.id if sms else None, "amount_rial": _deposit},', 1)

    old_ret = '        "amount_rial": amount,'
    if old_ret in src:
        src = src.replace(old_ret, '        "amount_rial": _settle,\n'
                                   '        "deposit_rial": _deposit,', 1)

    MANUAL.write_text(src, encoding="utf-8")
    print("  ✔ manual — مبلغِ تأیید برابرِ مبلغِ فاکتور")

r = subprocess.run([PY, "-m", "py_compile", str(MANUAL)], capture_output=True, text=True)
if r.returncode != 0:
    print("سینتکس خراب شد — برگشت")
    print(r.stderr.strip()[:400])
    with tarfile.open(BACKUP) as tar:
        tar.extractall(APP)
    raise SystemExit(1)
print("کامپایل شد.")
