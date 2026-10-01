"""ヤフオク落札相場(実験的)。HTMLを解析する非公式手法で、サイト変更で壊れる/規約に抵触しうる。
ENABLE_SCRAPING=1 のときだけ有効。個人利用・低頻度に留めること。**未検証(開発環境から接続不可)**。"""
import re, time
import httpx
from statistics import median
from .base import Provider, PricePoint
from .. import config


class YahooAuctions(Provider):
    name = "yahoo-auctions"
    enabled = config.ENABLE_SCRAPING

    def fetch(self, name, set_code="", number=""):
        time.sleep(2)  # 相手サーバへの配慮
        q = " ".join(x for x in (name, number) if x)
        r = httpx.get("https://auctions.yahoo.co.jp/closedsearch/closedsearch",
                      params={"p": q, "va": q, "ei": "UTF-8"}, timeout=20,
                      headers={"User-Agent": "Mozilla/5.0 pokecard-personal-tool"})
        r.raise_for_status()
        prices = [int(m.replace(",", "")) for m in re.findall(r'"price"\s*:\s*"?([\d,]{3,9})', r.text)]
        prices = prices[:30]
        return [PricePoint(self.name, "sold", float(median(prices)))] if prices else []
