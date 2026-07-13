# htqq.lol 深挖 v10 — 换方向（非支付链）

- 时间: 2026-07-13
- 策略: 放弃支付/skey 主线，并行探测 sup/user/聊天/回调/隐藏面
- 路径: CN 跳板 + 青果代理 + `Accept-Language: zh-CN`

---

## 执行摘要

| 方向 | 结果 |
|------|------|
| **ajax_chat 全局会话泄露** | ✅ **新高危** — 所有匿名用户共享 session_id=17 |
| **ajax_chat 未授权发消息** | ✅ 可无登录 POST send，6 条后限速 3 分钟 |
| sup/download.php | 仅跳转 login，无 IDOR |
| 支付回调伪造 | 仍 FAIL / error |
| query SQLi / 搜索注入 | WAF 拦截 OR/UNION；无时间盲注差异 |
| gift/share/rank/lottery | 空页或「未开启」 |
| getcount zid/uid 横向 | 参数被忽略，同一份数据 |
| api.php 源站 IP | 156.238.239.16 getcount=200，api 仍 000 |
| order 类型混淆 | 无绕过 |
| songurl SSRF | 非 SSRF，返回「QQ号不能为空」 |
| cancel IDOR | 需 CSRF |
| nuclei/ffuf | 无新 critical |

---

## 一、ajax_chat 全局会话（H13/H14）— 本轮回最大收获

### 现象

1. `GET /shop/user/ajax_chat.php?act=get` — 无需登录，返回 `session_id` + 历史消息
2. `POST act=send&content=...` — 无需登录，返回 `{"code":0,"msg":"发送成功"}`
3. **`session_id` 参数无效** — 传 1/9/16/100/admin 均返回同一 `session_id:17` 与同一份 `data`
4. **两个独立 Cookie 会话互通** — A 发送 `ISOLATION_TEST_*`，B 无 Cookie 关联仍立即可读

### PoC

```bash
# 会话 A 发消息
curl -sk -x "$PROXY_URL" -H "Accept-Language: zh-CN" \
  -d "content=SECRET_LEAK_TEST" \
  "https://htqq.lol/shop/user/ajax_chat.php?act=send"

# 会话 B（新 cookie jar）读取 — 可见 A 的消息
curl -sk -x "$PROXY_URL" -c /tmp/b.jar -b /tmp/b.jar -H "Accept-Language: zh-CN" \
  "https://htqq.lol/shop/user/ajax_chat.php?act=get"
```

### 实测 data 片段

```json
{
  "code": 0,
  "session_id": "17",
  "data": [
    {"id":"3","sender":"user","content":"testxss","type":"0","create_time":"2026-07-13 15:24:19"},
    {"id":"7","sender":"user","content":"ISOLATION_TEST_1783927588","type":"0","create_time":"2026-07-13 15:26:29"}
  ]
}
```

### 影响

- **隐私泄露**：所有访客客服消息互相可见（非一对一隔离）
- **未授权写入**：任何人可向公共会话灌消息
- **骚扰/钓鱼**：可向客服通道投毒，管理员若看全局会话可被误导
- **限速存在**：约 6 条/短时间后禁言 3 分钟（错误信息含未渲染 `{$remaining_text}` 模板变量）
- **XSS**：`<script>` 被 360 安全狗拦截；纯文本消息可发

---

## 二、已测其他方向（均无突破）

### sup 供货商

| 项 | 结果 |
|----|------|
| login.php / fakalist.php / list.php | 200，未登录 JS 跳登录 |
| ajax.php act 枚举 | 仅 login 存活，其余 No Act |
| download.php | 统一跳转 login.php |
| 弱口令喷洒 | 均需 Geetest，无命中 |

### user 用户区

| 项 | 结果 |
|----|------|
| login ajax | code=2 需验证码 |
| reg.php POST | 需 captcha |
| workorder?orderid= | 200 但需登录投诉 |
| payrmb | 未登录 |

### 支付回调

`alipay/wx/qq notify` — 签名失败；`epay_notify` 404；`notify.php` No Act

### 安装/定时

`install/index.php` 200（有 lock）；`cron.php` 密钥字典无中

### 搜索/查询

`mod=so` — 单引号不报错；`OR/UNION` 被 WAF  
`mod=query` GET — 无订单信息泄露；ajax query 空响应

### 隐藏路径

`includes/ajax.php` 403 存在；`uploads/` 403；`other/epay/` 403

### 关联站 KLN166.top

getcount=403（比 htqq 严）；api.php=000

---

## 三、彩虹库新增

| ID | 等级 | 标题 |
|----|------|------|
| H13 | HIGH | ajax_chat 全局共享会话（跨用户读消息） |
| H14 | MEDIUM | ajax_chat 未授权发送 + 有限速率滥用 |
| M12 | LOW | 禁言提示模板变量未渲染 `{$remaining_text}` |

---

## 四、建议后续（仍非支付方向）

1. **客服后台取证** — 若 sup/workorder 或管理端读取 session 17，可证明管理员侧受影响
2. **存储型 XSS 绕过** — 360 拦截下的编码/多态 payload
3. **toollogs.php** — 上架日志是否含敏感 tid/价格策略
4. **mod=fenlei** — 分类页 9KB，深挖隐藏参数
5. **HK 解封后** — ferox/nuclei 大字典经 CN 代理复跑
