"""CONNECT-V1 — اتصالِ ربات‌ها: تا سه مقصدِ وبهوک برای هر فروشگاه.

چرا این فایل: رباتی که فاکتور می‌سازد باید همان‌جا خبرِ «پرداخت شد» را بگیرد.
مدلِ قدیمی یک ``webhook_url`` داشت، پس با چند ربات هیچ‌کس نمی‌فهمید کدام یکی
صاحبِ فاکتور بوده. حالا هر فروشگاه تا سه مقصد دارد، هر مقصد secretِ خودش را
دارد، و رویدادِ هر فاکتور اول به مقصدی می‌رود که همان فاکتور را ساخته است.

جدولِ ``webhook_endpoints`` همان جدولی است که ``/api/v1/hooks/self`` استفاده
می‌کند؛ پس پنلِ ربات و API یک چیز را می‌بینند.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import select, text

from app.db import SessionLocal
from app.models import WebhookDelivery

MAX_ENDPOINTS = 3

DDL = (
    'create table if not exists webhook_endpoints ('
    ' id varchar(48) primary key,'
    ' store_id varchar(48),'
    ' api_key_id varchar(48),'
    ' url varchar(400),'
    ' label varchar(64),'
    ' secret varchar(160),'
    ' enabled boolean default 1,'
    ' created_at datetime)'
)


async def _ensure(session) -> None:
    await session.execute(text(DDL))


def _clean(url: str) -> str:
    url = (url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("آدرس باید با http:// یا https:// شروع شود")
    if len(url) > 400:
        raise ValueError("آدرس بلندتر از ۴۰۰ کاراکتر است")
    return url


async def list_endpoints(store_id: str) -> list[dict]:
    """مقصدهای همین فروشگاه، به‌ترتیبِ ساخت."""
    async with SessionLocal() as s:
        await _ensure(s)
        await s.commit()
        rows = (await s.execute(text(
            'select id, url, coalesce(label, \'\'), coalesce(secret, \'\'), '
            'coalesce(enabled, 1) from "webhook_endpoints" where store_id = :s order by rowid'
        ), {"s": store_id})).all()
    return [
        {"id": str(r[0]), "url": str(r[1]), "label": str(r[2] or ""),
         "secret": str(r[3] or ""), "enabled": bool(r[4])}
        for r in rows
    ]


async def add_endpoint(store_id: str, url: str, label: str = "") -> tuple[bool, str]:
    """یک مقصد تازه. سقف سه‌تاست؛ آدرسِ تکراری مقصدِ تازه نمی‌سازد."""
    try:
        url = _clean(url)
    except ValueError as exc:
        return False, str(exc)
    async with SessionLocal() as s:
        await _ensure(s)
        await s.commit()
        rows = (await s.execute(text(
            'select id, url from "webhook_endpoints" where store_id = :s order by rowid'
        ), {"s": store_id})).all()
        if len(rows) >= MAX_ENDPOINTS:
            return False, f"سقفِ سه مقصد پر است؛ اول یکی را حذف کن"
        if any(str(r[1]) == url for r in rows):
            return False, "این آدرس از قبل ثبت شده است"
        eid = "ep_" + secrets.token_hex(8)
        secret = "whsec_" + secrets.token_hex(24)
        await s.execute(text(
            'insert into "webhook_endpoints" (id, store_id, api_key_id, url, label, secret, '
            "enabled, created_at) values (:i, :s, null, :u, :l, :sec, 1, :c)"),
            {"i": eid, "s": store_id, "u": url, "l": (label or "")[:64], "sec": secret,
             "c": datetime.now(timezone.utc)})
        await s.commit()
    return True, secret


async def delete_endpoint(store_id: str, endpoint_id: str) -> bool:
    async with SessionLocal() as s:
        await _ensure(s)
        await s.commit()
        r = await s.execute(text(
            'delete from "webhook_endpoints" where id = :i and store_id = :s'),
            {"i": endpoint_id, "s": store_id})
        await s.commit()
        return bool(r.rowcount)


async def rotate_secret(store_id: str, endpoint_id: str) -> str:
    secret = "whsec_" + secrets.token_hex(24)
    async with SessionLocal() as s:
        await _ensure(s)
        await s.commit()
        await s.execute(text(
            'update "webhook_endpoints" set secret = :sec where id = :i and store_id = :s'),
            {"sec": secret, "i": endpoint_id, "s": store_id})
        await s.commit()
    return secret


async def recent_deliveries(store_id: str, limit: int = 6) -> list[dict]:
    async with SessionLocal() as s:
        rows = (await s.execute(
            select(WebhookDelivery).where(WebhookDelivery.store_id == store_id)
            .order_by(WebhookDelivery.created_at.desc()).limit(limit)
        )).scalars().all()
        return [
            {"event": r.event, "status": r.status, "attempts": int(r.attempts or 0),
             "code": r.response_status, "error": (r.last_error or "")[:120],
             "url": r.url}
            for r in rows
        ]


async def send_test(endpoint_id: str) -> tuple[bool, str]:
    """یک ``hook.test`` واقعی به همان مقصد؛ نتیجه را همین‌جا نشان می‌دهیم."""
    import json

    import aiohttp

    async with SessionLocal() as s:
        await _ensure(s)
        await s.commit()
        row = (await s.execute(text(
            'select url, coalesce(secret, \'\') from "webhook_endpoints" where id = :i'),
            {"i": endpoint_id})).first()
    if row is None:
        return False, "مقصد پیدا نشد"
    url, secret = str(row[0]), str(row[1] or "")
    body = json.dumps({
        "event": "hook.test",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": {"message": "آزمایشِ اتصال از پنل SIBILPAY"},
    }, ensure_ascii=False).encode()
    headers = {"Content-Type": "application/json", "X-SIBILPAY-Event": "hook.test"}
    if secret:
        import hashlib
        import hmac

        headers["X-SIBILPAY-Signature"] = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
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


async def endpoint_store_id(endpoint_id: str) -> str:
    """فروشگاهِ صاحبِ این مقصد؛ برای دکمه‌هایی که فقط شناسهٔ مقصد را دارند."""
    async with SessionLocal() as s:
        await _ensure(s)
        await s.commit()
        row = (await s.execute(text(
            'select store_id from "webhook_endpoints" where id = :i'), {"i": endpoint_id})).first()
    return str(row[0]) if row else ""
