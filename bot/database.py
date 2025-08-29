from motor.motor_asyncio import AsyncIOMotorClient
from bot.config import MONGO_URL, DB_NAME

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
users = db.users
orders = db.orders
user_orders = db.user_orders
transactions = db.transactions
user_accounts = db.user_accounts

gifts_db = client["telegram_gifts"]
gifts_history = gifts_db["gifts_history"]
