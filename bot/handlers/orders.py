from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bson import ObjectId
from bot.database import user_orders
from bot.states import OrdersState
from bot.keyboards.orders import orders_menu_kb, order_edit_kb
from bot.utils.texts import *

router = Router()


def check_order_overlaps(user_orders_list, new_order=None, exclude_id=None):
    """
    Проверяет пересечения параметров ордеров.
    Возвращает список предупреждений о пересечениях.
    """
    warnings = []
    orders_to_check = user_orders_list.copy()

    if new_order:
        orders_to_check.append(new_order)

    active_orders = [o for o in orders_to_check if o.get("enabled", True)]

    for i, order1 in enumerate(active_orders):
        if exclude_id and order1.get("_id") == exclude_id:
            continue

        for j, order2 in enumerate(active_orders[i + 1 :], i + 1):
            if exclude_id and order2.get("_id") == exclude_id:
                continue

            price1 = order1.get("price", {})
            price2 = order2.get("price", {})

            p1_min, p1_max = price1.get("min", 1), price1.get("max", 100000)
            p2_min, p2_max = price2.get("min", 1), price2.get("max", 100000)

            price_overlap = not (p1_max < p2_min or p2_max < p1_min)

            supply1 = order1.get("supply", {})
            supply2 = order2.get("supply", {})

            s1_min, s1_max = supply1.get("min", 1), supply1.get("max", 999999)
            s2_min, s2_max = supply2.get("min", 1), supply2.get("max", 999999)

            supply_overlap = not (s1_max < s2_min or s2_max < s1_min)

            if price_overlap and supply_overlap:
                name1 = order1.get("name", f"Ордер {i+1}")
                name2 = order2.get("name", f"Ордер {j+1}")
                warnings.append(
                    f"⚠️ Пересечение: '{name1}' и '{name2}'\n"
                    f"   Цена: {p1_min}-{p1_max} ⭐ ↔ {p2_min}-{p2_max} ⭐\n"
                    f"   Supply: {s1_min}-{s1_max} ↔ {s2_min}-{s2_max}"
                )

    return warnings


def _normalize_price_range(text: str):
    parts = (text or "").strip().split()
    if len(parts) != 2:
        return None
    try:
        a = int(parts[0].replace(",", ""))
        b = int(parts[1].replace(",", ""))
        if a < 0 or b < 0:
            return None
        return (min(a, b), max(a, b))
    except Exception:
        return None


def _parse_oid(raw: str):
    s = (raw or "").strip()

    if s.startswith("ObjectId("):
        s = s[s.find("(") + 1 : s.rfind(")")].strip().strip('"')
    try:
        return ObjectId(s)
    except Exception as e:
        print(f"DEBUG: Failed to parse ObjectId from '{raw}' -> '{s}': {e}")
        return None


def _normalize_supply_range(text: str):
    parts = (text or "").strip().split()
    if len(parts) != 2:
        return None
    try:
        a = int(parts[0].replace(",", ""))
        b = int(parts[1].replace(",", ""))
        if a < 0 or b < 0:
            return None
        return (min(a, b), max(a, b))
    except Exception:
        return None


@router.callback_query(F.data.startswith("order_edit_budget_"))
async def order_edit_budget(callback: CallbackQuery, state: FSMContext):
    oid = callback.data.split("_", 3)[3]
    await state.update_data(edit_id=oid)
    await state.set_state(OrdersState.edit_budget)
    await callback.message.edit_text(
        ORDER_ENTER_BUDGET, reply_markup=order_edit_kb("cancel")
    )


@router.callback_query(F.data.startswith("order_edit_price__"))
async def order_edit_price(callback: CallbackQuery, state: FSMContext):
    oid = callback.data.split("_", 3)[3]
    await state.update_data(edit_id=oid)
    await state.set_state(OrdersState.edit_price)
    await callback.message.edit_text(
        PRICE_FILTER_MENU_SIMPLE, reply_markup=order_edit_kb("cancel")
    )


@router.callback_query(F.data.startswith("order_edit_supply__"))
async def order_edit_supply(callback: CallbackQuery, state: FSMContext):
    oid = callback.data.split("_", 3)[3]
    await state.update_data(edit_id=oid)
    await state.set_state(OrdersState.edit_supply)
    await callback.message.edit_text(
        SUPPLY_FILTER_MENU_SIMPLE, reply_markup=order_edit_kb("cancel")
    )


@router.message(Command("orders"))
async def orders_command(message: Message):
    await show_orders(message, True)


