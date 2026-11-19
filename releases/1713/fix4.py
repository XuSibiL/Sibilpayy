import pathlib, subprocess, sys, tarfile, time

APP = pathlib.Path(sys.argv[1])
PY = sys.argv[2] if len(sys.argv) > 2 else sys.executable
EXT = "." + "py"
BACK = APP / "backend" / "app"
HOOKS = BACK / "services" / ("webhooks" + EXT)
INV_OPEN = BACK / "services" / ("invoices_open" + EXT)
ROUTER = BACK / "routers" / ("invoices" + EXT)
SCHEMAS = BACK / ("schemas" + EXT)
if not HOOKS.exists():
    raise SystemExit("فایل پیدا نشد: %s" % HOOKS)

BACKUP = APP / ".sp1713-backup" / ("before-" + time.strftime("%Y%m%d-%H%M%S") + ".tar.gz")
BACKUP.parent.mkdir(parents=True, exist_ok=True)
FILES = [f for f in (HOOKS, INV_OPEN, ROUTER, SCHEMAS) if f.exists()]
with tarfile.open(BACKUP, "w:gz") as tar:
    for f in FILES:
        tar.add(f, arcname=str(f.relative_to(APP)))
print("بکاپ: %s" % BACKUP)


def compile_all() -> None:
    for f in FILES:
        r = subprocess.run([PY, "-m", "py_compile", str(f)], capture_output=True, text=True)
        if r.returncode != 0:
            print("سینتکس خراب شد — برگشت")
            print(r.stderr.strip()[:500])
            with tarfile.open(BACKUP) as tar:
                tar.extractall(APP)
            raise SystemExit(1)
    print("کامپایل شد.")


HELPERS = '''# ---------------------------------------------------------------- MULTI-HOOK-V1
async def _endpoint_rows(session, store_id: str) -> list:
    """مقصدهایی که در جدولِ اتصالاتِ همین فروشگاه ثبت شده‌اند: (id، آدرس، secret)."""
    from sqlalchemy import text

    try:
        rows = (await session.execute(text(
            'select id, url, coalesce(secret, \\'\\') from "webhook_endpoints" '
            "where store_id = :s and coalesce(enabled, 1) = 1 order by rowid"
        ), {"s": store_id})).all()
    except Exception:                                       # noqa: BLE001
        return []
    return [(str(r[0]), str(r[1]), str(r[2] or "")) for r in rows if r[1]]


async def _invoice_callback(session, invoice) -> str:
    """آدرسی که خودِ این فاکتور با خودش آورده است (``callback_url``)."""
    if invoice is None:
        return ""
    url = getattr(invoice, "callback_url", None)
    if url:
        return str(url)
    from sqlalchemy import text

    try:
        return str((await session.execute(
            text('select coalesce(callback_url, \\'\\') from "invoices" where id = :i'),
            {"i": invoice.id},
        )).scalar() or "")
    except Exception:                                       # noqa: BLE001
        return ""


async def _store_callbacks(session, store_id: str, limit: int = 3) -> list:
    """دامنه‌هایی که تا حالا از همین فروشگاه فاکتور ساخته‌اند.

    ثبتِ دستی لازم نیست: هر فاکتور آدرسِ خودش را با خودش می‌آورد، اینجا آن
    آدرس‌ها به‌ترتیبِ تازگی نگه داشته می‌شوند تا فاکتورهای بعدی هم خبر بگیرند.
    """
    from sqlalchemy import text

    try:
        rows = (await session.execute(text(
            'select callback_url, max(created_at) as last from "invoices" '
            "where store_id = :s and coalesce(callback_url, '') <> '' "
            "group by callback_url order by last desc limit :n"
        ), {"s": store_id, "n": limit})).all()
    except Exception:                                       # noqa: BLE001
        return []
    return [str(r[0]) for r in rows if r[0]]


async def _bound_endpoint(session, invoice):
    """مقصدی که همین فاکتور به آن بسته شده (اگر ثبت شده باشد)."""
    from sqlalchemy import text

    if invoice is None:
        return None
    try:
        return (await session.execute(
            text('select webhook_endpoint_id from "invoices" where id = :i'),
            {"i": invoice.id},
        )).scalar()
    except Exception:                                       # noqa: BLE001
        return None


async def _delivery_endpoint(session, delivery_id: str):
    from sqlalchemy import text

    try:
        return (await session.execute(
            text('select endpoint_id from "webhook_deliveries" where id = :i'),
            {"i": delivery_id},
        )).scalar()
    except Exception:                                       # noqa: BLE001
        return None


async def _endpoint_secret(session, endpoint_id) -> str:
    from sqlalchemy import text

    if not endpoint_id:
        return ""
    try:
        return str((await session.execute(
            text('select coalesce(secret, \\'\\') from "webhook_endpoints" where id = :e'),
            {"e": endpoint_id},
        )).scalar() or "")
    except Exception:                                       # noqa: BLE001
        return ""


async def recipients(session, store, invoice=None) -> list:
    """آدرس‌هایی که این رویداد باید به آن‌ها برود، به‌ترتیبِ اولویت.

    اول آدرسی که همین فاکتور با خودش آورده، بعد دامنه‌های قبلیِ همین فروشگاه
    (حداکثر سه)، بعد مقصدهای ثبت‌شده و در آخر ``store.webhook_url``. قبلا رویدادِ
    «پرداخت شد» فقط به ``webhook_url`` می‌رفت، پس رباتی که فاکتور را از دامنهٔ
    خودش ساخته بود هیچ‌وقت خبر نمی‌گرفت.
    """
    bound = await _bound_endpoint(session, invoice)
    out, seen = [], set()

    def add(url, endpoint_id=None):
        url = (url or "").strip()
        if not url or url in seen:
            return
        seen.add(url)
        out.append((url, endpoint_id))

    callbacks = []
    own = await _invoice_callback(session, invoice)
    if own:
        callbacks.append(own)
    for url in await _store_callbacks(session, getattr(store, "id", ""), limit=3):
        if url not in callbacks:
            callbacks.append(url)
    for url in callbacks[:3]:
        add(url)

    endpoints = await _endpoint_rows(session, store.id)
    endpoints.sort(key=lambda row: 0 if (bound and row[0] == str(bound)) else 1)
    for eid, url, _secret in endpoints:
        add(url, eid)

    add(getattr(store, "webhook_url", None))
    return out[:3]                      # سقفِ سه مقصد، همان قاعدهٔ فروشنده


async def _ensure_delivery_endpoint_col(session) -> bool:
    """ستونِ ``endpoint_id`` روی صفِ تحویل، اگر نبود ساخته می‌شود (additive)."""
    from sqlalchemy import text

    try:
        cols = [row[1] for row in (await session.execute(
            text('pragma table_info("webhook_deliveries")'))).all()]
        if cols and "endpoint_id" not in cols:
            await session.execute(text(
                'alter table "webhook_deliveries" add column endpoint_id varchar(48)'))
            await session.commit()
        return cols == [] or "endpoint_id" in cols
    except Exception:                                       # noqa: BLE001
        return False


'''

