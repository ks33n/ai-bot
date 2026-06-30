"""Обёртка над официальным SDK GigaChat (ai-forever/gigachat).

Задачи модуля:
  - собрать системный промпт = инструкция + база знаний (RAG-лайт);
  - спросить модель async-методом achat (для aiogram);
  - распознать маркер NO_ANSWER (модель сама сигналит «нет в базе») и сообщить
    хэндлеру, что надо звать живого менеджера;
  - работать без ключа: режим заглушки, чтобы демо собиралось и без GigaChat.

Клиент GigaChat создаётся один раз на старте бота (см. bot.py) и переиспользуется
— SDK сам обновляет OAuth-токен. В тестах вместо реального клиента подсовываем мок.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional, Protocol

from core.config import NO_ANSWER_MARKER, SYSTEM_PROMPT_FILE, Settings
from services.knowledge import KnowledgeBase

logger = logging.getLogger(__name__)

TEMPERATURE = 0.3  # низкая — меньше отсебятины, ответы ближе к базе


@dataclass(frozen=True)
class AskResult:
    """Итог обращения к ИИ.

    text          — готовый ответ клиенту (если бот сам справился);
    needs_manager — True, если ответа в базе нет или ИИ не настроен: хэндлер тогда
                    мягко уводит к менеджеру и предлагает оставить заявку.
    """
    text: Optional[str]
    needs_manager: bool


class _ChatClient(Protocol):
    """Минимальный интерфейс клиента GigaChat, который нам нужен (для моков)."""
    async def achat(self, payload): ...


def _is_no_answer(text: str) -> bool:
    """True, если ответ модели — это маркер «нет в базе».

    Сравниваем без регистра и хвостовой пунктуации, чтобы ловить и 'NO_ANSWER',
    и 'NO_ANSWER.', и 'no_answer'.
    """
    cleaned = re.sub(r"[^A-Za-z_]", "", text).upper()
    return cleaned == NO_ANSWER_MARKER


def load_system_template() -> str:
    """Читает инструкцию для модели из prompts/system_prompt.txt."""
    if SYSTEM_PROMPT_FILE.exists():
        return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
    return ""


class Assistant:
    """ИИ-консультант: знает базу знаний, отвечает строго по ней."""

    def __init__(
        self,
        knowledge: KnowledgeBase,
        settings: Settings,
        client: Optional[_ChatClient] = None,
        system_template: Optional[str] = None,
    ) -> None:
        self._knowledge = knowledge
        self._settings = settings
        self._client = client
        self._system_template = (
            system_template if system_template is not None else load_system_template()
        )

    @property
    def is_configured(self) -> bool:
        """Есть ли рабочий клиент GigaChat (ключ задан и клиент создан)."""
        return self._settings.has_gigachat and self._client is not None

    def build_payload(self, user_text: str):
        """Собирает тело запроса: системный промпт (инструкция + база) + вопрос."""
        from gigachat.models import Chat, Messages, MessagesRole

        system = (
            f"{self._system_template}\n\n"
            f"=== БАЗА ЗНАНИЙ ===\n{self._knowledge.get_text()}"
        )
        return Chat(
            messages=[
                Messages(role=MessagesRole.SYSTEM, content=system),
                Messages(role=MessagesRole.USER, content=user_text),
            ],
            temperature=TEMPERATURE,
        )

    async def ask(self, user_text: str) -> AskResult:
        """Спрашивает ИИ. Возвращает ответ клиенту или сигнал «нужен менеджер»."""
        if not self.is_configured:
            # Нет ключа — не выдумываем, сразу зовём менеджера.
            return AskResult(text=None, needs_manager=True)

        payload = self.build_payload(user_text)
        try:
            response = await self._client.achat(payload)
            text = response.choices[0].message.content.strip()
        except Exception as exc:  # сеть/SDK упали — не роняем бота, зовём менеджера
            logger.error("GigaChat: запрос упал (%s)", exc)
            return AskResult(text=None, needs_manager=True)

        if not text or _is_no_answer(text):
            return AskResult(text=None, needs_manager=True)
        return AskResult(text=text, needs_manager=False)
