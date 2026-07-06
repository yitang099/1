#!/usr/bin/env python3
"""
生产环境 app.py 片段重建 — 来自 Werkzeug Debugger 实机泄露 (2026-07-06)

确认来源:
  - 路径: /home/试试看洋芋的新的查具体后台/app.py
  - SECRET: pohZc8RrQkczwHyYZUbX (debugger JS 变量)
  - 函数 api_desktop_decrease_balance @ line ~613
  - 表 accounts (account_type='user')
  - 路由 POST /admin/delete-cards (line 614+)
  - 路由 GET /admin/users (存在，需 admin session)

非完整文件；缺失部分用 [...] 标注。完整获取需 debugger PIN/RCE 或 SSH。
"""
from __future__ import annotations

# --- 泄露的 decrease-balance 核心 (line ~600-614) ---

def api_desktop_decrease_balance_LEAKED(conn, username, amount):
    """
    自 Werkzeug traceback 源码窗还原。
    """
    user = ...  # SELECT balance FROM accounts WHERE username=? ...
    if user is None:
        return {"ok": False, "message": "用户不存在"}, 404
    balance = float(user[0])
    if balance < amount:
        return {"ok": False, "message": "余额不足"}, 400
    conn.execute(
        "UPDATE accounts SET balance = balance - ? WHERE username = ? AND account_type = 'user'",
        (amount, username),
    )
    conn.commit()
    return {"ok": True}


# --- 泄露的路由 ---

# @app.route("/admin/delete-cards", methods=["POST"])
# def admin_delete_cards(): ...

# @app.route("/admin/users")  # GET 200 when authed
# def admin_users(): ...

# --- 生产与复刻差异备忘 ---
PRODUCTION_DIFFS = {
    "secret_key": "pohZc8RrQkczwHyYZUbX",
    "debug": True,  # Werkzeug debugger 公网可触发
    "user_table": "accounts",
    "account_type_col": "account_type",
    "register_dup_code": 409,
    "card_missing_code": 404,
    "admin_login_error": "管理员账号或密码错误",
    "user_info_missing_param": "missing username",
    "invalid_amount_msg": "金额不合法",
}
