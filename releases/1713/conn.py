"""CONNECT-V1 — پنلِ «🔌 اتصالات»: اتصالِ خودکار، بدون ثبتِ دستی.

هر فاکتوری که از یک دامنه بیاید، خبرِ «پرداخت شد» به همان دامنه برمی‌گردد.
این پنل فقط نشان می‌دهد کدام دامنه‌ها در کارند، آخرین ارسال چه شد، و یک
آزمایشِ واقعی می‌فرستد. هیچ کلیدِ API هم با یک ضربه ساخته یا باطل نمی‌شود.

هیچ دکمه‌ای بی‌جواب نمی‌ماند: هر هندلر داخل try است و در بدترین حالت یک
پیامِ کوتاه نشان می‌دهد.
"""
from __future__ import annotations

import html
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import keyboards as kb
import ui
from services import conn_repo, repo
from services.dates import fa_digits

log = logging.getLogger("sibilpay.conn")
router = Router(name="connections")

MAX = conn_repo.MAX_ENDPOINTS

WORDS = {"اتصالات", "🔌 اتصالات", "اتصالات و وبهوک‌ها", "وبهوک", "وبهوک‌ها", "هوک"}

_ICON = {"delivered": "✅", "failed": "✘", "pending": "⏳"}


def _short(url: str) -> str:
    pretty = url.replace("https://", "").replace("http://", "")
    return pretty if len(pretty) <= 58 else pretty[:55] + "…"


async def _text(store_id: str) -> str:
    destinations = await conn_repo.auto_destinations(store_id)
    lines = ["🔌 <b>اتصالات</b>", ""]
    lines.append("خبرِ هر فاکتور خودکار به همان دامنه‌ای می‌رود که فاکتور را ساخته.")
    lines.append("یک دامنه، یک مقصد؛ سقف سه دامنه.")
    lines.append("")
    if not destinations:
        lines.append("<b>هنوز از هیچ دامنه‌ای خبری نیست.</b>")
        lines.append("اولین فاکتور که ساخته شود، دامنه‌اش همین‌جا می‌آید.")
    else:
        for i, item in enumerate(destinations, 1):
            last = await conn_repo.last_result(item["url"])
            icon = _ICON.get((last or {}).get("status", ""), "•")
            code = (last or {}).get("code")
            tail = f" · {icon} {code}" if code else ""
            lines.append(f"{fa_digits(i)} · <code>{html.escape(_short(item['url']))}</code>")
            lines.append(f"   {fa_digits(item['count'])} فاکتور{tail}")
    lines.append("")
    lines.append(f"سقف: {fa_digits(MAX)} دامنه.")
    return "\n".join(lines)


def _keyboard(store_id: str, destinations: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i, item in enumerate(destinations, 1):
        rows.append([kb.glass(f"🧪 آزمایشِ {fa_digits(i)}",
                             callback_data=f"cn:t:{i}:{store_id}",
                             style="success", emoji="🧪")])
    rows.append([kb.glass("📡 تاریخچهٔ ارسال‌ها", callback_data=f"wh:show:{store_id}",
                          style="primary", emoji="📡")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _paint(event, store_id: str, toast: str | None = None, alert: bool = False) -> None:
    destinations = await conn_repo.auto_destinations(store_id)
    await ui.render(event, await _text(store_id), _keyboard(store_id, destinations),
                    toast=toast, alert=alert)


@router.message(F.text.in_(WORDS))
async def connections_word(message: Message) -> None:
    """کلمهٔ «اتصالات» هم پنل را باز می‌کند، نه فقط دکمه‌اش."""
    try:
        stores = await repo.list_stores(message.from_user.id)
        if not stores:
            await message.answer("اول یک فروشگاه بساز.")
            return
        store_id = stores[0][0]
        destinations = await conn_repo.auto_destinations(store_id)
        await message.answer(await _text(store_id), reply_markup=_keyboard(store_id, destinations),
                             disable_web_page_preview=True)
    except Exception:                                   # noqa: BLE001
        log.exception("پنلِ اتصالات باز نشد")
        await message.answer("پنلِ اتصالات باز نشد؛ دوباره بزن.")


@router.callback_query(F.data.startswith("cn:p:"))
async def connections_show(call: CallbackQuery) -> None:
    store_id = (call.data or "").split(":", 2)[2]
    try:
        await _paint(call, store_id)
    except Exception:                                   # noqa: BLE001
        log.exception("نمایشِ اتصالات")
        await call.answer("باز نشد؛ دوباره بزن", show_alert=True)


@router.callback_query(F.data.startswith("cn:t:"))
async def connections_test(call: CallbackQuery) -> None:
    parts = (call.data or "").split(":")
    store_id = parts[3] if len(parts) > 3 else ""
    index = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    destinations = await conn_repo.auto_destinations(store_id)
    if not 1 <= index <= len(destinations):
        await call.answer("این مقصد دیگر نیست", show_alert=True)
        return
    await call.answer("در حال ارسال…")
    ok, note = await conn_repo.send_test(destinations[index - 1]["url"], store_id)
    await call.answer(("✅ " if ok else "✘ ") + note, show_alert=not ok)
