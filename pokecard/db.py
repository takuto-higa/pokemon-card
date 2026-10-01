import sqlite3
from contextlib import contextmanager
from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, set_code TEXT DEFAULT '', number TEXT DEFAULT '',
  rarity TEXT DEFAULT '', lang TEXT DEFAULT 'ja', image_path TEXT DEFAULT '',
  qty INTEGER DEFAULT 1, purchase_price REAL DEFAULT 0, status TEXT DEFAULT 'holding',
  notes TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS watchlist(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, set_code TEXT DEFAULT '', number TEXT DEFAULT '',
  lang TEXT DEFAULT 'ja', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS prices(
  id INTEGER PRIMARY KEY, card_key TEXT NOT NULL, source TEXT NOT NULL, kind TEXT NOT NULL,
  price_jpy REAL NOT NULL, observed_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_prices ON prices(card_key, observed_at);
CREATE TABLE IF NOT EXISTS sales(
  id INTEGER PRIMARY KEY, card_id INTEGER, qty INTEGER DEFAULT 1, sold_price REAL, fees REAL DEFAULT 0,
  shipping REAL DEFAULT 0, channel TEXT DEFAULT '', sold_at TEXT DEFAULT CURRENT_DATE);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, title TEXT NOT NULL, impact REAL DEFAULT 0.1,
  keyword TEXT DEFAULT '');
"""


def card_key(name: str, set_code: str = "", number: str = "") -> str:
    return "|".join(p.strip().lower() for p in (name, set_code, number))


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with conn() as c:
        c.executescript(SCHEMA)
