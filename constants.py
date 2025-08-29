from pathlib import Path

ENCODING = "utf-8"

WORK_DIRPATH = Path(__file__).parent
LOGS_DIRPATH = WORK_DIRPATH / "logs"
LOG_FILEPATH = LOGS_DIRPATH / "main.log"
GIFTS_DATA_FILEPATH = WORK_DIRPATH / "gifts_data" / "star_gifts.json"
SESSIONS_DIRPATH = WORK_DIRPATH / "sessions"

if not LOGS_DIRPATH.exists():
    LOGS_DIRPATH.mkdir()

if not SESSIONS_DIRPATH.exists():
    SESSIONS_DIRPATH.mkdir()
