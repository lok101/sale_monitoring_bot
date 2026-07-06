from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from beartype import beartype

from sale_monitoring_bot.domain.entities import (
    CompareReport,
    NoSalesItem,
    OfflineItem,
    ReportScenario,
    SalesDeclineItem,
    TodayReport,
)


_MACHINE_SEPARATOR = "\n---\n"


class ReportFormatter:
    def __init__(self, last_sale_lookup_days: int, tz: ZoneInfo) -> None:
        self._last_sale_lookup_days = last_sale_lookup_days
        self._tz = tz

    @beartype
    def format_all_ok(self, scenario: ReportScenario) -> str:
        if scenario is ReportScenario.TODAY:
            day_label = self._format_day_label(self._today())
            return f"Продажи за {day_label}: отклонений не обнаружено, всё в норме."
        day_label = self._format_day_label(self._yesterday())
        return f"Продажи за {day_label}: отклонений не обнаружено, всё в норме."

    @beartype
    def format_today(self, report: TodayReport) -> str:
        sections: list[str] = []

        if report.offline_items:
            sections.append(self._format_offline_block(report.offline_items))

        if report.items:
            items = [self._format_no_sales_item(item) for item in report.items]
            heading = f"Аппараты без продаж за {self._format_day_label(self._today())}:"
            sections.append(self._format_block(heading, items))

        return "\n\n".join(sections)

    @beartype
    def format_compare(self, report: CompareReport) -> str:
        sections: list[str] = []
        yesterday_label = self._format_day_label(self._yesterday())

        if report.offline_items:
            sections.append(self._format_offline_block(report.offline_items))

        if report.no_sales_yesterday:
            items = [
                self._format_no_sales_item(item) for item in report.no_sales_yesterday
            ]
            sections.append(
                self._format_block(f"Аппараты без продаж за {yesterday_label}:", items)
            )

        if report.sales_decline:
            items = [self._format_decline_item(item) for item in report.sales_decline]
            sections.append(self._format_block("Аппараты с падением продаж:", items))

        return "\n\n".join(sections)

    @beartype
    def _format_block(self, heading: str, items: list[str]) -> str:
        body = _MACHINE_SEPARATOR.join(items)
        return f"{heading}\n\n{body}"

    @beartype
    def _format_offline_block(self, items: list[OfflineItem]) -> str:
        body = [self._format_offline_item(item) for item in items]
        return self._format_block("Аппараты без связи:", body)

    @beartype
    def _format_offline_item(self, item: OfflineItem) -> str:
        return (
            f"{item.machine.name}\n{self._format_last_ping(item.last_ping_timestamp)}"
        )

    @beartype
    def _format_no_sales_item(self, item: NoSalesItem) -> str:
        return (
            f"{item.machine.name}\n{self._format_last_sale(item.last_sale_timestamp)}"
        )

    @beartype
    def _format_decline_item(self, item: SalesDeclineItem) -> str:
        percent = round(item.drop_percent)
        day_label = self._format_day_label(self._yesterday())
        return f"{item.machine.name}\nПадение продаж за {day_label} на {percent}%"

    @beartype
    def _today(self) -> date:
        return datetime.now(self._tz).date()

    @beartype
    def _yesterday(self) -> date:
        return self._today() - timedelta(days=1)

    @beartype
    def _format_day_label(self, day: date) -> str:
        return day.strftime("%d.%m.%y")

    @beartype
    def _format_in_report_tz(self, timestamp: datetime) -> str:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=self._tz)
        else:
            timestamp = timestamp.astimezone(self._tz)
        return timestamp.strftime("%d.%m.%Y %H:%M")

    @beartype
    def _format_last_ping(self, timestamp: datetime | None) -> str:
        if timestamp is None:
            return "Последний пинг: неизвестно"
        return f"Последний пинг: {self._format_in_report_tz(timestamp)}"

    @beartype
    def _format_last_sale(self, timestamp: datetime | None) -> str:
        if timestamp is None:
            return f"Последняя продажа: более {self._last_sale_lookup_days} дней назад"
        return f"Последняя продажа: {self._format_in_report_tz(timestamp)}"
