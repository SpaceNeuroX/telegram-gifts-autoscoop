from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from bot.database import users, transactions
from bot.utils.texts import *
from bot.utils.helpers import format_date, get_status_emoji, get_type_emoji
from bot.keyboards.balance import get_balance_keyboard, get_refund_keyboard
from bot import config

router = Router()


@router.message(Command("balance"))
async def balance_command(message: Message):
    await show_balance(message, True)


@router.callback_query(F.data == "balance_menu")
async def balance_menu_callback(callback: CallbackQuery):
    await show_balance(callback, False)


@router.callback_query(F.data == "refresh_balance")
async def refresh_balance_callback(callback: CallbackQuery):
    await callback.answer("🔄 Обновляю...")
    await show_balance(callback, False)


async def show_balance(obj, is_message):
    user = await users.find_one({"user_id": obj.from_user.id})
    balance = user.get("balance", 0) if user else 0

    txs = (
        await transactions.find({"user_id": obj.from_user.id})
        .sort("created_at", -1)
        .limit(10)
        .to_list(10)
    )

    if not txs:
        text = BALANCE_EMPTY.format(balance=balance)
        text += f"\n\n{REFUND_MANUAL_NOTE}"
        keyboard = get_balance_keyboard()
    else:
        text = BALANCE_TEXT.format(balance=balance)

        displayed_txs = []
        skip_next = set()

        for i, tx in enumerate(txs):
            if tx["transaction_id"] in skip_next:
                continue

            if tx["type"] == "deposit":
                meta = tx.get("meta", {})
                if "gross" in meta and "commission" in meta:

                    displayed_txs.append(
                        {
                            "tx": tx,
                            "display_amount": meta["gross"],
                            "net_amount": tx["amount"],
                            "commission": meta["commission"],
                            "has_commission": True,
                        }
                    )
                else:
                    displayed_txs.append(
                        {
                            "tx": tx,
                            "display_amount": tx["amount"],
                            "has_commission": False,
                        }
                    )
            else:

                if tx["type"] in ("commission_fee", "referral_bonus_out") and tx.get(
                    "meta", {}
                ).get("source_tx"):

                    source_tx_id = tx["meta"]["source_tx"]
                    source_exists = any(
                        t["transaction_id"] == source_tx_id for t in txs
                    )
                    if source_exists:

                        continue

                displayed_txs.append(
                    {"tx": tx, "display_amount": tx["amount"], "has_commission": False}
                )

        for i, tx_data in enumerate(displayed_txs, 1):
            tx = tx_data["tx"]
            text += TRANSACTION_ITEM.format(
                num=i,
                status=get_status_emoji(tx["status"]),
                type_emoji=get_type_emoji(tx["type"]),
                amount=tx_data["display_amount"],
                date=format_date(tx["created_at"]),
                tx_id=tx["transaction_id"][:8],
            )

            meta = tx.get("meta") or {}
            extra_lines = []

            if tx_data.get("has_commission"):
                extra_lines.append(
                    f"💎 Зачислено: <code>{tx_data['net_amount']:,} ⭐</code>"
                )
                extra_lines.append(
                    f"💸 Комиссия: <code>{tx_data['commission']:,} ⭐</code> (2%)"
                )

            if tx["type"] in ("transfer_out", "deposit_to_other") and meta.get(
                "recipient_id"
            ):
                extra_lines.append(f"↪️ Кому: <code>{meta['recipient_id']}</code>")
            if tx["type"] in (
                "transfer_in",
                "deposit_from_user",
                "referral_bonus_in",
            ) and meta.get("from_user_id"):
                extra_lines.append(f"↩️ От кого: <code>{meta['from_user_id']}</code>")

            if extra_lines:
                text += "\n" + "\n".join(extra_lines) + "\n"

        text += f"\n{REFUND_MANUAL_NOTE}"
        keyboard = get_balance_keyboard([tx_data["tx"] for tx_data in displayed_txs])

    if is_message:
        await obj.answer(text, reply_markup=keyboard)
    else:
        await obj.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("refund_"))
async def refund_callback(callback: CallbackQuery):
    tx_id = callback.data.split("_", 1)[1]

    tx = await transactions.find_one({"transaction_id": tx_id})

    user = await users.find_one({"user_id": callback.from_user.id})
    if user and user.get("refund_locked"):
        await callback.answer(
            "❌ Возврат недоступен после переводов/реферальных выплат", show_alert=True
        )
        return

    if not tx or tx["user_id"] != callback.from_user.id or tx["status"] != "completed":
        await callback.answer("❌ Транзакция недоступна для возврата")
        return

    await callback.message.edit_text(
        REFUND_CONFIRM.format(
            amount=tx["amount"], date=format_date(tx["created_at"]), tx_id=tx_id[:8]
        ),
        reply_markup=get_refund_keyboard(tx_id),
    )


@router.callback_query(F.data.startswith("confirm_refund_"))
async def confirm_refund_callback(callback: CallbackQuery, bot: Bot):
    tx_id = callback.data.split("_", 2)[2]

    tx = await transactions.find_one({"transaction_id": tx_id})

    user = await users.find_one({"user_id": callback.from_user.id})
    if user and user.get("refund_locked"):
        await callback.answer(
            "❌ Возврат недоступен после переводов/реферальных выплат", show_alert=True
        )
        return

    if not tx or tx["user_id"] != callback.from_user.id or tx["status"] != "completed":
        await callback.answer("❌ Ошибка обработки")
        return

    user = await users.find_one({"user_id": callback.from_user.id})
    if user["balance"] < tx["amount"]:
        await callback.answer(ERROR_INSUFFICIENT, show_alert=True)
        return

    try:
        await bot.refund_star_payment(
            user_id=callback.from_user.id, telegram_payment_charge_id=tx["charge_id"]
        )

        await users.update_one(
            {"user_id": callback.from_user.id}, {"$inc": {"balance": -tx["amount"]}}
        )

        await transactions.update_one(
            {"transaction_id": tx_id}, {"$set": {"status": "refunded"}}
        )

        await callback.message.edit_text(
            SUCCESS_REFUND.format(amount=tx["amount"], tx_id=tx_id[:8])
        )

    except Exception:
        await callback.answer(ERROR_REFUND_FAILED, show_alert=True)


@router.message(Command("refund"))
async def force_refund_command(message: Message, bot: Bot):

    owner_id = 7554417587
    if not owner_id or message.from_user.id != owner_id:
        return

    parts = (message.text or "").strip().split(maxsplit=4)
    if len(parts) < 4:
        await message.answer("Использование: /refund user_id charge_id amount")
        return

    try:
        user_id = int(parts[1])
        charge_id = parts[2]
        amount = float(parts[3].replace(",", "."))
    except Exception:
        await message.answer(
            "❌ Неверные параметры. Пример: /refund 123456789 abcdef123 100.50"
        )
        return

    try:
        await bot.refund_star_payment(
            user_id=user_id, telegram_payment_charge_id=charge_id
        )

        await users.update_one({"user_id": user_id}, {"$inc": {"balance": -amount}})

        await message.answer(
            f"✅ Форс-возврат выполнен. user_id: <code>{user_id}</code>, charge: <code>{charge_id}</code>, сумма: {amount} ⭐"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка форс-возврата: {e}")
