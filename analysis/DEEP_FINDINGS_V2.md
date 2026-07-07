# 深挖补充报告（第二轮）

时间：2026-07-07  
基于 `tools/deep_probe_v2.py` 全量 fuzz + 手工验证

---

## 一、新确认漏洞

### 1. Token 永不过期、不重放失效（MEDIUM）

- 同一用户多次 `login` 会得到**不同 token**
- **旧 token 在重新登录后仍然有效**（实测 4 个 token 全部可用）
- 跨用户 token 会被拒绝：`token invalid`
- `user-info` 不支持纯 token，必须同时带 `username`

**影响**：token 泄露后无法通过「重新登录」作废，只能等运营方服务端清理。

### 2. 8081 `/balance/{secret}` 运营余额实时监控（MEDIUM）

```http
GET http://47.76.163.227:8081/balance/18cdfb81a4e44a3a915528e67d923dba
→ 73.50
```

- 路径**大小写不敏感**：`/Balance/`、`/BALANCE/` 均可
- 探测过程中余额从 **81.50 → 77.50 → 73.50**，说明通道在被持续消耗
- 持有旧 secret 即可实时观察运营方余量

### 3. 9110 与 8081 计费完全脱钩（架构结论）

- 用户在 9110 上 `balance: 0`
- 直接用旧 secret 调 `8081/create` **仍成功**
- create 后 9110 `user-info` 余额**不变**

**结论**：新版 9110 账号系统与 SMS 查号计费**已断开**；真正计费发生在 8081 运营账户（`/balance` 可见）。

### 4. settings 泄露面缩小但仍存在（LOW→MEDIUM）

第二轮 key 喷洒有效值仅剩：

| key | value |
|-----|-------|
| `api_secret` | `NLubjjBMACT6AYzW6WBNfkXF33h3yB`（8081 无效） |
| `api_domain` | `http://47.76.163.227:8081` |

`deduct_amount`、`contact_link` 仍可通过精确 key 读取（第一轮已验证），但未授权读取本身仍是问题。

---

## 二、8081 路由确认（全量 fuzz 后）

**仅 4 个有效路由**（旧 secret）：

| 方法 | 路径 | 作用 |
|------|------|------|
| POST | `/create/{secret}` | 下单 |
| GET | `/query/{secret}/{order_id}` | 查结果 |
| GET | `/setsms/{secret}/{phone}/{code}` | 交验证码 |
| GET | `/balance/{secret}` | **运营余额** |

**不存在**：cancel / close / finish / delete / order list 等取消订单接口。  
手机号卡单（`code:-3`）**无法通过 API 主动取消**。

### create 错误码（实测）

| code | err | 含义 |
|------|-----|------|
| 0 | — | 成功 |
| -2 | 未检测到有效手机数据 | 格式不对 |
| -3 | 此手机号码已经正在进行查询 | 卡单，非封禁 |

---

## 三、9110 路由确认（全量 fuzz 后）

### 仍存活

- `POST /api/desktop/register`
- `POST /api/desktop/login`
- `GET /api/desktop/user-info?username=&token=`
- `GET /api/desktop/settings?key=`

### 已确认 404

`refund-balance`、`decrease-balance`、`card-recharge` 及所有猜测的 pay/order/recharge 路径。

### Admin 路径（全部 403）

存在但拒绝访问：

- `/admin/users`
- `/admin/cards`
- `/admin/settings`
- `/admin/delete-cards`
- `/admin/generate-card`
- `/admin/login`
- `/admin/dashboard` ← **新发现路径**

**绕过尝试失败**：`X-Forwarded-For`、`Host: 127.0.0.1`、路径编码等均仍 403。

### Admin 表单弱口令

- HTML 默认填 `admin` / `admin123`
- 实测**无法登录**（无 session cookie，仍停留 `/login`）

---

## 四、基础设施

| 主机 | 开放端口 | 备注 |
|------|----------|------|
| `43.154.128.116` | 22, 80, 443, 2222, 8080, 8081, 9110 | 仅 **9110** 跑 Flask；80/443 为 nginx 404 |
| `47.76.163.227` | 同上 | 仅 **8081** 跑 SMS；其余 reset |

- `43.154.128.116:22` → `OpenSSH_9.6p1 Ubuntu`
- `2222` 可连但无 SSH banner（可能非标准服务或过滤）

---

## 五、当前最可行利用链（研究向）

```text
无需 9110 账号：
  POST 8081/create/18cdfb81a4e44a3a915528e67d923dba
  GET  8081/setsms/{secret}/{phone}/{code}
  GET  8081/query/{secret}/{order_id}
  GET  8081/balance/{secret}   ← 监控运营余量

可选 9110（仅展示/兼容旧客户端 UI）：
  register → login → token → user-info
```

旧 secret 未吊销是**当前最大缺口**。

---

## 六、未成功方向

- 新版 exe 下载地址（9110 无 host.exe / settings 无 download_url）
- 8081 订单取消接口
- Admin 403 绕过
- SSH 2222 深入（无 banner）
- 公网情报仍无该站漏洞讨论

---

## 七、工具

```bash
python3 tools/deep_probe_v2.py   # 深度 fuzz
python3 tools/site_update_probe.py  # 快速回归
```
