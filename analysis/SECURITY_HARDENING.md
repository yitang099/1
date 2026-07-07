# 授权安全审计报告（更新后版本）

**角色**：运营方授权复测  
**时间**：2026-07-07  
**目标**：`43.154.128.116:9110` + `47.76.163.227:8081`

---

## 执行摘要

下午修复的 **refund / decrease / card-recharge / Debugger** 已确认生效，这是关键进展。

但当前仍存在 **可被外部继续白嫖 SMS 通道** 的路径，核心原因是：

> **8081 旧 `api_secret` 未吊销，且 9110 用户余额已与 8081 查号脱钩。**

攻击者**不需要**有效 9110 余额，只要持有旧 secret 即可持续 `create`，消耗的是你在 8081 侧的通道余额（`/balance` 已从 ~81 元降至 ~53 元）。

---

## 已修复项（确认有效）

| 项目 | 状态 |
|------|------|
| `POST /api/desktop/refund-balance` | 404 |
| `POST /api/desktop/decrease-balance` | 404 |
| `POST /api/desktop/card-recharge` | 404 |
| Werkzeug Debugger（NaN 触发） | 不可用 |
| `user-info` 未鉴权枚举 | 已加 `token` |
| admin 未登录 302 | 改为 403 |

---

## 仍存漏洞（按优先级）

### P0 — 必须立即处理

#### 1. 旧 8081 secret 未吊销

| 项目 | 内容 |
|------|------|
| 泄露 secret | `18cdfb81a4e44a3a915528e67d923dba` |
| 现状 | `create` / `query` / `setsms` / `balance` **全部仍有效** |
| settings 新 secret | `NLubjjBMACT6AYzW6WBNfkXF33h3yB` → 8081 返回 `无效Token!`（已与 8081 脱钩，但旧 key 仍活） |
| 影响 | 任何人可绕过 9110 账号体系直接查号，消耗通道余额 |

**修复建议**：
```text
1. 在 8081 立即吊销 18cdfb81... 及历史上所有泄露 secret
2. 重新生成 secret，仅下发给新版客户端（不要放 settings 明文）
3. 8081 增加 per-user / per-token 鉴权，不要只靠 URL path secret
```

#### 2. 9110 与 8081 计费脱钩

- 用户 `balance: 0` 仍可 `8081/create` 成功
- 9110 的 `deduct_amount`、`balance` 对查号**无约束力**

**修复建议**：
```text
方案 A（推荐）：8081 create 必须校验 9110 签发的短期 JWT + 扣费回调
方案 B：客户端 secret 绑定用户 token，8081 向 9110 验签后再下单
```

---

### P1 — 高优先级

#### 3. `GET /api/desktop/settings` 仍无鉴权

仍可读取：`api_secret`、`api_domain`、`deduct_amount`、`contact_link`

即使 8081 secret 不再与 settings 同步，也暴露业务配置，且未来一旦重新关联会再次泄露。

**修复**：settings 改为需 `token` 或 admin session；或仅返回客户端必需的非敏感字段。

#### 4. `GET /balance/{secret}` 泄露运营通道余额

```http
GET /balance/18cdfb81a4e44a3a915528e67d923dba → 53.50
```

攻击者可实时监控你的通道余量、判断攻击效果。

**修复**：删除该接口或限制内网 / admin 访问。

#### 5. Token 重新登录不失效

- 每次 `login` 生成新 token
- **旧 token 永久有效**，无法通过改密/重登作废

**修复**：
```python
# 登录时
UPDATE users SET token = ? WHERE username = ?  -- 覆盖旧 token
# 或维护 token 版本号 / 黑名单
```

---

### P2 — 中优先级

#### 6. 开放注册无限速

15 次连续注册全部成功，无验证码、无 IP 限速。

**修复**：同 IP 限速、验证码、或邀请码注册。

#### 7. 用户名枚举

| 场景 | 响应 |
|------|------|
| 注册已存在用户 | `409 用户名已存在` |
| 登录失败 | `401 用户名或密码错误` |

可区分「用户是否存在」。

**修复**：统一错误文案与 HTTP 状态码。

#### 8. 8081 无订单取消接口

手机号 `-3` 卡单后只能等超时，易被用来占坑骚扰。

**修复**：增加 `cancel/{secret}/{order_id}` 或超时自动释放（建议 10–15 分钟）。

#### 9. admin 登录页 HTML 泄露默认凭据样式

```html
<input name="username" value="admin" />
<input name="password" value="admin123" />
```

虽实测无法登录，但会引导攻击者聚焦弱口令。

**修复**：移除 `value` 默认值。

#### 10. 8081 `create` / `setsms` 无速率限制（第三轮）

- 10 个不同手机号连续 create：**10/10 成功**（~4.5s）
- 20 次错误 setsms：无封禁（~8.8s）
- 通道余额仅剩 **5.50 元时 create 仍返回 code:0**

**修复**：IP/secret 限速；余额低于阈值拒绝 create；setsms 失败锁定。

---

### P3 — 低优先级 / 已通过

| 项目 | 结果 |
|------|------|
| SQLi（login/register） | 未发现 |
| 注册 mass assignment（balance/admin） | 额外字段被忽略 |
| CORS 反射 | 未发现 |
| admin X-Forwarded-For 绕过 | 失败 |
| 8081 secret 暴力（抽样） | 无速率限制，但仅返回无效Token |

---

## 8081 路由清单（当前）

| 方法 | 路径 | 风险 |
|------|------|------|
| POST | `/create/{secret}` | 核心业务能力，需强鉴权 |
| GET | `/query/{secret}/{order_id}` | 需与 create 同权 |
| GET | `/setsms/{secret}/{phone}/{code}` | 可被暴力尝试验证码 |
| GET | `/balance/{secret}` | **信息泄露，建议删除** |

---

## 9110 路由清单（当前）

| 方法 | 路径 | 鉴权 |
|------|------|------|
| POST | `/api/desktop/register` | 无 |
| POST | `/api/desktop/login` | 无 |
| GET | `/api/desktop/user-info` | `username` + `token` |
| GET | `/api/desktop/settings` | **无（问题）** |

---

## 建议修复顺序（今天可做）

```text
[今天 P0]
1. 8081 吊销 secret: 18cdfb81a4e44a3a915528e67d923dba
2. 8081 下线 /balance 或限制内网
3. settings 停止返回 api_secret 明文

[本周 P1]
4. 8081 create 增加 9110 token 校验 + 扣费
5. login 时作废旧 token
6. 注册限速 + 验证码

[后续 P2]
7. 统一枚举错误信息
8. 8081 订单超时释放 / cancel 接口
9. admin 登录页去掉默认密码
```

---

## 复测命令

```bash
python3 tools/site_update_probe.py   # 快速回归
python3 tools/deep_probe_v2.py       # 深度 fuzz
python3 tools/authorized_audit.py    # 授权审计清单
```

修复 P0 后重新跑 `site_update_probe.py`，应看到：
- 旧 secret create 返回 `无效Token!`
- settings 不再返回 `api_secret` 或需鉴权

---

## 相关文档

- `analysis/SITE_UPDATE_REPORT.md` — 更新对比
- `analysis/DEEP_FINDINGS_V2.md` — 第二轮技术细节
- `analysis/ROUND3_FINDINGS.md` — 第三轮：无限速、低余额仍可 create
- `analysis/ROUND4_FINDINGS.md` — 第四轮：create 错误泄露单价4元/余额、国际号、竞态
