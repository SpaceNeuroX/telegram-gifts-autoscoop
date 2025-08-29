from pydantic import BaseModel, Field
from pathlib import Path

import simplejson as json

import constants


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
    first_appearance_timestamp: int | None = Field(
        default=None
    )
    message_id: int | None = Field(default=None)
    last_sale_timestamp: int | None = Field(default=None)
    is_upgradable: bool = Field(default=False)


class StarGiftsData(BaseConfigModel):
    DATA_FILEPATH: Path = Field(exclude=True)
    star_gifts: list[StarGiftData] = Field(default_factory=list[StarGiftData])

    @classmethod
    def load(cls, data_filepath: Path, new: bool = False) -> "StarGiftsData":
        if new:
            return cls(DATA_FILEPATH=data_filepath)

        try:
            with data_filepath.open("r", encoding=constants.ENCODING) as file:
                return cls.model_validate(
                    {**json.load(file), "DATA_FILEPATH": data_filepath}
                )

        except FileNotFoundError:
            return cls(DATA_FILEPATH=data_filepath)

    def save(self) -> None:
        with self.DATA_FILEPATH.open("w", encoding=constants.ENCODING) as file:
            json.dump(
                obj=self.model_dump(),
                fp=file,
                indent=4,
                ensure_ascii=True,
                sort_keys=False,
            )
