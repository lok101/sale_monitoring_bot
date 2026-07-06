# План реализации: блок «Аппараты без связи»

> **Для агентов:** Используй скилл executing-plans для реализации этого плана задача за задачей. Шаги используют чекбоксы (`- [ ]` → `- [x]`) **в этом файле** как единственный трекер прогресса (не TodoWrite). После каждого шага — отметка `[x]`; `plan-code-review` пропускает задачи с открытыми `[ ]`.

**Цель:** В обоих ежедневных отчётах первым блоком показывать «Аппараты без связи» по `GetVMStates.DateTime` и порогу `OFFLINE_PING_THRESHOLD_MINUTES` (default 25).

**Архитектура:** Новый метод `get_vm_states` в `kit_client` / `KitGateway`; domain-функции `build_ping_index`, `is_offline`, `collect_offline_machines`; сущность `OfflineItem` и поле `offline_items` в отчётах; сценарии загружают states параллельно с sales; `ReportFormatter` выводит offline-блок первым.

**Ключевые файлы / стек:** Python 3.12, `beartype`, `pydantic`/`pydantic-settings`, `aiohttp`; образцы — `kit_client.get_vending_machines`, `tests/test_grouping.py`, `tests/test_report_formatter.py`.

**Спек:** [docs/specs/2026-07-06-offline-machines-report-design.md](../specs/2026-07-06-offline-machines-report-design.md) · **Постановка:** [tasks/offline-machines-report/TASK.md](../../tasks/offline-machines-report/TASK.md)

**Стиль тестов:** `.cursor/rules/test-style.mdc` (sync pytest, явные даты). **Команды:** `uv run pytest`, `uv run mypy`.

**Статус post-review:** —

## Post-review (правки)

| Задача | Родитель | Источник | Суть | Статус |
|--------|----------|----------|------|--------|
| _(пусто до plan-code-review)_ | | | | |

---

## Покрытие спека

| Требование / решение из спека | Задача |
|-------------------------------|--------|
| `OFFLINE_PING_THRESHOLD_MINUTES`, default 25, `ge=1` | 1, 9 |
| `VMStateModel`, `get_vm_states()`, парсинг `VMStates` | 4 |
| `KitGateway.get_vm_states()` | 5 |
| `OfflineItem`, `offline_items` в отчётах | 2 |
| `build_ping_index`, `is_offline`, `collect_offline_machines` | 3 |
| Сценарии: загрузка states, `offline_items` | 6 |
| Formatter: блок первым, формат пинга | 7 |
| «Всё в норме» только при пустых всех блоках | 7 |
| `.env.example`, README | 9 |
| Ошибка `GetVMStates` → исключение (через `_post`) | 4 |
| Критерий CI: ruff, format, mypy, pytest | 10 |

---

## Карта файлов

**Создать:**
- `tests/test_config.py` — default и валидация `offline_ping_threshold_minutes`
- `tests/test_kit_client.py` — парсинг `VMStateModel`

**Изменить:**
- `src/sale_monitoring_bot/config.py` — поле `offline_ping_threshold_minutes`
- `src/sale_monitoring_bot/domain/entities.py` — `OfflineItem`, `offline_items`
- `src/sale_monitoring_bot/domain/grouping.py` — ping index, offline detection
- `src/sale_monitoring_bot/infra/kit_client.py` — `VMStateModel`, `get_vm_states`
- `src/sale_monitoring_bot/infra/kit_gateway.py` — `get_vm_states`
- `src/sale_monitoring_bot/services/scenario_today.py` — offline_items
- `src/sale_monitoring_bot/services/scenario_compare.py` — offline_items
- `src/sale_monitoring_bot/services/report_formatter.py` — offline-блок
- `tests/test_grouping.py` — domain offline tests
- `tests/test_report_formatter.py` — formatter offline tests
- `tests/test_scenario_offline.py` — сценарии с fake gateway (создать)
- `.env.example` — `OFFLINE_PING_THRESHOLD_MINUTES`
- `tasks/offline-machines-report/TASK.md` — ссылка на план