@router.callback_query(F.data.startswith("order_edit_comment_"))
async def order_edit_comment_cb(callback: CallbackQuery, state: FSMContext):
    oid = callback.data.split("_", 3)[3]
    await state.update_data(edit_id=oid)
    await state.set_state(OrdersState.edit_comment)
    await callback.message.edit_text(
        ORDER_ENTER_COMMENT,
        reply_markup=order_edit_kb("cancel"),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data.startswith("order_edit_channel_"))
async def order_edit_channel_cb(callback: CallbackQuery, state: FSMContext):
    oid = callback.data.split("_", 3)[3]
    await state.update_data(edit_id=oid)
    await state.set_state(OrdersState.edit_channel)
    await callback.message.edit_text(
        ORDER_ENTER_CHANNEL,
        reply_markup=order_edit_kb("cancel"),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == "orders_menu")
async def orders_menu_callback(callback: CallbackQuery):
    await show_orders(callback, False)


async def show_orders(obj, is_message: bool):
    user_id = obj.from_user.id
    items = (
        await user_orders.find({"user_id": user_id}).sort("created_at", 1).to_list(100)
    )
    text_lines = [ORDERS_HEADER]
    if not items:
        text_lines.append(ORDERS_EMPTY)
    else:

        warnings = check_order_overlaps(items)
        if warnings:
            text_lines.append("\n🚨 <b>ВНИМАНИЕ! Обнаружены пересечения ордеров:</b>")
            for warning in warnings:
                text_lines.append(warning)
    kb = orders_menu_kb(items)
    text = "\n".join(text_lines)
    if is_message:
        await obj.answer(text, reply_markup=kb)
    else:
        await obj.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "order_add")
