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
        description="Мониторинг продаж Kit Vending → Telegram"
    )
    parser.add_argument(
        "--no-sales-today",
        action="store_true",
        help="Отчёт: аппараты без продаж за сегодня (сценарий 1)",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Вывести отчёт в stdout, не отправлять в Telegram",
    )
    return parser.parse_args(argv)


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
        timezone=settings.kit_api_zoneinfo,
    )
    gateway = KitGateway(settings, client)

    try:
        if args.no_sales_today:
            today_service = ScenarioTodayService(settings, gateway)
            today_report = await today_service.build_report()
            text = formatter.format_today(today_report)
        else:
            compare_service = ScenarioCompareService(settings, gateway)
            compare_report = await compare_service.build_report()
            text = formatter.format_compare(compare_report)

        if not text:
            text = formatter.format_all_ok(scenario)

        if args.dev:
            print(text)
            return

        telegram = TelegramClient(settings)
        await telegram.send_message(text)
        logger.info("Отчёт отправлен в Telegram (%d символов)", len(text))
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
        asyncio.run(_run(args, settings))
    except ValueError:
        logger.exception("Ошибка выполнения")
        sys.exit(1)
    except Exception:
        logger.exception("Ошибка выполнения")
        sys.exit(1)


if __name__ == "__main__":
    main()
