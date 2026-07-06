@app.route("/admin/delete-cards", methods=["POST"])
balance = float(user[0])
conn.commit()
conn.execute("UPDATE accounts SET balance = balance - ? WHERE username = ? AND account_type = 'user'", (amount, username))        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
if balance < amount:
if user is None:
return jsonify({"ok": False, "message": "余额不足"}), 400
return jsonify({"ok": False, "message": "用户不存在"}), 404
return jsonify({"ok": True})