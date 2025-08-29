from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from bot.database import get_user
from bot.states import SettingsInput


async def refund_stars(bot, user_id: int, amount: int, charge_id: str):
    try:
        await bot.refund_star_payment(
            user_id=user_id, telegram_payment_charge_id=charge_id
        )
        return True
    except:
        return False


async def show_settings_menu(obj, is_message: bool):
    user = await get_user(obj.from_user.id)
    max_gifts = user.get("max_gifts_per_type", 1)
    min_price = user.get("min_price", 1)
    max_price = user.get("max_price", 10000)
    min_supply = user.get("min_supply", 1)
    max_supply = user.get("max_supply", 999999)
    rtype = user.get("gift_recipient_type", "personal")
    rid = user.get("gift_recipient_id")
    if rtype == "channel":
        rtext = f"@{user.get('gift_recipient_username', 'неизвестно')}"
    else:
        rtext = f"ID: {rid}" if rid else "Себе"
    text = f"""⚙️ <b>Настройки Автоскупа</b> 🌟

🎁 Макс. подарков на тип: <b>{max_gifts}</b>
💰 Диапазон цены: <b>{min_price:,} - {max_price:,}</b> ⭐
📦 Диапазон supply: <b>{min_supply:,} - {max_supply:,}</b>
👤 Получатель: <b>{rtext}</b> ({rtype.capitalize()})"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎁 Кол. подарков (1-5)", callback_data="choose_max_gifts"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Фильтр цены", callback_data="price_filters"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Фильтр supply", callback_data="supply_filters"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Настроить получателя", callback_data="recipient_settings"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню", callback_data="back_to_main"
                )
            ],
        ]
    )
    if is_message:
        await obj.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await obj.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


async def show_main_menu(message):
    text = """✨ <b>Добро пожаловать!</b>

👋 Привет, <b>{message.from_user.first_name}</b>!

<b>Меню:</b>
• 💰 Баланс и транзакции
• ⚙️ Настройки автоскупа
• ❓ Помощь

Нажмите кнопку ниже для действий! 🚀"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Пополнить баланс", callback_data="start_deposit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Просмотреть баланс", callback_data="show_balance"
                )
            ],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="show_settings")],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="show_help")],
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
