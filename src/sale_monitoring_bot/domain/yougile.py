from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class YouGileCompany:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class YouGileGroupChat:
    id: str
    title: str
