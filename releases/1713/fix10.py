"""fix10 — دکمهٔ «اتصالات» هیچ‌جوره قابلِ بلعیدن نباشد.

سه لایه:
  ۱) روترِ اتصالات اول از همه ثبت می‌شود (قبلا آخر بود؛ هر هندلرِ دیگری می‌توانست
     پیام را بگیرد).
  ۲) یک میان‌افزار که *قبل از* همهٔ هندلرها متنِ «اتصالا/وبهوک» را می‌گیرد و پنل را
     همان‌جا باز می‌کند. حتی اگر هندلری در حالتِ گفتگو باشد، این یکی اول است.
  ۳) دستورِ /connections هم اضافه می‌شود.

هر بار که این میان‌افزار کاری می‌کند یک خطِ INFO در لاگ می‌نویسد، تا معلوم باشد
پیام رسیده یا نه.
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
INIT = BOT / "handlers" / ("__init__" + EXT)
MID = BOT / ("middlewares" + EXT)
MAIN = BOT / ("main" + EXT)
CONN = BOT / "handlers" / ("conn" + EXT)

for p in (INIT, MID, MAIN, CONN):
    if not p.exists():
        raise SystemExit("فایل کم است: %s" % p)

BACKUP = APP / ".sp1713-backup" / ("v5-" + time.strftime("%Y%m%d-%H%M%S") + ".tar.gz")
BACKUP.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(BACKUP, "w:gz") as tar:
    for f in (INIT, MID, MAIN, CONN):
        tar.add(f, arcname=str(f.relative_to(APP)))
print("بکاپ: %s" % BACKUP)

done = []

# ---------------------------------------------------------------- ۱) روتر اول از همه
src = INIT.read_text(encoding="utf-8")
if "CONNECT-FIRST-V5" not in src:
    old = ("    root.include_router(pay.router)")
    new = ("    # CONNECT-FIRST-V5 — پنلِ اتصالات قبل از هر روترِ دیگری؛ هیچ هندلری\n"
           "    # نمی‌تواند پیامش را ببلعد.\n"
           "    if _conn is not None:\n"
           "        root.include_router(_conn.router)\n"
           "    root.include_router(pay.router)")
    if old in src:
        src = src.replace(old, new, 1)
        INIT.write_text(src, encoding="utf-8")
        done.append("روتر اول")
    else:
        print("  • include_router(pay) پیدا نشد — ترتیب عوض نشد")

# ---------------------------------------------------------------- تک‌بار ثبت شود
src = INIT.read_text(encoding="utf-8")
_pair = "    if _conn is not None:\n        root.include_router(_conn.router)\n"
_lines = src.split("\n")
_out, _seen, _i = [], False, 0
while _i < len(_lines):
    _hit = (_lines[_i].strip().startswith("if _conn is not None:")
            and _i + 1 < len(_lines) and "_conn.router" in _lines[_i + 1])
    if _hit:
        if _seen:                              # LEGACY-INCLUDE-V5: تکرار حذف
            _i += 2
            continue
        _seen = True
    _out.append(_lines[_i])
    _i += 1
if _seen and len(_out) != len(_lines):
    INIT.write_text("\n".join(_out), encoding="utf-8")

# ---------------------------------------------------------------- ۲) میان‌افزار
src = MID.read_text(encoding="utf-8")
if "CONNECT-SHORTCUT-V5" not in src:
    block = '''

# ---------------------------------------------------------------- CONNECT-SHORTCUT-V5
_CONNECT_WORDS = ("اتصالا", "وبهوک", "وبهوک‌ها")


def _looks_like_connections(text: str) -> bool:
    clean = (text or "").replace("\\u200c", "").replace("\\ufe0f", "").strip()
    if not clean or clean.startswith("/"):
        return False
    return any(word in (text or "") or word in clean for word in _CONNECT_WORDS)


class ConnectionShortcut(BaseMiddleware):
    """«اتصالات» را قبل از هر هندلری می‌گیرد و پنل را باز می‌کند.

    دلیل: همین دکمه در چند نصب کار نمی‌کرد چون پیامش به هندلرِ دیگری می‌رسید
    (حالتِ گفتگو، روترِ دیرتر، یا برچسبِ عوض‌شده). اینجا دیگر ترتیب مهم نیست.
    """

    async def __call__(self, handler, event, data):  # type: ignore[override]
        try:
            text = getattr(event, "text", None)
            if isinstance(text, str) and _looks_like_connections(text):
                from handlers import conn as _conn_panel

                log.info("اتصالات: پیام «%s» به پنل رسید", text[:40])
                await _conn_panel.open_panel(event)
                return None
        except Exception:                            # noqa: BLE001 — هرگز پیام را نشکن
            log.exception("اتصالات: میان‌افزار خطا داد")
            return await handler(event, data)
        return await handler(event, data)
'''
    src = src.rstrip("\n") + "\n" + block
    MID.write_text(src, encoding="utf-8")
    done.append("میان‌افزار")

# ---------------------------------------------------------------- ۳) ثبت در main
src = MAIN.read_text(encoding="utf-8")
if "CONNECT-SHORTCUT-V5" not in src:
    old_imp = "from middlewares import MenuAlias, MenuReset, StoreGate"
    new_imp = "from middlewares import ConnectionShortcut, MenuAlias, MenuReset, StoreGate"
    if old_imp in src:
        src = src.replace(old_imp, new_imp, 1)
    old_reg = "    dispatcher.message.middleware(MenuReset())"
    new_reg = ("    dispatcher.message.middleware(ConnectionShortcut())   # CONNECT-SHORTCUT-V5\n"
               "    dispatcher.message.middleware(MenuReset())")
    if old_reg in src:
        src = src.replace(old_reg, new_reg, 1)
        MAIN.write_text(src, encoding="utf-8")
        done.append("ثبت در main")
    else:
        print("  • ثبتِ میان‌افزار در main پیدا نشد")

# ---------------------------------------------------------------- ۴) تابعِ مشترکِ پنل
src = CONN.read_text(encoding="utf-8")
if "async def open_panel(" not in src:
    anchor = "@router.message(F.text.func(_is_connections))"
    helper = '''async def open_panel(message: Message) -> None:
    """CONNECT-SHORTCUT-V5 — یک نقطه برای باز کردنِ پنل، از هر راهی."""
    try:
        stores = await repo.list_stores(message.from_user.id)
        if not stores:
            await message.answer("اول یک فروشگاه بساز.")
            return
        store_id = stores[0][0]
        destinations = await conn_repo.auto_destinations(store_id)
        await message.answer(await _text(store_id),
                             reply_markup=_keyboard(store_id, destinations),
                             disable_web_page_preview=True)
    except Exception:                                   # noqa: BLE001
        log.exception("پنلِ اتصالات باز نشد")
        await message.answer("پنلِ اتصالات باز نشد؛ دوباره بزن.")


'''
    if anchor in src:
        src = src.replace(anchor, helper + anchor, 1)
        # هندلرِ متنی حالا از همان تابع استفاده می‌کند
        start = src.index(anchor)
        end = src.index('@router.callback_query(F.data.startswith("cn:p:"))', start)
        src = src[:start] + ('@router.message(F.text.func(_is_connections))\n'
                            'async def connections_word(message: Message) -> None:\n'
                            '    await open_panel(message)\n\n\n'
                            '@router.message(Command("connections"))\n'
                            'async def connections_command(message: Message) -> None:\n'
                            '    await open_panel(message)\n\n\n') + src[end:]
        if "from aiogram.filters import Command" not in src:
            src = src.replace("from aiogram import F, Router",
                              "from aiogram import F, Router\nfrom aiogram.filters import Command", 1)
        CONN.write_text(src, encoding="utf-8")
        done.append("تابعِ open_panel")

for f in (INIT, MID, MAIN, CONN):
    r = subprocess.run([PY, "-m", "py_compile", str(f)], capture_output=True, text=True)
    if r.returncode != 0:
        print("سینتکس خراب شد — برگشت")
        print(r.stderr.strip()[:500])
        with tarfile.open(BACKUP) as tar:
            tar.extractall(APP)
        raise SystemExit(1)
print("  ✔ ربات — %s" % (" · ".join(done) if done else "چیزی لازم نبود"))
print("کامپایل شد.")
