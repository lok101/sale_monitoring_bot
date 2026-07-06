# Design: блок «Аппараты без связи» в отчёте

**Статус:** утверждён (brainstorming 2026-07-06)
**Постановка:** [tasks/offline-machines-report/TASK.md](../../tasks/offline-machines-report/TASK.md)
**Контекст:** [README.md](../../README.md)
**Смежное (вне scope):** поле `NetworkConnection` в `GetVMStates`; история состояний (`GetVendingMachineStatusHistory`)
**Глоссарий:** [glossary.md](../glossary.md)

## Переменные окружения (новые)

| Переменная | Обязательна | Default | Назначение |
|------------|-------------|---------|------------|
| `OFFLINE_PING_THRESHOLD_MINUTES` | нет | `25` | Минут с последнего пинга (`GetVMStates.DateTime`), после которых аппарат считается без связи. В `Settings`: `offline_ping_threshold_minutes`, `Field(ge=1)`. |

## Контекст

Сервис дважды в сутки формирует отчёты о продажах и отправляет в YouGile и Telegram. Операторам нужен отдельный сигнал о потере связи с аппаратом по данным Kit API.

### Текущее состояние

| Компонент / аспект | Где | Как сейчас |
|--------------------|-----|------------|
| Сценарии отчёта | `scenario_today.py`, `scenario_compare.py` | Только продажи (без продаж / падение) |
| Каталог аппаратов | `kit_client.get_vending_machines` → `KitGateway.get_active_machines` | `VendingMachineId`, `VendingMachineName`; фильтр активных в `grouping.py` |
| Состояния аппаратов | — | `GetVMStates` не вызывается |
| Модель отчёта | `domain/entities.py` | `TodayReport`, `CompareReport` без поля связи |
| Форматирование | `report_formatter.py` | Блоки только по продажам; «всё в норме» при пустых sales-блоках |
| Порог офлайна | `config.py` | Переменной нет |

### Проблемы

1. Потеря связи с аппаратом не отражается в отчёте.
2. Время последнего пинга доступно в Kit API (`GetVMStates`, поле `DateTime`), но не используется.

### Цель

В обоих ежедневных отчётах (08:00 compare, 15:00 today) первым блоком показывать **«Аппараты без связи»**: активные аппараты, у которых с момента последнего пинга прошло не меньше `OFFLINE_PING_THRESHOLD_MINUTES` минут (по умолчанию 25). Формат строки — как у блока «без продаж»: имя аппарата + `Последний пинг: DD.MM.YYYY HH:MM` (или `неизвестно`).

## Терминология

| Термин | Роль |
|--------|------|
| `GetVMStates` | Kit API: текущие состояния ТА; запрос только с `Auth` |
| `VMStateModel` | Pydantic-модель элемента ответа (`VendingMachineId`, `DateTime`) |
| `OfflineItem` | Элемент отчёта: аппарат + `last_ping_timestamp` |
| `offline_ping_threshold_minutes` | Порог офлайна в минутах (`Settings`) |
| `is_offline` | Domain-функция: аппарат без связи относительно `now` и порога |
| `collect_offline_machines` | Сбор `OfflineItem` по каталогу и индексу пингов |

## Архитектура / Решение

```
KitVendingAPIClient.get_vm_states()
        ↓
KitGateway.get_vm_states()
        ↓
build_ping_index(states) → dict[kit_id, datetime | None]
        ↓
collect_offline_machines(machines, ping_index, now, threshold)
        ↓
ScenarioTodayService / ScenarioCompareService → offline_items в отчёт
        ↓
ReportFormatter — блок «Аппараты без связи» первым
```

### Kit API (`kit_client.py`)

- Метод `get_vm_states(account=None) -> list[VMStateModel]`.
- URL: `POST https://api2.kit-invest.ru/APIService.svc/GetVMStates`.
- Тело: `{"Auth": ...}` (как `get_vending_machines`).
- Ответ: массив в ключе **`VendingMachines`** (фактический ответ API; не `VMStates`).
- `VMStateModel`: `id` ← `VendingMachineId`, `last_ping` ← `DateTime` (`BeforeValidator(_KitDateTime.from_api_str)`); пустая строка `DateTime` → `None` (custom validator или `BeforeValidator`).

### Gateway (`kit_gateway.py`)

- `get_vm_states() -> list[VMStateModel]` — прокси к клиенту.

### Domain (`grouping.py`, `entities.py`)

- `OfflineItem(machine: VendingMachineInfo, last_ping_timestamp: datetime | None)`.
- `TodayReport.offline_items`, `CompareReport.offline_items` — `list[OfflineItem]`.
- `build_ping_index(states) -> dict[int, datetime | None]` — ключ `kit_id`.
- `is_offline(last_ping, now, threshold_minutes) -> bool`:
  - `last_ping is None` → `True`;
  - иначе `now - last_ping >= timedelta(minutes=threshold_minutes)`.
- `collect_offline_machines(machines, ping_index, now, threshold_minutes) -> list[OfflineItem]`:
  - только аппараты из `machines` (уже отфильтрованы как активные);
  - `last_ping = ping_index.get(machine.kit_id)` — отсутствие ключа → `None`;
  - сортировка по `machine.name` (стабильный порядок в отчёте).

