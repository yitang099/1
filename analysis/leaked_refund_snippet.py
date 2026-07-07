# Leaked from Werkzeug debugger — api_desktop_refund_balance @ app.py line ~635

@app.route("/api/desktop/refund-balance", methods=["POST"])
def api_desktop_refund_balance():
    # ...
    # return jsonify({"ok": False, "message": "参数不完整"}), 400
    with closing(get_conn()) as conn:
        user = conn.execute(
            "SELECT id FROM accounts WHERE username = ? AND account_type = 'user'",
            (username,),
        ).fetchone()
        if user is None:
            return jsonify({"ok": False, "message": "用户不存在"}), 404
        conn.execute(
            "UPDATE accounts SET balance = balance + ? WHERE username = ? AND account_type = 'user'",
            (amount, username),
        )
        conn.commit()
    return jsonify({"ok": True, "amount": amount})

# Next route in file:
# @app.route("/admin/delete-cards", methods=["POST"])
