from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.config import TELETHON_API_ID, TELETHON_API_HASH
from bot.database import user_accounts, users
from bot.states import LinkState
from bot.utils.texts import (
    ACCOUNT_MENU,
    ACCOUNT_CONSENT,
    ACCOUNT_ENTER_PHONE,
    ACCOUNT_ENTER_CODE,
    ACCOUNT_ENTER_PASSWORD,
    ACCOUNT_LINK_SUCCESS,
    ACCOUNT_UNLINKED,
    ACCOUNT_TEST_RESULT,
    ACCOUNT_TEST_WARNING,
    ERROR_NOT_CONNECTED,
    ERROR_INVALID_PHONE,
    ERROR_CODE_EMPTY,
    ERROR_LOGIN_FAILED,
    ERROR_LOW_BOT_BALANCE,
)
from bot.keyboards.settings import (
    get_account_menu_keyboard,
    build_code_keypad,
    get_account_consent_keyboard,
)
from bot.utils.telethon_client import (
    get_account_doc,
    save_session,
    clear_session,
    start_login_send_code,
    complete_login_with_code,
    complete_login_with_password,
    check_stars_balance,
    set_toggle,
    get_client_for_user,
)

router = Router()


async def render_account_menu(cb_or_msg, is_message: bool):
    user_id = cb_or_msg.from_user.id
    doc = await get_account_doc(user_id)
    connected = bool(doc and doc.get("session_string"))
    use_personal = bool(doc.get("use_personal_buy", False)) if doc else False
    allow_premium_buy = bool(doc.get("allow_premium_buy", False)) if doc else False
    buy_only_personal = bool(doc.get("only_personal_buy", False)) if doc else False

    has_premium = False
    if connected:

        try:
            balance, has_premium = await check_stars_balance(user_id)
        except Exception:
            pass

    ui_allow_premium = allow_premium_buy if has_premium else False

    text = ACCOUNT_MENU
    kb = get_account_menu_keyboard(
        connected, use_personal, ui_allow_premium, buy_only_personal
    )
    if is_message:
        await cb_or_msg.answer(text, reply_markup=kb)
    else:
        await cb_or_msg.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "account_menu")
async def account_menu_callback(callback: CallbackQuery):
    await render_account_menu(callback, False)


@router.callback_query(F.data == "link_account")
async def link_account_start(callback: CallbackQuery, state: FSMContext):
    if not TELETHON_API_ID or not TELETHON_API_HASH:
        await callback.answer(
            "❌ TELETHON_API_ID/HASH не заданы в config.py", show_alert=True
        )
        return

    doc = await users.find_one({"user_id": callback.from_user.id})
    balance = int(doc.get("balance", 0)) if doc else 0
    if balance < 20:
        await callback.answer(ERROR_LOW_BOT_BALANCE, show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        ACCOUNT_CONSENT, reply_markup=get_account_consent_keyboard()
    )


@router.callback_query(F.data == "account_consent_accept")
async def account_consent_accept(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LinkState.phone)
    await callback.message.edit_text(ACCOUNT_ENTER_PHONE, reply_markup=None)


