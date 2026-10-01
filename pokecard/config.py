import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("POKECARD_DATA", ROOT / "data"))
DB_PATH = DATA_DIR / "pokecard.db"
UPLOAD_DIR = DATA_DIR / "uploads"
USD_JPY = float(os.getenv("USD_JPY", "150"))
EUR_JPY = float(os.getenv("EUR_JPY", "165"))
# メルカリ等の販売手数料率(売却記録の既定値)
DEFAULT_FEE_RATE = float(os.getenv("FEE_RATE", "0.10"))
# 規約上グレーなスクレイピング系プロバイダは明示的にオンにした時だけ動く
ENABLE_SCRAPING = os.getenv("ENABLE_SCRAPING") == "1"
VISION_MODEL = os.getenv("VISION_MODEL", "claude-sonnet-5-5")
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
