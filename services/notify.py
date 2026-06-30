"""Уведомления владельцу в Telegram: новая заявка и вопрос-эскалация.

И заявки, и вопросы без ответа падают в ОДИН чат владельца (OWNER_CHAT_ID).
Формирование текста вынесено в чистые функции — их легко протестировать без сети.
Сама отправка — тонкая async-обёртка над aiogram Bot.send_message; нет настроенного
чата -> печатаем в лог, не падаем.
"""
from __future__ import annotations

import logging
from typing import Optional

from services.leads import Lead

logger = logging.getLogger(__name__)


def format_lead_message(lead: Lead) -> str:
    """Текст уведомления о новой заявке."""
    return (
        "🆕 Новая заявка!\n"
        f"👤 Имя: {lead.name}\n"
        f"📞 Контакт: {lead.contact}\n"
        f"🕒 Удобное время: {lead.preferred_time}"
    )


def format_unanswered_message(question: str, username: Optional[str], user_id: int) -> str:
    """Текст эскалации: вопрос клиента, на который у бота нет ответа в базе."""
    who = f"@{username}" if username else f"id {user_id}"
    return (
        "❓ Вопрос без ответа в базе — нужен живой ответ.\n"
        f"От: {who}\n"
        f"Вопрос: {question}"
    )


async def send_to_owner(bot, owner_chat_id: Optional[str], text: str) -> bool:
    """Шлёт текст владельцу. Нет chat_id -> лог и False (не падаем)."""
    if not owner_chat_id:
        logger.warning("[OWNER_CHAT_ID не задан] %s", text)
        return False
    try:
        await bot.send_message(owner_chat_id, text)
    except Exception as exc:  # доставка упала — лог, но бот не падает
        logger.error("Не удалось уведомить владельца (%s): %s", exc, text)
        return False
    return True
