from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sale_monitoring_bot.domain.entities import (
    CompareReport,
    NoSalesItem,
    ReportScenario,
    SalesDeclineItem,
    TodayReport,
    VendingMachineInfo,
)
from sale_monitoring_bot.services.report_formatter import ReportFormatter

_TZ = ZoneInfo("Asia/Yekaterinburg")
_MACHINE = VendingMachineInfo(key="101", name="[101] Кофе", kit_id=1)
_REFERENCE = datetime(2026, 5, 26, 12, 0, tzinfo=_TZ)
_TODAY_LABEL = "26.05.26"
_YESTERDAY_LABEL = "25.05.26"


def test_format_all_ok_uses_day_labels(monkeypatch) -> None:
    formatter = ReportFormatter(last_sale_lookup_days=10, tz=_TZ)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def]
            return _REFERENCE

    monkeypatch.setattr(
        "sale_monitoring_bot.services.report_formatter.datetime",
        _FixedDatetime,
    )

    assert _TODAY_LABEL in formatter.format_all_ok(ReportScenario.TODAY)
    assert "сегодня" not in formatter.format_all_ok(ReportScenario.TODAY)
    assert _YESTERDAY_LABEL in formatter.format_all_ok(ReportScenario.COMPARE)
    assert "вчера" not in formatter.format_all_ok(ReportScenario.COMPARE)


def test_format_today_empty_returns_empty_string() -> None:
    formatter = ReportFormatter(last_sale_lookup_days=10, tz=_TZ)
    assert formatter.format_today(TodayReport(items=[])) == ""


def test_format_today_separates_machines_with_divider(monkeypatch) -> None:
    formatter = ReportFormatter(last_sale_lookup_days=10, tz=_TZ)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def]
            return _REFERENCE

    monkeypatch.setattr(
        "sale_monitoring_bot.services.report_formatter.datetime",
        _FixedDatetime,
    )

    machine_b = VendingMachineInfo(key="202", name="[202] Снек", kit_id=2)
    report = TodayReport(
        items=[
            NoSalesItem(machine=_MACHINE, last_sale_timestamp=None),
            NoSalesItem(machine=machine_b, last_sale_timestamp=None),
        ]
    )
    text = formatter.format_today(report)
    assert text.count("---") == 1
    assert _TODAY_LABEL in text
    assert "сегодня" not in text
    assert "[101] Кофе" in text
    assert "[202] Снек" in text


def test_format_compare_with_blocks(monkeypatch) -> None:
    formatter = ReportFormatter(last_sale_lookup_days=10, tz=_TZ)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def]
            return _REFERENCE

    monkeypatch.setattr(
        "sale_monitoring_bot.services.report_formatter.datetime",
        _FixedDatetime,
    )

    ts = datetime(2026, 5, 20, 15, 30, tzinfo=_TZ)
    report = CompareReport(
        no_sales_yesterday=[
            NoSalesItem(machine=_MACHINE, last_sale_timestamp=ts),
        ],
        sales_decline=[
            SalesDeclineItem(machine=_MACHINE, drop_percent=42.6),
        ],
    )
    text = formatter.format_compare(report)
    assert _YESTERDAY_LABEL in text
    assert "вчера" not in text
    assert "Аппараты с падением продаж" in text
    assert "43%" in text
    assert "20.05.2026 15:30" in text