async def order_add(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(OrdersState.name)
    await callback.message.edit_text(
        ORDER_ENTER_NAME, reply_markup=order_edit_kb("cancel")
    )


@router.message(OrdersState.name)
async def order_set_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()[:64] or None
    await state.update_data(name=name)
    await state.set_state(OrdersState.price_range)
    await message.answer(ORDER_ENTER_PRICE_RANGE)


@router.message(OrdersState.price_range)
async def order_set_price_range(message: Message, state: FSMContext):
    rng = _normalize_price_range(message.text)
    if not rng:
        await message.answer(ERROR_INVALID_FORMAT)
        return
    await state.update_data(price={"min": rng[0], "max": rng[1]})
    await state.set_state(OrdersState.supply_range)
    await message.answer(ORDER_ENTER_SUPPLY_RANGE)


@router.message(OrdersState.supply_range)
async def order_set_supply_range(message: Message, state: FSMContext):
    rng = _normalize_supply_range(message.text)
    if not rng:
        await message.answer(ERROR_INVALID_FORMAT)
        return
    await state.update_data(supply={"min": rng[0], "max": rng[1]})
    await state.set_state(OrdersState.budget)
    await message.answer(ORDER_ENTER_BUDGET)


@router.message(OrdersState.budget)
async def order_set_budget(message: Message, state: FSMContext):
    try:
        val = int((message.text or "").strip())
        if val <= 0 or val > 1000000:
            raise ValueError
    except Exception:
        await message.answer(ERROR_INVALID_FORMAT)
        return

    data = await state.get_data()
    new_order = {
        "user_id": message.from_user.id,
        "name": data.get("name") or "Ордер",
        "price": data.get("price") or {"min": 1, "max": 100000},
        "supply": data.get("supply") or {"min": 1, "max": 999999},
        "budget": val,
        "spent": 0,
        "enabled": True,
        "comment": "",
        "channel": None,
        "created_at": message.date.timestamp(),
    }

    existing_orders = await user_orders.find({"user_id": message.from_user.id}).to_list(
        100
    )
    warnings = check_order_overlaps(existing_orders, new_order)

    await user_orders.insert_one(new_order)
    await state.clear()

    if warnings:
        warning_text = (
            "⚠️ <b>Ордер создан, но обнаружены пересечения:</b>\n\n"
            + "\n\n".join(warnings)
        )
        warning_text += (
            "\n\n<i>Пересекающиеся ордера могут обрабатывать одни и те же подарки!</i>"
        )
        await message.answer(warning_text)

    await show_orders(message, True)


@router.callback_query(F.data.startswith("order_toggle_"))
async def order_toggle(callback: CallbackQuery):
    oid = callback.data.split("_", 2)[2]
    _id = _parse_oid(oid)
    if not _id:
        await callback.answer("❌ Не найдено")
        return
    doc = await user_orders.find_one({"_id": _id})
    if not doc:
        await callback.answer("❌ Не найдено")
        return
    await user_orders.update_one(
        {"_id": doc["_id"]}, {"$set": {"enabled": not doc.get("enabled", True)}}
    )

    doc = await user_orders.find_one({"_id": _id})
    await callback.message.edit_text(
        _render_order_card_text(doc), reply_markup=order_edit_kb(doc)
    )


@router.callback_query(F.data.startswith("order_delete_"))
async def order_delete(callback: CallbackQuery):
    oid = callback.data.split("_", 2)[2]
    _id = _parse_oid(oid)
    if not _id:
        await callback.answer("❌ Не найдено")
        return
    await user_orders.delete_one({"_id": _id})
    await show_orders(callback, False)


@router.callback_query(F.data.startswith("order_open_"))
async def order_edit_menu(callback: CallbackQuery, state: FSMContext):
    print(f"DEBUG: Full callback data: '{callback.data}'")
    oid = callback.data.split("_", 2)[2]
    print(f"DEBUG: Extracted oid: '{oid}'")
    _id = _parse_oid(oid)
    if not _id:
        await callback.answer("❌ Не найдено")
        return
    doc = await user_orders.find_one({"_id": _id})
    if not doc:
        await callback.answer("❌ Не найдено")
        return
    await state.update_data(edit_id=oid)
    pr = doc.get("price") or {}
    sr = doc.get("supply") or {}
    text = ORDER_CARD.format(
        status=("✅" if doc.get("enabled", True) else "⏸"),
        name=doc.get("name", "Ордер"),
        min_price=pr.get("min", 1),
        max_price=pr.get("max", 100000),
        min_supply=sr.get("min", 1),
        max_supply=sr.get("max", 999999),
        budget=doc.get("budget", 10000),
        spent=doc.get("spent", 0),
    )

    if (doc.get("comment") or "").strip():
        text += f"\n🗒 Комментарий: {doc.get('comment').strip()}"
    if doc.get("channel"):
        text += f"\n📢 Канал: {doc.get('channel')}"
    await callback.message.edit_text(text, reply_markup=order_edit_kb(doc))


@router.callback_query(F.data.startswith("order_edit_price_min_"))
async def order_edit_price_min_cb(callback: CallbackQuery, state: FSMContext):
    oid = callback.data.split("_", 4)[4]
    await state.update_data(edit_id=oid)
    await state.set_state(OrdersState.edit_price_min)
    await callback.message.edit_text(
        "💰 Введите минимальную цену (целое число)",
        reply_markup=order_edit_kb("cancel"),
    )


@router.callback_query(F.data.startswith("order_edit_price_max_"))
async def order_edit_price_max_cb(callback: CallbackQuery, state: FSMContext):
    oid = callback.data.split("_", 4)[4]
    await state.update_data(edit_id=oid)
    await state.set_state(OrdersState.edit_price_max)
    await callback.message.edit_text(
        "💰 Введите максимальную цену (целое число)",
        reply_markup=order_edit_kb("cancel"),
    )


@router.callback_query(F.data.startswith("order_edit_supply_min_"))
async def order_edit_supply_min_cb(callback: CallbackQuery, state: FSMContext):
    oid = callback.data.split("_", 4)[4]
    await state.update_data(edit_id=oid)
    await state.set_state(OrdersState.edit_supply_min)
    await callback.message.edit_text(
        "📦 Введите минимальный тираж (целое число)",
        reply_markup=order_edit_kb("cancel"),
    )


@router.callback_query(F.data.startswith("order_edit_supply_max_"))
async def order_edit_supply_max_cb(callback: CallbackQuery, state: FSMContext):
    oid = callback.data.split("_", 4)[4]
    await state.update_data(edit_id=oid)
    await state.set_state(OrdersState.edit_supply_max)
    await callback.message.edit_text(
        "📦 Введите максимальный тираж (целое число)",
        reply_markup=order_edit_kb("cancel"),
    )


def _render_order_card_text(doc: dict) -> str:
    pr = doc.get("price") or {}
    sr = doc.get("supply") or {}
    text = ORDER_CARD.format(
        status=("✅" if doc.get("enabled", True) else "⏸"),
        name=doc.get("name", "Ордер"),
        min_price=pr.get("min", 1),
        max_price=pr.get("max", 100000),
        min_supply=sr.get("min", 1),
        max_supply=sr.get("max", 999999),
        budget=doc.get("budget", 10000),
        spent=doc.get("spent", 0),
    )
    if (doc.get("comment") or "").strip():
        text += f"\n🗒 Комментарий: {doc.get('comment').strip()}"
    if doc.get("channel"):
        text += f"\n📢 Канал: {doc.get('channel')}"
    return text


@router.message(OrdersState.edit_price_min)
async def order_set_price_min(message: Message, state: FSMContext):
    try:
        new_min = int((message.text or "").strip())
        if new_min < 0:
            raise ValueError
    except Exception:
        await message.answer(ERROR_INVALID_FORMAT)
        return
    data = await state.get_data()
    _id = _parse_oid(data.get("edit_id"))
    if not _id:
        await state.clear()
        await message.answer("❌ Не найдено")
        return
    doc = await user_orders.find_one({"_id": _id})
    pr = (doc or {}).get("price") or {}
    old_max = int(pr.get("max", 100000))
    new_max = max(new_min, old_max)
    await user_orders.update_one(
        {"_id": _id}, {"$set": {"price": {"min": new_min, "max": new_max}}}
    )
    await state.clear()
    doc = await user_orders.find_one({"_id": _id})
    await message.answer(_render_order_card_text(doc), reply_markup=order_edit_kb(doc))


@router.message(OrdersState.edit_comment)
async def order_do_edit_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    oid = data.get("edit_id")
    _id = _parse_oid(oid)
    if not _id:
        await message.answer("❌ Не найдено")
        await state.clear()
        return
    text = (message.text or "").strip()

    if text.lower() in {"-", "—", "удалить", "delete"}:
        comment = ""
    else:
        comment = text[:200]
    await user_orders.update_one({"_id": _id}, {"$set": {"comment": comment}})
    await state.clear()
    doc = await user_orders.find_one({"_id": _id})
    await message.answer(_render_order_card_text(doc), reply_markup=order_edit_kb(doc))


@router.message(OrdersState.edit_channel)
async def order_do_edit_channel(message: Message, state: FSMContext):
    data = await state.get_data()
    oid = data.get("edit_id")
    _id = _parse_oid(oid)
    if not _id:
        await message.answer("❌ Не найдено")
        await state.clear()
        return
    raw = (message.text or "").strip()
    if raw.lower() in {"-", "—", "удалить", "delete"}:
        channel = None
    else:
        channel = raw or None
    await user_orders.update_one({"_id": _id}, {"$set": {"channel": channel}})
    await state.clear()
    doc = await user_orders.find_one({"_id": _id})
    await message.answer(_render_order_card_text(doc), reply_markup=order_edit_kb(doc))


@router.message(OrdersState.edit_price_max)
async def order_set_price_max(message: Message, state: FSMContext):
    try:
        new_max = int((message.text or "").strip())
        if new_max < 0:
            raise ValueError
    except Exception:
        await message.answer(ERROR_INVALID_FORMAT)
        return
    data = await state.get_data()
    _id = _parse_oid(data.get("edit_id"))
    if not _id:
        await state.clear()
        await message.answer("❌ Не найдено")
        return
    doc = await user_orders.find_one({"_id": _id})
    pr = (doc or {}).get("price") or {}
    old_min = int(pr.get("min", 1))
    new_min = min(old_min, new_max)
    await user_orders.update_one(
        {"_id": _id}, {"$set": {"price": {"min": new_min, "max": new_max}}}
    )
    await state.clear()
    doc = await user_orders.find_one({"_id": _id})
    await message.answer(_render_order_card_text(doc), reply_markup=order_edit_kb(doc))


@router.message(OrdersState.edit_supply_min)
async def order_set_supply_min(message: Message, state: FSMContext):
    try:
        new_min = int((message.text or "").strip())
        if new_min < 0:
            raise ValueError
    except Exception:
        await message.answer(ERROR_INVALID_FORMAT)
        return
    data = await state.get_data()
    _id = _parse_oid(data.get("edit_id"))
    if not _id:
        await state.clear()
        await message.answer("❌ Не найдено")
        return
    doc = await user_orders.find_one({"_id": _id})
    sr = (doc or {}).get("supply") or {}
    old_max = int(sr.get("max", 999999))
    new_max = max(new_min, old_max)
    await user_orders.update_one(
        {"_id": _id}, {"$set": {"supply": {"min": new_min, "max": new_max}}}
    )
    await state.clear()
    doc = await user_orders.find_one({"_id": _id})
    await message.answer(_render_order_card_text(doc), reply_markup=order_edit_kb(doc))


@router.message(OrdersState.edit_supply_max)
async def order_set_supply_max(message: Message, state: FSMContext):
    try:
        new_max = int((message.text or "").strip())
        if new_max < 0:
            raise ValueError
    except Exception:
        await message.answer(ERROR_INVALID_FORMAT)
        return
    data = await state.get_data()
    _id = _parse_oid(data.get("edit_id"))
    if not _id:
        await state.clear()
        await message.answer("❌ Не найдено")
        return
    doc = await user_orders.find_one({"_id": _id})
    sr = (doc or {}).get("supply") or {}
    old_min = int(sr.get("min", 1))
    new_min = min(old_min, new_max)
    await user_orders.update_one(
        {"_id": _id}, {"$set": {"supply": {"min": new_min, "max": new_max}}}
    )
    await state.clear()
    doc = await user_orders.find_one({"_id": _id})
    await message.answer(_render_order_card_text(doc), reply_markup=order_edit_kb(doc))


@router.message(OrdersState.edit_price)
async def order_do_edit_price(message: Message, state: FSMContext):
    data = await state.get_data()
    oid = data.get("edit_id")
    rng = _normalize_price_range(message.text)
    if not rng:
        await message.answer(ERROR_INVALID_FORMAT)
        return
    _id = _parse_oid(oid)
    if not _id:
        await message.answer("❌ Не найдено")
        await state.clear()
        return

    existing_orders = await user_orders.find({"user_id": message.from_user.id}).to_list(
        100
    )

    current_order = await user_orders.find_one({"_id": _id})
    if current_order:
        temp_order = current_order.copy()
        temp_order["price"] = {"min": rng[0], "max": rng[1]}
        warnings = check_order_overlaps(existing_orders, temp_order, exclude_id=_id)

    await user_orders.update_one(
        {"_id": _id}, {"$set": {"price": {"min": rng[0], "max": rng[1]}}}
    )
    await state.clear()
    if warnings:
        warning_text = (
            "⚠️ <b>Цена изменена, но обнаружены пересечения:</b>\n\n"
            + "\n\n".join(warnings)
        )
        warning_text += (
            "\n\n<i>Пересекающиеся ордера могут обрабатывать одни и те же подарки!</i>"
        )
        await message.answer(warning_text)

    doc = await user_orders.find_one({"_id": _id})
    await message.answer(_render_order_card_text(doc), reply_markup=order_edit_kb(doc))


@router.message(OrdersState.edit_supply)
async def order_do_edit_supply(message: Message, state: FSMContext):
    data = await state.get_data()
    oid = data.get("edit_id")
    rng = _normalize_supply_range(message.text)
    if not rng:
        await message.answer(ERROR_INVALID_FORMAT)
        return
    _id = _parse_oid(oid)
    if not _id:
        await message.answer("❌ Не найдено")
        await state.clear()
        return

    existing_orders = await user_orders.find({"user_id": message.from_user.id}).to_list(
        100
    )

    current_order = await user_orders.find_one({"_id": _id})
    if current_order:
        temp_order = current_order.copy()
        temp_order["supply"] = {"min": rng[0], "max": rng[1]}
        warnings = check_order_overlaps(existing_orders, temp_order, exclude_id=_id)

    await user_orders.update_one(
        {"_id": _id}, {"$set": {"supply": {"min": rng[0], "max": rng[1]}}}
    )
    await state.clear()
    if warnings:
        warning_text = (
            "⚠️ <b>Supply изменен, но обнаружены пересечения:</b>\n\n"
            + "\n\n".join(warnings)
        )
        warning_text += (
            "\n\n<i>Пересекающиеся ордера могут обрабатывать одни и те же подарки!</i>"
        )
        await message.answer(warning_text)

    doc = await user_orders.find_one({"_id": _id})
    await message.answer(_render_order_card_text(doc), reply_markup=order_edit_kb(doc))


@router.message(OrdersState.edit_budget)
async def order_do_edit_budget(message: Message, state: FSMContext):
    data = await state.get_data()
    oid = data.get("edit_id")
    try:
        val = int((message.text or "").strip())
        if val <= 0 or val > 1000000:
            raise ValueError
    except Exception:
        await message.answer(ERROR_INVALID_FORMAT)
        return
    _id = _parse_oid(oid)
    if not _id:
        await message.answer("❌ Не найдено")
        await state.clear()
        return
    await user_orders.update_one({"_id": _id}, {"$set": {"budget": val}})
    await state.clear()

    doc = await user_orders.find_one({"_id": _id})
    await message.answer(_render_order_card_text(doc), reply_markup=order_edit_kb(doc))
