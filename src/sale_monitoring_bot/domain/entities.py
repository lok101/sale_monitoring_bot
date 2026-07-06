from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ReportScenario(Enum):
    TODAY = "today"
    COMPARE = "compare"


@dataclass(frozen=True, slots=True)
class VendingMachineInfo:
    key: str
    name: str
    kit_id: int


@dataclass(frozen=True, slots=True)
class OfflineItem:
    machine: VendingMachineInfo
    last_ping_timestamp: datetime | None


@dataclass(frozen=True, slots=True)
class NoSalesItem:
    machine: VendingMachineInfo
    last_sale_timestamp: datetime | None


@dataclass(frozen=True, slots=True)
class SalesDeclineItem:
    machine: VendingMachineInfo
    drop_percent: float


@dataclass(frozen=True, slots=True)
class TodayReport:
    items: list[NoSalesItem]
    offline_items: list[OfflineItem]


@dataclass(frozen=True, slots=True)
class CompareReport:
    no_sales_yesterday: list[NoSalesItem]
    sales_decline: list[SalesDeclineItem]
    offline_items: list[OfflineItem]
