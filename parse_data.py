from pyrogram import Client
from pyrogram.raw.types.payments.star_gifts import StarGifts
from pyrogram.raw.types.payments.star_gifts_not_modified import StarGiftsNotModified
from pyrogram.raw.functions.payments.get_star_gifts import GetStarGifts
from pyrogram.raw.types.star_gift import StarGift
from pyrogram.raw.types.document_attribute_filename import DocumentAttributeFilename
from pyrogram.file_id import FileId, FileType

import utils
import typing

from star_gifts_data import StarGiftData


@typing.overload
async def get_all_star_gifts(
    client: Client, hash: typing.Literal[None] = ...
) -> tuple[int, dict[int, StarGiftData]]: ...


@typing.overload
async def get_all_star_gifts(
    client: Client, hash: int
) -> tuple[int, dict[int, StarGiftData] | None]: ...


async def get_all_star_gifts(
    client: Client, hash: int | None = None
) -> tuple[int, dict[int, StarGiftData] | None]:
    r = typing.cast(
        StarGifts | StarGiftsNotModified,
        await client.invoke(GetStarGifts(hash=hash or 0)),
    )

    if isinstance(r, StarGiftsNotModified):
        return (typing.cast(int, hash), None)

    r_gifts = typing.cast(list[StarGift], r.gifts)

    all_star_gifts_dict: dict[int, StarGiftData] = {
        star_gift_raw.id: StarGiftData(
            id=star_gift_raw.id,
            number=number,
            sticker_file_id=FileId(
                file_type=FileType.DOCUMENT,
                dc_id=typing.cast(int, star_gift_raw.sticker.dc_id),
                media_id=typing.cast(int, star_gift_raw.sticker.id),
                access_hash=typing.cast(int, star_gift_raw.sticker.access_hash),
                file_reference=typing.cast(bytes, star_gift_raw.sticker.file_reference),
            ).encode(),
            sticker_file_name=next(
                (
                    attr.file_name
                    for attr in typing.cast(
                        list[DocumentAttributeFilename | typing.Any],
                        star_gift_raw.sticker.attributes,
                    )
                    if isinstance(attr, DocumentAttributeFilename)
                ),
                f"{star_gift_raw.id}.tgs",
            ),
            price=star_gift_raw.stars,
            convert_price=star_gift_raw.convert_stars,
            available_amount=star_gift_raw.availability_remains or 0,
            total_amount=star_gift_raw.availability_total or 0,
            require_premium=star_gift_raw.require_premium or False,
            user_limited=(
                (star_gift_raw.per_user_total or 0)
                if star_gift_raw.limited_per_user
                else None
            ),
            is_limited=star_gift_raw.limited or False,
            first_appearance_timestamp=star_gift_raw.first_sale_date
            or utils.get_current_timestamp(),
            last_sale_timestamp=star_gift_raw.last_sale_date,
        )
        for number, star_gift_raw in enumerate(
            sorted(r_gifts, key=lambda sgr: sgr.id, reverse=False), 1
        )
    }

    return (r.hash, all_star_gifts_dict)
