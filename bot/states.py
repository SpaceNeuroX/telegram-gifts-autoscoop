from aiogram.fsm.state import State, StatesGroup


class DepositState(StatesGroup):
    amount = State()


class SettingsState(StatesGroup):
    price_range = State()
    supply_range = State()
    recipient_input = State()


class LinkState(StatesGroup):
    phone = State()
    code = State()
    password = State()


class TransferState(StatesGroup):
    recipient = State()
    amount = State()


class DepositToState(StatesGroup):
    recipient = State()
    amount = State()


class OrdersState(StatesGroup):
    name = State()
    price_range = State()
    supply_range = State()
    budget = State()

    edit_price = State()
    edit_supply = State()
    edit_budget = State()
    edit_comment = State()
    edit_channel = State()

    # New granular edit states for card buttons
    edit_price_min = State()
    edit_price_max = State()
    edit_supply_min = State()
    edit_supply_max = State()
