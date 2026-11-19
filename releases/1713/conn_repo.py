"""CONNECT-V1 — اتصالِ خودکارِ ربات‌ها: هر دامنه، خبرِ فاکتورِ خودش.

قاعدهٔ کار: هیچ ثبتِ دستی‌ای لازم نیست. هر فاکتور آدرسِ خودش را با خودش می‌آورد
(``callback_url`` یا هدرِ Origin در همان درخواستِ ساختِ فاکتور) و خبرِ «پرداخت شد»
دقیقا به همان دامنه برمی‌گردد. این فایل فقط چیزی را که هست نشان می‌دهد: از کدام
دامنه‌ها فاکتور آمده، آخرین ارسال‌ها چه شدند، و یک آزمایشِ واقعی.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

from sqlalchemy import text

from app.db import SessionLocal
from app.models import WebhookDelivery

MAX_ENDPOINTS = 3


def _base_url(url: str) -> str:
    """آدرسِ مقصد بدونِ query — یک دامنه، یک مقصد."""
    url = (url or "").strip()
    if not url:
        return ""
    head = url.partition("?")[0].partition("#")[0]
    return head or url


async def auto_destinations(store_id: str, limit: int = MAX_ENDPOINTS) -> list[dict]:
    """دامنه‌هایی که از همین فروشگاه فاکتور ساخته‌اند، به‌ترتیبِ تازگی.

    آدرس‌ها بدونِ query شمرده می‌شوند: `...return.php?order_id=A` و `...?order_id=B`
    یک مقصد هستند، نه دو.
    """
    async with SessionLocal() as s:
        try:
            rows = (await s.execute(text(
                'select callback_url, created_at from "invoices" '
                "where store_id = :s and coalesce(callback_url, '') <> '' "
                "order by created_at desc limit 300"
            ), {"s": store_id})).all()
        except Exception:                               # noqa: BLE001
            return []
    seen: dict[str, dict] = {}
    order: list[str] = []
    for url, created in rows:
        base = _base_url(str(url or ""))
        if not base:
            continue
        if base not in seen:
            seen[base] = {"url": base, "count": 0, "last": str(created or "")}
            order.append(base)
        seen[base]["count"] += 1
    return [seen[u] for u in order[:limit]]


async def recent_deliveries(store_id: str, limit: int = 6) -> list[dict]:
    async with SessionLocal() as s:
        rows = (await s.execute(
            WebhookDelivery.__table__.select()
            .where(WebhookDelivery.store_id == store_id)
            .order_by(WebhookDelivery.created_at.desc()).limit(limit)
        )).all()
    return [
        {"event": r.event, "status": r.status, "attempts": int(r.attempts or 0),
         "code": r.response_status, "error": (r.last_error or "")[:120], "url": r.url}
        for r in rows
    ]


async def last_result(url: str) -> dict | None:
    """آخرین تلاشِ ارسال به این آدرس: کدِ HTTP و وضعیت."""
    async with SessionLocal() as s:
        rows = (await s.execute(
            WebhookDelivery.__table__.select()
            .where(WebhookDelivery.url == url)
            .order_by(WebhookDelivery.created_at.desc()).limit(1)
        )).all()
    if not rows:
        return None
    r = rows[0]
    return {"status": r.status, "code": r.response_status,
            "error": (r.last_error or "")[:120], "event": r.event}


async def send_test(url: str, store_id: str = "") -> tuple[bool, str]:
    """یک ``hook.test`` واقعی به همان آدرس؛ نتیجه را همین‌جا برمی‌گردانیم."""
    import aiohttp

    body = json.dumps({
        "event": "hook.test",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": {"message": "آزمایشِ اتصال از پنل SIBILPAY", "store_id": store_id},
    }, ensure_ascii=False).encode()
    headers = {"Content-Type": "application/json", "X-SIBILPAY-Event": "hook.test"}
    secret = ""
    async with SessionLocal() as s:
        try:
            secret = str((await s.execute(text(
                "select coalesce(webhook_secret, '') from stores where id = :i"
            ), {"i": store_id})).scalar() or "")
        except Exception:                               # noqa: BLE001
            secret = ""
    if secret:
        headers["X-Signature"] = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Sibipay-Signature"] = headers["X-Signature"]
    try:
        async with aiohttp.ClientSession() as client:
            async with client.post(url, data=body, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=12)) as resp:
                code = resp.status
                text_body = (await resp.text())[:120]
    except Exception as exc:                            # noqa: BLE001
        return False, f"خطای شبکه: {type(exc).__name__}"
    if 200 <= code < 300:
        return True, f"{code} — مقصد جواب داد"
    return False, f"{code} — {text_body}"
