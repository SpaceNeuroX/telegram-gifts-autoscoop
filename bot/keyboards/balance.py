from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_balance_keyboard(transactions=None):
    buttons = [
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_balance"),
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"),
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_refund_keyboard(tx_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data=f"confirm_refund_{tx_id}"
                ),
                InlineKeyboardButton(text="❌ Отмена", callback_data="balance_menu"),
            ]
        ]
    )
