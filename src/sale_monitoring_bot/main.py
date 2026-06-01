from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from beartype import beartype

from sale_monitoring_bot.config import Settings, get_settings
from sale_monitoring_bot.domain.entities import ReportScenario
from sale_monitoring_bot.infra.kit_gateway import KitGateway
from sale_monitoring_bot.infra.telegram_client import TelegramClient
from sale_monitoring_bot.infra.yougile_client import YouGileAPIError, YouGileClient
from sale_monitoring_bot.services.report_formatter import ReportFormatter
from sale_monitoring_bot.services.scenario_compare import ScenarioCompareService
from sale_monitoring_bot.services.scenario_today import ScenarioTodayService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@beartype
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Мониторинг продаж Kit Vending → YouGile и Telegram"
    )
    parser.add_argument(
        "--no-sales-today",
        action="store_true",
        help="Отчёт: аппараты без продаж за сегодня (сценарий 1)",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Вывести отчёт в stdout, не отправлять в YouGile и Telegram",
    )
    parser.add_argument(
        "--get-yougile-api-key",
        action="store_true",
        help="Получить API-ключ YouGile (YOUGILE_LOGIN, YOUGILE_PASSWORD, YOUGILE_COMPANY_ID)",
    )
    parser.add_argument(
        "--list-yougile-companies",
        action="store_true",
        help="Список компаний YouGile (YOUGILE_LOGIN, YOUGILE_PASSWORD)",
    )
    parser.add_argument(
        "--list-yougile-group-chats",
        action="store_true",
        help="Список групповых чатов YouGile (YOUGILE_API_KEY)",
    )
    return parser.parse_args(argv)


@beartype
async def _run_get_api_key(settings: Settings) -> None:
    login, password, company_id = settings.require_yougile_auth()
    api_key = await YouGileClient.get_api_key(
        base_url=settings.yougile_base_url,
        login=login,
        password=password,
        company_id=company_id,
    )
    print(api_key)


@beartype
async def _run_list_group_chats(settings: Settings) -> None:
    api_key = settings.require_yougile_api_key()
    chats = await YouGileClient.list_group_chats(
        base_url=settings.yougile_base_url,
        api_key=api_key,
    )
    if not chats:
        print("Групповые чаты не найдены.")
        return
    for chat in chats:
        print(f"{chat.id}\t{chat.title}")


@beartype
async def _run_list_companies(settings: Settings) -> None:
    if not settings.yougile_login:
        raise ValueError("Не задан YOUGILE_LOGIN")
    if settings.yougile_password is None:
        raise ValueError("Не задан YOUGILE_PASSWORD")
    companies = await YouGileClient.list_companies(
        base_url=settings.yougile_base_url,
        login=settings.yougile_login,
        password=settings.yougile_password.get_secret_value(),
    )
    if not companies:
        print("Компании не найдены.")
        return
    for company in companies:
        print(f"{company.id}\t{company.name}")


@beartype
async def _run(args: argparse.Namespace, settings: Settings) -> None:
    formatter = ReportFormatter(
        last_sale_lookup_days=settings.last_sale_lookup_days,
        tz=settings.zoneinfo,
    )
    scenario = ReportScenario.TODAY if args.no_sales_today else ReportScenario.COMPARE

    from sale_monitoring_bot.infra.kit_client import KitVendingAPIClient  # noqa: PLC0415

    client = KitVendingAPIClient(
        account=settings.kit_account,
        timezone=settings.zoneinfo,
    )
    gateway = KitGateway(settings, client)

    try:
        if args.no_sales_today:
            service = ScenarioTodayService(settings, gateway)
            report = await service.build_report()
            text = formatter.format_today(report)
        else:
            service = ScenarioCompareService(settings, gateway)
            report = await service.build_report()
            text = formatter.format_compare(report)

        if not text:
            text = formatter.format_all_ok(scenario)

        if args.dev:
            print(text)
            return

        yougile = YouGileClient(settings)
        telegram = TelegramClient(settings)
        await yougile.send_message(text)
        await telegram.send_message(text)
        logger.info(
            "Отчёт отправлен в YouGile и Telegram (%d символов)",
            len(text),
        )
    finally:
        await gateway.close()


@beartype
def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    try:
        settings = get_settings()
    except Exception:
        logger.exception("Ошибка загрузки настроек")
        sys.exit(1)

    try:
        if args.get_yougile_api_key:
            asyncio.run(_run_get_api_key(settings))
            return
        if args.list_yougile_companies:
            asyncio.run(_run_list_companies(settings))
            return
        if args.list_yougile_group_chats:
            asyncio.run(_run_list_group_chats(settings))
            return
        asyncio.run(_run(args, settings))
    except (YouGileAPIError, ValueError):
        logger.exception("Ошибка выполнения")
        sys.exit(1)
    except Exception:
        logger.exception("Ошибка выполнения")
        sys.exit(1)


if __name__ == "__main__":
    main()
