from __future__ import annotations

from sale_monitoring_bot.infra.telegram_client import _split_message


def test_split_message_short_text_unchanged() -> None:
    text = "hello"
    assert _split_message(text, 4096) == [text]


def test_split_message_by_lines() -> None:
    lines = [f"line-{index}" for index in range(100)]
    text = "\n".join(lines)
    chunks = _split_message(text, 50)
    assert len(chunks) > 1
    assert "\n".join(chunks) == text
