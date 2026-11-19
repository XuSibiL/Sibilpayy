"""fix11 — ایموجیِ پریمیوم روی دکمهٔ *کیبورد* (نه فقط اینلاین).

سه چیز:
  ۱) services/premium.py: ``_apply_to_buttons`` حالا ``markup.keyboard`` را هم
     می‌بیند. تا امروز فقط ``inline_keyboard`` را می‌گشت، پس دکمهٔ کیبوردِ ربات
     هیچ‌وقت آیکون نمی‌گرفت — همان چیزی که در اسکرین‌شات دیدی.
  ۲) خاموش‌شدنِ آیکون‌ها: قبلا اولین «نه»ِ تلگرام کلِ آیکون‌ها (اینلاین و کیبورد)
     را برای همیشه خاموش می‌کرد و بی‌صدا. حالا جدا حساب می‌شود و در لاگ می‌نویسد
     تلگرام چه گفت.
  ۳) دستورِ /icons : یک پیام می‌فرستد که همه‌چیز را نشان می‌دهد — نسخهٔ aiogram،
     چند نگاشت داری، خودِ نگاشت‌ها، و یک دکمهٔ آزمایشی با آیکون. اگر تلگرام رد
     کند، متنِ خطای خودش را می‌نویسد. یک تپ، بدونِ لاگ.
"""
import pathlib
import subprocess
import sys
import tarfile
import time

APP = pathlib.Path(sys.argv[1])
PY = sys.argv[2] if len(sys.argv) > 2 else sys.executable
EXT = "." + "py"
BOT = APP / "bot"
PREMIUM = BOT / "services" / ("premium" + EXT)
INIT = BOT / "handlers" / ("__init__" + EXT)
ICONS = BOT / "handlers" / ("icons" + EXT)

for p in (PREMIUM, INIT):
    if not p.exists():
        raise SystemExit("فایل کم است: %s" % p)

BACKUP = APP / ".sp1713-backup" / ("v6-" + time.strftime("%Y%m%d-%H%M%S") + ".tar.gz")
BACKUP.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(BACKUP, "w:gz") as tar:
    for f in (PREMIUM, INIT) + ((ICONS,) if ICONS.exists() else ()):
        tar.add(f, arcname=str(f.relative_to(APP)))
print("بکاپ: %s" % BACKUP)

done = []
src = PREMIUM.read_text(encoding="utf-8")

# ------------------------------------------------------- ۱) دکمهٔ کیبورد هم آیکون بگیرد
if "REPLY-ICON-V6" not in src:
    old = '''def _apply_to_buttons(method) -> None:'''
    new_helper = '''_CONNECT_WORDS = ("اتصالا", "وبهوک")


def _icon_for_text(text: str):
    """REPLY-ICON-V6 — ایموجیِ اولِ متن و شناسهٔ پریمیومِ آن، با هر شکلی از نوشتن."""
    if not text or not MAP:
        return None, None
    head = ""
    for ch in text:
        if ch.isalpha():
            break
        head += ch
    head = head.strip()
    candidates = [head, head.replace("\\ufe0f", ""), head + "\\ufe0f"]
    for cand in candidates:
        if cand and cand in MAP:
            return cand, MAP[cand]
    norm = _strip_variation(head)
    for key, cid in MAP.items():
        if norm and _strip_variation(key) == norm:
            return head, cid
    return None, None


def _apply_to_reply_keyboard(markup) -> None:
    """REPLY-ICON-V6 — همین کار برای دکمه‌های کیبوردِ پایینِ صفحه.

    تلگرام برای این دکمه‌ها فیلدِ ``icon_custom_emoji_id`` دارد؛ هیچ entityای
    پشتیبانی نمی‌شود. اگر آیکون بیفتد، ایموجیِ متنی فقط وقتی برداشته می‌شود که
    متن پس از برداشتن هنوز همان دکمه را نشان بدهد (مثل «اتصالات»)، تا فیلترهای
    هندلر به‌هم نریزند.
    """
    if not MAP:
        return
    rows = getattr(markup, "keyboard", None)
    if not rows:
        return
    for row in rows:
        items = row if isinstance(row, list) else [row]
        for item in items:
            text = getattr(item, "text", None)
            if not isinstance(text, str) or not text:
                continue
            glyph, custom_id = _icon_for_text(text)
            if not custom_id:
                continue
            try:
                setattr(item, "icon_custom_emoji_id", custom_id)
            except Exception:                     # noqa: BLE001 — aiogramِ قدیمی
                log.debug("this aiogram build cannot put icons on reply buttons")
                continue
            if glyph:
                rest = text.replace(glyph, "", 1).strip()
                keep = any(word in rest for word in _CONNECT_WORDS)
                if rest and not keep:             # برچسب دست‌نخورده می‌مانَد
                    continue
                if rest:
                    item.text = rest


def _apply_to_buttons(method) -> None:'''
    if old in src:
        src = src.replace(old, new_helper, 1)
        done.append("تابعِ آیکونِ کیبورد")
    else:
        print("  • _apply_to_buttons پیدا نشد")

