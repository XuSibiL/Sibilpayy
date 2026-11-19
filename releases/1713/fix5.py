import pathlib, subprocess, sys, tarfile, time

APP = pathlib.Path(sys.argv[1])
PY = sys.argv[2] if len(sys.argv) > 2 else sys.executable
BOT = APP / "bot"
EXT = "." + "py"
INIT = BOT / "handlers" / ("__init__" + EXT)
KBD = BOT / ("keyboards" + EXT)
LATE = BOT / "handlers" / ("late" + EXT)
CONN = BOT / "handlers" / ("conn" + EXT)
CREPO = BOT / "services" / ("conn_repo" + EXT)

missing = [str(p) for p in (INIT, KBD, LATE, CONN, CREPO) if not p.exists()]
if missing:
    raise SystemExit("فایل کم است:\n  " + "\n  ".join(missing))

BACKUP = APP / ".sp1713-backup" / ("bot-" + time.strftime("%Y%m%d-%H%M%S") + ".tar.gz")
BACKUP.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(BACKUP, "w:gz") as tar:
    for f in (INIT, KBD, LATE):
        tar.add(f, arcname=str(f.relative_to(APP)))
print("بکاپ: %s" % BACKUP)


def compile_all() -> None:
    for f in (INIT, KBD, LATE, CONN, CREPO):
        r = subprocess.run([PY, "-m", "py_compile", str(f)], capture_output=True, text=True)
        if r.returncode != 0:
            print("سینتکس خراب شد — برگشت")
            print(r.stderr.strip()[:500])
            with tarfile.open(BACKUP) as tar:
                tar.extractall(APP)
            raise SystemExit(1)
    print("کامپایل شد.")


done = []

# ---------------------------------------------------------------- ۱) روترِ اتصالات
src = INIT.read_text(encoding="utf-8")
if "CONNECT-V1" not in src:
    old_import = ("try:\n"
                  "    from . import hooks as _hooks\n"
                  "except Exception:                             # noqa: BLE001\n"
                  "    _hooks = None")
    new_import = (old_import + "\n\n"
                  "try:                                          # CONNECT-V1 — پنلِ اتصالات\n"
                  "    from . import conn as _conn\n"
                  "except Exception:                             # noqa: BLE001\n"
                  "    _conn = None")
    if old_import not in src:
        raise SystemExit("ایمپورتِ hooks در handlers/__init__ پیدا نشد")
    src = src.replace(old_import, new_import, 1)

    old_inc = ("    if _hooks is not None:                # 📡 /hooks\n"
               "        root.include_router(_hooks.router)")
    new_inc = (old_inc + "\n"
               "    if _conn is not None:                 # CONNECT-V1 — 🔌 اتصالات\n"
               "        root.include_router(_conn.router)")
    if old_inc not in src:
        raise SystemExit("include_router هوکس پیدا نشد")
    src = src.replace(old_inc, new_inc, 1)
    INIT.write_text(src, encoding="utf-8")
    done.append("روتر")
else:
    print("  • روترِ اتصالات از قبل هست")

# ---------------------------------------------------------------- ۲) دکمهٔ اتصالات در پنلِ درگاه
src = KBD.read_text(encoding="utf-8")
if "CONNECT-V1" not in src:
    old = ('    return InlineKeyboardMarkup(inline_keyboard=[\n'
           '        [glass("دریافت API و لینک درگاه اختصاصی من",\n'
           '               callback_data=f"gw:show:{store_id}", style="success", emoji="🔑")],\n'
           '        [glass("آموزش و مستندات", url=docs_url, style="primary", emoji="📘")],\n'
           '    ])')
    new = ('    return InlineKeyboardMarkup(inline_keyboard=[\n'
           '        [glass("دریافت API و لینک درگاه اختصاصی من",\n'
           '               callback_data=f"gw:show:{store_id}", style="success", emoji="🔑")],\n'
           '        # CONNECT-V1 — مقصدهای وبهوک: هر رباتی فاکتور خودش را خبر می‌گیرد.\n'
           '        [glass("اتصالات و وبهوک‌ها", callback_data=f"cn:p:{store_id}",\n'
           '               style="primary", emoji="🔌")],\n'
           '        [glass("آموزش و مستندات", url=docs_url, style="primary", emoji="📘")],\n'
           '    ])')
    if old not in src:
        raise SystemExit("کیبوردِ gateway_kb پیدا نشد")
    src = src.replace(old, new, 1)

    old_kb = '[glass("نمایش / ساخت کلید API", callback_data=f"gw:key:{store_id}",'
    new_kb = '[glass("ساخت کلید API تازه", callback_data=f"gw:key:{store_id}",'
    if old_kb in src:
        src = src.replace(old_kb, new_kb, 1)
    KBD.write_text(src, encoding="utf-8")
    done.append("دکمه")
else:
    print("  • دکمهٔ اتصالات از قبل هست")

# ---------------------------------------------------------------- ۳) کلیدِ زنده با یک ضربه نمی‌سوزد
src = LATE.read_text(encoding="utf-8")
if "KEY-CONFIRM-V1" not in src:
    old_imp = "from aiogram.types import CallbackQuery, InlineKeyboardButton, Message"
    new_imp = "from aiogram.types import (CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,\n                            Message)"
    if old_imp not in src:
        raise SystemExit("ایمپورتِ aiogram.types در late پیدا نشد")
    src = src.replace(old_imp, new_imp, 1)

    old = ('@router.callback_query(F.data.startswith("gw:key:"))\n'
           'async def gateway_key(callback: CallbackQuery) -> None:\n'
           '    """Deliberately a *new* key: the old one dies, so nothing is left with two keys."""\n'
           '    store_id = (callback.data or "").split(":")[2]')
    new = ('@router.callback_query(F.data.startswith("gw:key:"))\n'
           'async def gateway_key_confirm(call: CallbackQuery) -> None:\n'
           '    # KEY-CONFIRM-V1 — کلیدِ زنده با یک ضربهٔ اشتباه باطل نمی‌شود.\n'
           '    store_id = (call.data or "").split(":")[2]\n'
           '    await ui.render(\n'
           '        call,\n'
           '        "🔑 <b>کلید تازه</b>\\n\\n"\n'
           '        "کلیدِ فعلی همین لحظه باطل می‌شود و رباتی که با آن کار می‌کند از کار می‌افتد.\\n"\n'
           '        "اگر مطمئنی، تأیید کن.",\n'
           '        InlineKeyboardMarkup(inline_keyboard=[\n'
           '            [kb.glass("بله، کلید تازه بساز", callback_data=f"gw:key2:{store_id}",\n'
           '                      style="danger", emoji="🔑")],\n'
           '            [kb.glass("انصراف", callback_data=f"gw:show:{store_id}",\n'
           '                      style="primary", emoji="↩")],\n'
           '        ]),\n'
           '    )\n'
           '\n'
           '\n'
           '@router.callback_query(F.data.startswith("gw:key2:"))\n'
           'async def gateway_key(callback: CallbackQuery) -> None:\n'
           '    """کلیدِ تازه، بعد از تأیید؛ کلیدِ قبلی همان لحظه باطل می‌شود."""\n'
           '    store_id = (callback.data or "").split(":")[2]')
    if old not in src:
        raise SystemExit("هندلرِ gw:key پیدا نشد")
    src = src.replace(old, new, 1)
    LATE.write_text(src, encoding="utf-8")
    done.append("تأییدِ کلید")
else:
    print("  • تأییدِ کلید از قبل هست")

print("  ✔ ربات — %s" % (" · ".join(done) if done else "چیزی لازم نبود"))
compile_all()
