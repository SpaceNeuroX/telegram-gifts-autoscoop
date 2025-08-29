from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def orders_menu_kb(items):
    rows = []
    for it in items or []:
        oid = str(it.get("_id"))
        name = it.get("name") or "Ордер"
        status = "✅" if it.get("enabled", True) else "⏸"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {name}", callback_data=f"order_open_{oid}"
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data="order_add")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_edit_kb(order_or_cancel):
    """Build detailed order keyboard.

    Accepts either the string "cancel" or a full order dict.
    """
    if order_or_cancel == "cancel":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="↩️ К списку", callback_data="orders_menu")]
            ]
        )
    order = order_or_cancel
    oid = str(order.get("_id"))
    pr = order.get("price") or {}
    sr = order.get("supply") or {}
    min_price = pr.get("min", 1)
    max_price = pr.get("max", 100000)
    min_supply = sr.get("min", 1)
    max_supply = sr.get("max", 999999)
    enabled = order.get("enabled", True)
    budget = order.get("budget", 0)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=("🟢 Ордер включён" if enabled else "⚪ Ордер выключен"),
                    callback_data=f"order_toggle_{oid}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"От: {min_price:,} ⭐",
                    callback_data=f"order_edit_price_min_{oid}",
                ),
                InlineKeyboardButton(
                    text=f"До: {max_price:,} ⭐",
                    callback_data=f"order_edit_price_max_{oid}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"Тираж: от {min_supply:,} 🎁",
                    callback_data=f"order_edit_supply_min_{oid}",
                ),
                InlineKeyboardButton(
                    text=f"Тираж: до {max_supply:,} 🎁",
                    callback_data=f"order_edit_supply_max_{oid}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗒 Комментарий", callback_data=f"order_edit_comment_{oid}"
                ),
                InlineKeyboardButton(
                    text="📢 Канал", callback_data=f"order_edit_channel_{oid}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"💳 Бюджет: {budget:,} ⭐",
                    callback_data=f"order_edit_budget_{oid}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить ордер", callback_data=f"order_delete_{oid}"
                )
            ],
            [InlineKeyboardButton(text="↩️ К списку", callback_data="orders_menu")],
        ]
    )
