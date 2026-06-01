from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime

from beartype import beartype
from sale_monitoring_bot.infra.kit_client import SaleModel, VendingMachineModel

from sale_monitoring_bot.domain.entities import VendingMachineInfo

_INACTIVE_NAME_RE = re.compile(r"^\[\s*[ХхXx]\s*\]", re.IGNORECASE)


@beartype
def machine_key(code: str | None, kit_id: int) -> str:
    if code:
        return code
    return f"id:{kit_id}"


@beartype
def is_active_machine(name: str) -> bool:
    if "тест" in name.lower() or "офис" in name.lower():
        return False
    return _INACTIVE_NAME_RE.match(name) is None


@beartype
def group_sales_by_machine(sales: Iterable[SaleModel]) -> dict[str, list[SaleModel]]:
    grouped: dict[str, list[SaleModel]] = defaultdict(list)
    for sale in sales:
        key = machine_key(sale.vending_machine_code, sale.vending_machine_id)
        grouped[key].append(sale)
    return dict(grouped)


@beartype
def build_machine_catalog(models: Iterable[VendingMachineModel]) -> dict[str, VendingMachineInfo]:
    by_key: dict[str, VendingMachineInfo] = {}
    for model in models:
        if not is_active_machine(model.name):
            continue
        key = machine_key(model.code, model.id)
        existing = by_key.get(key)
        if existing is None or model.id < existing.kit_id:
            by_key[key] = VendingMachineInfo(key=key, name=model.name, kit_id=model.id)
    return by_key


@beartype
def sum_sales_by_day(
    sales: Iterable[SaleModel],
    tz_day: date,
) -> float:
    total = 0.0
    for sale in sales:
        if sale.timestamp.date() == tz_day:
            total += float(sale.price)
    return total


@beartype
def last_sale_timestamp(sales: Iterable[SaleModel]) -> datetime | None:
    latest: datetime | None = None
    for sale in sales:
        if latest is None or sale.timestamp > latest:
            latest = sale.timestamp
    return latest


@beartype
def has_sales_on_day(sales: Iterable[SaleModel], day: date) -> bool:
    return any(sale.timestamp.date() == day for sale in sales)
