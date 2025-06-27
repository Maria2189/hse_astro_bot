from telebot.types import Message, CallbackQuery
from tgbot.models import TelegramUser
from tgbot.models import Configuration
from pathlib import Path
from loguru import logger
from tgbot.dispatcher import get_main_bot

Path("logs").mkdir(parents=True, exist_ok=True)

log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="INFO")

def sync_user_data(update: Message | CallbackQuery | TelegramUser) -> tuple[TelegramUser, bool] | None:
    """
    Синхронизирует поля TelegramUser (first_name, last_name, username, can_publish_tasks)
    на основании приходящего Message или CallbackQuery.
    Возвращает кортеж (user, created) или None, если не удалось получить chat_id
    или если это групповой чат.
    """
    # 1) Определяем chat и chat_id
    if isinstance(update, Message):
        chat = update.chat
    elif isinstance(update, CallbackQuery):
        if not update.message:
            logger.error("sync_user_data: у CallbackQuery нет message")
            return None
        chat = update.message.chat
    elif isinstance(update, TelegramUser):
        bot = get_main_bot()
        chat = bot.get_chat(update.chat_id)
    else:
        logger.error(f"sync_user_data: Unsupported update type {type(update)}")
        return None

    # 2) Пропускаем групповые чаты
    if is_group_chat(update):
        return None
    
    chat_id = chat.id
    first_name = chat.first_name or chat.title or ""
    # 3) Получаем или создаем пользователя
    user, created = TelegramUser.objects.get_or_create(
        chat_id=chat_id,
        defaults={
            "first_name": first_name,
            "last_name": chat.last_name or "",
            "username": chat.username or "" ,
        }
    )

    # 4) При необходимости обновляем изменившиеся поля
    changed = False
    if user.first_name != (first_name):
        user.first_name = first_name
        changed = True
    if user.last_name != (chat.last_name or ""):
        user.last_name = chat.last_name or ""
        changed = True
    if user.username != (chat.username or ""):
        user.username = chat.username or ""
        changed = True

    if changed:
        try:
            user.save()
            logger.info(f"sync_user_data: Updated TelegramUser {user.chat_id}")
        except Exception as e:
            logger.error(f"sync_user_data: Failed to save TelegramUser {user.chat_id}: {e}")
    else:
        logger.info(f"sync_user_data: No changes for TelegramUser {user.chat_id}")

    return user, created

def is_group_chat(obj: Message | CallbackQuery) -> bool:
    # достаём объект chat
    if isinstance(obj, Message):
        chat = obj.chat
    elif isinstance(obj, CallbackQuery):
        # у callback всегда есть .message
        chat = obj.message.chat
    else:
        return False

    return chat.type in ('group', 'supergroup')
