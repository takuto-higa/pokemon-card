from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PricePoint:
    source: str
    kind: str          # market(相場) / sold(成約) / listing(出品)
    price_jpy: float
    observed_at: str = ""

    def __post_init__(self):
        self.observed_at = self.observed_at or datetime.now().isoformat(timespec="seconds")


class Provider:
    name = "base"
    enabled = True

    def fetch(self, name: str, set_code: str = "", number: str = "") -> list[PricePoint]:
        raise NotImplementedError
