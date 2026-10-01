"""相場分析。純粋関数のみ(DB/ネットワーク非依存)でテストしやすくしてある。

注意: ヒューリスティックによる目安であり、利益を保証するものではない。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from statistics import median


@dataclass
class Trend:
    current: float | None = None   # 直近7日の中央値
    avg30: float | None = None
    avg90: float | None = None
    momentum: float = 0.0          # current/avg30 - 1
    discount90: float = 0.0        # 1 - current/avg90 (正=90日平均より安い)
    volatility: float = 0.0
    n: int = 0


@dataclass
class Advice:
    action: str
    score: float
    reasons: list[str] = field(default_factory=list)
    target_price: float | None = None
    best_window: str = ""


def _d(s: str) -> date:
    return datetime.fromisoformat(s).date()


def _med(vals):
    return median(vals) if vals else None


def compute_trend(points: list[tuple[str, float]], today: date | None = None) -> Trend:
    """points: (ISO日時, 円) のリスト。"""
    today = today or date.today()
    t = Trend(n=len(points))
    if not points:
        return t

    def window(days):
        lo = today - timedelta(days=days)
        return [p for d, p in points if lo <= _d(d) <= today]

    w7, w30, w90 = window(7), window(30), window(90)
    t.current = _med(w7) or _med(w30) or _med(w90) or _med([p for _, p in points])
    t.avg30 = _med(w30) or t.current
    t.avg90 = _med(w90) or t.avg30
    if t.avg30:
        t.momentum = t.current / t.avg30 - 1
    if t.avg90:
        t.discount90 = 1 - t.current / t.avg90
    base = w90 or [p for _, p in points]
    if len(base) > 2 and t.avg90:
        m = sum(base) / len(base)
        t.volatility = (sum((x - m) ** 2 for x in base) / len(base)) ** 0.5 / m
    return t


def upcoming_events(events: list[dict], name: str, today: date | None = None, horizon: int = 180):
    """カード名にkeywordが含まれる(またはkeyword空=全体)イベントのみ。"""
    today = today or date.today()
    out = []
    for e in events:
        days = (_d(e["date"]) - today).days
        if 0 <= days <= horizon and (not e["keyword"] or e["keyword"] in name):
            out.append({**e, "days": days})
    return sorted(out, key=lambda e: e["days"])


def sell_advice(trend: Trend, events: list[dict], purchase_price: float = 0.0) -> Advice:
    if trend.current is None:
        return Advice("データ不足", 0, ["相場データがありません。更新または手入力してください"])
    reasons, score = [], 0.0
    # 上昇中・平均より高い=売り時、下落中=損切り/保有判断
    if trend.momentum > 0.08:
        score += 1; reasons.append(f"直近価格が30日中央値より{trend.momentum:+.0%}と上昇中")
    elif trend.momentum < -0.08:
        score -= 1; reasons.append(f"直近価格が30日中央値より{trend.momentum:+.0%}と下落中")
    if trend.discount90 < -0.10:
        score += 1; reasons.append("90日中央値より1割以上高く、割高圏")
    elif trend.discount90 > 0.10:
        score -= 1; reasons.append("90日中央値より1割以上安く、割安圏(売りを急がない)")
    near = [e for e in events if e["impact"] > 0]
    future_boost = max((e["impact"] for e in near), default=0)
    if near:
        e = near[0]
        reasons.append(f"{e['date']}に「{e['title']}」(あと{e['days']}日)、需要増を見込む")
    if future_boost >= 0.15 and trend.momentum < 0.05:
        score -= 1; reasons.append("イベント前で価格が未織り込みのため待つ価値あり")
    if purchase_price and trend.current < purchase_price:
        reasons.append(f"現在値が仕入値({purchase_price:,.0f}円)を下回っている")
    if score >= 1:
        action = "今売る"
    elif score <= -1:
        action = "待つ"
    else:
        action = "様子見"
    adv = Advice(action, score, reasons)
    if near and action != "今売る":
        e = near[0]
        adv.best_window = f"{e['date']}前後(〜{_d(e['date']) + timedelta(days=14)})"
        adv.target_price = round(trend.current * (1 + future_boost))
    else:
        adv.target_price = round(trend.current)
        adv.best_window = "現在"
    return adv


def buy_score(trend: Trend, events: list[dict]) -> tuple[float, list[str]]:
    """今は安いが今後上がりそうなカードを高得点にする。"""
    if trend.current is None or trend.n < 3:
        return 0.0, ["データ点が少なく判定不能"]
    score, reasons = 0.0, []
    if trend.discount90 > 0.05:
        score += min(trend.discount90, 0.4) * 5
        reasons.append(f"90日中央値より{trend.discount90:.0%}安い")
    if -0.05 < trend.momentum < 0.15 and trend.discount90 > 0.05:
        score += 0.5; reasons.append("下げ止まり気配(直近の下落が止まっている)")
    for e in events[:2]:
        if e["impact"] > 0:
            score += e["impact"] * 5
            reasons.append(f"{e['date']}「{e['title']}」で需要増の可能性(あと{e['days']}日)")
    if trend.volatility > 0.35:
        score -= 1; reasons.append("値動きが荒くリスク高")
    return round(score, 2), reasons


def net_profit(sold_price: float, fees: float, shipping: float, purchase_price: float, qty=1) -> float:
    return sold_price * qty - fees - shipping - purchase_price * qty
