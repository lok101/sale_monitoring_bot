from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from beartype import beartype

from sale_monitoring_bot.config import Settings
from sale_monitoring_bot.domain.entities import (
    NoSalesItem,
    TodayReport,
    VendingMachineInfo,
)
from sale_monitoring_bot.domain.grouping import (
    build_ping_index,
    collect_offline_machines,
    group_sales_by_machine,
    has_sales_on_day,
    last_sale_timestamp,
)
from sale_monitoring_bot.infra.kit_gateway import KitGateway


class ScenarioTodayService:
    def __init__(self, settings: Settings, gateway: KitGateway) -> None:
        self._settings = settings
        self._gateway = gateway

    @beartype
    async def build_report(self) -> TodayReport:
        tz = self._settings.zoneinfo
        now = datetime.now(tz)
        today = now.date()
        lookup_from = now - timedelta(days=self._settings.last_sale_lookup_days)

        machines = await self._gateway.get_active_machines()
        states, sales = await asyncio.gather(
            self._gateway.get_vm_states(),
            self._gateway.get_sales(from_date=lookup_from, to_date=now),
        )
        ping_index = build_ping_index(states)
        offline_items = collect_offline_machines(
            machines,
            ping_index,
            now,
            self._settings.offline_ping_threshold_minutes,
        )
        sales_by_key = group_sales_by_machine(sales)

        items: list[NoSalesItem] = []
        machine: VendingMachineInfo
        for machine in machines.values():
            vm_sales = sales_by_key.get(machine.key, [])
            if has_sales_on_day(vm_sales, today):
                continue
            items.append(
                NoSalesItem(
                    machine=machine,
                    last_sale_timestamp=last_sale_timestamp(vm_sales),
                )
            )

        return TodayReport(items=items, offline_items=offline_items)