BODY = '''    """MULTI-HOOK-V1 — یک ردیفِ تحویل برای هر مقصدِ فعالِ همین فروشگاه."""
    payload: dict = {
        "event": event,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "livemode": not store.test_mode,
    }
    if invoice is not None:
        payload["data"] = invoice_payload(store, invoice)
    if extra:
        payload.update(extra)

    targets = await recipients(session, store, invoice)
    if not targets:
        return None
    have_col = await _ensure_delivery_endpoint_col(session)
    first = None
    for url, endpoint_id in targets:
        delivery = WebhookDelivery(
            store_id=store.id,
            event=event,
            invoice_id=invoice.id if invoice else None,
            url=url,
            payload=payload,
            next_attempt_at=datetime.now(timezone.utc),
        )
        session.add(delivery)
        await session.flush()
        if endpoint_id and have_col:
            try:
                from sqlalchemy import text as _text

                await session.execute(
                    _text('update "webhook_deliveries" set endpoint_id = :e where id = :i'),
                    {"e": endpoint_id, "i": delivery.id},
                )
            except Exception:                           # noqa: BLE001
                log.debug("ثبتِ مقصد روی تحویل رد شد", exc_info=True)
        if first is None:
            first = delivery
    try:
        asyncio.get_running_loop().create_task(_nudge_soon())
    except Exception:                               # noqa: BLE001
        log.debug("webhook nudge not scheduled", exc_info=True)
    return first
'''

AUTO_HOOK = '''def _auto_hook_url(request) -> str | None:
    """آدرسِ وبهوک از دلِ همان درخواستِ ساختِ فاکتور، بدون ثبتِ دستی.

    ترتیب: هدرِ صریح (x-webhook-url / x-callback-url / webhook-url)، بعد
    Origin یا Referer به‌همراهِ x-webhook-path. اگر هیچ‌کدام نبود، آدرس خالی
    می‌ماند و بقیهٔ مقصدهای فروشگاه کار خودشان را می‌کنند.
    """
    if request is None:
        return None
    try:
        headers = request.headers
        for name in ("x-webhook-url", "x-callback-url", "webhook-url"):
            value = (headers.get(name) or "").strip()
            if value.startswith(("http://", "https://")):
                return value[:400]
        origin = (headers.get("origin") or "").strip()
        if not origin:
            referer = (headers.get("referer") or "").strip()
            if referer.startswith(("http://", "https://")):
                origin = "/".join(referer.split("/")[:3])
        if origin.startswith(("http://", "https://")):
            path = (headers.get("x-webhook-path") or "").strip()
            if path and not path.startswith("/"):
                path = "/" + path
            return (origin.rstrip("/") + (path or "/"))[:400]
    except Exception:                                       # noqa: BLE001
        return None
    return None


'''

