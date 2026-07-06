# Развёртывание sale_monitoring_bot на Ubuntu 24.04 (Docker)

Инструкция для удалённого сервера с уже установленным Docker. Предполагается доступ по SSH и отдельный Git-репозиторий для этого проекта.

Клиент Kit Vending API встроен в приложение (`infra/kit_client.py`). Для деплоя достаточно одного `git clone` каталога `sale_monitoring_bot`.

---

## 1. Подготовка Git (на вашем компьютере)

В каталоге проекта (где лежит `pyproject.toml`):

```bash
cd /path/to/sale_monitoring_bot
git init
git add .
git commit -m "Initial commit: sale monitoring bot"
```

Создайте пустой репозиторий на GitHub / GitLab / Gitea и привяжите remote:

```bash
git remote add origin git@github.com:YOUR_USER/sale_monitoring_bot.git
git branch -M main
git push -u origin main
```

Файл `.env` в Git не попадает (см. `.gitignore`) — секреты на сервер добавляются отдельно.

---

## 2. Подготовка сервера (Ubuntu 24.04)

Подключение:

```bash
ssh user@YOUR_SERVER_IP
```

### 2.1. Проверка Docker

```bash
docker --version
docker compose version
```

Если `docker compose` не найден:

```bash
sudo apt update
sudo apt install -y docker-compose-v2
```

Пользователь в группе `docker` (чтобы не писать `sudo` каждый раз):

```bash
sudo usermod -aG docker $USER
```

Выйдите из SSH и зайдите снова, чтобы группа применилась.

### 2.2. Git на сервере (если ещё нет)

```bash
sudo apt update
sudo apt install -y git
```

### 2.3. SSH-ключ для Git (рекомендуется)

На сервере:

```bash
ssh-keygen -t ed25519 -C "deploy@sale-monitoring-bot"
cat ~/.ssh/id_ed25519.pub
```

Добавьте выведенный ключ в настройки SSH Keys вашего Git-хостинга (Deploy key с правом read на нужные репозитории).

---

## 3. Клонирование на сервер

```bash
mkdir -p ~/apps
cd ~/apps
git clone git@github.com:YOUR_USER/sale_monitoring_bot.git sale_monitoring_bot
cd ~/apps/sale_monitoring_bot
```

---

## 4. Настройка переменных окружения

В каталоге `sale_monitoring_bot` на сервере:

```bash
cp .env.example .env
nano .env
```

Заполните обязательные поля (см. `.env.example`):

| Переменная | Назначение |
|------------|------------|
| `KIT_API_LOGIN`, `KIT_API_PASSWORD`, `KIT_API_COMPANY_ID` | Kit Vending |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Telegram |
| `DAYS_FOR_AVERAGE`, `SALES_DROP_PERCENT` | логика отчётов |
| `TZ` | таймзона cron (по умолчанию `Asia/Yekaterinburg`) |

Права на файл:

```bash
chmod 600 .env
```

---

## 5. Сборка и запуск контейнера

Из корня репозитория (там же лежат `Dockerfile` и `docker-compose.yml`):

```bash
cd ~/apps/sale_monitoring_bot
docker compose up -d --build
```

Проверка:

```bash
docker compose ps
docker compose logs -f
```

Контейнер `sale_monitoring_bot` работает в фоне, внутри — **cron**:

| Время (TZ из `.env`) | Задача |
|----------------------|--------|
| 08:00 | сравнение продаж (сценарий 2) |
| 15:00 | отчёт без продаж за сегодня (сценарий 1) |

Логи cron: volume `sale_monitoring_bot_logs`, внутри контейнера путь `/var/log/sale_monitoring_bot/cron.log`.

Просмотр лога:

```bash
docker compose exec sale_monitoring_bot tail -f /var/log/sale_monitoring_bot/cron.log
```

---

## 6. Ручная проверка отчёта (без ожидания cron)

Разовый запуск сценария «без продаж за сегодня»:

```bash
docker compose exec sale_monitoring_bot \
  python -m sale_monitoring_bot --no-sales-today
```

Только вывод в консоль, без отправки в Telegram:

```bash
docker compose exec sale_monitoring_bot \
  python -m sale_monitoring_bot --no-sales-today --dev
```

---

## 7. Обновление после изменений в Git

На сервере:

```bash
cd ~/apps/sale_monitoring_bot
git pull
docker compose up -d --build
```

---

## 8. Остановка и удаление

Остановить:

```bash
docker compose down
```

Остановить и удалить volume с логами:

```bash
docker compose down -v
```

---

## 9. Автозапуск после перезагрузки сервера

В `docker-compose.yml` уже указано `restart: unless-stopped`. После перезагрузки Ubuntu контейнер поднимется сам, если включён сервис Docker:

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

---

## 10. Типичные проблемы

**`Нужен KIT_API_LOGIN` при старте контейнера**  
Не создан или пустой `.env` в `sale_monitoring_bot`, либо запуск не из этой папки.

**Отчёты не уходят в Telegram**  
Проверьте токены и ID в `.env`, затем ручной запуск без `--dev` и логи:

```bash
docker compose logs --tail=100
```

**Cron не срабатывает в нужное время**  
Проверьте `TZ` в `.env` и время на сервере: `timedatectl`.

---

## Краткая шпаргалка

```bash
# первый деплой
mkdir -p ~/apps && cd ~/apps
git clone <sale_monitoring_bot-url> sale_monitoring_bot
cd sale_monitoring_bot
cp .env.example .env && nano .env
docker compose up -d --build

# обновление
git pull && docker compose up -d --build
```
