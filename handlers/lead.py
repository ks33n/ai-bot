"""FSM сбора заявки: имя → контакт → удобное время → подтверждение.

Вход в диалог: кнопка меню «Записаться» ИЛИ инлайн-кнопка «Оставить заявку»
(из эскалации в qa). На подтверждении заявка пишется в leads.xlsx и дублируется
владельцу в Telegram.

Чистые функции lead_from_data() и build_summary() вынесены отдельно — их удобно
тестировать без Telegram.
"""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from core.config import Settings
from handlers.keyboards import (
    BTN_LEAD,
    CB_LEAD_CANCEL,
    CB_LEAD_SEND,
    CB_LEAD_SKIP_TIME,
    CB_LEAD_START,
    confirm_kb,
    main_menu,
    skip_time_kb,
)
from services.leads import Lead, append_lead
from services.notify import format_lead_message, send_to_owner

router = Router()

NO_TIME = "—"


class LeadForm(StatesGroup):
    name = State()
    contact = State()
    time = State()
    confirm = State()


def lead_from_data(data: dict) -> Lead:
    """Собирает Lead из накопленных в FSM данных."""
    return Lead(
        name=data.get("name", ""),
        contact=data.get("contact", ""),
        preferred_time=data.get("time") or NO_TIME,
    )


def build_summary(data: dict) -> str:
    """Текст подтверждения заявки перед отправкой."""
    lead = lead_from_data(data)
    return (
        "Проверьте заявку:\n"
        f"👤 Имя: {lead.name}\n"
        f"📞 Контакт: {lead.contact}\n"
        f"🕒 Удобное время: {lead.preferred_time}\n\n"
        "Всё верно?"
    )


async def _start_lead(message: Message, state: FSMContext) -> None:
    await state.set_state(LeadForm.name)
    await message.answer("Давайте оформим заявку. Как вас зовут?")


async def _show_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(LeadForm.confirm)
    await message.answer(build_summary(data), reply_markup=confirm_kb())


# --- Входы в FSM ------------------------------------------------------------
@router.message(F.text == BTN_LEAD)
async def start_from_menu(message: Message, state: FSMContext) -> None:
    await _start_lead(message, state)


@router.callback_query(F.data == CB_LEAD_START)
async def start_from_button(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_lead(callback.message, state)
    await callback.answer()


# --- Шаги сбора -------------------------------------------------------------
@router.message(LeadForm.name, F.text)
async def process_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(LeadForm.contact)
    await message.answer("Оставьте телефон или @username для связи:")


@router.message(LeadForm.contact, F.text)
async def process_contact(message: Message, state: FSMContext) -> None:
    await state.update_data(contact=message.text.strip())
    await state.set_state(LeadForm.time)
    await message.answer(
        "Когда вам удобно? Напишите дату/время или нажмите «Пропустить».",
        reply_markup=skip_time_kb(),
    )


@router.message(LeadForm.time, F.text)
async def process_time(message: Message, state: FSMContext) -> None:
    await state.update_data(time=message.text.strip())
    await _show_confirm(message, state)


@router.callback_query(LeadForm.time, F.data == CB_LEAD_SKIP_TIME)
async def skip_time(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(time=NO_TIME)
    await _show_confirm(callback.message, state)
    await callback.answer()


# --- Подтверждение ----------------------------------------------------------
@router.callback_query(LeadForm.confirm, F.data == CB_LEAD_SEND)
async def send_lead(
    callback: CallbackQuery, state: FSMContext, settings: Settings, bot: Bot
) -> None:
    data = await state.get_data()
    lead = lead_from_data(data)
    append_lead(lead)
    await send_to_owner(bot, settings.owner_chat_id, format_lead_message(lead))
    await state.clear()
    await callback.message.answer(
        "Готово! Заявку приняли — менеджер скоро свяжется ✅", reply_markup=main_menu()
    )
    await callback.answer()


@router.callback_query(LeadForm.confirm, F.data == CB_LEAD_CANCEL)
async def cancel_lead(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Окей, отменил. Если что — я на связи 🙂")
    await callback.answer()
