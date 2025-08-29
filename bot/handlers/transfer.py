from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime
from bot.database import users, transactions
from bot.states import TransferState
from bot.utils.helpers import generate_transaction_id
from bot.keyboards.transfer import (
    get_transfer_cancel_keyboard,
    get_transfer_confirm_keyboard,
)
from bot.keyboards.main_menu import get_main_menu

router = Router()


@router.message(Command("transfer"))
async def transfer_start(message: Message, state: FSMContext):
    await state.set_state(TransferState.recipient)
    await message.answer(
        "👤 Введите ID получателя (число).", reply_markup=get_transfer_cancel_keyboard()
    )


@router.callback_query(F.data == "transfer_menu")
async def transfer_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TransferState.recipient)
    await callback.message.edit_text(
        "👤 Введите ID получателя (число).", reply_markup=get_transfer_cancel_keyboard()
    )


@router.callback_query(F.data == "cancel_transfer")
async def cancel_transfer(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "✅ Действие отменено", reply_markup=get_main_menu()
    )


@router.message(TransferState.recipient)
async def transfer_recipient(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(
            "❌ Укажите числовой ID пользователя",
            reply_markup=get_transfer_cancel_keyboard(),
        )
        return
    recipient_id = int(text)
    if recipient_id == message.from_user.id:
        await message.answer(
            "❌ Нельзя переводить самому себе",
            reply_markup=get_transfer_cancel_keyboard(),
        )
        return
    rec = await users.find_one({"user_id": recipient_id})
    if not rec:
        await message.answer(
            "❌ Пользователь с таким ID не найден в боте",
            reply_markup=get_transfer_cancel_keyboard(),
        )
        return
    await state.update_data(recipient_id=recipient_id)
    await state.set_state(TransferState.amount)

    sender = await users.find_one({"user_id": message.from_user.id})
    balance = sender.get("balance", 0) if sender else 0
    await message.answer(
        f"💫 Введите сумму перевода в звёздах\n\n"
        f"Доступно: <b>{balance:,} ⭐</b>\n"
        f"Только <b>целые</b> значения. Комиссия <b>не взимается</b>.",
        reply_markup=get_transfer_cancel_keyboard(),
    )


@router.message(TransferState.amount)
async def transfer_amount(message: Message, state: FSMContext):
    try:
        amount = int((message.text or "").strip())
        if amount <= 0:
            raise ValueError
    except Exception:
        await message.answer(
            "❌ Введите положительное целое число (комиссия не взимается)",
            reply_markup=get_transfer_cancel_keyboard(),
        )
        return

    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    if not recipient_id:
        await state.clear()
        await message.answer(
            "⚠️ Сессия перевода сброшена. Начните заново через меню.",
            reply_markup=get_main_menu(),
        )
        return

    sender = await users.find_one({"user_id": message.from_user.id})
    if not sender or sender.get("balance", 0) < amount:
        await message.answer(
            "❌ Недостаточно средств на балансе",
            reply_markup=get_transfer_cancel_keyboard(),
        )
        return

    await message.answer(
        f"💰 Подтвердите перевод:\n\n"
        f"👤 Получатель: <code>{recipient_id}</code>\n"
        f"💎 Сумма: <b>{amount:,} ⭐</b>\n\n"
        f"⚠️ <i>После подтверждения возврат будет невозможен</i>",
        reply_markup=get_transfer_confirm_keyboard(recipient_id, amount),
    )


@router.callback_query(F.data.startswith("confirm_transfer_"))
async def confirm_transfer(callback: CallbackQuery, state: FSMContext):
    data_parts = callback.data.split("_")
    if len(data_parts) != 4:
        await callback.answer("❌ Ошибка данных")
        return

    recipient_id = int(data_parts[2])
    amount = int(data_parts[3])

    state_data = await state.get_data()
    if state_data.get("recipient_id") != recipient_id:
        await callback.answer("❌ Данные сессии не совпадают")
        return

    sender = await users.find_one({"user_id": callback.from_user.id})
    if not sender or sender.get("balance", 0) < amount:
        await callback.message.edit_text(
            "❌ Недостаточно средств на балансе", reply_markup=get_main_menu()
        )
        return

    await users.update_one(
        {"user_id": callback.from_user.id},
        {"$inc": {"balance": -amount}, "$set": {"refund_locked": True}},
    )
    await users.update_one({"user_id": recipient_id}, {"$inc": {"balance": amount}})

    out_tx = generate_transaction_id()
    in_tx = generate_transaction_id()
    now = datetime.utcnow()
    await transactions.insert_many(
        [
            {
                "transaction_id": out_tx,
                "user_id": callback.from_user.id,
                "type": "transfer_out",
                "amount": amount,
                "created_at": now,
                "status": "completed",
                "meta": {"recipient_id": recipient_id},
            },
            {
                "transaction_id": in_tx,
                "user_id": recipient_id,
                "type": "transfer_in",
                "amount": amount,
                "created_at": now,
                "status": "completed",
                "meta": {"from_user_id": callback.from_user.id},
            },
        ]
    )

    try:
        rec_doc = await users.find_one({"user_id": recipient_id})
        rec_balance = rec_doc.get("balance", 0) if rec_doc else 0
        await callback.bot.send_message(
            recipient_id,
            f"📥 Вам перевели {amount:,} ⭐ от ID {callback.from_user.id}. Баланс: {rec_balance:,} ⭐",
        )
    except Exception:
        pass

    await state.clear()
    snd_doc = await users.find_one({"user_id": callback.from_user.id})
    snd_balance = snd_doc.get("balance", 0) if snd_doc else 0
    await callback.message.edit_text(
        f"✅ Перевод {amount:,} ⭐ пользователю {recipient_id} выполнен.\n\n"
        f"💰 Ваш баланс: <b>{snd_balance:,} ⭐</b>\n\n"
        f"⚠️ <i>Возврат средств больше недоступен</i>",
        reply_markup=get_main_menu(),
    )
