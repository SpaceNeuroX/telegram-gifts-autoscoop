from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.fsm.context import FSMContext
from datetime import datetime
from bot.database import users, transactions
from bot import config
from bot.config import TAKE_COMMISSION
from bot.states import DepositState, DepositToState
from bot.utils.texts import *
from bot.utils.helpers import generate_transaction_id
from bot.keyboards.deposit import (
    get_deposit_keyboard,
    get_custom_deposit_keyboard,
    get_cancel_deposit_to_keyboard,
)
from bot.keyboards.main_menu import get_main_menu
from decimal import Decimal, ROUND_HALF_UP

router = Router()


@router.callback_query(F.data == "deposit_menu")
async def deposit_menu_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        DEPOSIT_INSTRUCTION, reply_markup=get_deposit_keyboard()
    )


@router.callback_query(F.data == "deposit_custom")
async def custom_deposit_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DepositState.amount)
    await callback.message.edit_text(
        DEPOSIT_INSTRUCTION, reply_markup=get_custom_deposit_keyboard()
    )


@router.callback_query(F.data.startswith("deposit_"))
async def preset_deposit_callback(callback: CallbackQuery, bot: Bot):
    data = callback.data.split("_")
    if len(data) == 2 and data[1].isdigit():
        amount = int(data[1])
        await send_invoice(bot, callback.from_user.id, amount)
        await callback.answer(f"💳 Создан счёт на {amount:,} ⭐")


@router.message(DepositState.amount)
async def custom_amount_handler(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = int(message.text.strip())
        if 1 <= amount <= 100000:
            await send_invoice(bot, message.from_user.id, amount)
            await state.clear()
        else:
            await message.answer(DEPOSIT_ERROR)
    except ValueError:
        await message.answer(DEPOSIT_ERROR)


async def send_invoice(bot: Bot, user_id: int, amount: int):
    await bot.send_invoice(
        chat_id=user_id,
        title="🌟 Пополнение баланса",
        description=f"Пополнение на {amount:,} звёзд",
        payload=f"deposit_{user_id}_{amount}",
        currency="XTR",
        prices=[LabeledPrice(label="⭐", amount=amount)],
        provider_token="",
    )


async def send_invoice_to_other(
    bot: Bot, payer_id: int, recipient_id: int, amount: int
):
    await bot.send_invoice(
        chat_id=payer_id,
        title="🌟 Пополнение другого пользователя",
        description=f"Пополнение ID {recipient_id} на {amount:,} звёзд",
        payload=f"depositto_{payer_id}_{recipient_id}_{amount}",
        currency="XTR",
        prices=[LabeledPrice(label="⭐", amount=amount)],
        provider_token="",
    )


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.text == "/deposit_to")
async def deposit_to_start(message: Message, state: FSMContext):
    await state.set_state(DepositToState.recipient)
    await message.answer(
        "👤 Введите ID получателя (число).",
        reply_markup=get_cancel_deposit_to_keyboard(),
    )


@router.callback_query(F.data == "depositTo_menu")
async def deposit_to_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DepositToState.recipient)
    await callback.message.edit_text(
        "👤 Введите ID получателя (число).",
        reply_markup=get_cancel_deposit_to_keyboard(),
    )


