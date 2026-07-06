from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sale_monitoring_bot.infra.kit_client import SaleModel

from sale_monitoring_bot.domain.grouping import sum_sales_by_day

_TZ = ZoneInfo("Asia/Yekaterinburg")


def _sale(price: float, day: date) -> SaleModel:
    dt = datetime.combine(day, datetime.min.time(), tzinfo=_TZ)
    return SaleModel.model_validate(
        {
            "LineNumber": 1,
            "Sum": price,
            "DateTime": dt.strftime("%d.%m.%Y %H:%M:%S"),
            "GoodsName": "1234 | Товар",
            "VendingMachine": 1,
            "VendingMachineName": "[101] Кофе",
            "MatrixId": None,
        }
    )


def test_compare_average_and_drop_percent() -> None:
    """N=6: среднее за 5 дней до вчера, сравнение с вчера."""
    today = date(2026, 5, 26)
    yesterday = today - timedelta(days=1)
    n_days = 6

    average_days = [today - timedelta(days=offset) for offset in range(n_days, 1, -1)]
    assert len(average_days) == 5
    assert yesterday not in average_days

    sales = [
        _sale(100.0, average_days[0]),
        _sale(100.0, average_days[1]),
        _sale(100.0, average_days[2]),
        _sale(100.0, average_days[3]),
        _sale(100.0, average_days[4]),
        _sale(30.0, yesterday),
    ]

    average_total = sum(sum_sales_by_day(sales, day) for day in average_days)
    average = average_total / (n_days - 1)
    yesterday_total = sum_sales_by_day(sales, yesterday)

    assert average == 100.0
    assert yesterday_total == 30.0

    drop_percent = (average - yesterday_total) / average * 100.0
    assert drop_percent == 70.0
    assert drop_percent >= 30


def test_no_sales_yesterday_detection() -> None:
    today = date(2026, 5, 26)
    yesterday = today - timedelta(days=1)
    sales = [_sale(50.0, today - timedelta(days=3))]
    assert sum_sales_by_day(sales, yesterday) == 0.0
