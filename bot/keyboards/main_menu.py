from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import TAKE_COMMISSION


def get_main_menu():
    keyboard = [
        [
            InlineKeyboardButton(text="💳 Пополнить", callback_data="deposit_menu"),
            InlineKeyboardButton(text="💰 Баланс", callback_data="balance_menu"),
        ],
        [
            InlineKeyboardButton(text="🔁 Перевод", callback_data="transfer_menu"),
            InlineKeyboardButton(
                text="🎯 Пополнить другому", callback_data="depositTo_menu"
            ),
        ],
        [InlineKeyboardButton(text="📈 Ордера", callback_data="orders_menu")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_menu")],
    ]

    if TAKE_COMMISSION:
        keyboard.append(
            [InlineKeyboardButton(text="🔗 Реф. ссылка", callback_data="ref_link")]
        )

    keyboard.append([InlineKeyboardButton(text="📚 Помощь", callback_data="help_menu")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_help_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ]
    )
