"""CONNECT-V1 — پنلِ «🔌 اتصالات»: تا سه مقصدِ وبهوک برای هر فروشگاه.

قاعده‌ای که این پنل دنبال می‌کند: فاکتور از هر مقصدی ساخته شود، خبرِ
«پرداخت شد» اول به همان مقصد می‌رود و بعد به بقیهٔ مقصدهای همین فروشگاه.
هر مقصد کلیدِ امضای خودش را دارد، پس یک ربات نمی‌تواند جای رباتِ دیگر را بگیرد.

هیچ دکمه‌ای در این فایل بی‌جواب نمی‌ماند: هر هندلر داخل try است و در بدترین
حالت یک پیامِ کوتاه نشان می‌دهد.
"""
from __future__ import annotations

import html
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import keyboards as kb
import ui
from services import conn_repo
from services.dates import fa_digits

log = logging.getLogger("sibilpay.conn")
router = Router(name="connections")

MAX = conn_repo.MAX_ENDPOINTS


class AddHook(StatesGroup):
    url = State()


def _mask(secret: str) -> str:
    return "…" + secret[-4:] if len(secret) > 4 else "—"


def _short(url: str) -> str:
    pretty = url.replace("https://", "").replace("http://", "")
    return pretty if len(pretty) <= 58 else pretty[:55] + "…"


async def _text(store_id: str) -> str:
    endpoints = await conn_repo.list_endpoints(store_id)
    lines = ["🔌 <b>اتصالات</b>", ""]
    lines.append(
        "فاکتور از هر مقصدی که ساخته شود، خبرِ پرداخت اول به همان مقصد می‌رود و "
        "بعد به بقیهٔ مقصدها."
    )
    lines.append("")
    if not endpoints:
        lines.append("<b>هیچ مقصدی ثبت نشده.</b>")
        lines.append("تا مقصد نباشد، رباتت از پرداخت خبردار نمی‌شود.")
    else:
        for i, ep in enumerate(endpoints, 1):
            name = html.escape(ep["label"]) if ep["label"] else f"مقصد {fa_digits(i)}"
            lines.append(f"{fa_digits(i)} · <b>{name}</b>")
            lines.append(f"   <code>{html.escape(_short(ep['url']))}</code>")
            lines.append(f"   کلیدِ امضا: <code>{_mask(ep['secret'])}</code>")
    lines.append("")
    lines.append(f"ظرفیت: {fa_digits(len(endpoints))} از {fa_digits(MAX)}")
    return "\n".join(lines)


