"""fix7 — یک دامنه، یک مقصد: آدرسِ خبر بدونِ query جدا می‌شود.

سرورِ فروشنده آدرسِ بازگشت را با `?order_id=...` می‌فرستد، پس هر فاکتور یک آدرسِ
تازه به‌نظر می‌رسید و سقفِ سه مقصد با سه فاکتور پر می‌شد. اینجا آدرس تا حدِ
scheme://host/path بریده می‌شود تا یک دامنه یک مقصد باشد.
"""
import pathlib
import subprocess
import sys
import tarfile
import time

APP = pathlib.Path(sys.argv[1])
PY = sys.argv[2] if len(sys.argv) > 2 else sys.executable
EXT = "." + "py"
BACK = APP / "backend" / "app"
HOOKS = BACK / "services" / ("webhooks" + EXT)
ROUTER = BACK / "routers" / ("invoices" + EXT)
SCHEMAS = BACK / ("schemas" + EXT)
if not HOOKS.exists():
    raise SystemExit("فایل پیدا نشد: %s" % HOOKS)

BACKUP = APP / ".sp1713-backup" / ("v2-" + time.strftime("%Y%m%d-%H%M%S") + ".tar.gz")
BACKUP.parent.mkdir(parents=True, exist_ok=True)
FILES = [f for f in (HOOKS, ROUTER, SCHEMAS) if f.exists()]
with tarfile.open(BACKUP, "w:gz") as tar:
    for f in FILES:
        tar.add(f, arcname=str(f.relative_to(APP)))
print("بکاپ: %s" % BACKUP)


def compile_all() -> None:
    for f in FILES:
        r = subprocess.run([PY, "-m", "py_compile", str(f)], capture_output=True, text=True)
        if r.returncode != 0:
            print("سینتکس خراب شد — برگشت")
            print(r.stderr.strip()[:400])
            with tarfile.open(BACKUP) as tar:
                tar.extractall(APP)
            raise SystemExit(1)
    print("کامپایل شد.")


BASE_FN = '''def _base_url(url: str) -> str:
    """MULTI-HOOK-V2 — آدرسِ مقصد بدونِ query؛ یک دامنه = یک مقصد.

    ``?order_id=...`` شناسهٔ همان فاکتور است، نه بخشی از آدرسِ وبهوک. با بریدنِ
    query، فاکتورهای بعدی هم به همان مقصد می‌روند، نه به آدرسِ یک فاکتورِ خاص.
    """
    url = (url or "").strip()
    if not url:
        return ""
    head, sep, _tail = url.partition("?")
    head = head.partition("#")[0]
    return head or url


'''

src = HOOKS.read_text(encoding="utf-8")

if "MULTI-HOOK-V2" in src:
    print("  • webhooks — دامنه‌ها از قبل یکی شده‌اند")
