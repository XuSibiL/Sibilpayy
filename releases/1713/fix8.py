"""fix8 — یک نام برای دکمه، و ایموجیِ پریمیوم که واقعا بنشیند.

سه کار:
  ۱) هر ثابتِ منو که «اتصالات» در آن است، «📡 اتصالات» می‌شود (یک نام، همه‌جا).
  ۲) دکمهٔ اینلاینِ همان پنل هم «📡 اتصالات» می‌شود.
  ۳) ``reply_button`` اگر ایموجیِ اولِ برچسب را ببیند همان را آیکونِ پریمیوم می‌کند؛
     قبلا فقط وقتی کار می‌کرد که فراخوان ایموجی را جدا پاس می‌داد و بعضی ردیف‌ها
     این کار را نمی‌کردند — نتیجه: ایموجیِ عادی می‌ماند و آیکون نمی‌نشیند.
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

LABEL = "📡 اتصالات"

BACKUP = APP / ".sp1713-backup" / ("v3-" + time.strftime("%Y%m%d-%H%M%S") + ".tar.gz")
BACKUP.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(BACKUP, "w:gz") as tar:
    tar.add(KBD, arcname=str(KBD.relative_to(APP)))
print("بکاپ: %s" % BACKUP)

src = KBD.read_text(encoding="utf-8")
done = []

# ---------------------------------------------------------------- ۱) نامِ ثابت‌ها
pattern = re.compile(r'^([A-Z][A-Z0-9_]*)\s*=\s*"([^"\n]*اتصالات[^"\n]*)"', re.M)
hits = pattern.findall(src)
if hits:
    src = pattern.sub(lambda m: '%s = "%s"   # CONNECTIONS-LABEL-V4' % (m.group(1), LABEL), src)
    done.append("ثابت‌ها: " + " · ".join(name for name, _ in hits))

# ---------------------------------------------------------------- ۲) دکمهٔ اینلاین
if '"اتصالات و وبهوک‌ها"' in src:
    src = src.replace('"اتصالات و وبهوک‌ها"', '"📡 اتصالات"')
    done.append("دکمهٔ اینلاین")
elif '"📡 اتصالات"' not in src:
    done.append("دکمهٔ اینلاین نبود")

# ---------------------------------------------------------------- ۳) آیکونِ خودکار
if "AUTO-ICON-V1" not in src:
    anchor = "def reply_button("
    helper = '''def _leading_emoji(text: str) -> str:
    """AUTO-ICON-V1 — ایموجیِ اولِ برچسب، تا برای آیکونِ پریمیوم شناخته شود."""
    out = []
    for ch in text or "":
        if ch.isalpha():
            break
        out.append(ch)
    return "".join(out).strip()


'''
    if anchor in src:
        src = src.replace(anchor, helper + anchor, 1)
        old = "    icon_id = _icon_for(emoji) if emoji else None\n    label = text\n"
        new = ("    icon_id = _icon_for(emoji) if emoji else None\n"
               "    if not icon_id:                        # AUTO-ICON-V1\n"
               "        head = _leading_emoji(text)\n"
               "        if head:\n"
               "            icon_id = _icon_for(head)\n"
               "            if icon_id:\n"
               "                emoji = head\n"
               "    label = text\n")
        if old in src:
            src = src.replace(old, new, 1)
            done.append("آیکونِ خودکار")
        else:
            print("  • بدنهٔ reply_button پیدا نشد — آیکونِ خودکار اضافه نشد")

if done:
    KBD.write_text(src, encoding="utf-8")
print("  ✔ keyboards — %s" % (" · ".join(done) if done else "چیزی لازم نبود"))

r = subprocess.run([PY, "-m", "py_compile", str(KBD)], capture_output=True, text=True)
if r.returncode != 0:
    print("سینتکس خراب شد — برگشت")
    print(r.stderr.strip()[:400])
    with tarfile.open(BACKUP) as tar:
        tar.extractall(APP)
    raise SystemExit(1)
print("کامپایل شد.")