def _keyboard(store_id: str, endpoints: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i, ep in enumerate(endpoints, 1):
        rows.append([
            kb.glass(f"🧪 {fa_digits(i)}", callback_data=f"cn:t:{ep['id']}", style="success", emoji="🧪"),
            kb.glass(f"🔑 {fa_digits(i)}", callback_data=f"cn:r:{ep['id']}", style="primary", emoji="🔑"),
            kb.glass(f"🗑 {fa_digits(i)}", callback_data=f"cn:d:{ep['id']}", style="danger", emoji="🗑"),
        ])
    if len(endpoints) < MAX:
        rows.append([kb.glass("افزودن مقصد", callback_data=f"cn:a:{store_id}",
                              style="success", emoji="➕")])
    rows.append([kb.glass("📡 تاریخچهٔ ارسال‌ها", callback_data=f"wh:show:{store_id}",
                          style="primary", emoji="📡")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _paint(call: CallbackQuery, store_id: str, toast: str | None = None,
                 alert: bool = False) -> None:
    endpoints = await conn_repo.list_endpoints(store_id)
    await ui.render(call, await _text(store_id), _keyboard(store_id, endpoints),
                    toast=toast, alert=alert)


@router.callback_query(F.data.startswith("cn:p:"))
async def connections_show(call: CallbackQuery) -> None:
    store_id = (call.data or "").split(":", 2)[2]
    try:
        await _paint(call, store_id)
    except Exception:                                   # noqa: BLE001
        log.exception("نمایشِ اتصالات")
        await call.answer("باز نشد؛ دوباره بزن", show_alert=True)


@router.callback_query(F.data.startswith("cn:a:"))
async def connections_add_start(call: CallbackQuery, state: FSMContext) -> None:
    store_id = (call.data or "").split(":", 2)[2]
    endpoints = await conn_repo.list_endpoints(store_id)
    if len(endpoints) >= MAX:
        await _paint(call, store_id, toast=f"سقفِ {MAX} مقصد پر است", alert=True)
        return
    await state.set_state(AddHook.url)
    await state.update_data(store_id=store_id)
    await ui.render(
        call,
        "🔌 <b>مقصد تازه</b>\n\nآدرسِ وبهوک را بفرست.\n"
        "مثال:\n<code>https://bot.example.com/sibilpay/hook</code>\n\n"
        "آدرس را لغو کن با دکمهٔ پایین.",
        InlineKeyboardMarkup(inline_keyboard=[[
            kb.glass("لغو", callback_data=f"cn:p:{store_id}", style="danger", emoji="✖")]]),
    )


@router.message(AddHook.url)
async def connections_add_url(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    store_id = data.get("store_id") or ""
    url = (message.text or "").strip()
    ok, note = await conn_repo.add_endpoint(store_id, url)
    await state.clear()
    if not ok:
        endpoints = await conn_repo.list_endpoints(store_id)
        await message.answer(f"ثبت نشد: {html.escape(note)}",
                             reply_markup=_keyboard(store_id, endpoints))
        return
    endpoints = await conn_repo.list_endpoints(store_id)
    lines = [await _text(store_id), "",
             "مقصد ثبت شد. کلیدِ امضای همین مقصد:",
             f"<code>{html.escape(note)}</code>",
             "",
             "این کلید فقط یک بار نشان داده می‌شود. آن را در رباتِ خودت بگذار و "
             "امضای <code>X-SIBILPAY-Signature</code> را با همین بساز."]
    await message.answer("\n".join(lines), reply_markup=_keyboard(store_id, endpoints),
                         disable_web_page_preview=True)


@router.callback_query(F.data.startswith("cn:t:"))
async def connections_test(call: CallbackQuery) -> None:
    endpoint_id = (call.data or "").split(":", 2)[2]
    await call.answer("در حال ارسال…")
    ok, note = await conn_repo.send_test(endpoint_id)
    await call.answer(("✅ " if ok else "✘ ") + note, show_alert=not ok)


@router.callback_query(F.data.startswith("cn:r:"))
async def connections_rotate(call: CallbackQuery) -> None:
    endpoint_id = (call.data or "").split(":", 2)[2]
    store_id = ""
    store_id = await conn_repo.endpoint_store_id(endpoint_id)
    secret = await conn_repo.rotate_secret(store_id, endpoint_id) if store_id else ""
    if not secret:
        await call.answer("مقصد پیدا نشد", show_alert=True)
        return
    endpoints = await conn_repo.list_endpoints(store_id) if store_id else []
    await ui.render(
        call,
        "🔑 <b>کلیدِ تازه</b>\n\nکلیدِ قدیمی همین مقصد دیگر معتبر نیست.\n\n"
        f"<code>{html.escape(secret)}</code>\n\nکلیدِ تازه را در رباتت جای‌گذاری کن.",
        _keyboard(store_id, endpoints),
    )


@router.callback_query(F.data.startswith("cn:d:"))
async def connections_delete(call: CallbackQuery) -> None:
    endpoint_id = (call.data or "").split(":", 2)[2]
    store_id = ""
    store_id = await conn_repo.endpoint_store_id(endpoint_id)
    if not store_id:
        await call.answer("مقصد پیدا نشد", show_alert=True)
        return
    ok = await conn_repo.delete_endpoint(store_id, endpoint_id)
    await _paint(call, store_id, toast="حذف شد" if ok else "حذف نشد", alert=not ok)
