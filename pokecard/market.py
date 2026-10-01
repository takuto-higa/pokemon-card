from .db import conn, card_key
from .providers import PROVIDERS


def refresh(name, set_code="", number=""):
    """全プロバイダから相場を取得して保存。プロバイダごとのエラーは握りつぶさず返す。"""
    key, saved, errors = card_key(name, set_code, number), 0, []
    for p in PROVIDERS:
        if not p.enabled:
            continue
        try:
            pts = p.fetch(name, set_code, number)
        except Exception as e:  # ネットワーク/解析失敗
            errors.append(f"{p.name}: {e}")
            continue
        with conn() as c:
            for pt in pts:
                c.execute("INSERT INTO prices(card_key,source,kind,price_jpy,observed_at) VALUES(?,?,?,?,?)",
                          (key, pt.source, pt.kind, pt.price_jpy, pt.observed_at))
                saved += 1
    return saved, errors


def history(name, set_code="", number=""):
    with conn() as c:
        rows = c.execute("SELECT observed_at, price_jpy FROM prices WHERE card_key=? ORDER BY observed_at",
                         (card_key(name, set_code, number),)).fetchall()
    return [(r["observed_at"], r["price_jpy"]) for r in rows]
