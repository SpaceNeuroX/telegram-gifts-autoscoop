import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot.config import BOT_TOKEN
from bot.handlers import (
    start,
    deposit,
    balance,
    settings,
    telethon_connect,
    transfer,
    orders,
)


async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_routers(
        start.router,
        deposit.router,
        balance.router,
        settings.router,
        telethon_connect.router,
        transfer.router,
        orders.router,
    )

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="🌟 Главное меню"),
            BotCommand(command="balance", description="💰 Баланс и операции"),
            BotCommand(command="settings", description="⚙️ Настройки автоскупа"),
            BotCommand(command="transfer", description="🔁 Перевод звёзд другому"),
            BotCommand(command="deposit_to", description="💳 Пополнить баланс другого"),
            BotCommand(command="orders", description="📈 Мои ордера"),
        ]
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
