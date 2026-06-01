from __future__ import annotations

import pytest

from sale_monitoring_bot.infra.yougile_client import (
    YouGileAPIError,
    _has_next_page,
    _parse_api_key,
    _parse_companies,
    _parse_group_chats,
)


def test_parse_api_key_from_key_field() -> None:
    assert _parse_api_key({"key": "secret-token"}) == "secret-token"


def test_parse_api_key_missing_raises() -> None:
    with pytest.raises(YouGileAPIError):
        _parse_api_key({})


def test_parse_companies_from_content() -> None:
    companies = _parse_companies(
        {
            "content": [
                {"id": "uuid-1", "name": "ООО Тест"},
                {"id": "uuid-2", "title": "Другая"},
            ]
        }
    )
    assert len(companies) == 2
    assert companies[0].id == "uuid-1"
    assert companies[0].name == "ООО Тест"
    assert companies[1].name == "Другая"


def test_parse_group_chats_from_content() -> None:
    chats = _parse_group_chats(
        {
            "content": [
                {"id": "chat-1", "title": "Отчёты"},
                {"id": "chat-2", "name": "Общий"},
            ]
        }
    )
    assert len(chats) == 2
    assert chats[0].id == "chat-1"
    assert chats[0].title == "Отчёты"
    assert chats[1].title == "Общий"


def test_has_next_page_uses_paging_next() -> None:
    assert _has_next_page({"paging": {"next": True}}, page_size=50, limit=50) is True
    assert _has_next_page({"paging": {"next": False}}, page_size=10, limit=50) is False
