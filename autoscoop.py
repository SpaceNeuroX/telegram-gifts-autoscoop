import asyncio
import time
from aiogram import Bot
from star_gifts_data import StarGiftData
from bot.config import BOT_TOKEN
from bot.database import (
    users as users_collection,
    orders as orders_collection,
    user_orders as user_orders_collection,
)
from bot.utils.telethon_client import (
    send_gift_via_personal,
    get_account_doc,
    check_stars_balance,
)
import logging
import config
import constants
import utils
from autoscoop_texts import T

logger = utils.get_logger(
    name=config.SESSION_NAME,
    log_filepath=constants.LOG_FILEPATH,
    console_log_level=config.CONSOLE_LOG_LEVEL,
    file_log_level=config.FILE_LOG_LEVEL,
)


async def send_notification(user_bot: Bot, user_id: int, message: str):
    try:
        await user_bot.send_message(user_id, message, parse_mode="HTML")
    except Exception:
        pass


async def process_new_gift_for_autoscoop(star_gift: StarGiftData):
    all_users = users_collection.find({})

    async for user in all_users:
        user_id = user["user_id"]
        user_bot = Bot(token=BOT_TOKEN)
        current_balance = int(user.get("balance", 0))

        try:
            await send_notification(
                user_bot,
                user_id,
                T.new_gift(
                    id=star_gift.id,
                    price=star_gift.price,
                    total_amount=star_gift.total_amount,
                    is_premium=getattr(star_gift, "require_premium", False),
                ),
            )

            if current_balance < 1:
                await send_notification(
                    user_bot,
                    user_id,
                    T.insufficient_balance_notification(current_balance)
                )
                continue

            active_orders_cursor = user_orders_collection.find(
                {
                    "user_id": user_id,
                    "enabled": True,
                }
            )
            active_orders = await active_orders_cursor.to_list(100)

            if not active_orders:
                await send_notification(
                    user_bot,
                    user_id,
                    T.no_active_orders()
                )
                continue

            active_orders.sort(key=lambda order: order.get("supply", {}).get("min", 1))

            user_account_doc = await get_account_doc(user_id)
            total_success = 0
            processed_orders = 0

            for order in active_orders:
                current_user = await users_collection.find_one({"user_id": user_id})
                current_balance = int(current_user.get("balance", 0))

                if current_balance < star_gift.price:
                    await send_notification(
                        user_bot,
                        user_id,
                        T.insufficient_balance_for_order(
                            order_name=order.get("name", "Ордер"),
                            balance=current_balance,
                            price=star_gift.price
                        )
                    )
                    break

                pr = order.get("price", {})
                sr = order.get("supply", {})
                min_price = int(pr.get("min", 1))
                max_price = int(pr.get("max", 100000))
                min_supply = int(sr.get("min", 1))
                max_supply = int(sr.get("max", 999999))

                if not (min_price <= star_gift.price <= max_price):
                    await send_notification(
                        user_bot,
                        user_id,
                        T.price_not_match_order(
                            order_name=order.get("name", "Ордер"),
                            gift_price=star_gift.price,
                            min_price=min_price,
                            max_price=max_price
                        )
                    )
                    continue

                gift_supply = star_gift.total_amount
                if not (min_supply <= gift_supply <= max_supply):
                    await send_notification(
                        user_bot,
                        user_id,
                        T.supply_not_match_order(
                            order_name=order.get("name", "Ордер"),
                            gift_supply=gift_supply,
                            min_supply=min_supply,
                            max_supply=max_supply
                        )
                    )
                    continue

                current_order = await user_orders_collection.find_one(
                    {"_id": order.get("_id")}
                )
                order_budget = int(current_order.get("budget", 10000))
                order_spent = int(current_order.get("spent", 0))
                order_remaining_budget = order_budget - order_spent

                if order_remaining_budget <= 0:
                    await send_notification(
                        user_bot,
                        user_id,
                        T.budget_exceeded(
                            order_name=order.get("name", "Ордер"),
                            spent=order_spent,
                            budget=order_budget
                        )
                    )
                    continue

                max_by_budget = order_remaining_budget // star_gift.price
                if max_by_budget <= 0:
                    await send_notification(
                        user_bot,
                        user_id,
                        T.insufficient_budget_for_single_gift(
                            order_name=order.get("name", "Ордер"),
                            remaining_budget=order_remaining_budget,
                            price=star_gift.price
                        )
                    )
                    continue

                remaining_to_buy = max_by_budget
                if (
                    star_gift.user_limited is not None
                    and remaining_to_buy > star_gift.user_limited
                ):
                    remaining_to_buy = star_gift.user_limited

                affordable = current_balance // star_gift.price
                remaining_to_buy = min(remaining_to_buy, affordable)
                if remaining_to_buy <= 0:
                    continue

                processed_orders += 1
                order_name = order.get("name", "Ордер")
                await send_notification(
                    user_bot,
                    user_id,
                    T.order_buying(
                        order_name=order_name, remaining_to_buy=remaining_to_buy
                    ),
                )

                successful_purchases = 0
                is_premium_gift = getattr(star_gift, "require_premium", False)

                if is_premium_gift:
                    await send_notification(user_bot, user_id, T.premium_check_start())

                    if not user_account_doc or not user_account_doc.get(
                        "session_string"
                    ):
                        await send_notification(user_bot, user_id, T.personal_not_set())
                        continue

                    allow_premium = bool(
                        user_account_doc.get("allow_premium_buy", False)
                    )
                    if not allow_premium:
                        await send_notification(user_bot, user_id, T.premium_disabled())
                        continue

                    try:
                        _, has_premium = await check_stars_balance(user_id)
                    except Exception:
                        has_premium = False

                    if not has_premium:
                        await send_notification(user_bot, user_id, T.no_premium())
                        continue

                    _ch = order.get("channel")
                    target = (
                        f"@{_ch}" if _ch and not str(_ch).startswith("@") else _ch
                    ) or None

                    await send_notification(
                        user_bot, user_id, T.premium_personal_buying(remaining_to_buy)
                    )

                    try:
                        succ, fail = await send_gift_via_personal(
                            user_id=user_id,
                            gift_id=star_gift.id,
                            count=remaining_to_buy,
                            target=target,
                            message_text="",
                            include_upgrade=False,
                            gift_price=star_gift.price,
                        )

                        if succ > 0:
                            total_spent = succ * star_gift.price

                            await users_collection.update_one(
                                {"user_id": user_id},
                                {"$inc": {"balance": -total_spent}},
                            )
                            await user_orders_collection.update_one(
                                {"_id": order.get("_id")},
                                {"$inc": {"spent": total_spent}},
                            )

                            successful_purchases += succ
                            total_success += succ

                            await send_notification(
                                user_bot,
                                user_id,
                                T.success_buy_personal(
                                    count=succ, gift_id=star_gift.id
                                ),
                            )
                        else:
                            await send_notification(
                                user_bot, user_id, T.fail_buy_personal(star_gift.id)
                            )

                    except Exception as e:
                        await send_notification(
                            user_bot, user_id, T.error_buy_personal(star_gift.id)
                        )

                    continue

                if user_account_doc and user_account_doc.get(
                    "only_personal_buy", False
                ):
                    if not user_account_doc.get("session_string"):
                        await send_notification(
                            user_bot, user_id, T.only_personal_no_account()
                        )
                        continue

                    _ch = order.get("channel")
                    target = (
                        f"@{_ch}" if _ch and not str(_ch).startswith("@") else _ch
                    ) or None

                    await send_notification(
                        user_bot, user_id, T.only_personal_buying(remaining_to_buy)
                    )

                    try:
                        succ, fail = await send_gift_via_personal(
                            user_id=user_id,
                            gift_id=star_gift.id,
                            count=remaining_to_buy,
                            target=target,
                            message_text="",
                            include_upgrade=False,
                            gift_price=star_gift.price,
                        )

                        if succ > 0:
                            total_spent = succ * star_gift.price

                            await users_collection.update_one(
                                {"user_id": user_id},
                                {"$inc": {"balance": -total_spent}},
                            )
                            await user_orders_collection.update_one(
                                {"_id": order.get("_id")},
                                {"$inc": {"spent": total_spent}},
                            )

                            successful_purchases += succ
                            total_success += succ

                            await send_notification(
                                user_bot,
                                user_id,
                                T.success_buy_personal_short(
                                    order_name=order.get("name", "Ордер")
                                ),
                            )

                    except Exception:
                        await send_notification(
                            user_bot, user_id, T.error_buy_personal(star_gift.id)
                        )
                    continue

                await send_notification(
                    user_bot,
                    user_id,
                    T.bot_api_order_start(
                        order_name=order.get("name", "Ордер"), count=remaining_to_buy
                    ),
                )

                for i in range(remaining_to_buy):
                    current_user = await users_collection.find_one({"user_id": user_id})
                    current_balance = int(current_user.get("balance", 0))

                    current_order = await user_orders_collection.find_one(
                        {"_id": order.get("_id")}
                    )
                    current_spent = int(current_order.get("spent", 0))
                    current_budget = int(current_order.get("budget", 10000))

                    if (
                        current_balance < star_gift.price
                        or current_spent >= current_budget
                    ):
                        await send_notification(
                            user_bot,
                            user_id,
                            T.insufficient_funds_budget(
                                balance=current_balance,
                                spent=current_spent,
                                budget=current_budget,
                            ),
                        )
                        break

                    order_id = f"{user_id}_{star_gift.id}_{int(time.time())}_{i}"

                    deducted = False
                    purchase_succeeded = False
                    try:
                        result = await users_collection.find_one_and_update(
                            {"user_id": user_id, "balance": {"$gte": star_gift.price}},
                            {"$inc": {"balance": -star_gift.price}},
                            return_document=True,
                        )

                        if not result:
                            await send_notification(
                                user_bot, user_id, T.insufficient_funds_changed()
                            )
                            break

                        deducted = True

                        await orders_collection.insert_one(
                            {
                                "order_id": order_id,
                                "user_id": user_id,
                                "gift_id": star_gift.id,
                                "price": star_gift.price,
                                "status": "pending",
                                "is_premium": is_premium_gift,
                                "purchase_method": "bot_api",
                                "created_at": time.time(),
                                "user_order_id": order.get("_id"),
                            }
                        )

                        await send_notification(
                            user_bot,
                            user_id,
                            T.order_attempt(
                                order_name=order.get("name", "Ордер"),
                                attempt_idx=i + 1,
                                total=remaining_to_buy,
                            ),
                        )

                        success = await send_gift_for_order(
                            user_bot,
                            user_id=user_id,
                            channel=order.get("channel"),
                            gift_id=star_gift.id,
                        )

                        if success:
                            await orders_collection.update_one(
                                {"order_id": order_id},
                                {"$set": {"status": "completed"}},
                            )
                            await user_orders_collection.update_one(
                                {"_id": order.get("_id")},
                                {"$inc": {"spent": star_gift.price}},
                            )

                            successful_purchases += 1
                            total_success += 1
                            purchase_succeeded = True

                            await send_notification(
                                user_bot,
                                user_id,
                                T.order_success(
                                    order_name=order.get("name", "Ордер"),
                                    i=i + 1,
                                    price=star_gift.price,
                                ),
                            )
                        else:
                            await send_notification(
                                user_bot,
                                user_id,
                                T.order_bot_api_failed_try_personal(
                                    order_name=order.get("name", "Ордер")
                                ),
                            )

                            if (
                                user_account_doc
                                and user_account_doc.get("session_string")
                                and bool(
                                    user_account_doc.get("use_personal_buy", False)
                                )
                            ):
                                _ch = order.get("channel")
                                target = (
                                    f"@{_ch}"
                                    if _ch and not str(_ch).startswith("@")
                                    else _ch
                                ) or None

                                try:
                                    succ, fail = await send_gift_via_personal(
                                        user_id=user_id,
                                        gift_id=star_gift.id,
                                        count=1,
                                        target=target,
                                        message_text="",
                                        include_upgrade=False,
                                        gift_price=star_gift.price,
                                    )

                                    if succ > 0:
                                        await orders_collection.update_one(
                                            {"order_id": order_id},
                                            {
                                                "$set": {
                                                    "status": "completed",
                                                    "purchase_method": "personal",
                                                }
                                            },
                                        )
                                        await user_orders_collection.update_one(
                                            {"_id": order.get("_id")},
                                            {"$inc": {"spent": star_gift.price}},
                                        )

                                        successful_purchases += 1
                                        total_success += 1
                                        purchase_succeeded = True

                                        await send_notification(
                                            user_bot,
                                            user_id,
                                            T.success_buy_personal_short(
                                                order_name=order.get("name", "Ордер")
                                            ),
                                        )
                                        continue
                                    else:
                                        await send_notification(
                                            user_bot,
                                            user_id,
                                            T.personal_failed(
                                                order_name=order.get("name", "Ордер")
                                            ),
                                        )
                                except Exception:
                                    await send_notification(
                                        user_bot, user_id, T.personal_account_error()
                                    )
                            else:
                                await send_notification(
                                    user_bot, user_id, T.personal_unavailable()
                                )

                            await orders_collection.update_one(
                                {"order_id": order_id}, {"$set": {"status": "failed"}}
                            )
                            break

                    except Exception as e:
                        await send_notification(
                            user_bot,
                            user_id,
                            T.critical_purchase_error(str(e)),
                        )
                        break
                    finally:
                        # Ensure refund if nothing was purchased in this attempt
                        if deducted and not purchase_succeeded:
                            await users_collection.update_one(
                                {"user_id": user_id}, {"$inc": {"balance": star_gift.price}}
                            )

                if successful_purchases > 0:
                    await send_notification(
                        user_bot,
                        user_id,
                        T.order_summary(
                            order_name=order.get("name", "Ордер"),
                            count=successful_purchases,
                        ),
                    )

            if processed_orders == 0:
                await send_notification(
                    user_bot,
                    user_id,
                    T.no_suitable_orders(gift_id=star_gift.id, price=star_gift.price)
                )

            current_user = await users_collection.find_one({"user_id": user_id})
            final_balance = int(current_user.get("balance", 0))

            await send_notification(
                user_bot,
                user_id,
                T.final_summary(
                    gift_id=star_gift.id,
                    total_success=total_success,
                    final_balance=final_balance,
                ),
            )

        finally:
            await user_bot.session.close()


