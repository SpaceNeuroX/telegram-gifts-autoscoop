from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl import functions, types
from telethon.tl.functions.payments import GetStarsStatusRequest
from telethon.tl.types import InputPeerSelf
from bot.config import TELETHON_API_ID, TELETHON_API_HASH
from bot.database import user_accounts


async def get_account_doc(user_id: int):
    return await user_accounts.find_one({"user_id": user_id})


async def save_session(user_id: int, session_string: str):
    await user_accounts.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "session_string": session_string,
                "use_personal_buy": False,
                "updated_at": 0,
            },
            "$setOnInsert": {
                "allow_premium_buy": False,
                "only_personal_buy": False,
                "created_at": 0,
            },
        },
        upsert=True,
    )


async def clear_session(user_id: int):
    await user_accounts.delete_one({"user_id": user_id})


def build_client_from_session(session_string: str | None):
    session = StringSession(session_string) if session_string else StringSession()
    return TelegramClient(session, TELETHON_API_ID, TELETHON_API_HASH)


async def get_client_for_user(user_id: int) -> TelegramClient | None:
    doc = await get_account_doc(user_id)
    if not doc or not doc.get("session_string"):
        return None
    client = build_client_from_session(doc["session_string"])
    await client.connect()
    return client


async def check_stars_balance(user_id: int):
    client = await get_client_for_user(user_id)
    if not client:
        return None, None
    try:
        me = await client.get_me()
        status = await client(GetStarsStatusRequest(peer=InputPeerSelf()))
        balance = status.balance.amount if getattr(status, "balance", None) else 0
        return balance, bool(getattr(me, "premium", False))
    finally:
        await client.disconnect()


async def start_login_send_code(phone: str):
    client = build_client_from_session(None)
    await client.connect()
    sent = await client.send_code_request(phone)
    session_string = client.session.save()
    await client.disconnect()
    return session_string, sent.phone_code_hash


async def complete_login_with_code(
    session_string: str, phone: str, code: str, phone_code_hash: str
):
    client = build_client_from_session(session_string)
    await client.connect()
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        new_session = client.session.save()
        return {"status": "ok", "session": new_session}
    except SessionPasswordNeededError:
        return {"status": "password", "session": session_string}
    finally:
        await client.disconnect()


async def complete_login_with_password(session_string: str, password: str):
    client = build_client_from_session(session_string)
    await client.connect()
    try:
        await client.sign_in(password=password)
        return client.session.save()
    finally:
        await client.disconnect()


async def set_toggle(user_id: int, field: str, value: bool):
    await user_accounts.update_one({"user_id": user_id}, {"$set": {field: value}})


async def _resolve_target_peer(client, target):
    """
    Resolve InputPeer for arbitrary target.
    - None -> self
    - str/int -> resolve via get_input_entity
    """
    if not target:
        print("[DEBUG] Target пустой, возвращаю InputPeerSelf()")
        return InputPeerSelf()
    try:
        peer = await client.get_input_entity(target)
        print(f"[DEBUG] get_input_entity успешно: {peer}")
        return peer
    except Exception as e:
        print(f"[ERROR] Не удалось получить entity для target={target}, ошибка: {e}")
        return InputPeerSelf()


async def send_gift_via_personal(
    user_id: int,
    gift_id: int,
    count: int,
    target: str | int | None,
    message_text: str,
    include_upgrade: bool,
    gift_price: int | None = None,
) -> tuple[int, int]:
    """Send gift(s) using the user's personal Telethon session.
    Returns (success_count, failed_count)

    gift_price: price of a single gift in stars; if provided, we will
    pre-check the personal account balance and fail fast if insufficient.
    """
    print(
        f"[INFO] Запуск send_gift_via_personal("
        f"user_id={user_id}, gift_id={gift_id}, count={count}, target={target})"
    )

    client = await get_client_for_user(user_id)
    if not client:
        raise RuntimeError("No linked account")

    count = max(1, int(count))
    print(f"[DEBUG] Привёл count к int: {count}")

    try:

        if gift_price is not None:
            try:
                status = await client(GetStarsStatusRequest(peer=InputPeerSelf()))
                balance = (
                    status.balance.amount if getattr(status, "balance", None) else 0
                )
            except Exception as e:
                print(f"[ERROR] Не удалось получить баланс звёзд: {e}")
                balance = 0
            need = int(gift_price) * count
            print(f"[DEBUG] Проверка баланса: balance={balance}, need={need}")
            if balance < need:
                print(
                    "[WARN] Недостаточно звёзд на личном аккаунте — прерываю отправку"
                )
                return 0, count

        print(f"[DEBUG] Разрешение цели для user_id={user_id}, target={target}")
        try:
            primary_peer = await _resolve_target_peer(client, target)
            print(f"[DEBUG] Цель успешно разрешена: {primary_peer}")
        except Exception as e:
            print(f"[ERROR] Не удалось разрешить target={target}, ошибка: {e}")
            return 0, count

        success = 0
        failed = 0

        async def _try_send(to_peer) -> bool:
            print(f"[DEBUG] Вызов _try_send(to_peer={to_peer})")
            invoice = types.InputInvoiceStarGift(
                peer=to_peer,
                gift_id=int(gift_id),
                hide_name=False,
                include_upgrade=bool(include_upgrade),
                message=types.TextWithEntities(text=message_text or "", entities=[]),
            )
            try:
                print(
                    f"[DEBUG] Попытка получить PaymentForm (peer={to_peer}, include_upgrade={invoice.include_upgrade})"
                )
                payment_form = await client(
                    functions.payments.GetPaymentFormRequest(invoice=invoice)
                )
            except Exception as e:
                print(f"[WARN] Ошибка при GetPaymentFormRequest: {e}")
                if "STARGIFT_UPGRADE_UNAVAILABLE" in str(e):
                    invoice.include_upgrade = False
                    print(f"[DEBUG] Повторная попытка без include_upgrade")
                    try:
                        payment_form = await client(
                            functions.payments.GetPaymentFormRequest(invoice=invoice)
                        )
                    except Exception as e2:
                        print(f"[ERROR] Не удалось получить PaymentForm повторно: {e2}")
                        return False
                else:
                    return False
            try:
                print(
                    f"[DEBUG] Отправка SendStarsFormRequest (form_id={payment_form.form_id})"
                )
                await client(
                    functions.payments.SendStarsFormRequest(
                        form_id=payment_form.form_id, invoice=invoice
                    )
                )
                print(f"[SUCCESS] Успешно отправлен подарок (gift_id={gift_id})")
                return True
            except Exception as e:
                print(f"[ERROR] Ошибка при SendStarsFormRequest: {e}")
                return False

        print(f"[DEBUG] Готов к циклу отправки (count={count})")

        try:
            for i in range(max(1, int(count))):
                print(f"[INFO] Отправка подарка {i+1}/{count}")
                sent = await _try_send(primary_peer)
                if not sent:
                    print(f"[WARN] Основной peer не сработал, пробуем InputPeerSelf()")
                    sent = await _try_send(InputPeerSelf())
                if sent:
                    success += 1
                else:
                    failed += 1
        except Exception as e:
            print(f"[FATAL] Ошибка до/во время цикла отправки: {e}")
            return 0, count

        print(f"[RESULT] Отправка завершена: success={success}, failed={failed}")
        return success, failed
    finally:
        print(f"[DEBUG] Отключение клиента для user_id={user_id}")
        await client.disconnect()
