import pathlib, re, subprocess, sys, tarfile, time

APP = pathlib.Path(sys.argv[1])
PY = sys.argv[2] if len(sys.argv) > 2 else sys.executable
EXT = "." + "py"
HOOKS = APP / "backend" / "app" / "services" / ("webhooks" + EXT)
INV_OPEN = APP / "backend" / "app" / "services" / ("invoices_open" + EXT)
if not HOOKS.exists():
    raise SystemExit("فایل پیدا نشد: %s" % HOOKS)

BACKUP = APP / ".sp1713-backup" / ("before-" + time.strftime("%Y%m%d-%H%M%S") + ".tar.gz")
BACKUP.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(BACKUP, "w:gz") as tar:
    for f in (HOOKS, INV_OPEN):
        if f.exists():
            tar.add(f, arcname=str(f.relative_to(APP)))
print("بکاپ: %s" % BACKUP)


def compile_all() -> None:
    for f in (HOOKS, INV_OPEN):
        if not f.exists():
            continue
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
    """مقصدهای فعالِ همین فروشگاه: (id، آدرس، secret)."""
    from sqlalchemy import text

    try:
        rows = (await session.execute(text(
            'select id, url, coalesce(secret, \\'\\') from "webhook_endpoints" '
            "where store_id = :s and coalesce(enabled, 1) = 1 order by rowid"
        ), {"s": store_id})).all()
    except Exception:                                       # noqa: BLE001
        return []
    return [(str(r[0]), str(r[1]), str(r[2] or "")) for r in rows if r[1]]


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

    اول مقصدی که خودِ فاکتور را ساخته، بعد بقیهٔ مقصدهای همین فروشگاه (تا سه)،
    و در آخر ``store.webhook_url`` اگر با هیچ‌کدام یکی نبود. قبلا رویدادِ «پرداخت
    شد» فقط به ``webhook_url`` می‌رفت، پس رباتی که فاکتور را از دامنهٔ خودش ساخته
    بود هیچ‌وقت خبر نمی‌گرفت.
    """
    bound = await _bound_endpoint(session, invoice)
    out = []
    seen = set()
    endpoints = await _endpoint_rows(session, store.id)
    endpoints.sort(key=lambda row: 0 if (bound and row[0] == str(bound)) else 1)
    for eid, url, _secret in endpoints[:3]:
        if url in seen:
            continue
        seen.add(url)
        out.append((url, eid))
    store_url = getattr(store, "webhook_url", None)
    if store_url and store_url not in seen:
        out.append((store_url, None))
    return out


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

src = HOOKS.read_text(encoding="utf-8")

if "MULTI-HOOK-V1" in src:
    print("  • webhooks — از قبل درست است")
else:
    lines = src.split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith("async def enqueue")), None)
    if start is None:
        raise SystemExit("تابعِ enqueue پیدا نشد")

    # انتهای امضای تابع: خطی که پرانتزها بسته می‌شود و با «:» تمام می‌شود
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

    # انتهای تابع: اولین خطِ بدونِ تورفتگی بعد از بدنه
    end = len(lines)
    for j in range(sig_end + 1, len(lines)):
        line = lines[j]
        if not line.strip():
            continue
        if line[0] not in (" ", "\t"):
            end = j
            break

    print("  • بدنهٔ enqueue از خط %d تا %d جای‌گذاری می‌شود" % (sig_end + 2, end))
    lines[sig_end + 1:end] = BODY.split("\n")
    src = "\n".join(lines)

    anchor = "async def enqueue"
    src = src.replace(anchor, HELPERS + anchor, 1)
    HOOKS.write_text(src, encoding="utf-8")
    print("  ✔ webhooks — مسیرِ چند مقصدی")

    # ------------------------------------------------------------ امضا در deliver_due
    src = HOOKS.read_text(encoding="utf-8")
    hit = -1
    scan = 0
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
            print("  • الگوی _resolve_endpoint پیدا نشد — مقصد با ساختارِ فعلی می‌ماند")

compile_all()