async def send_gift_for_order(
    bot: Bot, user_id: int, channel: str | None, gift_id: int | str
):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            logger.info(
                f"Попытка {attempt+1}/{max_retries} отправки подарка {gift_id} (channel={channel}) пользователю {user_id}"
            )
            if channel:
                chat_id = f"@{channel}" if not str(channel).startswith("@") else channel
                logger.debug(
                    f"Отправляю подарок {gift_id} в канал {chat_id} через Bot API"
                )
                try:
                    await bot.send_gift(chat_id=chat_id, gift_id=str(gift_id))
                except Exception as e:
                    logger.warning(
                        f"Ошибка при отправке в канал {chat_id}: {e}. Пробую отправить пользователю {user_id}"
                    )
                    await bot.send_gift(user_id=user_id, gift_id=str(gift_id))
            else:
                logger.debug(
                    f"Отправляю подарок {gift_id} user_id={user_id} через Bot API"
                )
                await bot.send_gift(user_id=user_id, gift_id=str(gift_id))

            logger.info(f"Подарок {gift_id} успешно отправлен")
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Попытка {attempt+1} не удалась: {e}")
            if attempt < max_retries - 1:
                delay = 2**attempt
                logger.info(f"Жду {delay} секунд перед повтором")
                await asyncio.sleep(delay)
    logger.critical(
        f"Не удалось отправить подарок {gift_id} после {max_retries} попыток"
    )
    return False