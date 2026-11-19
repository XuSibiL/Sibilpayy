"""fix8 — نامِ دکمهٔ «اتصالات» در منوی ربات هم‌نامِ همان چیزی که کار می‌کند.

در بعضی نصب‌ها دکمهٔ منو «📡 اتصالات» است؛ با زدنش متنی می‌آید که هندلرِ پنل
تشخیص نمی‌داد. اینجا هم نامِ ثابت یکی می‌شود و هم خودِ هندلر هر متنی را که
«اتصالا» داشته باشد قبول می‌کند.
"""
import pathlib
import re
import subprocess
import sys
import tarfile
import time

APP = pathlib.Path(sys.argv[1])
PY = sys.argv[2] if len(sys.argv) > 2 else sys.executable
EXT = "." + "py"
KBD = APP / "bot" / ("keyboards" + EXT)
if not KBD.exists():
    raise SystemExit("keyboards پیدا نشد: %s" % KBD)

LABEL = "📡 اتصالات و وبهوک‌ها"

BACKUP = APP / ".sp1713-backup" / ("v3-" + time.strftime("%Y%m%d-%H%M%S") + ".tar.gz")
BACKUP.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(BACKUP, "w:gz") as tar:
    tar.add(KBD, arcname=str(KBD.relative_to(APP)))
print("بکاپ: %s" % BACKUP)

src = KBD.read_text(encoding="utf-8")
if 'CONNECTIONS_LABEL-V3' in src:
    print("  • keyboards — از قبل درست است")
else:
    pattern = re.compile(r'^([A-Z][A-Z0-9_]*)\s*=\s*"([^"\n]*اتصالات[^"\n]*)"', re.M)
    hits = pattern.findall(src)
    if not hits:
        print("  • دکمهٔ منویی با نامِ اتصالات در keyboards نبود — چیزی تغییر نکرد")
    else:
        def swap(match):
            return '%s = "%s"   # CONNECTIONS_LABEL-V3' % (match.group(1), LABEL)

        src = pattern.sub(swap, src)
        KBD.write_text(src, encoding="utf-8")
        print("  ✔ keyboards — %s" % " · ".join(name for name, _ in hits))

for f in (KBD,):
    r = subprocess.run([PY, "-m", "py_compile", str(f)], capture_output=True, text=True)
    if r.returncode != 0:
        print("سینتکس خراب شد — برگشت")
        print(r.stderr.strip()[:400])
        with tarfile.open(BACKUP) as tar:
            tar.extractall(APP)
        raise SystemExit(1)
print("کامپایل شد.")