### Сценарии

- `ScenarioTodayService.build_report` и `ScenarioCompareService.build_report`:
  - после `get_active_machines()` запросить `get_vm_states()` (допустимо `asyncio.gather` с `get_sales` для сокращения latency);
  - заполнить `offline_items` через `collect_offline_machines`.
- Аппарат может одновременно попасть в блок связи и в блоки по продажам.

### Форматирование (`report_formatter.py`)

**Порядок блоков:**

| Сценарий | Порядок |
|----------|---------|
| compare (08:00) | 1. Аппараты без связи → 2. без продаж за вчера → 3. падение продаж |
| today (15:00) | 1. Аппараты без связи → 2. без продаж за сегодня |

- Заголовок: `Аппараты без связи:`.
- Строка аппарата: `{name}\nПоследний пинг: {DD.MM.YYYY HH:MM}` или `Последний пинг: неизвестно`.
- Разделитель между аппаратами: `\n---\n` (как сейчас).
- Пустой `offline_items` — блок не выводится.

**«Всё в норме»** (`main.py`): сообщение «отклонений не обнаружено» только если formatter вернул пустую строку — т.е. все блоки (включая offline) пусты.

### Config

- `Settings.offline_ping_threshold_minutes: int = Field(default=25, ge=1)`.
- `Settings.kit_api_tz: str = "Europe/Moscow"` — парсинг `DateTime` из Kit API; `TZ` — отчёт и `now()`.
- Обновить `.env.example`, `README.md`.

## Обработка ошибок (сводка)

| Ситуация | Поведение |
|----------|-----------|
| Ошибка `GetVMStates` (сеть, auth, `ResultCode`) | Исключение → отчёт не отправляется (как при сбое `GetSales`) |
| Пустой / невалидный `DateTime` | `last_ping=None` → аппарат в блоке с «неизвестно» |
| Аппарат в каталоге, нет записи в `VMStates` | `last_ping=None` → в блоке offline |
| Неактивный аппарат (`[Х]`, «тест», «офис») | Исключён на этапе `build_machine_catalog` |

## Тестирование (TDD)

| Файл / область | Тип | Сценарий |
|----------------|-----|----------|
| `tests/test_grouping.py` | happy | `is_offline` на пороге (`>=`), чуть ниже порога |
| `tests/test_grouping.py` | edge | `last_ping=None`; аппарат без state в индексе |
| `tests/test_grouping.py` | edge | неактивный аппарат не в `collect_offline_machines` |
| `tests/test_report_formatter.py` | happy | offline-блок первым в compare и today |
| `tests/test_report_formatter.py` | happy | формат `Последний пинг: …` и `неизвестно` |
| `tests/test_kit_client.py` (новый) или расширение | happy | парсинг `VMStateModel` с `DateTime`; пустая строка → `None` |
| `tests/test_scenario_*` (по необходимости) | happy | offline_items попадают в отчёт при мок gateway |

## Решения и шаги для плана

1. `kit_client.py`: `VMStateModel`, `get_vm_states()`; валидатор пустого `DateTime`.
2. `kit_gateway.py`: `get_vm_states()`.
3. `domain/entities.py`: `OfflineItem`, поля `offline_items` в отчётах.
4. `domain/grouping.py`: `build_ping_index`, `is_offline`, `collect_offline_machines`.
5. `config.py` + `.env.example`: `offline_ping_threshold_minutes`.
6. `scenario_today.py`, `scenario_compare.py`: загрузка states, заполнение `offline_items`.
7. `report_formatter.py`: `format_offline_block`, порядок блоков; передача threshold не нужна в formatter.
8. `main.py`: убедиться, что пустой текст учитывает offline (через formatter).
9. `README.md`: env и описание нового блока в сценариях.
10. Тесты по таблице выше.
11. **AGENTS.md** — файл отсутствует; при появлении — добавить `GetVMStates` в список методов Kit client.

## Границы (что НЕ входит)

- Использование `NetworkConnection` и других полей state для определения офлайна.
- Отдельные push-алерты вне cron-отчёта.
- `GetVendingMachineStatusHistory` и исторический анализ пингов.
- Дедупликация аппарата между блоками (один аппарат может быть в нескольких блоках).

## Критерии приёмки

1. `OFFLINE_PING_THRESHOLD_MINUTES` читается из env, default 25, `ge=1`; отражено в `.env.example` и `README.md`.
2. `get_vm_states()` вызывает `GetVMStates`, парсит `VendingMachines`, поле `DateTime` — время последнего пинга.
3. Аппарат без связи: `last_ping is None` или `now - last_ping >= threshold` минут; только активные аппараты из каталога.
4. Блок «Аппараты без связи» — **первый** в обоих сценариях; формат строки с `Последний пинг: …`.
5. При непустом offline-блоке и пустых sales-блоках отчёт **не** содержит «всё в норме».
6. Ошибка `GetVMStates` прерывает формирование отчёта (не silent skip).
7. `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest` — зелёные.