**Порядок выполнения:** 1 (config) → 2 (entities) → 3 (grouping) → 4 (kit_client) → 5 (gateway) → 6 (scenarios) → 7 (formatter) → 8 (wiring check) → 9 (env/docs) → 10 (quality gate)

---

## Задача 1: Config — `offline_ping_threshold_minutes`

**Файлы:**
- Изменить: `src/sale_monitoring_bot/config.py`
- Создать: `tests/test_config.py`

- [x] **Шаг 1: Написать падающий тест (happy — default)**

```python
# tests/test_config.py
from __future__ import annotations

from sale_monitoring_bot.config import Settings


def test_offline_ping_threshold_minutes_default(monkeypatch) -> None:
    monkeypatch.delenv("OFFLINE_PING_THRESHOLD_MINUTES", raising=False)
    monkeypatch.setenv("KIT_API_LOGIN", "u")
    monkeypatch.setenv("KIT_API_PASSWORD", "p")
    monkeypatch.setenv("KIT_API_COMPANY_ID", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.setenv("DAYS_FOR_AVERAGE", "6")
    monkeypatch.setenv("SALES_DROP_PERCENT", "30")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.offline_ping_threshold_minutes == 25
```

- [x] **Шаг 2: Запустить тест и убедиться что он падает**

Запуск: `uv run pytest tests/test_config.py::test_offline_ping_threshold_minutes_default -q`  
Ожидается: FAIL (`AttributeError: 'Settings' object has no attribute 'offline_ping_threshold_minutes'`)

- [x] **Шаг 3: Добавить поле в Settings**

```python
# src/sale_monitoring_bot/config.py — после last_sale_lookup_days
offline_ping_threshold_minutes: int = Field(default=25, ge=1)
```

- [x] **Шаг 4: Запустить тест и убедиться что он проходит**

Запуск: `uv run pytest tests/test_config.py::test_offline_ping_threshold_minutes_default -q`  
Ожидается: PASS

- [x] **Шаг 5: Тест edge — env override и error при ge=0**

```python
def test_offline_ping_threshold_minutes_from_env(monkeypatch) -> None:
    monkeypatch.setenv("OFFLINE_PING_THRESHOLD_MINUTES", "30")
    # ... те же обязательные env что в шаге 1 ...
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.offline_ping_threshold_minutes == 30


def test_offline_ping_threshold_minutes_rejects_zero(monkeypatch) -> None:
    monkeypatch.setenv("OFFLINE_PING_THRESHOLD_MINUTES", "0")
    # ... обязательные env ...
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]
```

Запуск: `uv run pytest tests/test_config.py -q` → PASS

---

## Задача 2: Domain entities — `OfflineItem`

**Файлы:**
- Изменить: `src/sale_monitoring_bot/domain/entities.py`

- [x] **Шаг 1: Добавить `OfflineItem` и поля `offline_items`**

```python
@dataclass(frozen=True, slots=True)
class OfflineItem:
    machine: VendingMachineInfo
    last_ping_timestamp: datetime | None


@dataclass(frozen=True, slots=True)
class TodayReport:
    items: list[NoSalesItem]
    offline_items: list[OfflineItem]


@dataclass(frozen=True, slots=True)
class CompareReport:
    no_sales_yesterday: list[NoSalesItem]
    sales_decline: list[SalesDeclineItem]
    offline_items: list[OfflineItem]
```

- [x] **Шаг 2: Обновить существующие тесты/вызовы с пустым `offline_items`**

В `tests/test_report_formatter.py` все `TodayReport(...)` и `CompareReport(...)` дополнить `offline_items=[]`.

Запуск: `uv run pytest tests/test_report_formatter.py -q`  
Ожидается: PASS (после правки конструкторов; до правки — `TypeError` на missing argument)

---

## Задача 3: Domain grouping — offline detection

**Файлы:**
- Изменить: `src/sale_monitoring_bot/domain/grouping.py`
- Изменить: `tests/test_grouping.py`

- [x] **Шаг 1: Написать падающие тесты (happy + edge)**

