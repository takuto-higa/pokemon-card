import shutil, uuid
from datetime import date
from pathlib import Path
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pokecard import config, db, analysis, market, vision
from pokecard.events import SEED
from pokecard.providers import manual

db.init()
with db.conn() as c:
    if not c.execute("SELECT 1 FROM events").fetchone():
        c.executemany("INSERT INTO events(date,title,impact,keyword) VALUES(?,?,?,?)", SEED)

app = FastAPI(title="ポケカ せどり管理")
app.mount("/uploads", StaticFiles(directory=config.UPLOAD_DIR), name="uploads")
tpl = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
back = lambda msg="": RedirectResponse(f"/?msg={msg}", status_code=303)


def events():
    with db.conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM events ORDER BY date")]


@app.get("/")
def index(request: Request, msg: str = ""):
    evs = events()
    with db.conn() as c:
        cards = [dict(r) for r in c.execute("SELECT * FROM cards WHERE status='holding' ORDER BY id DESC")]
        watch = [dict(r) for r in c.execute("SELECT * FROM watchlist ORDER BY id DESC")]
        sales = [dict(r) for r in c.execute(
            "SELECT s.*, c.name, c.purchase_price FROM sales s JOIN cards c ON c.id=s.card_id ORDER BY s.id DESC")]
    for cd in cards:
        t = analysis.compute_trend(market.history(cd["name"], cd["set_code"], cd["number"]))
        cd["trend"] = t
        cd["advice"] = analysis.sell_advice(
            t, analysis.upcoming_events(evs, cd["name"]), cd["purchase_price"])
    cands = []
    for w in watch:
        t = analysis.compute_trend(market.history(w["name"], w["set_code"], w["number"]))
        s, why = analysis.buy_score(t, analysis.upcoming_events(evs, w["name"]))
        cands.append({**w, "trend": t, "score": s, "reasons": why})
    cands.sort(key=lambda x: -x["score"])
    for s in sales:
        s["profit"] = analysis.net_profit(s["sold_price"], s["fees"], s["shipping"], s["purchase_price"], s["qty"])
    total = sum(s["profit"] for s in sales)
    return tpl.TemplateResponse(request, "index.html", dict(
        cards=cards, cands=cands, sales=sales, total=total, events=evs, msg=msg,
        fee_rate=config.DEFAULT_FEE_RATE, scraping=config.ENABLE_SCRAPING))


@app.post("/cards")
def add_card(name: str = Form(""), set_code: str = Form(""), number: str = Form(""), rarity: str = Form(""),
             qty: int = Form(1), purchase_price: float = Form(0), image: UploadFile | None = File(None)):
    path = ""
    if image and image.filename:
        dest = config.UPLOAD_DIR / f"{uuid.uuid4().hex}{Path(image.filename).suffix.lower()}"
        with open(dest, "wb") as f:
            shutil.copyfileobj(image.file, f)
        path = dest.name
    info = {}
    if path and not name:
        try:
            info = vision.identify(str(config.UPLOAD_DIR / path))
        except Exception as e:
            info = {}
            err = f"画像判定失敗: {e}"
            if not name:
                name = "(未判定)"
    name = name or info.get("name") or "(未判定)"
    with db.conn() as c:
        c.execute("INSERT INTO cards(name,set_code,number,rarity,image_path,qty,purchase_price) VALUES(?,?,?,?,?,?,?)",
                  (name, set_code or info.get("set_code", ""), number or info.get("number", ""),
                   rarity or info.get("rarity", ""), path, qty, purchase_price))
    return back("登録しました" + ("(画像判定に失敗。名前を編集してください)" if name == "(未判定)" else ""))


@app.post("/cards/{cid}/edit")
def edit_card(cid: int, name: str = Form(...), set_code: str = Form(""), number: str = Form(""),
              purchase_price: float = Form(0)):
    with db.conn() as c:
        c.execute("UPDATE cards SET name=?,set_code=?,number=?,purchase_price=? WHERE id=?",
                  (name, set_code, number, purchase_price, cid))
    return back("更新しました")


@app.post("/cards/{cid}/refresh")
def refresh_card(cid: int):
    with db.conn() as c:
        cd = c.execute("SELECT * FROM cards WHERE id=?", (cid,)).fetchone()
    n, errs = market.refresh(cd["name"], cd["set_code"], cd["number"])
    return back(f"相場{n}件取得" + (" / エラー: " + "; ".join(errs) if errs else ""))


@app.post("/cards/{cid}/sell")
def sell(cid: int, sold_price: float = Form(...), qty: int = Form(1), channel: str = Form("mercari"),
         fees: float | None = Form(None), shipping: float = Form(0)):
    fees = sold_price * qty * config.DEFAULT_FEE_RATE if fees is None else fees
    with db.conn() as c:
        c.execute("INSERT INTO sales(card_id,qty,sold_price,fees,shipping,channel,sold_at) VALUES(?,?,?,?,?,?,?)",
                  (cid, qty, sold_price, fees, shipping, channel, date.today().isoformat()))
        c.execute("UPDATE cards SET qty=qty-?, status=CASE WHEN qty-?<=0 THEN 'sold' ELSE status END WHERE id=?",
                  (qty, qty, cid))
    return back("売却を記録しました")


@app.post("/watch")
def add_watch(name: str = Form(...), set_code: str = Form(""), number: str = Form("")):
    with db.conn() as c:
        c.execute("INSERT INTO watchlist(name,set_code,number) VALUES(?,?,?)", (name, set_code, number))
    return back("ウォッチに追加しました")


@app.post("/watch/{wid}/refresh")
def refresh_watch(wid: int):
    with db.conn() as c:
        w = c.execute("SELECT * FROM watchlist WHERE id=?", (wid,)).fetchone()
    n, errs = market.refresh(w["name"], w["set_code"], w["number"])
    return back(f"相場{n}件取得" + (" / エラー: " + "; ".join(errs) if errs else ""))


@app.post("/watch/{wid}/delete")
def del_watch(wid: int):
    with db.conn() as c:
        c.execute("DELETE FROM watchlist WHERE id=?", (wid,))
    return back("削除しました")


@app.post("/prices")
def add_price(name: str = Form(...), set_code: str = Form(""), number: str = Form(""),
              price: float = Form(...), source: str = Form("manual"), kind: str = Form("sold")):
    manual.add_price(name, set_code, number, price, source, kind)
    return back("価格を追加しました")


@app.post("/prices/csv")
async def prices_csv(file: UploadFile = File(...)):
    n = manual.import_csv((await file.read()).decode("utf-8-sig"))
    return back(f"CSV {n}件取り込み")


@app.post("/events")
def add_event(date_: str = Form(..., alias="date"), title: str = Form(...), impact: float = Form(0.1),
              keyword: str = Form("")):
    with db.conn() as c:
        c.execute("INSERT INTO events(date,title,impact,keyword) VALUES(?,?,?,?)", (date_, title, impact, keyword))
    return back("イベント追加")


@app.post("/events/{eid}/delete")
def del_event(eid: int):
    with db.conn() as c:
        c.execute("DELETE FROM events WHERE id=?", (eid,))
    return back("削除しました")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
