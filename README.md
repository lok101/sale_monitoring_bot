# sale_monitoring_bot

Сервис мониторинга продаж Kit Vending: дважды в сутки формирует отчёты и отправляет их в Telegram.

## Сценарии

| Время (TZ) | Команда | Описание |
|------------|---------|----------|
| 08:00 | `python -m sale_monitoring_bot` | Аппараты без связи; сравнение вчера со средним за N−1 дней (без сегодня) |
| 15:00 | `python -m sale_monitoring_bot --no-sales-today` | Аппараты без связи; аппараты без продаж за сегодня |

При отсутствии отклонений (включая связь) в чат уходит сообщение, что всё в норме.

Design: [docs/specs/2026-07-06-offline-machines-report-design.md](docs/specs/2026-07-06-offline-machines-report-design.md)

## Настройка

Скопируйте `.env.example` в `.env` и заполните переменные.

## Локальный запуск

```bash
uv sync --dev
uv run python -m sale_monitoring_bot --dev
uv run python -m sale_monitoring_bot --no-sales-today --dev
```

## Docker

Сборка из корня репозитория:

```bash
docker compose up -d --build
```

Клиент Kit API — `src/sale_monitoring_bot/infra/kit_client.py` (`get_sales`, `get_vending_machines`, `get_vm_states`).

Логи cron: volume `sale_monitoring_bot_logs`, файл `/var/log/sale_monitoring_bot/cron.log`.

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `KIT_API_LOGIN`, `KIT_API_PASSWORD`, `KIT_API_COMPANY_ID` | Kit Vending API |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Telegram (отчёты) |
| `DAYS_FOR_AVERAGE` | N (≥ 2) |
| `SALES_DROP_PERCENT` | Порог падения в % (0–100) |
| `TZ` | Таймзона отчёта и границ «сегодня»/«вчера» (по умолчанию `Asia/Yekaterinburg`) |
| `KIT_API_TZ` | Таймзона полей `DateTime` в ответах Kit API (по умолчанию `Europe/Moscow`) |
| `LAST_SALE_LOOKUP_DAYS` | Окно поиска последней продажи (по умолчанию 10) |
| `OFFLINE_PING_THRESHOLD_MINUTES` | Минут без пинга до статуса «без связи» (по умолчанию 25) |
