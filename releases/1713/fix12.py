"""fix12 — در فهرستِ دستورهای ربات فقط /start بمانَد.

«/admin» و «/icons» از منویِ کنارِ اینپوت برداشته می‌شوند، ولی خودِ دستورها
سرِ جایشان کار می‌کنند (فقط دیگر لیست نمی‌شوند).
"""
import pathlib
import re
import subprocess
import sys
import tarfile
import time

APP = pathlib.Path(sys.argv[1])
PY = sys.argv[2] if len(sys.argv) > 2 else sys.executable
MAIN = APP / "bot" / ("main" + "." + "py")
if not MAIN.exists():
    raise SystemExit("فایل کم است: %s" % MAIN)

BACKUP = APP / ".sp1713-backup" / ("v7-" + time.strftime("%Y%m%d-%H%M%S") + ".tar.gz")
BACKUP.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(BACKUP, "w:gz") as tar:
    tar.add(MAIN, arcname=str(MAIN.relative_to(APP)))
print("بکاپ: %s" % BACKUP)

src = MAIN.read_text(encoding="utf-8")
new = ('COMMANDS = [                    # COMMANDS-START-ONLY-V7 — فقط /start در فهرست\n'
       '    BotCommand(command="start", description="شروع و منوی اصلی"),\n'
       ']\n')

if "COMMANDS-START-ONLY-V7" in src:
    print("  ✔ منو — از قبل فقط /start")
else:
    m = re.search(r"COMMANDS\s*=\s*\[.*?\n\]\n", src, re.S)
    if not m:
        raise SystemExit("فهرستِ COMMANDS پیدا نشد")
    src = src[:m.start()] + new + src[m.end():]
    MAIN.write_text(src, encoding="utf-8")
    print("  ✔ منو — فقط /start")

r = subprocess.run([PY, "-m", "py_compile", str(MAIN)], capture_output=True, text=True)
if r.returncode != 0:
    print("سینتکس خراب شد — برگشت")
    print(r.stderr.strip()[:400])
    with tarfile.open(BACKUP) as tar:
        tar.extractall(APP)
    raise SystemExit(1)
print("کامپایل شد.")
