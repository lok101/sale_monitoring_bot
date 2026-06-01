from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from beartype import beartype

from sale_monitoring_bot.domain.entities import (
    CompareReport,
    NoSalesItem,
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
        if not report.items:
            return ""
        items = [self._format_no_sales_item(item) for item in report.items]
        heading = f"Аппараты без продаж за {self._format_day_label(self._today())}:"
        return self._format_block(heading, items)

    @beartype
    def format_compare(self, report: CompareReport) -> str:
        sections: list[str] = []
        yesterday_label = self._format_day_label(self._yesterday())

        if report.no_sales_yesterday:
            items = [self._format_no_sales_item(item) for item in report.no_sales_yesterday]
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
    def _format_no_sales_item(self, item: NoSalesItem) -> str:
        return f"{item.machine.name}\n{self._format_last_sale(item.last_sale_timestamp)}"

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
    def _format_last_sale(self, timestamp: datetime | None) -> str:
        if timestamp is None:
            return (
                f"Последняя продажа: более {self._last_sale_lookup_days} дней назад"
            )
        formatted = timestamp.strftime("%d.%m.%Y %H:%M")
        return f"Последняя продажа: {formatted}"
