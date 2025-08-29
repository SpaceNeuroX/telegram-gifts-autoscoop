from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_settings_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Телеграм аккаунт", callback_data="account_menu"
                )
            ],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")],
        ]
    )


def get_gifts_count_keyboard(current):
    buttons = []
    for i in range(1, 6):
        emoji = "✅" if i == current else str(i)
        if i == 1:
            row = [
                InlineKeyboardButton(text=f"{emoji}", callback_data=f"set_gifts_{i}")
            ]
        else:
            row.append(
                InlineKeyboardButton(text=f"{emoji}", callback_data=f"set_gifts_{i}")
            )

        if len(row) == 5 or i == 5:
            buttons.append(row)
            row = []

    buttons.append(
        [InlineKeyboardButton(text="🔙 Настройки", callback_data="settings_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_filter_input_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Настройки", callback_data="settings_menu")]
        ]
    )


def get_account_menu_keyboard(
    connected: bool,
    use_personal_buy: bool,
    allow_premium_buy: bool,
    buy_only_personal: bool = False,
):
    rows = []
    if connected:
        rows.append(
            [InlineKeyboardButton(text="✅ Аккаунт привязан", callback_data="noop")]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="🧪 Тест подключения", callback_data="telethon_test"
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        "🛠️ Пробовать через личный: Вкл"
                        if use_personal_buy
                        else "🛠️ Пробовать через личный: Выкл"
                    ),
                    callback_data="toggle_personal_buy",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        "🔒 Покупать только через личный: Вкл"
                        if buy_only_personal
                        else "🔒 Покупать только через личный: Выкл"
                    ),
                    callback_data="toggle_only_personal_buy",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        "👑 Покупать премиум подарки: Вкл"
                        if allow_premium_buy
                        else "👑 Покупать премиум подарки: Выкл"
                    ),
                    callback_data="toggle_premium_buy",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="❌ Отключить аккаунт", callback_data="unlink_account"
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔗 Привязать аккаунт", callback_data="link_account"
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="🔙 Настройки", callback_data="settings_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_code_keypad(code: str):
    display = f"Код: {code or '—'}"
    rows = [
        [InlineKeyboardButton(text=display, callback_data="noop")],
        [
            InlineKeyboardButton(text="1", callback_data="code_digit_1"),
            InlineKeyboardButton(text="2", callback_data="code_digit_2"),
            InlineKeyboardButton(text="3", callback_data="code_digit_3"),
        ],
        [
            InlineKeyboardButton(text="4", callback_data="code_digit_4"),
            InlineKeyboardButton(text="5", callback_data="code_digit_5"),
            InlineKeyboardButton(text="6", callback_data="code_digit_6"),
        ],
        [
            InlineKeyboardButton(text="7", callback_data="code_digit_7"),
            InlineKeyboardButton(text="8", callback_data="code_digit_8"),
            InlineKeyboardButton(text="9", callback_data="code_digit_9"),
        ],
        [
            InlineKeyboardButton(text="⌫", callback_data="code_back"),
            InlineKeyboardButton(text="0", callback_data="code_digit_0"),
            InlineKeyboardButton(text="✅ Отправить", callback_data="code_submit"),
        ],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="account_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_account_consent_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принимаю", callback_data="account_consent_accept"
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="account_menu")],
        ]
    )