# داخلِ _apply_to_buttons: به کیبوردِ ربات هم سر بزن
old_rows = '''    rows = getattr(markup, "inline_keyboard", None)
    if not rows:
        return
    for row in rows:'''
new_rows = '''    _apply_to_reply_keyboard(markup)          # REPLY-ICON-V6
    rows = getattr(markup, "inline_keyboard", None)
    if not rows:
        return
    for row in rows:'''
if "REPLY-ICON-V6" not in PREMIUM.read_text(encoding="utf-8") or new_rows not in src:
    if old_rows in src and new_rows not in src:
        src = src.replace(old_rows, new_rows, 1)
        done.append("فراخوانی در _apply_to_buttons")

# ------------------------------------------------------- ۲) خاموشیِ بی‌صدا حذف شود
old_kill = '''                if _strip_bling(method):
                    BUTTON_BLING = False'''
new_kill = '''                if _strip_bling(method):
                    # REPLY-ICON-V6 — قبلا اینجا کلِ آیکون‌ها برای همیشه و بی‌صدا
                    # خاموش می‌شد. حالا فقط همان پیام ساده می‌رود و علتش لاگ می‌شود.
                    BLING_ERRORS.append(str(exc)[:200])
                    log.warning("Telegram آیکونِ دکمه را رد کرد (%s) — همان پیام ساده رفت", exc)'''
if old_kill in src:
    src = src.replace(old_kill, new_kill, 1)
    done.append("لاگِ رد شدن")

# پرچمِ جدا: آیکونِ کیبورد را می‌شود بی‌خطر خاموش کرد، اینلاین را نه
if "REPLY_BLING = True" not in src:
    src = src.replace(
        "def _apply_to_reply_keyboard(markup) -> None:",
        "#: REPLY-ICON-V6 — اگر تلگرام آیکونِ کیبورد را رد کند فقط این خاموش می‌شود؛\n"
        "#: آیکونِ دکمه‌های اینلاین دست‌نخورده می‌مانَد.\n"
        "REPLY_BLING = True\n\n\n"
        "def _apply_to_reply_keyboard(markup) -> None:", 1)
    src = src.replace(
        "    rows = getattr(markup, \"keyboard\", None)",
        "    if not REPLY_BLING:\n        return\n"
        "    rows = getattr(markup, \"keyboard\", None)", 1)
    done.append("پرچمِ جدا")

if "_markup = getattr(method" not in src:
    src = src.replace(
        '                    BLING_ERRORS.append(str(exc)[:200])',
        '                    BLING_ERRORS.append(str(exc)[:200])\n'
        '                    _markup = getattr(method, "reply_markup", None)\n'
        '                    if getattr(_markup, "keyboard", None):\n'
        '                        globals()["REPLY_BLING"] = False', 1)
    done.append("خاموشیِ فقط کیبورد")

if "BLING_ERRORS" not in src.split("def _strip_bling")[0]:
    src = src.replace('BUTTON_BLING = True',
                      'BUTTON_BLING = True\n\n#: آخرین خطاهای تلگرام دربارهٔ آیکونِ دکمه‌ها (برای /icons)\nBLING_ERRORS: list[str] = []', 1)
    done.append("BLING_ERRORS")

PREMIUM.write_text(src, encoding="utf-8")

