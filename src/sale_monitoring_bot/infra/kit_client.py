"""Минимальный клиент Kit Vending API для мониторинга продаж."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from types import TracebackType
from typing import Annotated, Any, cast
from zoneinfo import ZoneInfo

import aiohttp
from aiohttp import ClientError as AioHTTPClientError, ContentTypeError
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, computed_field

_VM_CODE_RE = re.compile(r"\[(\d{3})\]")
_KIT_DATETIME_FORMAT = "%d.%m.%Y %H:%M:%S"
_DEFAULT_TZ = ZoneInfo("Asia/Yekaterinburg")


class KitAPIError(Exception):
    pass


class KitAPIAuthError(KitAPIError):
    pass


class KitAPIResponseError(KitAPIError):
    def __init__(self, message: str, *, result_code: int) -> None:
        super().__init__(message)
        self.result_code = result_code


class KitAPINetworkError(KitAPIError):
    pass


class KitAPIValidationError(KitAPIError):
    pass


class ResultCode(IntEnum):
    SUCCESS = 0
    TOO_MANY_REQUEST = 27


def _extract_vending_machine_code(vending_machine_name: str) -> str | None:
    match = _VM_CODE_RE.search(vending_machine_name)
    return match.group(1) if match else None


class _KitDateTime:
    _tz: ZoneInfo = _DEFAULT_TZ

    @classmethod
    def set_timezone(cls, tz: ZoneInfo) -> None:
        cls._tz = tz

    @classmethod
    def to_api_str(cls, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=cls._tz)
        else:
            dt = dt.astimezone(cls._tz)
        return dt.strftime(_KIT_DATETIME_FORMAT)

    @classmethod
    def from_api_str(cls, val: str) -> datetime:
        dt = datetime.strptime(val, _KIT_DATETIME_FORMAT)
        return dt.replace(tzinfo=cls._tz)


class _RateLimiter:
    def __init__(self, max_requests: int, time_window: float) -> None:
        self._max_requests = max_requests
        self._time_window = time_window
        self._requests: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            while self._requests and self._requests[0] <= now - self._time_window:
                self._requests.popleft()
            if len(self._requests) < self._max_requests:
                self._requests.append(now)
                return
            wait_until = self._requests[0] + self._time_window
            wait_time = max(0.0, wait_until - now)
            self._requests.append(wait_until)
            self._requests.popleft()
            if wait_time > 0:
                await asyncio.sleep(wait_time)


class _GlobalBackoff:
    def __init__(self, timeout: float) -> None:
        self._timeout = timeout
        self._event: asyncio.Event | None = None
        self._lock: asyncio.Lock | None = None

    def _ensure_initialized(self) -> None:
        if self._event is None:
            self._event = asyncio.Event()
            self._event.set()
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def wait_if_blocked(self) -> None:
        self._ensure_initialized()
        assert self._event is not None
        await self._event.wait()

    async def trigger_backoff(self) -> None:
        self._ensure_initialized()
        assert self._lock is not None
        assert self._event is not None
        async with self._lock:
            if self._event.is_set():
                self._event.clear()
                asyncio.create_task(self._backoff_timer())
        await self._event.wait()

    async def _backoff_timer(self) -> None:
        try:
            await asyncio.sleep(self._timeout)
        finally:
            assert self._event is not None
            self._event.set()


try:
    _MAX_REQUESTS = int(os.getenv("KIT_API_REQUEST_PER_WINDOW", "1"))
    _TIME_WINDOW = float(os.getenv("KIT_API_WINDOW_SECONDS", "10"))
    _BACKOFF_SECONDS = float(os.getenv("KIT_API_BACKOFF_SECONDS", "60"))
except ValueError as exc:
    raise KitAPIValidationError(
        "KIT_API_REQUEST_PER_WINDOW, KIT_API_WINDOW_SECONDS и KIT_API_BACKOFF_SECONDS "
        "(.env) должны быть числами."
    ) from exc


@dataclass(frozen=True, slots=True, kw_only=True)
class KitAPIAccount:
    login: str
    password: str
    company_id: int


class SaleModel(BaseModel):
    price: Annotated[float, Field(validation_alias="Sum")]
    timestamp: Annotated[
        datetime,
        Field(validation_alias="DateTime"),
        BeforeValidator(_KitDateTime.from_api_str),
    ]
    vending_machine_id: Annotated[int, Field(validation_alias="VendingMachine")]
    vending_machine_name: Annotated[str, Field(validation_alias="VendingMachineName")]

    @computed_field
    @property
    def vending_machine_code(self) -> str | None:
        return _extract_vending_machine_code(self.vending_machine_name)


class VendingMachineModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Annotated[int, Field(validation_alias="VendingMachineId")]
    name: Annotated[str, Field(validation_alias="VendingMachineName")]

    @computed_field
    @property
    def code(self) -> str | None:
        return _extract_vending_machine_code(self.name)


class KitVendingAPIClient:
    _BASE_URL = "https://api2.kit-invest.ru/APIService.svc"

    def __init__(
        self,
        account: KitAPIAccount | None = None,
        *,
        timezone: ZoneInfo | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        if timezone is not None:
            _KitDateTime.set_timezone(timezone)

        self._login: str | None = None
        self._password: str | None = None
        self._company_id: int | None = None
        if account is not None:
            self._login = account.login
            self._password = account.password
            self._company_id = account.company_id

        self._session = session
        self._own_session = session is None
        self._rate_limiter = _RateLimiter(_MAX_REQUESTS, _TIME_WINDOW)
        self._backoff = _GlobalBackoff(_BACKOFF_SECONDS)

    def is_authenticated(self) -> bool:
        return (
            self._login is not None
            and self._password is not None
            and self._company_id is not None
        )

    async def get_sales(
        self,
        from_date: datetime,
        to_date: datetime,
        *,
        vending_machine_id: int | None = None,
        account: KitAPIAccount | None = None,
    ) -> list[SaleModel]:
        url = f"{self._BASE_URL}/GetSales"

        async def build_data() -> dict[str, Any]:
            request_id = int(time.time_ns())
            filter_data: dict[str, Any] = {
                "Filter": {
                    "UpDate": _KitDateTime.to_api_str(from_date),
                    "ToDate": _KitDateTime.to_api_str(to_date),
                }
            }
            if vending_machine_id is not None:
                filter_data["Filter"]["VendingMachineId"] = vending_machine_id
            return {"Auth": self._build_auth(request_id, account), **filter_data}

        response = await self._post(url, build_data)
        return [SaleModel.model_validate(item) for item in response["Sales"]]

    async def get_vending_machines(
        self,
        account: KitAPIAccount | None = None,
    ) -> list[VendingMachineModel]:
        url = f"{self._BASE_URL}/GetVendingMachines"

        async def build_data() -> dict[str, Any]:
            request_id = int(time.time_ns())
            return {"Auth": self._build_auth(request_id, account)}

        response = await self._post(url, build_data)
        return [
            VendingMachineModel.model_validate(item)
            for item in response["VendingMachines"]
        ]

    async def close(self) -> None:
        if self._session and not self._session.closed and self._own_session:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> KitVendingAPIClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    def _build_auth(
        self,
        request_id: int,
        account: KitAPIAccount | None,
    ) -> dict[str, Any]:
        if account is not None:
            login = account.login
            password = account.password
            company_id = account.company_id
        elif self.is_authenticated():
            assert self._login is not None
            assert self._password is not None
            assert self._company_id is not None
            login = self._login
            password = self._password
            company_id = self._company_id
        else:
            raise KitAPIAuthError(
                "Учётные данные не установлены. Передайте KitAPIAccount в конструктор "
                "или в аргументе метода."
            )

        sign = hashlib.md5(
            f"{company_id}{password}{request_id}".encode("utf-8")
        ).hexdigest()
        return {
            "CompanyId": company_id,
            "RequestId": request_id,
            "UserLogin": login,
            "Sign": sign,
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        return self._session

    async def _post(
        self,
        url: str,
        build_data: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        max_retries = 2
        for attempt in range(max_retries):
            await self._backoff.wait_if_blocked()
            await self._rate_limiter.wait()
            data = await build_data()
            session = await self._get_session()
            try:
                async with session.post(url=url, data=json.dumps(data)) as response:
                    response.raise_for_status()
                    try:
                        response_data = cast(dict[str, Any], await response.json())
                    except (ContentTypeError, json.JSONDecodeError) as exc:
                        raise KitAPIResponseError(
                            f"Не удалось разобрать JSON ответ от API: {exc}",
                            result_code=-1,
                        ) from exc

                    try:
                        result_code = int(response_data["ResultCode"])
                    except KeyError as exc:
                        raise KitAPIResponseError(
                            "Ответ API не содержит поле ResultCode",
                            result_code=-1,
                        ) from exc

                    if result_code == ResultCode.TOO_MANY_REQUEST:
                        if attempt < max_retries - 1:
                            await self._backoff.trigger_backoff()
                            continue
                        raise KitAPIResponseError(
                            f"Превышен лимит запросов к API после {max_retries} попыток",
                            result_code=result_code,
                        )

                    if result_code != ResultCode.SUCCESS:
                        message = response_data.get(
                            "ErrorMessage", "Неизвестная ошибка"
                        )
                        raise KitAPIResponseError(
                            "Не удалось получить данные от Kit API, "
                            f"код ответа — {result_code}, текст: {message}",
                            result_code=result_code,
                        )
                    return response_data
            except AioHTTPClientError as exc:
                raise KitAPINetworkError(f"Ошибка сети: {exc}") from exc
            except KitAPIResponseError:
                raise
            except Exception as exc:
                raise KitAPIError(
                    f"Неожиданная ошибка при выполнении запроса: {exc}"
                ) from exc

        raise KitAPIError("Неожиданное завершение цикла retry")