src = HOOKS.read_text(encoding="utf-8")

if "MULTI-HOOK-V1" in src:
    print("  • webhooks — از قبل درست است")
else:
    lines = src.split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith("async def enqueue")), None)
    if start is None:
        raise SystemExit("تابعِ enqueue پیدا نشد")

    depth, sig_end = 0, None
    for i in range(start, min(start + 40, len(lines))):
        line = lines[i]
        depth += line.count("(") + line.count("[") + line.count("{")
        depth -= line.count(")") + line.count("]") + line.count("}")
        if depth <= 0 and line.rstrip().endswith(":"):
            sig_end = i
            break
    if sig_end is None:
        raise SystemExit("امضای enqueue خوانده نشد")

    end = len(lines)
    for j in range(sig_end + 1, len(lines)):
        line = lines[j]
        if not line.strip():
            continue
        if line[0] not in (" ", "\t"):
            end = j
            break

    lines[sig_end + 1:end] = BODY.split("\n")
    src = "\n".join(lines)
    src = src.replace("async def enqueue", HELPERS + "async def enqueue", 1)
    HOOKS.write_text(src, encoding="utf-8")
    print("  ✔ webhooks — مسیرِ چند مقصدی (بدنهٔ enqueue جای‌گذاری شد)")

    # ------------------------------------------------------------ امضا در deliver_due
    src = HOOKS.read_text(encoding="utf-8")
    hit, scan = -1, 0
    dd = src.find("async def deliver_due")
    while dd != -1:
        cand = src.find("signature_modes(", max(scan, dd))
        if cand == -1:
            break
        line_start = src.rfind("\n", 0, cand) + 1
        if "def " in src[line_start:cand]:
            scan = cand + 16
            continue
        hit = cand
        break
    if hit == -1:
        print("  • signature_modes پیدا نشد — امضا با کلیدِ فروشگاه می‌ماند")
    else:
        open_at = src.index("(", hit)
        depth, close_at = 0, None
        for k in range(open_at, len(src)):
            ch = src[k]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    close_at = k
                    break
        if close_at is None:
            raise SystemExit("پرانتزِ signature_modes خوانده نشد")
        inner = src[open_at + 1:close_at]
        parts, depth, cur = [], 0, ""
        for ch in inner:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append(cur)
                cur = ""
            else:
                cur += ch
        parts.append(cur)
        parts = [" ".join(p.split()) for p in parts if p.strip()]
        if len(parts) < 2:
            raise SystemExit("آرگومان‌های signature_modes خوانده نشد")
        secret_expr = ("(await _endpoint_secret(session, "
                       "await _delivery_endpoint(session, delivery.id))) "
                       "or (store.webhook_secret if store else \"unknown\")")
        new_inner = "%s, %s, %s" % (parts[0], parts[1], secret_expr)
        src = src[:open_at] + "(" + new_inner + src[close_at:]
        HOOKS.write_text(src, encoding="utf-8")
        print("  ✔ امضا — کلیدِ هر مقصد")

# ---------------------------------------------------------------- مقصد: هر دو ستون
if INV_OPEN.exists():
    src2 = INV_OPEN.read_text(encoding="utf-8")
    if "HOOK-OWNER-V1" in src2:
        print("  • invoices_open — از قبل درست است")
    else:
        old = ('    sql = f\'select * from "{schema["table"]}" where "{schema["owner"]}" = :owner\'\n'
               "    rows = []\n"
               "    for owner in dict.fromkeys([o for o in owners if o]):\n"
               '        rows.extend((await session.execute(text(sql), {"owner": owner})).all())')
        new = ("    # HOOK-OWNER-V1 — مقصد ممکن است با store_id ثبت شده باشد یا api_key_id؛\n"
               "    # قبلا فقط همان ستونی جست‌وجو می‌شد که schema انتخاب کرده بود.\n"
               '    cols = schema.get("cols") or []\n'
               "    rows = []\n"
               '    for column, value in (("store_id", store.id), ("api_key_id", key_id)):\n'
               "        if column not in cols or not value:\n"
               "            continue\n"
               "        try:\n"
               "            rows.extend((await session.execute(\n"
               '                text(f\'select * from "{schema["table"]}" where "{column}" = :v\'),\n'
               '                {"v": value})).all())\n'
               "        except Exception:                               # noqa: BLE001\n"
               "            continue")
        if old in src2:
            src2 = src2.replace(old, new, 1)
            INV_OPEN.write_text(src2, encoding="utf-8")
            print("  ✔ invoices_open — پیدا کردنِ مقصد با هر دو ستون")
        else:
            print("  • الگوی _resolve_endpoint پیدا نشد — ساختارِ فعلی می‌ماند")

