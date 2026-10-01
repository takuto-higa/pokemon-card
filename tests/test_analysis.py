from datetime import date, timedelta
from pokecard import analysis as a

TODAY = date(2026, 10, 1)


def series(vals_by_days_ago):
    return [((TODAY - timedelta(days=d)).isoformat(), p) for d, p in vals_by_days_ago]


def test_trend_and_sell_when_rising():
    pts = series([(60, 1000), (40, 1000), (20, 1000), (10, 1000), (3, 1500), (1, 1500)])
    t = a.compute_trend(pts, TODAY)
    assert t.current == 1500 and t.momentum > 0.08
    assert a.sell_advice(t, []).action == "今売る"


def test_wait_before_event():
    pts = series([(60, 1000), (40, 1000), (20, 1000), (3, 1000), (1, 1000)])
    ev = [{"date": "2026-11-01", "title": "x", "impact": 0.2, "keyword": "", "days": 31}]
    adv = a.sell_advice(a.compute_trend(pts, TODAY), ev)
    assert adv.action == "待つ" and adv.target_price == 1200


def test_no_data():
    assert a.sell_advice(a.compute_trend([], TODAY), []).action == "データ不足"


def test_buy_score_prefers_discount_and_event():
    pts = series([(80, 2000), (60, 2000), (40, 2000), (20, 2000), (3, 1500), (1, 1500)])
    t = a.compute_trend(pts, TODAY)
    ev = [{"date": "2026-12-01", "title": "x", "impact": 0.2, "keyword": "", "days": 61}]
    assert a.buy_score(t, ev)[0] > a.buy_score(t, [])[0] > 0


def test_upcoming_filter():
    evs = [{"date": "2026-11-01", "keyword": "リザードン", "impact": .1, "title": "t"},
           {"date": "2025-01-01", "keyword": "", "impact": .1, "title": "past"}]
    assert len(a.upcoming_events(evs, "リザードンex", TODAY)) == 1
    assert a.upcoming_events(evs, "ピカチュウ", TODAY) == []


def test_net_profit():
    assert a.net_profit(1000, 100, 200, 300, 2) == 1000 * 2 - 100 - 200 - 600
