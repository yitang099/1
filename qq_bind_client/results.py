"""Save captured QQ results."""
from __future__ import annotations

from datetime import datetime

from qq_bind_client.config import results_dir


def save_result(qq: str, source: str = "", note: str = "") -> str:
    folder = results_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = folder / f"QQ_{qq}_{stamp}.txt"
    body = "\n".join(
        [
            f"QQ号: {qq}",
            f"来源: {source or 'hook'}",
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            note,
            "",
        ]
    ).strip() + "\n"
    path.write_text(body, encoding="utf-8")
    return str(path)
