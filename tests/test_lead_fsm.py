"""Тесты FSM сбора заявки: переходы состояний, «Пропустить», отправка.

Telegram-объекты заменены лёгкими фейками; запись в xlsx и уведомление владельцу
подменяются monkeypatch'ем — никакой сети и файлов.
"""
import pytest

from core.config import Settings
from handlers import lead as lead_mod
from handlers.lead import (
    LeadForm,
    build_summary,
    cancel_lead,
    lead_from_data,
    process_contact,
    process_name,
    process_time,
    send_lead,
    skip_time,
)
from services.leads import Lead


class FakeState:
    def __init__(self):
        self.data = {}
        self.state = None

    async def set_state(self, s):
        self.state = s

    async def update_data(self, **kw):
        self.data.update(kw)

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.data = {}
        self.state = None


class FakeMessage:
    def __init__(self, text=""):
        self.text = text
        self.answers = []

    async def answer(self, text, reply_markup=None):
        self.answers.append(text)


class FakeCallback:
    def __init__(self, data=""):
        self.data = data
        self.message = FakeMessage()
        self.answered = False

    async def answer(self, *a, **kw):
        self.answered = True


# --- Чистые функции ---------------------------------------------------------
def test_lead_from_data_defaults_time():
    lead = lead_from_data({"name": "Иван", "contact": "@ivan"})
    assert lead == Lead(name="Иван", contact="@ivan", preferred_time="—")


def test_build_summary_contains_fields():
    summary = build_summary({"name": "Иван", "contact": "@ivan", "time": "суббота"})
    assert "Иван" in summary and "@ivan" in summary and "суббота" in summary


# --- Переходы состояний -----------------------------------------------------
@pytest.mark.asyncio
async def test_full_chain_to_confirm():
    state = FakeState()

    await process_name(FakeMessage("  Иван  "), state)
    assert state.data["name"] == "Иван"
    assert state.state == LeadForm.contact

    await process_contact(FakeMessage("+79990001122"), state)
    assert state.data["contact"] == "+79990001122"
    assert state.state == LeadForm.time

    await process_time(FakeMessage("в субботу днём"), state)
    assert state.data["time"] == "в субботу днём"
    assert state.state == LeadForm.confirm


@pytest.mark.asyncio
async def test_skip_time_sets_dash():
    state = FakeState()
    state.data = {"name": "Аня", "contact": "@anya"}
    cb = FakeCallback()

    await skip_time(cb, state)
    assert state.data["time"] == "—"
    assert state.state == LeadForm.confirm
    assert cb.answered is True


@pytest.mark.asyncio
async def test_cancel_clears_state():
    state = FakeState()
    state.data = {"name": "Аня"}
    state.state = LeadForm.confirm
    cb = FakeCallback()

    await cancel_lead(cb, state)
    assert state.data == {}
    assert state.state is None


@pytest.mark.asyncio
async def test_send_lead_writes_and_notifies(monkeypatch):
    saved = {}
    sent = {}

    def fake_append(lead):
        saved["lead"] = lead

    async def fake_send(bot, chat_id, text):
        sent["chat_id"] = chat_id
        sent["text"] = text
        return True

    monkeypatch.setattr(lead_mod, "append_lead", fake_append)
    monkeypatch.setattr(lead_mod, "send_to_owner", fake_send)

    state = FakeState()
    state.data = {"name": "Иван", "contact": "@ivan", "time": "суббота"}
    state.state = LeadForm.confirm
    cb = FakeCallback()
    settings = Settings("token", "owner123", "key", "GIGACHAT_API_PERS")

    await send_lead(cb, state, settings, bot=object())

    assert saved["lead"] == Lead("Иван", "@ivan", "суббота")
    assert sent["chat_id"] == "owner123"
    assert "Иван" in sent["text"]
    assert state.state is None  # state очищен
    assert cb.answered is True