```python
# tests/test_grouping.py — добавить импорты
from datetime import timedelta

from sale_monitoring_bot.domain.entities import OfflineItem, VendingMachineInfo
from sale_monitoring_bot.infra.kit_client import VMStateModel
from sale_monitoring_bot.domain.grouping import (
    build_ping_index,
    collect_offline_machines,
    is_offline,
)

_MACHINE = VendingMachineInfo(key="101", name="[101] Кофе", kit_id=1006360)
_NOW = datetime(2026, 7, 6, 13, 12, 13, tzinfo=_TZ)


def test_is_offline_at_threshold() -> None:
    ping = _NOW - timedelta(minutes=25)
    assert is_offline(ping, _NOW, 25) is True


def test_is_offline_below_threshold() -> None:
    ping = _NOW - timedelta(minutes=24, seconds=59)
    assert is_offline(ping, _NOW, 25) is False


def test_is_offline_when_ping_none() -> None:
    assert is_offline(None, _NOW, 25) is True


def test_build_ping_index() -> None:
    states = [
        VMStateModel.model_validate(
            {"VendingMachineId": 1, "DateTime": "06.07.2026 12:47:13"}
        ),
        VMStateModel.model_validate({"VendingMachineId": 2, "DateTime": ""}),
    ]
    index = build_ping_index(states)
    assert index[1] == datetime(2026, 7, 6, 12, 47, 13, tzinfo=_TZ)
    assert index[2] is None


def test_collect_offline_machines_missing_state() -> None:
    machines = {"101": _MACHINE}
    items = collect_offline_machines(machines, {}, _NOW, 25)
    assert len(items) == 1
    assert items[0].last_ping_timestamp is None


def test_collect_offline_machines_sorts_by_name() -> None:
    m_a = VendingMachineInfo(key="101", name="[101] А", kit_id=1)
    m_b = VendingMachineInfo(key="202", name="[202] Б", kit_id=2)
    machines = {"101": m_a, "202": m_b}
    ping_index = {
        1: _NOW - timedelta(minutes=30),
        2: _NOW - timedelta(minutes=5),
    }
    items = collect_offline_machines(machines, ping_index, _NOW, 25)
    assert [i.machine.name for i in items] == ["[101] А"]
```

- [x] **Шаг 2: Запустить тесты и убедиться что падают**

Запуск: `uv run pytest tests/test_grouping.py::test_is_offline_at_threshold -q`  
Ожидается: FAIL (`ImportError: cannot import name 'is_offline'`)

- [x] **Шаг 3: Реализовать функции**

```python
# src/sale_monitoring_bot/domain/grouping.py
from datetime import timedelta

from sale_monitoring_bot.domain.entities import OfflineItem, VendingMachineInfo
from sale_monitoring_bot.infra.kit_client import VMStateModel


@beartype
def is_offline(
    last_ping: datetime | None,
    now: datetime,
    threshold_minutes: int,
) -> bool:
    if last_ping is None:
        return True
    return now - last_ping >= timedelta(minutes=threshold_minutes)


@beartype
def build_ping_index(states: Iterable[VMStateModel]) -> dict[int, datetime | None]:
    return {state.id: state.last_ping for state in states}


@beartype
def collect_offline_machines(
    machines: dict[str, VendingMachineInfo],
    ping_index: dict[int, datetime | None],
    now: datetime,
    threshold_minutes: int,
) -> list[OfflineItem]:
    items: list[OfflineItem] = []
    for machine in machines.values():
        last_ping = ping_index.get(machine.kit_id)
        if not is_offline(last_ping, now, threshold_minutes):
            continue
        items.append(
            OfflineItem(machine=machine, last_ping_timestamp=last_ping)
        )
    items.sort(key=lambda item: item.machine.name)
    return items
```

- [x] **Шаг 4: Запустить все новые тесты grouping**

Запуск: `uv run pytest tests/test_grouping.py -q`  
Ожидается: PASS

---

## Задача 4: Kit client — `VMStateModel` и `get_vm_states`

**Файлы:**
- Изменить: `src/sale_monitoring_bot/infra/kit_client.py`
- Создать: `tests/test_kit_client.py`

- [x] **Шаг 1: Написать падающие тесты парсинга (happy + edge)**

