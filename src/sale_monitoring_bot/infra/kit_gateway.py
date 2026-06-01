from __future__ import annotations

from datetime import datetime

from beartype import beartype
from sale_monitoring_bot.infra.kit_client import (
    KitVendingAPIClient,
    SaleModel,
    VendingMachineModel,
)

from sale_monitoring_bot.config import Settings
from sale_monitoring_bot.domain.entities import VendingMachineInfo
from sale_monitoring_bot.domain.grouping import build_machine_catalog


class KitGateway:
    def __init__(self, settings: Settings, client: KitVendingAPIClient) -> None:
        self._settings = settings
        self._client = client

    @beartype
    async def get_active_machines(self) -> dict[str, VendingMachineInfo]:
        models: list[VendingMachineModel] = await self._client.get_vending_machines()
        return build_machine_catalog(models)

    @beartype
    async def get_sales(self, from_date: datetime, to_date: datetime) -> list[SaleModel]:
        return await self._client.get_sales(from_date=from_date, to_date=to_date)

    @beartype
    async def close(self) -> None:
        await self._client.close()
