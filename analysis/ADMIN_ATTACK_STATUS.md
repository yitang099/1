# 后台攻击与源码获取状态 (2026-07-07)

## 目标

进入 `/admin/users`、`/dashboard`，读取生产 `app.py` 真源码。

---

## 已尝试（未成功）

| 攻击面 | 结果 |
|--------|------|
| `admin` / 135+ 弱口令喷洒 | 全部 `管理员账号或密码错误` |
| 多用户名喷洒 (14×8) | 无命中 |
| Session 伪造 `session['admin']` + `pohZc8RrQkczwHyYZUbX` | **签名不匹配** — 该值不是 Flask `secret_key` |
| rockyou 前 6.1 万条作 secret 爆破 | 未破解 |
| PIN cookie RCE (500+ 候选) | 未命中；`pinauth exhausted` |
| Debugger `cmd=execute` | `EVALEX=false`；需 PIN |
| SSH 43.154:22 / :2222 | 连接关闭或密码未中 |
| SQLi / SSTI / 注册提权 | 无效 |
| `/.git` / `app.py` 直链 | 404 |

---

## 关键纠正

**debugger 页面里的 `SECRET = "..."` 是 Werkzeug 调试会话密钥（每次 500 随机），不是 Flask `secret_key`。**

验证方式：

```python
from flask.sessions import SecureCookieSessionInterface
ser = SecureCookieSessionInterface().get_signing_serializer(type('A',(),{'secret_key':'pohZc8RrQkczwHyYZUbX'})())
ser.loads(real_session_cookie)  # BadSignature
```

因此此前 session 伪造进后台失败是预期行为。

---

## 仍可推进的路径

1. **Flask secret 大字典爆破** — `tools/admin_attack.py --crack-session`（需更大 wordlist / hashcat）
2. **Werkzeug PIN** — 等 `exhausted` 重置 + 拿到服务端 `machine-id`/MAC
3. **Debugger RCE** — PIN 正确后 `GET ?__debugger__=yes&cmd=open(...).read()&frm=...`
4. **SSH** — 2222 端口开放但需密钥或正确口令
5. **运营泄露** — GitHub/Gitee 未发现同源仓库

---

## 当前最接近真源码的文件

| 文件 | 说明 |
|------|------|
| `analysis/recovered/app_production_reconstructed.py` | 合并 debugger 泄露 SQL/路由 + 实机 API 行为 + 生产登录页 HTML |
| `analysis/leaked_refund_snippet.py` | refund handler 片段 (line ~635) |
| `analysis/leaked_app_snippet.py` | decrease handler 片段 (line ~613) |
| `analysis/page_login.html` | 生产登录页原样 |

**真 `app.py` 尚未完整拿到**；重建稿覆盖约 7 个 desktop API + admin 路由骨架。

---

## 工具

```bash
python3 tools/admin_attack.py --spray-login
python3 tools/admin_attack.py --crack-session
python3 tools/admin_attack.py --forge --secret '<key>' --admin-user admin
```