```python
# tests/test_kit_client.py
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sale_monitoring_bot.infra.kit_client import VMStateModel

_TZ = ZoneInfo("Asia/Yekaterinburg")


def test_vm_state_model_parses_datetime() -> None:
    model = VMStateModel.model_validate(
        {
            "VendingMachineId": 1006360,
            "DateTime": "06.07.2026 12:47:13",
            "NetworkConnection": 0,
        }
    )
    assert model.id == 1006360
    assert model.last_ping == datetime(2026, 7, 6, 12, 47, 13, tzinfo=_TZ)


def test_vm_state_model_empty_datetime_is_none() -> None:
    model = VMStateModel.model_validate(
        {"VendingMachineId": 1, "DateTime": ""}
    )
    assert model.last_ping is None
```

- [x] **Шаг 2: Запустить тесты — FAIL**

Запуск: `uv run pytest tests/test_kit_client.py -q`  
Ожидается: FAIL (`ImportError: cannot import name 'VMStateModel'`)

- [x] **Шаг 3: Добавить валидатор и модель**

```python
# kit_client.py — перед SaleModel
def _parse_optional_kit_datetime(val: object) -> datetime | None:
    if val is None or val == "":
        return None
    if not isinstance(val, str):
        raise TypeError("DateTime must be str or empty")
    return _KitDateTime.from_api_str(val)


class VMStateModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Annotated[int, Field(validation_alias="VendingMachineId")]
    last_ping: Annotated[
        datetime | None,
        Field(validation_alias="DateTime"),
        BeforeValidator(_parse_optional_kit_datetime),
    ] = None
```

- [x] **Шаг 4: Добавить `get_vm_states` (по образцу `get_vending_machines`)**

```python
async def get_vm_states(
    self,
    account: KitAPIAccount | None = None,
) -> list[VMStateModel]:
    url = f"{self._BASE_URL}/GetVMStates"

    async def build_data() -> dict[str, Any]:
        request_id = int(time.time_ns())
        return {"Auth": self._build_auth(request_id, account)}

    response = await self._post(url, build_data)
    return [
        VMStateModel.model_validate(item)
        for item in response["VMStates"]
    ]
```

- [x] **Шаг 5: Запустить тесты парсинга**

Запуск: `uv run pytest tests/test_kit_client.py -q`  
Ожидается: PASS

---

## Задача 5: KitGateway — прокси `get_vm_states`

**Файлы:**
- Изменить: `src/sale_monitoring_bot/infra/kit_gateway.py`

- [x] **Шаг 1: Добавить импорт `VMStateModel` и метод**

```python
from sale_monitoring_bot.infra.kit_client import (
    KitVendingAPIClient,
    SaleModel,
    VendingMachineModel,
    VMStateModel,
)

@beartype
async def get_vm_states(self) -> list[VMStateModel]:
    return await self._client.get_vm_states()
```

- [x] **Шаг 2: Проверить типы**

Запуск: `uv run mypy`  
Ожидается: Success (или без новых ошибок в изменённых файлах)

---

## Задача 6: Сценарии — заполнение `offline_items`

**Файлы:**
- Изменить: `src/sale_monitoring_bot/services/scenario_today.py`
- Изменить: `src/sale_monitoring_bot/services/scenario_compare.py`
- Создать: `tests/test_scenario_offline.py`

- [x] **Шаг 1: Написать падающий тест с fake gateway (happy)**

