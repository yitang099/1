#!/usr/bin/env python3
"""
Recovered Flask billing backend (43.154.128.116:9110).

Reverse-engineered from live HTTP behavior + desktop_app.pyc bytecode strings.
Not the operator's original file, but API-compatible with production.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from contextlib import closing
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("BILLING_DB", APP_DIR / "billing.db"))

DEFAULT_SETTINGS = {
    "api_secret": "b9887333ae4c43858c9235e0ac4e0921",
    "api_domain": "http://47.76.163.227:8081",
    "deduct_amount": "3.0",
    "contact_link": "https://t.me/kuaichaq",
    "version": "3.0",
}

LOGIN_HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>登录</title>
  <style>
    body { font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; display:flex; min-height:100vh; align-items:center; justify-content:center; margin:0; }
    .card { width: 420px; background:#111827; padding:28px; border-radius:18px; }
    input, button { width:100%; padding:12px 14px; margin:8px 0; border-radius:10px; border:1px solid #334155; background:#0b1220; color:#fff; box-sizing:border-box; }
    button { background:#2563eb; border:none; cursor:pointer; }
    .error { background:#7f1d1d; padding:10px; border-radius:10px; margin:8px 0; }
  </style>
</head>
<body>
  <div class="card">
    <h1>账号系统</h1>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <div>管理员登录</div>
    <form method="post" action="/login">
      <input name="username" placeholder="管理员用户名" value="admin" />
      <input name="password" type="password" placeholder="管理员密码" />
      <button type="submit">登录</button>
    </form>
    <p style="color:#94a3b8; font-size:14px;">此网页后台仅管理员使用，不提供注册入口。</p>
  </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>后台</title></head>
<body style="font-family:sans-serif;padding:24px">
<h1>一码快查 · 管理后台 (recovered)</h1>
<p>用户 {{ user_count }} · 未用卡密 {{ card_count }}</p>
<h2>设置</h2>
<ul>{% for k,v in settings.items() %}<li><b>{{k}}</b>: {{v}}</li>{% endfor %}</ul>
<form method="post" action="/admin/generate-card">
  <input name="amount" placeholder="卡密面额" value="3" />
  <button type="submit">生成卡密</button>
</form>
{% if new_card %}<p>新卡密: <code>{{ new_card }}</code></p>{% endif %}
<p><a href="/logout">退出</a></p>
</body></html>
"""


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET", "recovered-billing-secret")

    def db() -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db() -> None:
        with closing(db()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    balance REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'normal',
                    is_admin INTEGER NOT NULL DEFAULT 0
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
            row = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO users(username,password_hash,balance,is_admin) VALUES(?,?,?,1)",
                    (
                        "admin",
                        generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123")),
                        0.0,
                    ),
                )
            conn.commit()

    def get_setting(key: str, default: str = "") -> str:
        with closing(db()) as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(key: str, value: str) -> None:
        with closing(db()) as conn:
            conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            conn.commit()

    def admin_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("admin"):
                return redirect(url_for("login"))
            return fn(*args, **kwargs)

        return wrapper

    @app.post("/api/desktop/login")
    def api_login():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return jsonify(ok=False, message="用户名或密码不能为空"), 400
        with closing(db()) as conn:
            row = conn.execute(
                "SELECT username,balance,status,password_hash FROM users WHERE username=?",
                (username,),
            ).fetchone()
        if not row or not check_password_hash(row["password_hash"], password):
            return jsonify(ok=False, message="用户名或密码错误"), 400
        return jsonify(
            ok=True,
            user={
                "username": row["username"],
                "balance": float(row["balance"]),
                "status": row["status"],
            },
        )

    @app.post("/api/desktop/register")
    def api_register():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return jsonify(ok=False, message="用户名或密码不能为空"), 400
        with closing(db()) as conn:
            try:
                conn.execute(
                    "INSERT INTO users(username,password_hash) VALUES(?,?)",
                    (username, generate_password_hash(password)),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                return jsonify(ok=False, message="用户名已存在"), 400
        return jsonify(ok=True, message="注册成功")

    @app.get("/api/desktop/user-info")
    def api_user_info():
        username = (request.args.get("username") or "").strip()
        if not username:
            return jsonify(ok=False, message="参数不完整"), 400
        with closing(db()) as conn:
            row = conn.execute(
                "SELECT username,balance,status FROM users WHERE username=?", (username,)
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
    def api_settings():
        key = (request.args.get("key") or "").strip()
        if not key:
            return jsonify(ok=False, message="missing key"), 400
        return jsonify(ok=True, value=get_setting(key, ""))

    @app.post("/api/desktop/decrease-balance")
    def api_decrease_balance():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        amount = data.get("amount")
        if not username or amount is None:
            return jsonify(ok=False, message="参数不完整"), 400
        try:
            amount_f = float(amount)
        except (TypeError, ValueError):
            return jsonify(ok=False, message="参数不完整"), 400
        with closing(db()) as conn:
            row = conn.execute(
                "SELECT balance FROM users WHERE username=?", (username,)
            ).fetchone()
            if not row:
                return jsonify(ok=False, message="用户不存在"), 404
            if float(row["balance"]) < amount_f:
                return jsonify(ok=False, message="余额不足"), 400
            conn.execute(
                "UPDATE users SET balance = balance - ? WHERE username=?",
                (amount_f, username),
            )
            conn.commit()
        return jsonify(ok=True)

    @app.post("/api/desktop/card-recharge")
    def api_card_recharge():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        card_code = (data.get("card_code") or "").strip()
        if not username or not card_code:
            return jsonify(ok=False, message="参数不完整"), 400
        with closing(db()) as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE username=?", (username,)
            ).fetchone()
            if not user:
                return jsonify(ok=False, message="用户不存在"), 404
            card = conn.execute(
                "SELECT code,amount,used_by FROM cards WHERE code=?", (card_code,)
            ).fetchone()
            if not card:
                return jsonify(ok=False, message="卡密不存在"), 400
            if card["used_by"]:
                return jsonify(ok=False, message="卡密已使用"), 400
            conn.execute(
                "UPDATE users SET balance = balance + ? WHERE username=?",
                (float(card["amount"]), username),
            )
            conn.execute(
                "UPDATE cards SET used_by=?, used_at=datetime('now') WHERE code=?",
                (username, card_code),
            )
            conn.commit()
            amount = float(card["amount"])
        return jsonify(ok=True, amount=amount)

    @app.get("/login")
    def login():
        return render_template_string(LOGIN_HTML, error=None)

    @app.post("/login")
    def login_post():
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        with closing(db()) as conn:
            row = conn.execute(
                "SELECT password_hash,is_admin FROM users WHERE username=?", (username,)
            ).fetchone()
        if not row or not row["is_admin"] or not check_password_hash(row["password_hash"], password):
            return render_template_string(LOGIN_HTML, error="用户名或密码错误"), 302
        session["admin"] = username
        return redirect(url_for("dashboard"))

    @app.get("/dashboard")
    @admin_required
    def dashboard():
        with closing(db()) as conn:
            user_count = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
            card_count = conn.execute(
                "SELECT COUNT(*) c FROM cards WHERE used_by IS NULL"
            ).fetchone()["c"]
            settings = {
                r["key"]: r["value"] for r in conn.execute("SELECT key,value FROM settings")
            }
        return render_template_string(
            DASHBOARD_HTML,
            user_count=user_count,
            card_count=card_count,
            settings=settings,
            new_card=session.pop("new_card", None),
        )

    @app.post("/admin/generate-card")
    @admin_required
    def generate_card():
        amount = float(request.form.get("amount") or 3)
        code = secrets.token_hex(8)
        with closing(db()) as conn:
            conn.execute(
                "INSERT INTO cards(code,amount) VALUES(?,?)", (code, amount)
            )
            conn.commit()
        session["new_card"] = code
        return redirect(url_for("dashboard"))

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    init_db()
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "9110")), debug=False)
