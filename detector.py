from pyrogram import Client
from pytz import timezone as _timezone
from autoscoop import process_new_gift_for_autoscoop
import asyncio

from parse_data import get_all_star_gifts
from star_gifts_data import StarGiftData, StarGiftsData

import utils
import constants
import config

timezone = _timezone(config.TIMEZONE)
USERBOT_SLEEP_THRESHOLD = 60

STAR_GIFTS_DATA = StarGiftsData.load(config.DATA_FILEPATH)

logger = utils.get_logger(
    name=config.SESSION_NAME,
    log_filepath=constants.LOG_FILEPATH,
    console_log_level=config.CONSOLE_LOG_LEVEL,
    file_log_level=config.FILE_LOG_LEVEL,
)


async def detector(app: Client, save_only: bool = False) -> None:
    current_hash = 0

    while True:
        logger.debug("Checking for new gifts...")

        if not app.is_connected:
            try:
                await app.start()
            except Exception as ex:
                logger.error(f"Failed to start Pyrogram client: {ex}")
                await asyncio.sleep(config.CHECK_INTERVAL)
                continue

        new_hash, all_star_gifts_dict = await get_all_star_gifts(app, current_hash)

        if save_only:
            if all_star_gifts_dict is None:
                logger.debug("No new gifts found, exiting save-only mode.")
                return

            logger.info(f"Gifts found, saving data to {STAR_GIFTS_DATA.DATA_FILEPATH}")

            STAR_GIFTS_DATA.star_gifts = [
                star_gift for star_gift in all_star_gifts_dict.values()
            ]

            STAR_GIFTS_DATA.save()
            return

        if all_star_gifts_dict is None:
            logger.debug("Star gifts data not modified.")
            await asyncio.sleep(config.CHECK_INTERVAL)
            continue

        current_hash = new_hash

        old_star_gifts_dict = {
            star_gift.id: star_gift for star_gift in STAR_GIFTS_DATA.star_gifts
        }

        new_star_gifts_found = []
        for star_gift_id, star_gift in all_star_gifts_dict.items():
            if star_gift_id not in old_star_gifts_dict:
                new_star_gifts_found.append(star_gift)

        if new_star_gifts_found:
            logger.info(
                f"Found {len(new_star_gifts_found)} new gifts: [{', '.join(map(str, [g.id for g in new_star_gifts_found]))}]"
            )

            for star_gift in sorted(
                new_star_gifts_found, key=lambda sg: sg.total_amount
            ):
                await process_new_gift_for_autoscoop(star_gift)
                STAR_GIFTS_DATA.star_gifts.append(star_gift)
                STAR_GIFTS_DATA.save()

        await asyncio.sleep(config.CHECK_INTERVAL)


async def main() -> None:
    logger.info("Starting gifts detector...")

    app = Client(
        name=config.SESSION_NAME,
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        sleep_threshold=USERBOT_SLEEP_THRESHOLD,
        workdir=str(constants.SESSIONS_DIRPATH),
    )

    try:
        await app.start()
    except Exception as ex:
        logger.critical(f"Failed to start Pyrogram client, exiting: {ex}")
        return

    logger.info("Pyrogram client started.")

    await detector(app)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Detector stopped by user (KeyboardInterrupt).")
    except Exception as ex:
        logger.critical(f"An unhandled exception occurred in main: {ex}")
    finally:
        logger.info("Saving star gifts data before exit...")
        STAR_GIFTS_DATA.save()
        logger.info("Star gifts data saved. Exiting.")
