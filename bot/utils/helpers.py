from datetime import datetime
import uuid
from decimal import Decimal, ROUND_HALF_UP


def format_date(dt):
    return dt.strftime("%d.%m.%Y %H:%M")


def generate_transaction_id():
    return str(uuid.uuid4())


def get_status_emoji(status):
    return {"completed": "✅", "refunded": "🔄", "failed": "❌"}.get(status, "❓")


def get_type_emoji(tx_type):
    return {
        "deposit": "💎",
        "deposit_to_other": "📤",
        "deposit_from_user": "📥",
        "referral_bonus_in": "🎁",
        "referral_bonus_out": "🎁",
        "commission_income": "💼",
        "commission_fee": "💼",
        "transfer_in": "➡️",
        "transfer_out": "⬅️",
        "purchase": "💸",
        "refund": "🔄",
    }.get(tx_type, "❓")


def format_amount(value):
    try:
        d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        s = f"{d:,.2f}"

        if s.endswith(".00"):
            s = s[:-3]
        elif s.endswith("0"):
            s = s[:-1]
        return s
    except Exception:
        return str(value)


def format_recipient(user_data):
    recipient_type = user_data.get("gift_recipient_type", "personal")
    recipient_id = user_data.get("gift_recipient_id")

    if recipient_type == "channel":
        username = user_data.get("gift_recipient_username", "неизвестно")
        return f"канал @{username}"
    else:
        if recipient_id:
            username = user_data.get("gift_recipient_username", "неизвестно")
            return f"@{username} (ID: {recipient_id})"
        return "себе"
