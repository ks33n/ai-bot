"""Клавиатуры и тексты кнопок бота — в одном месте, чтобы хэндлеры и тесты
ссылались на одни и те же константы."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# --- Тексты кнопок главного меню (reply-клавиатура) -------------------------
BTN_ASK = "❓ Задать вопрос"
BTN_LEAD = "📝 Записаться"
BTN_CONTACTS = "📍 Контакты"

# --- callback_data инлайн-кнопок --------------------------------------------
CB_LEAD_START = "lead_start"
CB_LEAD_SKIP_TIME = "lead_skip_time"
CB_LEAD_SEND = "lead_send"
CB_LEAD_CANCEL = "lead_cancel"


def main_menu() -> ReplyKeyboardMarkup:
    """Постоянное меню под полем ввода."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ASK)],
            [KeyboardButton(text=BTN_LEAD), KeyboardButton(text=BTN_CONTACTS)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Напишите вопрос или выберите пункт меню",
    )


def lead_offer_kb() -> InlineKeyboardMarkup:
    """Инлайн-кнопка «Оставить заявку» — показывается при эскалации к менеджеру."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📝 Оставить заявку", callback_data=CB_LEAD_START)]]
    )


def skip_time_kb() -> InlineKeyboardMarkup:
    """Кнопка «Пропустить» на шаге удобного времени."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data=CB_LEAD_SKIP_TIME)]]
    )


def confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение заявки: отправить / отмена."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить", callback_data=CB_LEAD_SEND)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=CB_LEAD_CANCEL)],
        ]
    )