@router.message(DepositToState.recipient)
async def deposit_to_recipient(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(
            "❌ Укажите числовой ID пользователя",
            reply_markup=get_cancel_deposit_to_keyboard(),
        )
        return
    recipient_id = int(text)
    if recipient_id == message.from_user.id:
        await message.answer(
            "❌ Нельзя пополнять самого себя через эту функцию. Используйте обычное пополнение."
        )
        return
    rec = await users.find_one({"user_id": recipient_id})
    if not rec:
        await message.answer("❌ Пользователь с таким ID не найден в боте")
        return
    await state.update_data(recipient_id=recipient_id)
    await state.set_state(DepositToState.amount)
    await message.answer(
        "💫 Введите сумму пополнения в звёздах (только целые значения)",
        reply_markup=get_cancel_deposit_to_keyboard(),
    )


@router.message(DepositToState.amount)
async def deposit_to_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = int((message.text or "").strip())
        if amount < 1 or amount > 100000:
            raise ValueError
    except Exception:
        await message.answer(
            "❌ Введите целое число от 1 до 100000",
            reply_markup=get_cancel_deposit_to_keyboard(),
        )
        return

    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    if not recipient_id:
        await state.clear()
        await message.answer(
            "⚠️ Сессия пополнения сброшена. Начните заново: /deposit_to"
        )
        return

    await send_invoice_to_other(bot, message.from_user.id, recipient_id, amount)
    await state.clear()
    await message.answer(
        f"🧾 Создан счёт на пополнение ID {recipient_id} на {amount:,} ⭐",
        reply_markup=get_main_menu(),
    )


@router.callback_query(F.data == "cancel_deposit_to")
async def cancel_deposit_to(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Отменено.", reply_markup=get_main_menu())


@router.message(F.successful_payment)
async def payment_success_handler(message: Message):
    payment = message.successful_payment
    payload_parts = payment.invoice_payload.split("_")

    if payload_parts[0] == "deposit":
        user_id = int(payload_parts[1])
        amount = int(payload_parts[2])
        tx_id = generate_transaction_id()

        gross = Decimal(str(amount))
        if TAKE_COMMISSION:
            commission_dec = (gross * Decimal("0.02")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            commission_dec = Decimal("0.00")
        net_dec = (gross - commission_dec).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        await transactions.insert_one(
            {
                "transaction_id": tx_id,
                "user_id": user_id,
                "type": "deposit",
                "amount": float(net_dec),
                "charge_id": payment.telegram_payment_charge_id,
                "created_at": datetime.utcnow(),
                "status": "completed",
                "meta": {"gross": float(gross), "commission": float(commission_dec)},
            }
        )

        await users.update_one(
            {"user_id": user_id}, {"$inc": {"balance": float(net_dec)}}
        )

        user_doc = await users.find_one({"user_id": user_id})
        referrer_id = (
            user_doc.get("referred_by") if user_doc and TAKE_COMMISSION else None
        )
        if commission_dec > 0 and TAKE_COMMISSION:
            recipient_for_commission = None
            commission_type_income = None
            meta_map = {"source_tx": tx_id}
            if referrer_id and await users.find_one({"user_id": referrer_id}):
                recipient_for_commission = referrer_id
                commission_type_income = "referral_bonus_in"
                meta_map.update({"from_user_id": user_id})

                await users.update_one(
                    {"user_id": user_id}, {"$set": {"refund_locked": True}}
                )

                out_tx = generate_transaction_id()
                await transactions.insert_one(
                    {
                        "transaction_id": out_tx,
                        "user_id": user_id,
                        "type": "referral_bonus_out",
                        "amount": float(commission_dec),
                        "created_at": datetime.utcnow(),
                        "status": "completed",
                        "meta": {"referrer_id": referrer_id, "source_tx": tx_id},
                    }
                )
                try:
                    await message.bot.send_message(
                        referrer_id,
                        f"🎉 Вам зачислен реферальный бонус {commission_dec} ⭐ от пополнения пользователя ID {user_id}",
                    )
                except Exception:
                    pass
            elif getattr(config, "DEV_USER_ID", None):
                recipient_for_commission = int(getattr(config, "DEV_USER_ID"))
                commission_type_income = "commission_income"
                meta_map.update({"from_user_id": user_id})

                out_tx = generate_transaction_id()
                await transactions.insert_one(
                    {
                        "transaction_id": out_tx,
                        "user_id": user_id,
                        "type": "commission_fee",
                        "amount": float(commission_dec),
                        "created_at": datetime.utcnow(),
                        "status": "completed",
                        "meta": {
                            "developer_id": recipient_for_commission,
                            "source_tx": tx_id,
                        },
                    }
                )

            if recipient_for_commission:
                await users.update_one(
                    {"user_id": recipient_for_commission},
                    {"$inc": {"balance": float(commission_dec)}},
                )
                in_tx = generate_transaction_id()
                await transactions.insert_one(
                    {
                        "transaction_id": in_tx,
                        "user_id": recipient_for_commission,
                        "type": commission_type_income,
                        "amount": float(commission_dec),
                        "created_at": datetime.utcnow(),
                        "status": "completed",
                        "meta": meta_map,
                    }
                )

        user = await users.find_one({"user_id": user_id})
        balance = user.get("balance", 0)

        if TAKE_COMMISSION and commission_dec > 0:
            commission_note = f"\n💸 Комиссия: {commission_dec} ⭐ (2%)"
        else:
            commission_note = ""
        await message.answer(
            SUCCESS_DEPOSIT.format(amount=float(net_dec), balance=balance, tx_id=tx_id)
            + commission_note
        )

    elif payload_parts[0] == "depositto":
        payer_id = int(payload_parts[1])
        recipient_id = int(payload_parts[2])
        amount = int(payload_parts[3])
        tx_id = generate_transaction_id()

        recipient = await users.find_one({"user_id": recipient_id})
        if not recipient:
            await message.answer(
                "❌ Получатель не найден в боте. Оплата зачислена вам, обратитесь в поддержку."
            )

            await users.update_one({"user_id": payer_id}, {"$inc": {"balance": amount}})
            await transactions.insert_one(
                {
                    "transaction_id": tx_id,
                    "user_id": payer_id,
                    "type": "deposit",
                    "amount": amount,
                    "charge_id": payment.telegram_payment_charge_id,
                    "created_at": datetime.utcnow(),
                    "status": "completed",
                }
            )
            return

        await transactions.insert_one(
            {
                "transaction_id": tx_id,
                "user_id": payer_id,
                "type": "deposit_to_other",
                "amount": amount,
                "charge_id": payment.telegram_payment_charge_id,
                "created_at": datetime.utcnow(),
                "status": "completed",
                "meta": {"recipient_id": recipient_id},
            }
        )

        gross = Decimal(str(amount))
        if TAKE_COMMISSION:
            commission_dec = (gross * Decimal("0.02")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            commission_dec = Decimal("0.00")
        net_dec = (gross - commission_dec).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        await users.update_one(
            {"user_id": recipient_id}, {"$inc": {"balance": float(net_dec)}}
        )

        recipient_tx_id = generate_transaction_id()
        await transactions.insert_one(
            {
                "transaction_id": recipient_tx_id,
                "user_id": recipient_id,
                "type": "deposit_from_user",
                "amount": float(net_dec),
                "created_at": datetime.utcnow(),
                "status": "completed",
                "meta": {
                    "from_user_id": payer_id,
                    "source_tx": tx_id,
                    "gross": float(gross),
                    "commission": float(commission_dec),
                },
            }
        )

        if commission_dec > 0 and TAKE_COMMISSION:
            payer_doc = await users.find_one({"user_id": payer_id})
            referrer_id = payer_doc.get("referred_by") if payer_doc else None
            recipient_for_commission = None
            commission_type_income = None
            meta_map = {
                "from_user_id": payer_id,
                "recipient_id": recipient_id,
                "source_tx": tx_id,
            }
            if referrer_id and await users.find_one({"user_id": referrer_id}):
                recipient_for_commission = referrer_id
                commission_type_income = "referral_bonus_in"

                await users.update_one(
                    {"user_id": payer_id}, {"$set": {"refund_locked": True}}
                )

                out_tx = generate_transaction_id()
                await transactions.insert_one(
                    {
                        "transaction_id": out_tx,
                        "user_id": payer_id,
                        "type": "referral_bonus_out",
                        "amount": float(commission_dec),
                        "created_at": datetime.utcnow(),
                        "status": "completed",
                        "meta": {"referrer_id": referrer_id, "source_tx": tx_id},
                    }
                )
                try:
                    await message.bot.send_message(
                        referrer_id,
                        f"🎉 Вам зачислен реферальный бонус {commission_dec} ⭐ от пополнения для пользователя ID {recipient_id}",
                    )
                except Exception:
                    pass
            elif getattr(config, "DEV_USER_ID", None):
                recipient_for_commission = int(getattr(config, "DEV_USER_ID"))
                commission_type_income = "commission_income"

                out_tx = generate_transaction_id()
                await transactions.insert_one(
                    {
                        "transaction_id": out_tx,
                        "user_id": payer_id,
                        "type": "commission_fee",
                        "amount": float(commission_dec),
                        "created_at": datetime.utcnow(),
                        "status": "completed",
                        "meta": {
                            "developer_id": recipient_for_commission,
                            "source_tx": tx_id,
                        },
                    }
                )
            if recipient_for_commission:
                await users.update_one(
                    {"user_id": recipient_for_commission},
                    {"$inc": {"balance": float(commission_dec)}},
                )
                in_tx = generate_transaction_id()
                await transactions.insert_one(
                    {
                        "transaction_id": in_tx,
                        "user_id": recipient_for_commission,
                        "type": commission_type_income,
                        "amount": float(commission_dec),
                        "created_at": datetime.utcnow(),
                        "status": "completed",
                        "meta": meta_map,
                    }
                )

        await users.update_one({"user_id": payer_id}, {"$set": {"refund_locked": True}})

        rec_doc = await users.find_one({"user_id": recipient_id})
        rec_balance = rec_doc.get("balance", 0) if rec_doc else 0
        try:
            await message.bot.send_message(
                recipient_id,
                f"💰 Ваш баланс пополнен на {net_dec} ⭐ пользователем ID {payer_id}. Текущий баланс: {rec_balance:,} ⭐",
            )
        except Exception:
            pass
        if TAKE_COMMISSION and commission_dec > 0:
            commission_text = f" (удержана комиссия {commission_dec} ⭐)"
        else:
            commission_text = ""
        await message.answer(
            f"✅ Вы пополнили баланс пользователя {recipient_id} на {net_dec} ⭐{commission_text}. Возврат для этой операции недоступен."
        )
