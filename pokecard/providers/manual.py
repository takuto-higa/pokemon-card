"""手入力/CSV取込。メルカリは公開APIがなく自動取得が規約で禁止されているため、
アプリで見た売り切れ価格をここから入れる(CSV: name,set_code,number,price,date,source,kind)。"""
import csv, io
from ..db import conn, card_key


def add_price(name, set_code, number, price, source="manual", kind="sold", observed_at=""):
    from datetime import datetime
    ts = observed_at or datetime.now().isoformat(timespec="seconds")
    with conn() as c:
        c.execute("INSERT INTO prices(card_key,source,kind,price_jpy,observed_at) VALUES(?,?,?,?,?)",
                  (card_key(name, set_code, number), source, kind, float(price), ts))


def import_csv(text: str) -> int:
    n = 0
    for row in csv.DictReader(io.StringIO(text)):
        add_price(row["name"], row.get("set_code", ""), row.get("number", ""), row["price"],
                  row.get("source") or "csv", row.get("kind") or "sold", row.get("date", ""))
        n += 1
    return n
