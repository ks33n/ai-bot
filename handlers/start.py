"""Команда /start, приветствие и пункты меню «Задать вопрос» / «Контакты».

Кнопка «Записаться» обрабатывается в handlers/lead.py (вход в FSM).
Эти хэндлеры регистрируются РАНЬШЕ qa, чтобы тексты кнопок не улетали в ИИ.
"""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from core.config import Settings
from handlers.keyboards import BTN_ASK, BTN_CONTACTS, main_menu
from handlers.qa import answer_question
from services.gigachat import Assistant

router = Router()

GREETING = (
    "Привет! 👋 Я бот-консультант барбершопа «Бритва».\n\n"
    "Отвечу на вопросы про услуги, цены, график и адрес — просто напишите.\n"
    "А если захотите записаться — жмите «Записаться», соберу заявку за минуту."
)

# Вопрос для кнопки «Контакты» — ответ берётся из той же базы знаний,
# чтобы всё рулилось одним файлом knowledge.md.
CONTACTS_QUESTION = "Подскажите ваш адрес, телефон и часы работы."


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(GREETING, reply_markup=main_menu())


@router.message(F.text == BTN_ASK)
async def on_ask(message: Message) -> None:
    await message.answer("Напишите ваш вопрос — отвечу по нашей базе 🙂")


@router.message(F.text == BTN_CONTACTS)
async def on_contacts(
    message: Message, assistant: Assistant, settings: Settings, bot: Bot
) -> None:
    await answer_question(message, CONTACTS_QUESTION, assistant, settings, bot)
