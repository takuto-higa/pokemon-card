"""Pokémon TCG API (pokemontcg.io)。公式の公開API。TCGplayer(USD)/Cardmarket(EUR)の相場を円換算。
主に英語版カードが対象。日本語版カードは名前が一致しない場合がある。"""
import httpx
from .base import Provider, PricePoint
from ..config import USD_JPY, EUR_JPY


class PokemonTCG(Provider):
    name = "pokemontcg.io"

    def fetch(self, name, set_code="", number=""):
        q = f'name:"{name}"'
        if number:
            q += f" number:{number.split('/')[0]}"
        r = httpx.get("https://api.pokemontcg.io/v2/cards", params={"q": q, "pageSize": 5}, timeout=20)
        r.raise_for_status()
        out = []
        for card in r.json().get("data", [])[:1]:
            for variant in (card.get("tcgplayer", {}).get("prices") or {}).values():
                if variant.get("market"):
                    out.append(PricePoint(self.name + "/tcgplayer", "market", variant["market"] * USD_JPY))
                    break
            cm = (card.get("cardmarket") or {}).get("prices") or {}
            if cm.get("trendPrice"):
                out.append(PricePoint(self.name + "/cardmarket", "market", cm["trendPrice"] * EUR_JPY))
        return out
