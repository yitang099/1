"""Save successful query results next to the executable."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sms8081_client.config import APP_DIR, load_config


def results_dir() -> Path:
    cfg = load_config()
    name = (cfg.get("results_dir") or "查询结果").strip() or "查询结果"
    path = Path(name)
    if not path.is_absolute():
        path = APP_DIR / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_query_result(phone: str, content: str, order_id: str = "") -> Path:
    folder = results_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_phone = "".join(ch for ch in phone if ch.isdigit()) or "unknown"
    path = folder / f"{safe_phone}_{stamp}.txt"
    body = "\n".join(
        [
            f"手机号: {phone}",
            f"订单号: {order_id}" if order_id else "",
            f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            content.strip(),
            "",
        ]
    ).strip() + "\n"
    path.write_text(body, encoding="utf-8")
    return path
