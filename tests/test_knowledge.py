"""Тесты базы знаний: чтение, кэш и перечитка по изменению файла."""
import os
import time

from services.knowledge import KnowledgeBase


def test_reads_file_content(tmp_path):
    kb_file = tmp_path / "knowledge.md"
    kb_file.write_text("Стрижка 1500₽", encoding="utf-8")

    kb = KnowledgeBase(kb_file)
    assert kb.get_text() == "Стрижка 1500₽"


def test_missing_file_returns_empty(tmp_path):
    kb = KnowledgeBase(tmp_path / "nope.md")
    assert kb.get_text() == ""


def test_caches_between_calls(tmp_path):
    kb_file = tmp_path / "knowledge.md"
    kb_file.write_text("v1", encoding="utf-8")
    kb = KnowledgeBase(kb_file)

    assert kb.get_text() == "v1"
    # Перезаписали с тем же mtime — кэш не должен меняться (читаем из кэша).
    mtime = kb_file.stat().st_mtime
    kb_file.write_text("v2-but-same-mtime", encoding="utf-8")
    os.utime(kb_file, (mtime, mtime))
    assert kb.get_text() == "v1"


def test_rereads_when_file_changes(tmp_path):
    kb_file = tmp_path / "knowledge.md"
    kb_file.write_text("старый прайс", encoding="utf-8")
    kb = KnowledgeBase(kb_file)
    assert kb.get_text() == "старый прайс"

    time.sleep(0.01)
    kb_file.write_text("новый прайс", encoding="utf-8")
    os.utime(kb_file, None)  # обновляем mtime на «сейчас»
    assert kb.get_text() == "новый прайс"
