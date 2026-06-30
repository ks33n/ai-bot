"""Точка входа: long polling, регистрация роутеров, создание клиента GigaChat.

Запуск:
    python bot.py

Секреты берутся из secrets/ai-bot.env (см. secrets.env.example). Без
GIGACHAT_CREDENTIALS бот работает в режиме заглушки (вопросы уводятся к менеджеру),
но меню и сбор заявок работают полностью. Без TELEGRAM_BOT_TOKEN запускать нечего —
честно падаем с понятным сообщением.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from core.config import load_settings
from handlers import lead, qa, start
from services.gigachat import Assistant
from services.knowledge import KnowledgeBase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("ai-bot")


def _build_gigachat_client(settings):
    """Создаёт клиент GigaChat, если задан ключ. Иначе None (режим заглушки)."""
    if not settings.has_gigachat:
        logger.warning("GIGACHAT_CREDENTIALS не задан — бот в режиме заглушки "
                       "(вопросы уводятся к менеджеру). Меню и заявки работают.")
        return None
    from gigachat import GigaChat

    return GigaChat(
        credentials=settings.gigachat_credentials,
        scope=settings.gigachat_scope,
        verify_ssl_certs=False,  # у Сбера РФ-сертификат, нет в стандартном хранилище
    )


async def _close_client(client) -> None:
    if client is None:
        return
    try:
        if hasattr(client, "aclose"):
            await client.aclose()
        elif hasattr(client, "close"):
            client.close()
    except Exception as exc:  # закрытие не должно ронять выход
        logger.warning("Не удалось закрыть клиент GigaChat: %s", exc)


async def main() -> None:
    settings = load_settings()
    if not settings.has_bot_token:
        raise SystemExit(
            "Не задан TELEGRAM_BOT_TOKEN. Скопируй secrets.env.example в "
            "secrets/ai-bot.env и впиши токен от @BotFather."
        )
    if not settings.has_owner_chat:
        logger.warning("OWNER_CHAT_ID не задан — заявки и вопросы не уйдут владельцу "
                       "(будут только в логах и leads.xlsx).")

    knowledge = KnowledgeBase()
    client = _build_gigachat_client(settings)
    assistant = Assistant(knowledge, settings, client=client)

    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    # Прокидываем зависимости в хэндлеры (aiogram внедрит по имени параметра).
    dp["assistant"] = assistant
    dp["settings"] = settings

    # Порядок важен: меню и FSM заявки — раньше catch-all qa.
    dp.include_router(start.router)
    dp.include_router(lead.router)
    dp.include_router(qa.router)

    logger.info("Бот запущен (long polling). Ctrl+C для остановки.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await _close_client(client)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit) as exc:
        logger.info("Остановлено: %s", exc)
