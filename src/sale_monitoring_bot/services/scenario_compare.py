from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta

from beartype import beartype

from sale_monitoring_bot.config import Settings
from sale_monitoring_bot.domain.entities import (
    CompareReport,
    NoSalesItem,
    SalesDeclineItem,
    VendingMachineInfo,
)
from sale_monitoring_bot.domain.grouping import (
    build_ping_index,
    collect_offline_machines,
    group_sales_by_machine,
    last_sale_timestamp,
    sum_sales_by_day,
)
from sale_monitoring_bot.infra.kit_gateway import KitGateway


class ScenarioCompareService:
    def __init__(self, settings: Settings, gateway: KitGateway) -> None:
        self._settings = settings
        self._gateway = gateway

    @beartype
    async def build_report(self) -> CompareReport:
        tz = self._settings.zoneinfo
        now = datetime.now(tz)
        today = now.date()
        yesterday = today - timedelta(days=1)
        n_days = self._settings.days_for_average

        analysis_from_date = today - timedelta(days=n_days)
        analysis_from = datetime.combine(analysis_from_date, time.min, tzinfo=tz)

        lookup_from = now - timedelta(days=self._settings.last_sale_lookup_days)

        machines = await self._gateway.get_active_machines()
        fetch_from = min(analysis_from, lookup_from)
        states, sales = await asyncio.gather(
            self._gateway.get_vm_states(),
            self._gateway.get_sales(from_date=fetch_from, to_date=now),
        )
        ping_index = build_ping_index(states)
        offline_items = collect_offline_machines(
            machines,
            ping_index,
            now,
            self._settings.offline_ping_threshold_minutes,
        )
        sales_by_key = group_sales_by_machine(sales)

        average_days = [
            today - timedelta(days=offset) for offset in range(n_days, 1, -1)
        ]

        no_sales_items: list[NoSalesItem] = []
        decline_items: list[SalesDeclineItem] = []

        machine: VendingMachineInfo
        for machine in machines.values():
            vm_sales = sales_by_key.get(machine.key, [])
            yesterday_total = sum_sales_by_day(vm_sales, yesterday)

            if yesterday_total <= 0.0:
                lookup_sales = [
                    sale for sale in vm_sales if sale.timestamp >= lookup_from
                ]
                no_sales_items.append(
                    NoSalesItem(
                        machine=machine,
                        last_sale_timestamp=last_sale_timestamp(lookup_sales),
                    )
                )
                continue

            average_total = sum(sum_sales_by_day(vm_sales, day) for day in average_days)
            divisor = n_days - 1
            average = average_total / divisor

            if average <= 0.0:
                continue

            drop_percent = (average - yesterday_total) / average * 100.0
            if drop_percent < self._settings.sales_drop_percent:
                continue

            decline_items.append(
                SalesDeclineItem(machine=machine, drop_percent=drop_percent)
            )

        return CompareReport(
            no_sales_yesterday=no_sales_items,
            sales_decline=decline_items,
            offline_items=offline_items,
        )
