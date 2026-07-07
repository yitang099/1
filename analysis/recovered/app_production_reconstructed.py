#!/usr/bin/env python3
"""
生产环境 Flask app.py 重建稿 — 合并:
  - Werkzeug debugger 泄露 (line 613, accounts 表, /admin/delete-cards)
  - 实机 API 行为差异 (HTTP 状态码/错误文案)
  - billing_server.py 复刻逻辑

部署路径: /home/试试看洋芋的新的查具体后台/
SECRET: 未知 (非 debugger 页内 SECRET=；session 签名无法用 pohZc8RrQkczwHyYZUbX 验证)
"""
from __future__ import annotations

import os
import secrets
import sqlite3
from contextlib import closing
from functools import wraps

from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

# --- 生产默认值 (settings 泄露) ---
DEFAULT_SETTINGS = {
    "api_secret": "b9887333ae4c43858c9235e0ac4e0921",
    "api_domain": "http://47.76.163.227:8081",
    "deduct_amount": "3.0",
    "contact_link": "https://t.me/kuaichaq",
}

DB_PATH = os.environ.get("DB_PATH", "billing.db")


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "UNKNOWN_USE_ENV")
    # 生产疑似 debug=True → Werkzeug debugger 公网可触发
    app.debug = os.environ.get("FLASK_DEBUG", "1") == "1"

    def db() -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db() -> None:
        with closing(db()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    balance REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'normal',
                    account_type TEXT NOT NULL DEFAULT 'user'
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS cards (
                    code TEXT PRIMARY KEY,
                    amount REAL NOT NULL,
                    used_by TEXT,
                    used_at TEXT
                );
                """
            )
            for k, v in DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v)
                )
            conn.commit()

    def get_setting(key: str, default: str = "") -> str:
        with closing(db()) as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default

    def admin_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("admin"):
                return redirect(url_for("login"))
            return fn(*args, **kwargs)

        return wrapper

    @app.post("/api/desktop/login")
    def api_desktop_login():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return jsonify(ok=False, message="用户名或密码不能为空"), 400
        with closing(db()) as conn:
            row = conn.execute(
                "SELECT username,balance,status,password_hash FROM accounts WHERE username=? AND account_type='user'",
                (username,),
            ).fetchone()
        if not row or not check_password_hash(row["password_hash"], password):
            return jsonify(ok=False, message="用户名或密码错误"), 401
        return jsonify(
            ok=True,
            user={
                "username": row["username"],
                "balance": float(row["balance"]),
                "status": row["status"],
            },
        )

    @app.post("/api/desktop/register")
    def api_desktop_register():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return jsonify(ok=False, message="用户名或密码不能为空"), 400
        with closing(db()) as conn:
            try:
                conn.execute(
                    "INSERT INTO accounts(username,password_hash,account_type) VALUES(?,?,?)",
                    (username, generate_password_hash(password), "user"),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                return jsonify(ok=False, message="用户名已存在"), 409
        return jsonify(ok=True, message="注册成功")

    @app.get("/api/desktop/user-info")
    def api_desktop_user_info():
        username = (request.args.get("username") or "").strip()
        if not username:
            return jsonify(ok=False, message="missing username"), 400
        with closing(db()) as conn:
            row = conn.execute(
                "SELECT username,balance,status FROM accounts WHERE username=? AND account_type='user'",
                (username,),
            ).fetchone()
        if not row:
            return jsonify(ok=False, message="用户不存在"), 404
        return jsonify(
            ok=True,
            deduct_amount=get_setting("deduct_amount", "3.0"),
            user={
                "username": row["username"],
                "balance": float(row["balance"]),
                "status": row["status"],
            },
        )

    @app.get("/api/desktop/settings")
    def api_desktop_settings():
        key = (request.args.get("key") or "").strip()
        if not key:
            return jsonify(ok=False, message="missing key"), 400
        return jsonify(ok=True, value=get_setting(key, ""))

    @app.post("/api/desktop/decrease-balance")
    def api_desktop_decrease_balance():
        """生产 line ~613 — debugger 泄露的 SQL"""
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        amount = data.get("amount")
        if not username or amount is None:
            return jsonify(ok=False, message="参数不完整"), 400
        try:
            amount_f = float(amount)
        except (TypeError, ValueError):
            return jsonify(ok=False, message="金额不合法"), 400
        with closing(db()) as conn:
            user = conn.execute(
                "SELECT balance FROM accounts WHERE username=? AND account_type='user'",
                (username,),
            ).fetchone()
            if user is None:
                return jsonify(ok=False, message="用户不存在"), 404
            balance = float(user[0])
            if balance < amount_f:
                return jsonify(ok=False, message="余额不足"), 400
            conn.execute(
                "UPDATE accounts SET balance = balance - ? WHERE username = ? AND account_type = 'user'",
                (amount_f, username),
            )
            conn.commit()
        return jsonify(ok=True)

    @app.post("/api/desktop/refund-balance")
    def api_desktop_refund_balance():
        """生产 line ~635 — debugger 泄露；实测未鉴权可任意加余额"""
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        amount = data.get("amount")
        if not username or amount is None:
            return jsonify(ok=False, message="参数不完整"), 400
        try:
            amount_f = float(amount)
        except (TypeError, ValueError):
            return jsonify(ok=False, message="金额不合法"), 400
        with closing(db()) as conn:
            user = conn.execute(
                "SELECT id FROM accounts WHERE username = ? AND account_type = 'user'",
                (username,),
            ).fetchone()
            if user is None:
                return jsonify(ok=False, message="用户不存在"), 404
            conn.execute(
                "UPDATE accounts SET balance = balance + ? WHERE username = ? AND account_type = 'user'",
                (amount_f, username),
            )
            conn.commit()
        return jsonify(ok=True, amount=amount_f)

    @app.post("/api/desktop/card-recharge")
    def api_desktop_card_recharge():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        card_code = (data.get("card_code") or "").strip()
        if not username or not card_code:
            return jsonify(ok=False, message="参数不完整"), 400
        with closing(db()) as conn:
            user = conn.execute(
                "SELECT id FROM accounts WHERE username=? AND account_type='user'",
                (username,),
            ).fetchone()
            if not user:
                return jsonify(ok=False, message="用户不存在"), 404
            card = conn.execute(
                "SELECT code,amount,used_by FROM cards WHERE code=?", (card_code,)
            ).fetchone()
            if not card:
                return jsonify(ok=False, message="卡密不存在"), 404
            if card["used_by"]:
                return jsonify(ok=False, message="卡密已使用"), 400
            conn.execute(
                "UPDATE accounts SET balance = balance + ? WHERE username=?",
                (float(card["amount"]), username),
            )
            conn.execute(
                "UPDATE cards SET used_by=?, used_at=datetime('now') WHERE code=?",
                (username, card_code),
            )
            conn.commit()
        return jsonify(ok=True, amount=float(card["amount"]))

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/login")
    def login():
        return render_template_string(LOGIN_HTML, error=None)

    @app.post("/login")
    def login_post():
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        with closing(db()) as conn:
            row = conn.execute(
                "SELECT password_hash,account_type FROM accounts WHERE username=?",
                (username,),
            ).fetchone()
        if not row or row["account_type"] != "admin" or not check_password_hash(row["password_hash"], password):
            session["_flashes"] = [("error", "管理员账号或密码错误")]
            return redirect(url_for("login"))
        session["admin"] = username
        return redirect(url_for("dashboard"))

    @app.get("/dashboard")
    @admin_required
    def dashboard():
        return "admin dashboard", 200

    @app.get("/admin/users")
    @admin_required
    def admin_users():
        return "user list", 200

    @app.post("/admin/delete-cards")
    @admin_required
    def admin_delete_cards():
        # debugger 泄露的路由; 实现未知
        return redirect(url_for("dashboard"))

    init_db()
    return app


LOGIN_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>登录</title>
  <style>
    body { font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; display:flex; min-height:100vh; align-items:center; justify-content:center; margin:0; }
    .card { width: 420px; background:#111827; padding:28px; border-radius:18px; box-shadow: 0 20px 50px rgba(0,0,0,.35); }
    input, button, select { width:100%; padding:12px 14px; margin:8px 0; border-radius:10px; border:1px solid #334155; background:#0b1220; color:#fff; box-sizing:border-box; }
    button { background:#2563eb; border:none; cursor:pointer; }
    h1 { margin-top:0; }
    .msg { margin:8px 0; padding:10px 12px; border-radius:10px; }
    .error { background:#7f1d1d; }
    .success { background:#14532d; }
    .tabs { display:flex; gap:8px; margin-bottom:12px; }
    .tab { flex:1; background:#1f2937; color:#fff; text-align:center; padding:10px; border-radius:10px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>账号系统</h1>
    {% if error %}<div class="msg error">{{ error }}</div>{% endif %}
    <div class="tabs"><div class="tab">管理员登录</div></div>
    <form method="post" action="/login">
      <input name="username" placeholder="管理员用户名" value="admin" />
      <input name="password" type="password" placeholder="管理员密码" value="admin123" />
      <button type="submit">登录</button>
    </form>
    <p style="color:#94a3b8; font-size:14px; margin-top:12px;">此网页后台仅管理员使用，不提供注册入口。</p>
  </div>
</body>
</html>"""

if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=9110, debug=True)