else:
    # ۱) تابعِ کمکی
    if "def _base_url" not in src:
        anchor = "async def _invoice_callback"
        if anchor not in src:
            raise SystemExit("_invoice_callback پیدا نشد")
        src = src.replace(anchor, BASE_FN + anchor, 1)

    # ۲) آدرسِ فاکتور → آدرسِ مقصد
    old = '''    if url:
        return str(url)'''
    new = '''    if url:
        return _base_url(str(url))          # MULTI-HOOK-V2'''
    if old not in src:
        raise SystemExit("بازگشتِ _invoice_callback پیدا نشد")
    src = src.replace(old, new, 1)

    old2 = '''        return str((await session.execute(
            text('select coalesce(callback_url, \\'\\') from "invoices" where id = :i'),
            {"i": invoice.id},
        )).scalar() or "")'''
    new2 = '''        return _base_url(str((await session.execute(
            text('select coalesce(callback_url, \\'\\') from "invoices" where id = :i'),
            {"i": invoice.id},
        )).scalar() or ""))'''
    if old2 in src:
        src = src.replace(old2, new2, 1)

    # ۳) فهرستِ دامنه‌های فروشگاه: بی‌تکرار و بی‌ترتیبِ زمانی
    old3 = '''        rows = (await session.execute(text(
            'select callback_url, max(created_at) as last from "invoices" '
            "where store_id = :s and coalesce(callback_url, '') <> '' "
            "group by callback_url order by last desc limit :n"
        ), {"s": store_id, "n": limit})).all()'''
    new3 = '''        rows = (await session.execute(text(
            'select callback_url, max(created_at) as last from "invoices" '
            "where store_id = :s and coalesce(callback_url, '') <> '' "
            "group by callback_url order by last desc limit 60"
        ), {"s": store_id})).all()'''
    if old3 in src:
        src = src.replace(old3, new3, 1)

    old4 = '''    return [str(r[0]) for r in rows if r[0]]'''
    new4 = '''    seen, out = set(), []
    for r in rows:                          # MULTI-HOOK-V2 — یک دامنه، یک بار
        base = _base_url(str(r[0] or ""))
        if not base or base in seen:
            continue
        seen.add(base)
        out.append(base)
        if len(out) >= limit:
            break
    return out'''
    if old4 not in src:
        raise SystemExit("بازگشتِ _store_callbacks پیدا نشد")
    src = src.replace(old4, new4, 1)

    HOOKS.write_text(src, encoding="utf-8")
    print("  ✔ webhooks — هر دامنه یک مقصد (query حذف شد)")

# ---------------------------------------------------------------- نامِ دیگرِ فیلد
if SCHEMAS.exists():
    src2 = SCHEMAS.read_text(encoding="utf-8")
    if "webhook_url: str | None" in src2 and "MULTI-HOOK-V2" in src2:
        print("  • schemas — از قبل درست است")
    else:
        done = False
        if "webhook_url: str | None = Field" not in src2:
            anchor = "class InvoiceCreate(BaseModel):"
            if anchor in src2:
                src2 = src2.replace(
                    anchor,
                    anchor + "\n"
                    "    # MULTI-HOOK-V2 — همان آدرس با نامِ دیگر؛ بعضی ربات‌ها این را می‌فرستند.\n"
                    "    webhook_url: str | None = Field(default=None, max_length=400)",
                    1)
                done = True
        if "model_validator" not in src2:
            anchor2 = "    @field_validator(\"callback_url\")"
            alias = ('    @model_validator(mode="after")          # MULTI-HOOK-V2\n'
                     "    def _hook_url_alias(self):\n"
                     "        if not self.callback_url and self.webhook_url:\n"
                     '            object.__setattr__(self, "callback_url", self.webhook_url)\n'
                     "        return self\n\n")
            if anchor2 in src2:
                src2 = src2.replace(anchor2, alias + anchor2, 1)
                done = True
        if "model_validator" in src2:
            line = [l for l in src2.split("\n") if l.startswith("from pydantic import")]
            if line and "model_validator" not in line[0]:
                src2 = src2.replace(line[0], line[0].replace("import ", "import model_validator, ", 1), 1)
        if done:
            SCHEMAS.write_text(src2, encoding="utf-8")
            print("  ✔ schemas — webhook_url پذیرفته می‌شود")

# ---------------------------------------------------------------- روتر: از payload هم بخوان
if ROUTER.exists():
    src3 = ROUTER.read_text(encoding="utf-8")
    if "MULTI-HOOK-V2" in src3:
        print("  • روتر — از قبل درست است")
    else:
        old = "        _auto = _auto_hook_url(request)"
        new = ('        _auto = (getattr(payload, "webhook_url", None)      # MULTI-HOOK-V2\n'
               "                 or _auto_hook_url(request))")
        if old in src3:
            src3 = src3.replace(old, new, 1)
            ROUTER.write_text(src3, encoding="utf-8")
            print("  ✔ روتر — webhook_url در بدنه هم خوانده می‌شود")
        else:
            print("  • بلوکِ آدرسِ خودکار در روتر پیدا نشد — رد شد")

compile_all()
