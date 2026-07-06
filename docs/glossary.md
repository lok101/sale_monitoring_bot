# Глоссарий

English-имена — как в коде. Env — UPPER_SNAKE в `.env`, snake_case в `Settings`.

## Kit API

| Термин | Описание |
|--------|----------|
| `GetVendingMachines` | Справочник торговых автоматов |
| `GetVMStates` | Текущие состояния ТА; поле `DateTime` — время последнего пинга |
| `GetSales` | Продажи за период |
| `VMStateModel` | Pydantic-модель элемента `GetVMStates` |
| `VendingMachineModel` | Pydantic-модель элемента `GetVendingMachines` |
| `KitGateway` | Фасад Kit API для сервисов отчёта |

## Отчёт

| Термин | Описание |
|--------|----------|
| `ReportScenario` | `TODAY` (15:00) или `COMPARE` (08:00) |
| `OfflineItem` | Аппарат в блоке «без связи» + `last_ping_timestamp` |
| `NoSalesItem` | Аппарат без продаж + `last_sale_timestamp` |
| `SalesDeclineItem` | Аппарат с падением продаж + `drop_percent` |
| `is_offline` | Domain-функция: аппарат без связи по пингу и порогу |
| `collect_offline_machines` | Сбор списка `OfflineItem` для отчёта |

## Переменные окружения

| Env | Settings field | Default | Описание |
|-----|----------------|---------|----------|
| `KIT_API_LOGIN` | `kit_api_login` | — | Kit API |
| `KIT_API_PASSWORD` | `kit_api_password` | — | Kit API |
| `KIT_API_COMPANY_ID` | `kit_api_company_id` | — | Kit API |
| `DAYS_FOR_AVERAGE` | `days_for_average` | — | N дней для среднего (≥ 2) |
| `SALES_DROP_PERCENT` | `sales_drop_percent` | — | Порог падения продаж, % |
| `TZ` | `tz` | `Asia/Yekaterinburg` | Таймзона отчёта, `now()` и границы дней |
| `KIT_API_TZ` | `kit_api_tz` | `Europe/Moscow` | Таймзона полей `DateTime` в ответах Kit API |
| `LAST_SALE_LOOKUP_DAYS` | `last_sale_lookup_days` | `10` | Окно поиска последней продажи |
| `OFFLINE_PING_THRESHOLD_MINUTES` | `offline_ping_threshold_minutes` | `25` | Минут без пинга до статуса «без связи» (≥ 1) |
| `TELEGRAM_BOT_TOKEN` | `telegram_bot_token` | — | Telegram |
| `TELEGRAM_CHAT_ID` | `telegram_chat_id` | — | Telegram |
| `YOUGILE_API_KEY` | `yougile_api_key` | — | YouGile |
| `YOUGILE_CHAT_ID` | `yougile_chat_id` | — | YouGile |
