# Задача: блок «Аппараты без связи» в отчёте

**Статус:** ✅ реализовано (2026-07-06)  
**Design:** [docs/specs/2026-07-06-offline-machines-report-design.md](../../docs/specs/2026-07-06-offline-machines-report-design.md)  
**План:** [docs/plans/2026-07-06-offline-machines-report.md](../../docs/plans/2026-07-06-offline-machines-report.md)

## Постановка

Добавить в ежедневные отчёты (08:00 и 15:00) блок **«Аппараты без связи»** на основе `GetVMStates.DateTime`. Порог офлайна — env `OFFLINE_PING_THRESHOLD_MINUTES` (default 25).

## Критерии готовности

См. § «Критерии приёмки» в design-спеке.

## Следующий шаг

`writing-plans` → `docs/plans/…` → `executing-plans` (TDD).
