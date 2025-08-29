from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_deposit_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ 100", callback_data="deposit_100"),
                InlineKeyboardButton(text="⭐ 500", callback_data="deposit_500"),
            ],
            [
                InlineKeyboardButton(text="⭐ 1000", callback_data="deposit_1000"),
                InlineKeyboardButton(text="⭐ 5000", callback_data="deposit_5000"),
            ],
            [InlineKeyboardButton(text="✍️ Своя сумма", callback_data="deposit_custom")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
        ]
    )


def get_custom_deposit_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="deposit_menu")],
        ]
    )


def get_cancel_deposit_to_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )
