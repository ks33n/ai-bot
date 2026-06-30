"""Хэндлер свободных вопросов: текст -> GigaChat -> ответ или эскалация.

Если ИИ не нашёл ответа в базе (маркер NO_ANSWER) или не настроен — клиенту уходит
мягкий ответ с кнопкой «Оставить заявку», а вопрос дублируется владельцу в чат.
"""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import Message

from core.config import Settings
from handlers.keyboards import lead_offer_kb
from services.gigachat import Assistant
from services.notify import format_unanswered_message, send_to_owner

router = Router()

ESCALATION_TEXT = (
    "Хороший вопрос! 🙌 Сейчас уточню у менеджера — он скоро ответит.\n"
    "А чтобы не ждать, можете сразу оставить заявку, и мы свяжемся с вами."
)


async def answer_question(
    message: Message,
    question: str,
    assistant: Assistant,
    settings: Settings,
    bot: Bot,
) -> None:
    """Ядро: спросить ИИ и либо ответить, либо увести к менеджеру.

    Используется и обычным текстовым хэндлером, и кнопкой «Контакты».
    """
    result = await assistant.ask(question)
    if result.needs_manager:
        await message.answer(ESCALATION_TEXT, reply_markup=lead_offer_kb())
        await send_to_owner(
            bot,
            settings.owner_chat_id,
            format_unanswered_message(question, message.from_user.username, message.from_user.id),
        )
    else:
        await message.answer(result.text)


# Ловит любой текст, который не перехватили роутеры меню и FSM заявки (они
# регистрируются раньше). Команды (начинаются с «/») игнорируем.
@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, assistant: Assistant, settings: Settings, bot: Bot) -> None:
    await answer_question(message, message.text, assistant, settings, bot)