# ---------------------------------------------------------------- خودکار: آدرس از درخواست
if ROUTER.exists():
    src3 = ROUTER.read_text(encoding="utf-8")
    if "MULTI-HOOK-V1" in src3:
        print("  • روترِ فاکتور — از قبل درست است")
    else:
        if "from fastapi import" in src3 and "Request" not in src3.split("from fastapi import")[1].split("\n")[0]:
            line = [l for l in src3.split("\n") if l.startswith("from fastapi import")][0]
            src3 = src3.replace(line, line.replace("import ", "import Request, ", 1) + "  # MULTI-HOOK-V1", 1)

        anchor = '@router.post("/invoices", status_code=201)'
        if anchor not in src3:
            raise SystemExit("مسیرِ ساختِ فاکتور پیدا نشد")
        src3 = src3.replace(anchor, AUTO_HOOK + anchor, 1)

        old_sig = ("async def create_invoice(\n"
                   "    payload: InvoiceCreate,\n")
        new_sig = ("async def create_invoice(\n"
                   "    payload: InvoiceCreate,\n"
                   "    request: Request,\n")
        if old_sig not in src3:
            raise SystemExit("امضای create_invoice پیدا نشد")
        src3 = src3.replace(old_sig, new_sig, 1)

        marker = "    # ── idempotency: با یک order_id همیشه همان فاکتور برمی‌گردد"
        if marker not in src3:
            raise SystemExit("بلوکِ idempotency پیدا نشد")
        inject = ("    # MULTI-HOOK-V1 — مقصدِ خبرِ این فاکتور از همان درخواست خوانده\n"
                  "    # می‌شود؛ نه پنلِ ثبتِ دستی، نه آدرسِ ثابتِ فروشگاه.\n"
                  "    try:\n"
                  "        _auto = _auto_hook_url(request)\n"
                  "        if _auto and not payload.callback_url:\n"
                  "            payload.callback_url = _auto\n"
                  "    except Exception:                            # noqa: BLE001\n"
                  "        log.debug(\"auto hook url skipped\", exc_info=True)\n\n")
        src3 = src3.replace(marker, inject + marker, 1)
        ROUTER.write_text(src3, encoding="utf-8")
        print("  ✔ روتر — آدرسِ وبهوک خودکار از درخواست")

# ---------------------------------------------------------------- نامِ دیگر برای همان فیلد
if SCHEMAS.exists():
    src4 = SCHEMAS.read_text(encoding="utf-8")
    if "MULTI-HOOK-V1" in src4:
        print("  • schemas — از قبل درست است")
    else:
        old = "    webhook_endpoint: str | None = Field(default=None, max_length=120)"
        if old in src4:
            new = (old + "\n"
                   "    # MULTI-HOOK-V1 — بعضی ربات‌ها همین آدرس را با نامِ webhook_url می‌فرستند.\n"
                   "    webhook_url: str | None = Field(default=None, max_length=400)")
            src4 = src4.replace(old, new, 1)

            hook = "    @field_validator(\"callback_url\")"
            if hook in src4:
                alias = ("    @model_validator(mode=\"after\")\n"
                         "    def _hook_url_alias(self):\n"
                         "        # MULTI-HOOK-V1 — webhook_url همان callback_url است.\n"
                         "        if not self.callback_url and self.webhook_url:\n"
                         "            object.__setattr__(self, \"callback_url\", self.webhook_url)\n"
                         "        return self\n\n")
                src4 = src4.replace(hook, alias + hook, 1)
            if "model_validator" in src4 and "model_validator" not in src4.split("class InvoiceCreate")[0]:
                imp = "from pydantic import"
                line = [l for l in src4.split("\n") if l.startswith(imp)]
                if line:
                    l0 = line[0]
                    if "model_validator" not in l0:
                        src4 = src4.replace(l0, l0.replace("import ", "import model_validator, ", 1), 1)
            SCHEMAS.write_text(src4, encoding="utf-8")
            print("  ✔ schemas — webhook_url هم پذیرفته می‌شود")
        else:
            print("  • فیلدِ webhook_endpoint در schemas پیدا نشد — رد شد")

compile_all()