# ------------------------------------------------------- ۳) دستورِ /icons
if not ICONS.exists():
    ICONS.write_text('''"""دستورِ /icons — نشان بده ایموجیِ پریمیوم روی دکمه‌ها کار می‌کند یا نه."""
from __future__ import annotations

import aiogram
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, \\
    ReplyKeyboardMarkup

from handlers.common import is_admin
from services import premium

router = Router(name="icons")


@router.message(Command("icons"))
async def icons(message) -> None:
    if not is_admin(message.from_user.id):
        return
    await premium.load_map()          # نگاشتِ تازه؛ لازم نیست ربات را ری‌استارت کنی
    try:
        has_field = "icon_custom_emoji_id" in KeyboardButton.model_fields
    except Exception:                                   # noqa: BLE001
        has_field = False
    mapping = dict(premium.MAP)
    lines = [
        "🎛 آیکونِ دکمه‌ها",
        "aiogram: %s" % getattr(aiogram, "__version__", "?"),
        "فیلدِ آیکون روی دکمهٔ کیبورد: %s" % ("دارد" if has_field else "ندارد — aiogram را به‌روز کن"),
        "نگاشت‌ها: %d" % len(mapping),
    ]
    shown = 0
    for base, cid in list(mapping.items()):
        if not base or not cid or shown >= 8:
            continue
        lines.append("• %s → %s" % (base, cid))
        shown += 1
    if not mapping:
        lines.append("هیچ نگاشتی نیست: پنل مدیریت ← ایموجیِ پریمیوم ← یک ایموجی معمولی "
                     "و یک ایموجی پریمیوم بفرست.")
    if premium.BLING_ERRORS:
        lines.append("آخرین «نه»ی تلگرام: %s" % premium.BLING_ERRORS[-1])

    first = next((cid for cid in mapping.values() if cid), None)
    buttons = []
    if first and has_field:
        buttons.append([KeyboardButton(text="📡 اتصالات", icon_custom_emoji_id=first)])
    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True) if buttons else None
    await message.answer("\\n".join(lines), reply_markup=markup,
                         disable_web_page_preview=True)

    if first and has_field:
        try:
            await message.answer(
                "این پیام با آیکونِ اینلاین است:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="آزمایش", callback_data="noop",
                                         icon_custom_emoji_id=first)]]))
        except Exception as exc:                        # noqa: BLE001
            await message.answer("تلگرام اینلاین را رد کرد: %s" % str(exc)[:180])
''', encoding="utf-8")
    done.append("دستورِ /icons")

src = INIT.read_text(encoding="utf-8")
_block = (
    "    try:\n"
    "        from handlers import icons as _icons       # ICONS-CMD-V6\n"
    "\n"
    "        root.include_router(_icons.router)\n"
    "    except Exception:                              # noqa: BLE001\n"
    '        logging.getLogger("sibilpay.bot").exception("روترِ /icons ثبت نشد")\n'
)
while _block in src:                                # پاک‌سازیِ ثبت‌های قبلی
    src = src.replace(_block, "", 1)
anchor = "    if _conn is not None:\n        root.include_router(_conn.router)\n"
if anchor in src:
    if "import logging" not in src:
        src = "import logging\n" + src
    src = src.replace(anchor, anchor + _block, 1)
    INIT.write_text(src, encoding="utf-8")
    done.append("ثبتِ /icons")
else:
    print("  • جای ثبتِ روتر پیدا نشد")

MAIN = BOT / ("main" + EXT)
if MAIN.exists():
    src = MAIN.read_text(encoding="utf-8")
    if 'command="icons"' not in src:
        anchor = '    BotCommand(command="admin", description="پنل مدیریت (فقط مدیر)"),'
        if anchor in src:
            src = src.replace(anchor, anchor + '\n'
                              '    BotCommand(command="icons", description="آیکونِ دکمه‌ها و ایموجیِ پریمیوم"),', 1)
            MAIN.write_text(src, encoding="utf-8")
            done.append("دستور در منو")

for f in (PREMIUM, ICONS, INIT, MAIN):
    if not f.exists():
        continue
    r = subprocess.run([PY, "-m", "py_compile", str(f)], capture_output=True, text=True)
    if r.returncode != 0:
        print("سینتکس خراب شد — برگشت")
        print(r.stderr.strip()[:600])
        with tarfile.open(BACKUP) as tar:
            tar.extractall(APP)
        raise SystemExit(1)
print("  ✔ آیکون — %s" % (" · ".join(done) if done else "چیزی لازم نبود"))
print("کامپایل شد.")
