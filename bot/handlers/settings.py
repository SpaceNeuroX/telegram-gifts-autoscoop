from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.database import users
from bot.states import SettingsState
from bot.utils.texts import *
from bot.keyboards.settings import *

router = Router()


@router.message(Command("settings"))
async def settings_command(message: Message):
    await show_settings(message, True)


@router.callback_query(F.data == "settings_menu")
async def settings_menu_callback(callback: CallbackQuery):
    await show_settings(callback, False)


async def show_settings(obj, is_message):

    text = SETTINGS_MAIN

    keyboard = get_settings_keyboard()

    if is_message:
        await obj.answer(text, reply_markup=keyboard)
    else:
        await obj.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "gifts_count")
async def gifts_count_callback(callback: CallbackQuery):
    user = await users.find_one({"user_id": callback.from_user.id})
    current = user.get("max_gifts_per_type", 1)

    await callback.message.edit_text(
        GIFTS_COUNT_MENU.format(current=current),
        reply_markup=get_gifts_count_keyboard(current),
    )


@router.callback_query(F.data.startswith("set_gifts_"))
async def set_gifts_callback(callback: CallbackQuery):
    count = int(callback.data.split("_")[2])
    if count < 1:
        count = 1
    elif count > 5:
        count = 5

    await users.update_one(
        {"user_id": callback.from_user.id}, {"$set": {"max_gifts_per_type": count}}
    )

    await callback.answer(f"✅ Установлено: {count}")
    await show_settings(callback, False)


@router.callback_query(F.data == "price_filter")
async def price_filter_callback(callback: CallbackQuery, state: FSMContext):
    user = await users.find_one({"user_id": callback.from_user.id})

    await state.set_state(SettingsState.price_range)
    await callback.message.edit_text(
        PRICE_FILTER_MENU.format(
            min_price=user.get("min_price", 1), max_price=user.get("max_price", 10000)
        ),
        reply_markup=get_filter_input_keyboard(),
    )


@router.callback_query(F.data == "supply_filter")
async def supply_filter_callback(callback: CallbackQuery, state: FSMContext):
    user = await users.find_one({"user_id": callback.from_user.id})

    await state.set_state(SettingsState.supply_range)
    await callback.message.edit_text(
        SUPPLY_FILTER_MENU.format(
            min_supply=user.get("min_supply", 1),
            max_supply=user.get("max_supply", 999999),
        ),
        reply_markup=get_filter_input_keyboard(),
    )


@router.message(SettingsState.price_range)
async def handle_price_input(message: Message, state: FSMContext):
    try:
        parts = message.text.strip().split()
        if len(parts) == 2:
            min_val, max_val = map(int, parts)
            if 1 <= min_val <= max_val <= 100000:
                await users.update_one(
                    {"user_id": message.from_user.id},
                    {"$set": {"min_price": min_val, "max_price": max_val}},
                )
                await message.answer(f"✅ Цена: {min_val:,} - {max_val:,} ⭐")
                await state.clear()
                return

        await message.answer(ERROR_INVALID_FORMAT)
    except ValueError:
        await message.answer(ERROR_INVALID_FORMAT)


@router.message(SettingsState.supply_range)
async def handle_supply_input(message: Message, state: FSMContext):
    try:
        parts = message.text.strip().split()
        if len(parts) == 2:
            min_val, max_val = map(int, parts)
            if min_val > 0 and min_val <= max_val:
                await users.update_one(
                    {"user_id": message.from_user.id},
                    {"$set": {"min_supply": min_val, "max_supply": max_val}},
                )
                await message.answer(f"✅ Supply: {min_val:,} - {max_val:,}")
                await state.clear()
                return

        await message.answer(ERROR_INVALID_FORMAT)
    except ValueError:
        await message.answer(ERROR_INVALID_FORMAT)
