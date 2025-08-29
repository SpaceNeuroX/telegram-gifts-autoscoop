import asyncio
from random import randint
from pydantic import BaseModel, Field
from bot.autoscoop import process_new_gift_for_autoscoop  # <-- импорт из твоего модуля


class BaseConfigModel(BaseModel, extra="ignore"):
    pass


class StarGiftData(BaseConfigModel):
    id: int
    number: int
    sticker_file_id: str
    sticker_file_name: str
    price: int
    convert_price: int
    available_amount: int
    total_amount: int
    require_premium: bool = Field(default=False)
    user_limited: int | None = Field(default=None)
    is_limited: bool
    first_appearance_timestamp: int | None = Field(default=None)
    message_id: int | None = Field(default=None)
    last_sale_timestamp: int | None = Field(default=None)
    is_upgradable: bool = Field(default=False)


async def main():
    star_gift = StarGiftData(
        id=5170233102089322756,
        number=randint(1, 50),
        sticker_file_id="sticker_" + str(randint(1000, 9999)),
        sticker_file_name="gift_" + str(randint(1, 100)) + ".webp",
        price=15,
        convert_price=15,
        available_amount=200_000,
        total_amount=randint(500, 2000),
        require_premium=False,
        user_limited=None,
        is_limited=True,
        first_appearance_timestamp=randint(1700000000, 1750000000),
        message_id=randint(10000, 20000),
        last_sale_timestamp=randint(1700000000, 1750000000),
        is_upgradable=True,
    )

    await process_new_gift_for_autoscoop(star_gift)


if __name__ == "__main__":
    asyncio.run(main())