@router.message(LinkState.phone)
async def handle_phone_input(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not (
        phone.startswith("+") and phone[1:].replace(" ", "").replace("-", "").isdigit()
    ):
        await message.answer(ERROR_INVALID_PHONE)
        return
    try:
        session_string, phone_code_hash = await start_login_send_code(phone)
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки кода: {e}")
        return
    await state.update_data(
        phone=phone, sess=session_string, hash=phone_code_hash, code=""
    )
    await state.set_state(LinkState.code)
    await message.answer(ACCOUNT_ENTER_CODE, reply_markup=build_code_keypad(""))


async def _update_code_kb(callback: CallbackQuery, state: FSMContext, new_code: str):
    await state.update_data(code=new_code)
    try:
        await callback.message.edit_reply_markup(
            reply_markup=build_code_keypad(new_code)
        )
    except Exception:

        pass


@router.callback_query(LinkState.code, F.data.startswith("code_digit_"))
async def code_digit(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    code = data.get("code", "")
    digit = callback.data.split("_")[-1]
    if len(code) < 6:
        code += digit
    await _update_code_kb(callback, state, code)
    await callback.answer()


@router.callback_query(LinkState.code, F.data == "code_back")
async def code_back(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    code = data.get("code", "")
    code = code[:-1]
    await _update_code_kb(callback, state, code)
    await callback.answer()


@router.callback_query(LinkState.code, F.data == "code_submit")
async def code_submit(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    code = data.get("code", "")
    session_string = data.get("sess")
    phone_code_hash = data.get("hash")
    phone = data.get("phone")
    if not code:
        await callback.answer(ERROR_CODE_EMPTY, show_alert=True)
        return
    try:
        result = await complete_login_with_code(
            session_string, phone, code, phone_code_hash
        )
        status = result.get("status")
        sess = result.get("session", session_string)
        if status == "ok":
            await save_session(callback.from_user.id, sess)
            await state.clear()

            await callback.answer("✅ Аккаунт привязан")
            await render_account_menu(callback, False)
            return
        elif status == "password":
            await state.update_data(sess=sess)
            await state.set_state(LinkState.password)
            await callback.message.edit_text(ACCOUNT_ENTER_PASSWORD)
            return
    except Exception as e:
        await callback.answer(ERROR_LOGIN_FAILED, show_alert=True)
        return


@router.message(LinkState.password)
async def handle_password(message: Message, state: FSMContext):
    data = await state.get_data()
    sess = data.get("sess")
    pwd = message.text
    try:
        final_session = await complete_login_with_password(sess, pwd)
        await save_session(message.from_user.id, final_session)
        await state.clear()

        await message.reply("✅ Аккаунт привязан")

        class _Shim:
            def __init__(self, msg):
                self.from_user = msg.from_user
                self.message = msg

        await render_account_menu(_Shim(message), True)
    except Exception as e:

        await message.reply(ERROR_LOGIN_FAILED)


@router.callback_query(F.data == "unlink_account")
async def unlink_account(callback: CallbackQuery):
    await clear_session(callback.from_user.id)
    await callback.answer("Отключено")
    await callback.message.edit_text(ACCOUNT_UNLINKED)
    await render_account_menu(callback, False)


@router.callback_query(F.data == "telethon_test")
async def telethon_test(callback: CallbackQuery):

    doc = await get_account_doc(callback.from_user.id)
    if not doc or not doc.get("session_string"):
        await callback.answer(ERROR_NOT_CONNECTED, show_alert=True)
        return
    try:
        stars, premium = await check_stars_balance(callback.from_user.id)
        premium_line = "👑 <b>Premium:</b> Да" if premium else "👑 <b>Premium:</b> Нет"
        warning = ACCOUNT_TEST_WARNING
        await callback.message.edit_text(
            ACCOUNT_TEST_RESULT.format(
                stars=stars or 0, premium=premium_line, warning=warning
            ),
            reply_markup=get_account_menu_keyboard(
                True,
                bool(doc.get("use_personal_buy", False)),
                bool(doc.get("allow_premium_buy", False)) if premium else False,
                bool(doc.get("only_personal_buy", False)),
            ),
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка запроса: {e}", show_alert=True)


@router.callback_query(F.data == "toggle_personal_buy")
async def toggle_personal_buy(callback: CallbackQuery):
    doc = await get_account_doc(callback.from_user.id)
    if not doc or not doc.get("session_string"):
        await callback.answer(ERROR_NOT_CONNECTED, show_alert=True)
        return
    new_val = not bool(doc.get("use_personal_buy", False))
    await set_toggle(callback.from_user.id, "use_personal_buy", new_val)
    await account_menu_callback(callback)


@router.callback_query(F.data == "toggle_only_personal_buy")
async def toggle_only_personal_buy(callback: CallbackQuery):
    doc = await get_account_doc(callback.from_user.id)
    if not doc or not doc.get("session_string"):
        await callback.answer(ERROR_NOT_CONNECTED, show_alert=True)
        return
    new_val = not bool(doc.get("only_personal_buy", False))
    await set_toggle(callback.from_user.id, "only_personal_buy", new_val)
    await account_menu_callback(callback)


@router.callback_query(F.data == "toggle_premium_buy")
async def toggle_premium_buy(callback: CallbackQuery):
    doc = await get_account_doc(callback.from_user.id)
    if not doc or not doc.get("session_string"):
        await callback.answer(ERROR_NOT_CONNECTED, show_alert=True)
        return

    try:
        _, has_premium = await check_stars_balance(callback.from_user.id)
    except Exception:
        has_premium = False
    if not has_premium:
        await callback.answer("❌ Требуется Telegram Premium", show_alert=True)
        return
    new_val = not bool(doc.get("allow_premium_buy", False))
    await set_toggle(callback.from_user.id, "allow_premium_buy", new_val)
    await account_menu_callback(callback)
