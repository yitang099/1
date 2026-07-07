# 一码快查 API 接口图谱

探测时间：2026-07-07  
目标：`43.154.128.116:9110`（Flask 计费）、`47.76.163.227:8081`（.NET SMS）

---

## 9110 Flask 计费后台

Base: `http://43.154.128.116:9110`

### 公开 API（`/api/desktop/*`）

| 方法 | 路径 | 鉴权 | 请求 | 响应要点 |
|------|------|------|------|----------|
| GET | `/api/desktop/settings` | 无 | `?key=<name>` 必填 | `{"ok":true,"value":"..."}`；key 不存在返回空字符串 |
| GET | `/api/desktop/user-info` | 无 | `?username=` 必填 | `balance`, `status`, `deduct_amount`；用户不存在 404 |
| POST | `/api/desktop/register` | 无 | `{"username","password"}` | 成功 200；已存在 409 |
| POST | `/api/desktop/login` | 无 | `{"username","password"}` | 成功 200 + token/session；失败 401 |
| POST | `/api/desktop/card-recharge` | 无 | `{"username","card_code"}` | 卡密不存在 404；已使用 400 |
| POST | `/api/desktop/decrease-balance` | **无** | `{"username","amount"}` | 扣费成功 `{"ok":true}`；余额不足 400 |
| POST | `/api/desktop/refund-balance` | **无** | `{"username","amount"}` | 加余额 `{"ok":true,"amount":N}`（隐藏接口） |

#### settings 已知有效 key（有值）

| key | 示例值 |
|-----|--------|
| `api_secret` | `b9887333ae4c43858c9235e0ac4e0921` |
| `api_domain` | `http://47.76.163.227:8081` |
| `contact_link` | `https://t.me/kuaichaq` |
| `deduct_amount` | `2.0`（曾观测 3.0，运营方可改） |

其余探测 key（`admin_password`, `host_exe`, `sms_token` 等）均返回空。

#### user-info 错误码

| HTTP | message |
|------|---------|
| 400 | `missing username` |
| 404 | `用户不存在` |

#### register / login 错误码

| 场景 | HTTP | message |
|------|------|---------|
| 用户已存在 | 409 | `用户名已存在` |
| 登录失败 | 401 | `用户名或密码错误` |
| 空字段 | 400 | `用户名或密码不能为空` |

#### decrease-balance / refund-balance

| 场景 | HTTP | message |
|------|------|---------|
| 缺参 | 400 | `参数不完整` |
| 非法金额 | 400 | `金额不合法` |
| 用户不存在 | 404 | `用户不存在` |
| 余额不足（decrease） | 400 | `余额不足` |
| amount=NaN | 500 | Werkzeug Debugger 泄露源码 |

---

### 管理后台（需 `session['admin']`）

| 方法 | 路径 | 未登录行为 |
|------|------|------------|
| GET | `/login` | 登录页 HTML |
| POST | `/login` | 表单登录；错误文案 `管理员账号或密码错误` |
| GET | `/logout` | 退出（跳转登录） |
| GET | `/dashboard` | 302 → `/login` |
| GET | `/admin/users` | 302 → `/login` |
| POST | `/admin/delete-cards` | 302 → `/login` |

**不存在**：`POST /admin/generate-card`（404，与本地重建版不同）

---

### Debugger 泄露的 app.py 函数

| 行号 | 函数 | 路由 |
|------|------|------|
| ~613 | `api_desktop_decrease_balance` | POST `/api/desktop/decrease-balance` |
| ~635 | `api_desktop_refund_balance` | POST `/api/desktop/refund-balance` |
| 下一行 | — | POST `/admin/delete-cards` |

客户端字节码确认的 9110 路径仅 6 个（无 refund，说明为服务端隐藏接口）。

---

## 8081 .NET SMS 后端

Base: `http://47.76.163.227:8081`  
鉴权：`api_secret` 作为 URL 路径段（非 Header）

### 接口一览

| 方法 | 路径 | Body / 说明 | 响应 |
|------|------|-------------|------|
| POST | `/create/{secret}` | `{"area":"86","data":"<手机号>","islink":false}` | `{"code":0,"data":"<order_id>"}` |
| POST | `/create/{secret}/` | 同上（尾斜杠可用） | 同上 |
| GET | `/query/{secret}/{order_id}` | — | JSON 见下表 |
| GET | `/setsms/{secret}/{phone}/{code}` | — | 纯文本 |
| POST | `/setsms/{secret}/{phone}/{code}` | — | 同 GET |

**不支持**：`/create/` 无 secret、`/query?order_id=` 查询串、Swagger、REST 风格 CRUD。

### create 请求体

```json
{
  "area": "86",
  "data": "13800138000",
  "islink": false
}
```

| 字段 | 说明 |
|------|------|
| `area` | 区号，支持 `86`、`1` 等 |
| `data` | 手机号或（`islink:true` 时）特殊链接格式 |
| `islink` | `true` 时需特定格式，否则 `code:-2` |

### create 错误码

| code | err 示例 |
|------|----------|
| 0 | 成功，`data`=order_id |
| -2 | `未检测到有效手机数据` |
| -3 | `此手机号码已经正在进行查询` |

### query 响应

| code | err | 含义 |
|------|-----|------|
| 0 | — | 成功，`data` 含查询结果（QQ 绑定信息等） |
| -1 | `订单不存在` | 无效 order_id |
| -1 | `订单正在处理` | 等待短信/验证流程 |

成功时 `data` 为 JSON 字符串；客户端解析失败关键词：`未注册`、`发送短信失败`、`失败`、`未绑定`、`短信发送失败`。

### setsms 响应（纯文本）

| 响应 | 含义 |
|------|------|
| `上传短信验证码成功` | 验证码已接收 |
| `没有该手机订单!` | 无匹配进行中的订单 |
| `无效手机或者短信验证码!` | 格式校验失败（如 5 位码） |

流程：create → 手机收到短信 → 用户/客户端调用 setsms 提交验证码 → query 轮询结果。

---

## 客户端调用顺序（正常业务）

```
1. GET  /api/desktop/settings?key=api_secret|api_domain|deduct_amount
2. POST /api/desktop/login 或 register
3. GET  /api/desktop/user-info?username=
4. POST {api_domain}/create/{api_secret}     ← 8081
5. POST /api/desktop/decrease-balance        ← 9110 扣费
6. GET  {api_domain}/setsms/{secret}/{phone}/{code}  ← 用户输入验证码
7. GET  {api_domain}/query/{secret}/{order_id}       ← 轮询结果
8. POST /api/desktop/card-recharge           ← 充值（或滥用 refund-balance）
```

---

## 探测结论

| 类别 | 9110 | 8081 |
|------|------|------|
| 已确认接口 | 7 个 desktop API + 5 个 admin 页 | 3 个（create/query/setsms） |
| 隐藏/未文档化 | `refund-balance` | 无 |
| 写接口未鉴权 | decrease、refund、register | create/query/setsms 仅 secret |
| 未发现 | records/logs/orders API、generate-card | swagger、admin、webhook |

工具：`python3 tools/api_deep_probe.py`
