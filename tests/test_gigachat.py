"""Тесты ИИ-обёртки: детект NO_ANSWER, заглушка без ключа, сборка промпта.

Реальный GigaChat не дёргаем — подсовываем мок-клиента с async achat.
"""
import pytest

from core.config import Settings
from services.gigachat import Assistant, AskResult, _is_no_answer
from services.knowledge import KnowledgeBase


class FakeKnowledge(KnowledgeBase):
    def __init__(self, text: str):
        self._text = text

    def get_text(self) -> str:
        return self._text


class FakeResponse:
    """Имитация ChatCompletion: response.choices[0].message.content."""
    def __init__(self, content: str):
        msg = type("M", (), {"content": content})
        choice = type("C", (), {"message": msg})
        self.choices = [choice]


class FakeClient:
    def __init__(self, content: str):
        self._content = content
        self.last_payload = None

    async def achat(self, payload):
        self.last_payload = payload
        return FakeResponse(self._content)


def _settings(creds="key"):
    return Settings(
        bot_token="t",
        owner_chat_id="1",
        gigachat_credentials=creds,
        gigachat_scope="GIGACHAT_API_PERS",
    )


def test_marker_detection_variants():
    assert _is_no_answer("NO_ANSWER")
    assert _is_no_answer("NO_ANSWER.")
    assert _is_no_answer("  no_answer  ")
    assert not _is_no_answer("Стрижка стоит 1500₽")
    assert not _is_no_answer("У нас нет маникюра, но есть стрижка")


@pytest.mark.asyncio
async def test_real_answer_passes_through():
    assistant = Assistant(
        FakeKnowledge("Стрижка 1500₽"),
        _settings(),
        client=FakeClient("Стрижка стоит 1500₽"),
        system_template="Отвечай по базе.",
    )
    result = await assistant.ask("сколько стоит стрижка?")
    assert result == AskResult(text="Стрижка стоит 1500₽", needs_manager=False)


@pytest.mark.asyncio
async def test_no_answer_marker_triggers_manager():
    assistant = Assistant(
        FakeKnowledge("Стрижка 1500₽"),
        _settings(),
        client=FakeClient("NO_ANSWER"),
        system_template="Отвечай по базе.",
    )
    result = await assistant.ask("делаете маникюр?")
    assert result.needs_manager is True
    assert result.text is None


@pytest.mark.asyncio
async def test_no_credentials_falls_back_to_manager():
    # Ключа нет -> даже с клиентом не спрашиваем, сразу зовём менеджера.
    assistant = Assistant(
        FakeKnowledge("Стрижка 1500₽"),
        _settings(creds=None),
        client=FakeClient("неважно"),
        system_template="x",
    )
    result = await assistant.ask("сколько стоит?")
    assert result.needs_manager is True


@pytest.mark.asyncio
async def test_client_error_falls_back_to_manager():
    class BoomClient:
        async def achat(self, payload):
            raise RuntimeError("сеть упала")

    assistant = Assistant(
        FakeKnowledge("..."), _settings(), client=BoomClient(), system_template="x"
    )
    result = await assistant.ask("вопрос")
    assert result.needs_manager is True


def test_build_payload_includes_knowledge_and_question():
    assistant = Assistant(
        FakeKnowledge("Адрес: Ленина 1"),
        _settings(),
        client=FakeClient("ok"),
        system_template="Инструкция",
    )
    payload = assistant.build_payload("где вы?")
    system_msg = payload.messages[0].content
    user_msg = payload.messages[1].content
    assert "Инструкция" in system_msg
    assert "Адрес: Ленина 1" in system_msg
    assert user_msg == "где вы?"
