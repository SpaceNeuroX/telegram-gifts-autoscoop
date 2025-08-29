from pathlib import Path
from logging.handlers import RotatingFileHandler

import logging
import time


class StrippingFormatter(logging.Formatter):
    """Formatter that trims leading/trailing spaces and decorates level with emoji."""

    _LEVEL_EMOJI = {
        logging.DEBUG: "🔍",
        logging.INFO: "ℹ️",
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
        logging.CRITICAL: "💥",
    }

    def format(self, record: logging.LogRecord) -> str:
        # Normalize message
        record.msg = record.msg.strip() if isinstance(record.msg, str) else record.msg
        # Inject emoji field used by format string (safe if placeholder missing)
        setattr(record, "levelemoji", self._LEVEL_EMOJI.get(record.levelno, ""))
        return super().format(record)


def get_logger(
    name: str,
    log_filepath: Path,
    console_log_level: int = logging.INFO,
    file_log_level: int = logging.INFO,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(min(console_log_level, file_log_level))
    logger.propagate = False

    # If handlers are already configured for this logger, reuse them to avoid duplicates
    if logger.handlers:
        return logger

    formatter = StrippingFormatter(
        "%(asctime)s | %(levelname)s %(levelemoji)s | %(name)s:%(filename)s:%(lineno)d | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_log_level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=log_filepath.resolve().as_posix(),
        mode="a",
        maxBytes=10 * 1024 * 1024,
        backupCount=1_000,
        encoding="utf-8",
    )

    file_handler.setLevel(file_log_level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_current_timestamp() -> int:
    return int(time.time())
