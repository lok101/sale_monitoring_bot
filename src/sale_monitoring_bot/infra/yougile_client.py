from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
from beartype import beartype

from sale_monitoring_bot.config import Settings
from sale_monitoring_bot.domain.yougile import YouGileCompany, YouGileGroupChat

logger = logging.getLogger(__name__)


class YouGileAPIError(Exception):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class YouGileClient:
    def __init__(self, settings: Settings) -> None:
        settings.require_yougile_runtime()
        assert settings.yougile_api_key is not None
        assert settings.yougile_chat_id is not None
        self._api_key = settings.yougile_api_key.get_secret_value()
        self._chat_id = settings.yougile_chat_id
        self._base_url = settings.yougile_base_url

    @beartype
    async def send_message(self, text: str) -> None:
        url = f"{self._base_url}/chats/{self._chat_id}/messages"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"text": text}
        await self._request("POST", url, json_body=payload, headers=headers)

    @beartype
    @staticmethod
    async def list_group_chats(
        *,
        base_url: str,
        api_key: str,
    ) -> list[YouGileGroupChat]:
        """Список групповых чатов (GET /group-chats, с пагинацией)."""
        return await fetch_group_chats(base_url, api_key)

    @beartype
    @staticmethod
    async def list_companies(
        *,
        base_url: str,
        login: str,
        password: str,
        name: str | None = None,
    ) -> list[YouGileCompany]:
        """Список компаний аккаунта (POST /auth/companies)."""
        url = f"{base_url.rstrip('/')}/auth/companies"
        payload: dict[str, str] = {"login": login, "password": password}
        if name is not None:
            payload["name"] = name

        data = await YouGileClient._request(
            "POST",
            url,
            json_body=payload,
            headers={"Content-Type": "application/json"},
        )
        return _parse_companies(data)

    @beartype
    @staticmethod
    async def get_api_key(
        *,
        base_url: str,
        login: str,
        password: str,
        company_id: str,
    ) -> str:
        """Получить API-ключ компании (POST /auth/keys, создаёт новый ключ)."""
        url = f"{base_url.rstrip('/')}/auth/keys"
        payload = {
            "login": login,
            "password": password,
            "companyId": company_id,
        }
        data = await YouGileClient._request(
            "POST",
            url,
            json_body=payload,
            headers={"Content-Type": "application/json"},
            success_statuses=frozenset({200, 201}),
        )
        return _parse_api_key(data)

    @beartype
    @staticmethod
    async def _request(
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        success_statuses: frozenset[int] = frozenset({200, 201}),
    ) -> dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url, json=json_body, headers=headers
            ) as response:
                body = await response.text()
                if response.status not in success_statuses:
                    logger.error(
                        "YouGile API error method=%s url=%s status=%s body=%s",
                        method,
                        url,
                        response.status,
                        body,
                    )
                    raise YouGileAPIError(
                        f"YouGile API: HTTP {response.status}: {body}",
                        status=response.status,
                    )
                if not body:
                    return {}
                parsed: Any = json.loads(body)
                if not isinstance(parsed, dict):
                    raise YouGileAPIError(
                        f"YouGile API: ожидался JSON-объект, получено: {type(parsed).__name__}"
                    )
                error = parsed.get("error")
                if error:
                    raise YouGileAPIError(f"YouGile API: {error}")
                return parsed


@beartype
def _parse_api_key(data: dict[str, Any]) -> str:
    for field in ("key", "apiKey", "token"):
        value = data.get(field)
        if isinstance(value, str) and value:
            return value
    raise YouGileAPIError(
        f"YouGile API: в ответе /auth/keys нет поля key/apiKey/token: {data!r}"
    )


@beartype
def _parse_companies(data: dict[str, Any]) -> list[YouGileCompany]:
    raw_items: Any = data.get("content", data)
    if not isinstance(raw_items, list):
        raise YouGileAPIError(
            f"YouGile API: в ответе /auth/companies нет списка content: {data!r}"
        )

    companies: list[YouGileCompany] = []
    item: Any
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        company_id = item.get("id") or item.get("companyId")
        name = item.get("name") or item.get("title") or ""
        if isinstance(company_id, str) and company_id:
            companies.append(YouGileCompany(id=company_id, name=str(name)))
    return companies


@beartype
async def fetch_group_chats(base_url: str, api_key: str) -> list[YouGileGroupChat]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    root = f"{base_url.rstrip('/')}/group-chats"
    all_chats: list[YouGileGroupChat] = []
    offset = 0
    limit = 50

    while True:
        url = f"{root}?limit={limit}&offset={offset}"
        data = await YouGileClient._request("GET", url, headers=headers)
        page = _parse_group_chats(data)
        all_chats.extend(page)
        if not _has_next_page(data, page_size=len(page), limit=limit):
            break
        offset += limit

    return all_chats


@beartype
def _parse_group_chats(data: dict[str, Any]) -> list[YouGileGroupChat]:
    raw_items: Any = data.get("content", data)
    if not isinstance(raw_items, list):
        raise YouGileAPIError(
            f"YouGile API: в ответе /group-chats нет списка content: {data!r}"
        )

    chats: list[YouGileGroupChat] = []
    item: Any
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        chat_id = item.get("id")
        title = item.get("title") or item.get("name") or ""
        if isinstance(chat_id, str) and chat_id:
            chats.append(YouGileGroupChat(id=chat_id, title=str(title)))
    return chats


@beartype
def _has_next_page(data: dict[str, Any], *, page_size: int, limit: int) -> bool:
    paging: Any = data.get("paging")
    if not isinstance(paging, dict):
        return page_size >= limit

    next_flag = paging.get("next")
    if next_flag is False:
        return False
    if next_flag is True:
        return True

    total = paging.get("count")
    offset = paging.get("offset", 0)
    if isinstance(total, int) and isinstance(offset, int):
        return offset + page_size < total

    return page_size >= limit
