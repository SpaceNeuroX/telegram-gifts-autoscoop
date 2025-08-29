from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from datetime import datetime
from bot.database import users
from bot.utils.texts import START_TEXT, HELP_TEXT
from bot.keyboards.main_menu import get_main_menu, get_help_keyboard
from bot.config import TAKE_COMMISSION

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    user = await users.find_one({"user_id": user_id})

    referrer_id = None
    try:
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) > 1 and parts[1].isdigit():
            cand = int(parts[1])
            if cand != user_id:
                ref_exists = await users.find_one({"user_id": cand})
                if ref_exists:
                    referrer_id = cand
    except Exception:
        referrer_id = None

    if not user:
        await users.insert_one(
            {
                "user_id": user_id,
                "username": message.from_user.username,
                "created_at": datetime.utcnow(),
                "balance": 0,
                "max_gifts_per_type": 1,
                "min_price": 1,
                "max_price": 10000,
                "min_supply": 1,
                "max_supply": 999999,
                "gift_recipient_type": "personal",
                "bot_id": bot.id,
                "refund_locked": False,
                "referred_by": referrer_id if TAKE_COMMISSION else None,
                "referrals_count": 0,
            }
        )

        if referrer_id and TAKE_COMMISSION:
            try:
                await users.update_one(
                    {"user_id": referrer_id}, {"$inc": {"referrals_count": 1}}
                )
                await bot.send_message(
                    chat_id=referrer_id,
                    text=f"👥 По вашей реферальной ссылке зарегистрировался новый пользователь: {message.from_user.first_name} (ID: {user_id})",
                )
            except Exception:
                pass

    await message.answer(
        START_TEXT.format(name=message.from_user.first_name),
        reply_markup=get_main_menu(),
    )


@router.callback_query(F.data == "ref_link")
async def ref_link_callback(callback: CallbackQuery, bot: Bot):
    if not TAKE_COMMISSION:
        await callback.answer("❌ Реферальная система отключена", show_alert=True)
        return

    me = await bot.me()
    link = f"https://t.me/{me.username}?start={callback.from_user.id}"
    text = (
        f"🔗 Ваша реферальная ссылка:\n<code>{link}</code>\n\n"
        "💡 Если пользователи будут регистрироваться по вашей ссылке и пополнять баланс, \n"
        "вы будете получать <b>2%</b> от суммы каждого их пополнения."
    )
    await callback.message.edit_text(text, reply_markup=get_main_menu())


@router.message(Command("reflink"))
async def ref_link_cmd(message: Message, bot: Bot):
    if not TAKE_COMMISSION:
        await message.answer("❌ Реферальная система отключена")
        return

    me = await bot.me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    await message.answer(
        """
🔗 Ваша реферальная ссылка:
<code>{link}</code>

💡 Если пользователи будут регистрироваться по вашей ссылке и пополнять баланс,
вы будете получать <b>2%</b> от суммы каждого их пополнения.
""".strip().format(
            link=link
        )
    )


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        START_TEXT.format(name=callback.from_user.first_name),
        reply_markup=get_main_menu(),
    )


@router.callback_query(F.data == "help_menu")
async def help_callback(callback: CallbackQuery):
    await callback.message.edit_text(HELP_TEXT, reply_markup=get_help_keyboard())