```python
# tests/test_scenario_offline.py
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from sale_monitoring_bot.config import Settings
from sale_monitoring_bot.domain.entities import VendingMachineInfo
from sale_monitoring_bot.infra.kit_client import SaleModel, VMStateModel
from sale_monitoring_bot.services.scenario_today import ScenarioTodayService

_TZ = ZoneInfo("Asia/Yekaterinburg")


class _FakeGateway:
    def __init__(self) -> None:
        self.machine = VendingMachineInfo(key="101", name="[101] Кофе", kit_id=1)

    async def get_active_machines(self):
        return {"101": self.machine}

    async def get_vm_states(self):
        return [
            VMStateModel.model_validate(
                {
                    "VendingMachineId": 1,
                    "DateTime": (datetime.now(_TZ) - timedelta(minutes=40)).strftime(
                        "%d.%m.%Y %H:%M:%S"
                    ),
                }
            )
        ]

    async def get_sales(self, from_date, to_date):
        return []


def _settings(monkeypatch) -> Settings:
    monkeypatch.setenv("KIT_API_LOGIN", "u")
    monkeypatch.setenv("KIT_API_PASSWORD", "p")
    monkeypatch.setenv("KIT_API_COMPANY_ID", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.setenv("DAYS_FOR_AVERAGE", "6")
    monkeypatch.setenv("SALES_DROP_PERCENT", "30")
    monkeypatch.setenv("OFFLINE_PING_THRESHOLD_MINUTES", "25")
    return Settings(_env_file=None)  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_scenario_today_includes_offline_items(monkeypatch) -> None:
    service = ScenarioTodayService(_settings(monkeypatch), _FakeGateway())
    report = await service.build_report()
    assert len(report.offline_items) == 1
    assert report.offline_items[0].machine.kit_id == 1
```

- [x] **Шаг 2: Запустить тест — FAIL**

Запуск: `uv run pytest tests/test_scenario_offline.py::test_scenario_today_includes_offline_items -q`  
Ожидается: FAIL (`AttributeError` или `TypeError` на `offline_items`)

- [x] **Шаг 3: Обновить `scenario_today.py`**

```python
import asyncio

from sale_monitoring_bot.domain.entities import NoSalesItem, OfflineItem, TodayReport, ...
from sale_monitoring_bot.domain.grouping import (
    build_ping_index,
    collect_offline_machines,
    ...
)

# в build_report после machines = await ...
states, sales = await asyncio.gather(
    self._gateway.get_vm_states(),
    self._gateway.get_sales(from_date=lookup_from, to_date=now),
)
ping_index = build_ping_index(states)
offline_items = collect_offline_machines(
    machines,
    ping_index,
    now,
    self._settings.offline_ping_threshold_minutes,
)
# ...
return TodayReport(items=items, offline_items=offline_items)
```

- [x] **Шаг 4: Аналогично обновить `scenario_compare.py`**

Тот же паттерн: `asyncio.gather(get_vm_states, get_sales)`, `offline_items` в `CompareReport(...)`.

- [x] **Шаг 5: Запустить тест сценария**

Запуск: `uv run pytest tests/test_scenario_offline.py -q`  
Ожидается: PASS

---

## Задача 7: ReportFormatter — блок «Аппараты без связи»

**Файлы:**
- Изменить: `src/sale_monitoring_bot/services/report_formatter.py`
- Изменить: `tests/test_report_formatter.py`

- [x] **Шаг 1: Написать падающие тесты (happy + edge)**

```python
from sale_monitoring_bot.domain.entities import OfflineItem

_OFFLINE_TS = datetime(2026, 7, 6, 12, 47, tzinfo=_TZ)


def test_format_compare_offline_block_first(monkeypatch) -> None:
    # monkeypatch datetime как в существующих тестах
    report = CompareReport(
        offline_items=[
            OfflineItem(machine=_MACHINE, last_ping_timestamp=_OFFLINE_TS),
        ],
        no_sales_yesterday=[],
        sales_decline=[],
    )
    text = formatter.format_compare(report)
    assert text.startswith("Аппараты без связи:")
    assert "Последний пинг: 06.07.2026 12:47" in text


def test_format_compare_offline_unknown_ping(monkeypatch) -> None:
    report = CompareReport(
        offline_items=[OfflineItem(machine=_MACHINE, last_ping_timestamp=None)],
        no_sales_yesterday=[],
        sales_decline=[],
    )
    text = formatter.format_compare(report)
    assert "Последний пинг: неизвестно" in text


def test_format_today_only_offline_returns_text(monkeypatch) -> None:
    report = TodayReport(
        items=[],
        offline_items=[
            OfflineItem(machine=_MACHINE, last_ping_timestamp=_OFFLINE_TS),
        ],
    )
    text = formatter.format_today(report)
    assert text != ""
    assert "Аппараты без связи:" in text
```

- [x] **Шаг 2: Запустить — FAIL**

