"""База знаний: чтение data/knowledge.md и подстановка в системный промпт.

Файл базы знаний правит сам клиент (обычный markdown). Чтобы не читать диск на
каждый вопрос, кэшируем содержимое и перечитываем только когда файл изменился
(сравниваем mtime). Так клиент может править knowledge.md «на лету», без перезапуска.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.config import KNOWLEDGE_FILE


class KnowledgeBase:
    """Кэширующая обёртка над файлом базы знаний.

    Создаётся один раз на старте бота. get_text() отдаёт актуальный текст,
    перечитывая файл только если он поменялся на диске.
    """

    def __init__(self, path: Path = KNOWLEDGE_FILE) -> None:
        self._path = path
        self._cache: Optional[str] = None
        self._mtime: Optional[float] = None

    def get_text(self) -> str:
        """Актуальный текст базы знаний. Нет файла -> пустая строка (не падаем)."""
        if not self._path.exists():
            self._cache = ""
            self._mtime = None
            return ""

        mtime = self._path.stat().st_mtime
        if self._cache is None or mtime != self._mtime:
            self._cache = self._path.read_text(encoding="utf-8")
            self._mtime = mtime
        return self._cache
