"""Конфигурация бота: пути, секреты (из одного файла) и константы.

Все секреты лежат в одном файле secrets/ai-bot.env (токен бота, chat_id владельца,
ключ GigaChat). Грузим через dotenv — тот же подход, что в price-watchdog.

Грациозная деградация:
  - нет GIGACHAT_CREDENTIALS -> бот живёт, на вопросы отвечает заглушкой;
  - нет TELEGRAM_BOT_TOKEN    -> запускать нечего, бот честно падает (см. bot.py).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import dotenv_values

# --- Пути -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts"
SECRETS_FILE = BASE_DIR / "secrets" / "ai-bot.env"

KNOWLEDGE_FILE = DATA_DIR / "knowledge.md"
LEADS_XLSX = DATA_DIR / "leads.xlsx"
SYSTEM_PROMPT_FILE = PROMPTS_DIR / "system_prompt.txt"

# Маркер «нет ответа в базе» — модель возвращает его дословно, код по нему ловит
# вопросы, на которые нужно звать живого менеджера.
NO_ANSWER_MARKER = "NO_ANSWER"


# --- Секреты ----------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    """Все секреты бота в одном объекте."""
    bot_token: Optional[str]
    owner_chat_id: Optional[str]
    gigachat_credentials: Optional[str]
    gigachat_scope: str

    @property
    def has_bot_token(self) -> bool:
        return bool(self.bot_token)

    @property
    def has_owner_chat(self) -> bool:
        return bool(self.owner_chat_id)

    @property
    def has_gigachat(self) -> bool:
        """Настроен ли GigaChat. Нет ключа -> бот работает в режиме заглушки."""
        return bool(self.gigachat_credentials)


def _clean(value: Optional[str]) -> Optional[str]:
    value = (value or "").strip()
    return value or None


def load_settings() -> Settings:
    """Читает секреты из secrets/ai-bot.env (с fallback на переменные окружения)."""
    values = dotenv_values(SECRETS_FILE) if SECRETS_FILE.exists() else {}

    def get(key: str) -> Optional[str]:
        return _clean(values.get(key) or os.getenv(key))

    return Settings(
        bot_token=get("TELEGRAM_BOT_TOKEN"),
        owner_chat_id=get("OWNER_CHAT_ID"),
        gigachat_credentials=get("GIGACHAT_CREDENTIALS"),
        gigachat_scope=get("GIGACHAT_SCOPE") or "GIGACHAT_API_PERS",
    )