Запуск: `uv run pytest tests/test_report_formatter.py::test_format_compare_offline_block_first -q`  
Ожидается: FAIL (блок не выводится / нет заголовка)

- [x] **Шаг 3: Реализовать formatter**

```python
from sale_monitoring_bot.domain.entities import OfflineItem, ...

@beartype
def _format_offline_item(self, item: OfflineItem) -> str:
    return f"{item.machine.name}\n{self._format_last_ping(item.last_ping_timestamp)}"

@beartype
def _format_last_ping(self, timestamp: datetime | None) -> str:
    if timestamp is None:
        return "Последний пинг: неизвестно"
    return f"Последний пинг: {timestamp.strftime('%d.%m.%Y %H:%M')}"

@beartype
def _format_offline_block(self, items: list[OfflineItem]) -> str:
    body = [self._format_offline_item(item) for item in items]
    return self._format_block("Аппараты без связи:", body)

# format_compare — в начале sections:
if report.offline_items:
    sections.append(self._format_offline_block(report.offline_items))

# format_today — собрать sections из offline + no_sales; return join или ""
```

- [x] **Шаг 4: Запустить все тесты formatter**

Запуск: `uv run pytest tests/test_report_formatter.py -q`  
Ожидается: PASS

---

## Задача 8: Wiring — `main.py` и «всё в норме»

**Файлы:**
- Проверить: `src/sale_monitoring_bot/main.py` (изменений может не потребоваться)

- [x] **Шаг 1: Убедиться что логика `main` корректна без правок**

`main.py` вызывает `format_today` / `format_compare`; при непустом только offline-блоке formatter вернёт непустой `text` → `format_all_ok` не вызовется. Подтвердить тестом из задачи 7 (`test_format_today_only_offline_returns_text`).

- [x] **Шаг 2: Полный прогон юнит-тестов**

Запуск: `uv run pytest -q`  
Ожидается: 0 failed

---

## Задача 9: Env и документация

**Файлы:**
- Изменить: `.env.example`
- Проверить: `README.md` (уже обновлён в brainstorming; добавить строку в `.env.example`)

- [x] **Шаг 1: Добавить в `.env.example`**

```
OFFLINE_PING_THRESHOLD_MINUTES=25
```

(после `LAST_SALE_LOOKUP_DAYS=10`)

- [x] **Шаг 2: Обновить `tasks/offline-machines-report/TASK.md`**

Добавить строку: **План:** [docs/plans/2026-07-06-offline-machines-report.md](../../docs/plans/2026-07-06-offline-machines-report.md)

- [x] **Шаг 3: Grep — env упомянут в README и glossary**

Запуск: `rg OFFLINE_PING_THRESHOLD README.md docs/glossary.md .env.example`  
Ожидается: совпадения во всех трёх файлах

---

## Задача 10: Проверки качества кода (финальный гейт)

- [x] **Шаг 1: Ruff (линт)** — `uv run ruff check .` → exit 0 (если ruff не в dev-deps: `uv add --dev ruff` или пропустить с пометкой в отчёте)

- [x] **Шаг 2: Ruff (формат)** — `uv run ruff format --check .` → exit 0

- [x] **Шаг 3: Типы** — `uv run mypy` → Success

- [x] **Шаг 4: Все тесты** — `uv run pytest -q` → 0 failed

---

## Самопроверка (для исполнителя, после всех задач)

- [x] Критерий 1: env default 25, `ge=1`, `.env.example`, README (Задачи 1, 9)
- [x] Критерий 2: `get_vm_states`, `VMStates`, `DateTime` (Задача 4, `test_kit_client.py`)
- [x] Критерий 3: offline logic, только активные аппараты (Задача 3, `test_grouping.py`)
- [x] Критерий 4: блок первым, формат пинга (Задача 7, `test_report_formatter.py`)
- [x] Критерий 5: не «всё в норме» при offline (Задача 7, `test_format_today_only_offline_returns_text`)
- [x] Критерий 6: ошибка API через `_post` без silent skip (Задача 4 — наследование поведения)
- [x] Критерий 7: ruff + mypy + pytest зелёные (Задача 10)
