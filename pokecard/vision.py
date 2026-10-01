"""カード画像→カード名/セット/番号の推定(Claude Vision)。ANTHROPIC_API_KEY が必要。未設定なら手入力。"""
import base64, json, os, re
from pathlib import Path
from . import config

PROMPT = ('このポケモンカードの画像から情報を読み取り、JSONのみで返してください: '
          '{"name":"カード名","set_code":"収録弾コード(例 SV2a)","number":"カード番号(例 201/165)",'
          '"rarity":"レアリティ(例 SAR)","lang":"ja または en"}。読み取れない項目は空文字。')


def identify(image_path: str) -> dict:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY が未設定です。カード情報は手入力してください")
    import anthropic
    p = Path(image_path)
    media = {".png": "image/png", ".webp": "image/webp"}.get(p.suffix.lower(), "image/jpeg")
    msg = anthropic.Anthropic().messages.create(
        model=config.VISION_MODEL, max_tokens=300,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media,
                                         "data": base64.b64encode(p.read_bytes()).decode()}},
            {"type": "text", "text": PROMPT}]}])
    m = re.search(r"\{.*\}", msg.content[0].text, re.S)
    return json.loads(m.group(0)) if m else {}
