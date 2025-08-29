# -*- coding: utf-8 -*-


class T:
    @staticmethod
    def new_gift(id: int | str, price: int, total_amount: int, is_premium: bool) -> str:
        return f"""
🆕 <b>Новый подарок</b>

💎 ID: <code>{id}</code>
⭐ Цена: {price} ⭐
📦 Доступно: {total_amount}
{'👑 Premium' if is_premium else '🎁 Обычный'}
"""

    @staticmethod
    def insufficient_balance_notification(balance: int) -> str:
        return f"⚠️ <b>Недостаточно баланса</b> — у вас {balance} ⭐, минимум нужен 1 ⭐ для покупок"

    @staticmethod
    def no_active_orders() -> str:
        return "⚠️ <b>Нет активных ордеров</b> — создайте ордер для автопокупки подарков"

    @staticmethod
    def insufficient_balance_for_order(order_name: str, balance: int, price: int) -> str:
        return f"⚠️ <b>Ордер {order_name}</b>: недостаточно баланса ({balance} ⭐) для цены {price} ⭐"

    @staticmethod
    def price_not_match_order(order_name: str, gift_price: int, min_price: int, max_price: int) -> str:
        return f"⚠️ <b>Ордер {order_name}</b>: цена {gift_price} ⭐ не подходит (нужно от {min_price} до {max_price} ⭐)"

    @staticmethod
    def supply_not_match_order(order_name: str, gift_supply: int, min_supply: int, max_supply: int) -> str:
        return f"⚠️ <b>Ордер {order_name}</b>: количество {gift_supply} не подходит (нужно от {min_supply} до {max_supply})"

    @staticmethod
    def budget_exceeded(order_name: str, spent: int, budget: int) -> str:
        return f"⚠️ <b>Ордер {order_name}</b>: бюджет исчерпан ({spent}/{budget} ⭐)"

    @staticmethod
    def insufficient_budget_for_single_gift(order_name: str, remaining_budget: int, price: int) -> str:
        return f"⚠️ <b>Ордер {order_name}</b>: в бюджете {remaining_budget} ⭐, нужно {price} ⭐"

    @staticmethod
    def no_suitable_orders(gift_id: int | str, price: int) -> str:
        return f"⚠️ <b>Нет подходящих ордеров</b> для подарка {gift_id} ценой {price} ⭐"

    @staticmethod
    def order_buying(order_name: str, remaining_to_buy: int) -> str:
        return f"🎯 <b>Ордер:</b> {order_name} — покупаю до {remaining_to_buy} шт."

    @staticmethod
    def premium_check_start() -> str:
        return "👑 <b>Premium подарок - проверяю возможность покупки через личный аккаунт...</b>"

    @staticmethod
    def personal_not_set() -> str:
        return "❌ <b>Личный аккаунт не настроен</b>\n\nДля покупки Premium подарков необходим привязанный аккаунт"

    @staticmethod
    def premium_disabled() -> str:
        return "❌ <b>Premium покупки отключены</b>\n\nВключите покупку Premium подарков в настройках"

    @staticmethod
    def no_premium() -> str:
        return "❌ <b>У вас нет Telegram Premium</b>\n\nДля покупки Premium подарков необходима подписка"

    @staticmethod
    def premium_personal_buying(count: int) -> str:
        return f"🚀 <b>Покупаю {count} Premium подарков через личный аккаунт...</b>"

    @staticmethod
    def success_buy_personal(count: int, gift_id: int | str) -> str:
        gift_text = "подарок" if count == 1 else f"{count} подарков"
        return f"""
✅ <b>Успешно куплено {gift_text}!</b>

💎 ID подарка: <code>{gift_id}</code>
🔧 Метод: через личный аккаунт
👑 Тип: Premium подарок
"""

    @staticmethod
    def fail_buy_personal(gift_id: int | str) -> str:
        return f"❌ <b>Не удалось купить подарок через личный аккаунт</b>\n\n💎 ID: <code>{gift_id}</code>\n⚠️ Подарок может быть недоступен или закончился"

    @staticmethod
    def error_buy_personal(gift_id: int | str) -> str:
        return f"❌ <b>Ошибка при покупке через личный аккаунт</b>\n\n💎 ID: <code>{gift_id}</code>\n🔧 Попробуйте позже"

    @staticmethod
    def only_personal_no_account() -> str:
        return "❌ <b>Включено 'только через личный', но аккаунт не привязан</b>"

    @staticmethod
    def only_personal_buying(count: int) -> str:
        return (
            f"🚀 <b>Покупаю {count} подарков через личный аккаунт (только личный)</b>"
        )

    @staticmethod
    def success_buy_personal_short(order_name: str) -> str:
        return f"✅ <b>Ордер {order_name}</b>: куплено через личный"

    @staticmethod
    def bot_api_order_start(order_name: str, count: int) -> str:
        return f"🚀 <b>Ордер:</b> {order_name} — покупка {count} через Bot API"

    @staticmethod
    def insufficient_funds_budget(balance: int, spent: int, budget: int) -> str:
        return f"⚠️ <b>Недостаточно средств/бюджета по ордеру</b> — баланс: {balance} ⭐, потрачено: {spent}/{budget}"

    @staticmethod
    def order_attempt(order_name: str, attempt_idx: int, total: int) -> str:
        return f"⏳ <b>Ордер {order_name}</b>: попытка {attempt_idx}/{total}"

    @staticmethod
    def order_success(order_name: str, i: int, price: int) -> str:
        return f"✅ <b>Ордер {order_name}</b>: куплен {i} — {price} ⭐"

    @staticmethod
    def order_bot_api_failed_try_personal(order_name: str) -> str:
        return f"❌ <b>Ордер {order_name}</b>: Bot API не удалось, пробую личный"

    @staticmethod
    def personal_failed(order_name: str) -> str:
        return f"❌ <b>Ордер {order_name}</b>: личный не помог"

    @staticmethod
    def personal_account_error() -> str:
        return "❌ <b>Ошибка личного аккаунта</b>"

    @staticmethod
    def personal_unavailable() -> str:
        return "⚠️ <b>Личный аккаунт недоступен</b>"

    @staticmethod
    def insufficient_funds_changed() -> str:
        return "⚠️ <b>Недостаточно средств</b> — баланс изменился во время покупки"

    @staticmethod
    def order_summary(order_name: str, count: int) -> str:
        return f"🎉 <b>Ордер {order_name}</b>: куплено {count}"

    @staticmethod
    def final_summary(
        gift_id: int | str, total_success: int, final_balance: int
    ) -> str:
        return f"📊 <b>Итог по подарку {gift_id}</b>: куплено {total_success}, баланс: {final_balance} ⭐"

    @staticmethod
    def critical_purchase_error(msg: str) -> str:
        return f"❌ <b>Критическая ошибка при покупке</b>: {msg}"