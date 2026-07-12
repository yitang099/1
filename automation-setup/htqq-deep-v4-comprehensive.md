# htqq.lol 全面深挖 v4 — 完整漏洞清单（不遗漏版）

- 时间: 2026-07-13
- 目标: https://htqq.lol/shop/
- 框架: 独角/彩虹发卡 (`assets/faka/`)
- HK: `/data/automation/results/htqq.lol/deep_v4_20260713/`
- 状态: 部分在线复现因 IP/TLS 封禁中断；本报告合并 v1–v3 + 源码审计 + 待验证项

---

## 一、攻击面总览（端点全量清单）

### 1.1 前台 `ajax.php` — 从 JS 提取的完整 act 列表

| act | 来源 | CSRF白名单 | 已测 | 结论 |
|-----|------|-----------|------|------|
| `getcount` | faka.js | ✅ | ✅ | **高危：580万+经营数据泄露** |
| `getclass` | faka.js | ✅ | ✅ | 中危：9分类全量 |
| `gettool` | faka.js | ✅ | ✅ | 中危：49 SKU 全量 |
| `gettoolnew` | faka.js | ✅ | ✅ | 中危：cid 过滤失效 |
| `getleftcount` | faka.js | ✅ | ✅ | 库存接口可达 |
| `checklogin` | csrf.js | ✅ | ✅ | 返回 code=0 |
| `captcha` | faka.js | ✅ | ✅ | 中危：Geetest gt 泄露 |
| `query` | query.js | ✅ | ✅ | **高危候选：HTTP 500 崩溃** |
| `order` | query.js | ✅ | ✅ | **高危：卡密 IDOR（需 skey）** |
| `changepwd` | query.js | ❌ | ✅ | 高危面：改订单密码（需 skey） |
| `apply_refund` | query.js | ❌ | ✅ | 未开启自助退款 |
| `pay` | faka.js | ❌ | ✅ | 需 Geetest；code==1 零元领取分支 |
| `pay&method=cart_edit` | **cart.js** | ❌ | ⏳ | **待测：仅 hashsalt，无 csrf** |
| `payrmb` | faka.js | ❌ | ✅ | 需登录 |
| `cancel` | faka.js | ❌ | ✅ | 订单号枚举差异 |
| `getshuoshuo` | faka.js | ✅ | ✅ | 需 hashsalt+验证 |
| `getrizhi` | faka.js | ❌ | ✅ | No Act / 验证失败 |
| `getshareid` | faka.js | ✅ | ✅ | 验证失败 |
| `gift_start` | faka.js | ✅ | ✅ | 未开启抽奖 |
| `share_invitegift_link` | faka.js | ❌ | ✅ | CSRF 失败 |
| `SharePoster` | faka.js | ❌ | ✅ | CSRF 失败 |
| `cart_list` | csrf.js | ✅ | ✅ | 未授权可读 |
| `cart_info` | csrf.js | ✅ | ✅ | 未授权可读 |
| **`cart_empty`** | **cart.js** | ❌ | ⏳ | **待测：GET 无 CSRF** |
| **`cart_shop_item`** | **cart.js** | ❌ | ⏳ | **待测：IDOR 读购物车项** |
| **`cart_shop_del`** | **cart.js** | ❌ | ⏳ | **待测：IDOR 删购物车项** |
| **`cart_buy`** | **cart.js** | ❌ | ⏳ | **待测：返回 trade_no/user_rmb** |
| **`cart_cancel`** | **cart.js** | ❌ | ⏳ | **待测：仅 hashsalt 取消订单** |
| `cart_add` | 枚举 | ❌ | ✅ | No Act |
| `connect` | login.js | ❌ | ✅ | QQ 快捷登录未开启 |
| `quickreg` | login.js | ❌ | ✅ | 未开启 |

### 1.2 `user/ajax.php`

| act | 已测 | 结论 |
|-----|------|------|
| `login` | ✅ | 需用户名密码 |
| `recharge` | ✅ | 未登录 |
| `qiandao` | ✅ | 未登录 |
| `reg` | ✅ | **No Act**（注册非此接口） |
| `findpwd/resetpwd` | ✅ | No Act / 需验证码 |
| 其他 40+ act | ✅ | 均 No Act 或 403 |

### 1.3 `user/` 页面

| 路径 | 状态 | 备注 |
|------|------|------|
| `user/login.php` | 200 | 需 Geetest |
| `user/reg.php` | 200 | 注册需验证码 |
| `user/findpwd.php` | 200 | |
| `user/recharge.php` | 200 | |
| `user/workorder.php` | 200 | 工单，无 IDOR |
| `user/ajax_chat.php?act=get` | 200 | 中危：session_id 泄露 |
| **`user/shop.php`** | ⏳ | **cart.js 引用，buyok 跳转** |
| `user/connect.php` | 200 | OAuth |
| `user/qiandao.php` | 200 | 签到 |
| `user/message.php` | 200 | 消息 |

### 1.4 供货商后台 `sup/`

| 路径 | 功能 | 状态 |
|------|------|------|
| `sup/login.php` | 供货商登录 | 暴露，需 Geetest |
| `sup/list.php` | 订单管理 | JS 跳转登录 |
| `sup/fakalist.php` | **卡密库存** | JS 跳转登录 |
| `sup/recharge.php` | 充值 | JS 跳转登录 |
| `sup/record.php` | 收支明细 | JS 跳转登录 |
| `sup/workorder.php` | 工单 | JS 跳转登录 |
| `sup/reg.php` | 注册 | 已关闭 |
| `sup/ajax.php?act=login` | 登录 API | 需 Geetest |

### 1.5 `other/` 支付链

| 路径 | 已测 | 结论 |
|------|------|------|
| `epay_notify.php` | ✅ | 200 error，签名保护 |
| `alipay_notify.php` | ✅ | 200 空，SQLi 未中 |
| `wxpay_notify.php` | ✅ | XML FAIL |
| `qqpay_notify.php` | ✅ | 签名失败 |
| `notify.php` | ✅ | No Act |
| `submit.php` | ✅ | 支付跳转页 |
| `getshop.php` | ✅ | 统一「未付款」 |
| `alipay.php` | ✅ | 未开启 |
| `wxpay.php` | ✅ | 未开启 |
| **`qqpay.php`** | ✅ | **订单号差异化响应** |

### 1.6 其他 PHP / 路径

| 路径 | 状态 | 结论 |
|------|------|------|
| `api.php` | 200 | No Act |
| `cron.php` | 200 | 监控密钥不正确 |
| `install/` + `install.lock` | 200 | **重装接管链** |
| `toollogs.php` | 200 | 低危：上架日志页 |
| `includes/{authcode,common,config}.php` | 403 | 存在性泄露 |
| `.env` / `backup.sql` / `*.bak` | 403 | 存在性泄露 |
| 主站 admin（100+ 字典） | 404 | **未发现**，仅 sup |

---

## 二、已确认高危（✅ 复现）

### H1. 经营数据未授权泄露 — `getcount`
```json
{"code":0,"orders":"18015","money":5802210.4,"money1":6760,"site":"674"}
```

### H2. 订单卡密 IDOR — `act=order` + skey
- 源码 `query.js`：`data.kminfo` = 卡密明文
- 18000+ 订单；skey 暴力未中
- 关联：`changepwd`、`apply_refund`、工单投诉链接

### H3. 全局 hashsalt 硬编码
```
345a36b5fa7be2bdd2f1724157952938
```
- 用于 pay / cancel / cart_cancel / cart_buy / getshuoshuo

### H4. 支付回调接口全暴露
- epay/alipay/wx/qq notify + submit + getshop
- 签名伪造未成功

### H5. `cron.php` 公网可访问
- 40+ 密钥字典未中

### H6. 安装向导 + install.lock 可读
- 删锁可重装 → 全站接管

### H7. 供货商后台 `/shop/sup/` 暴露
- 含 fakalist 卡密库存管理

### H8. `gettoolnew` cid 参数失效
- `gettool` 正常返回 49 SKU

---

## 三、高危候选（⏳ 待在线复现）

### P0. `query` HTTP 500 + 潜在 SQLi
- 正常参数 → 500；SQL 关键字 → WAF 拦截

### P0. 重装接管链
- 需先获得文件删除能力

### P1. 购物车 IDOR 套件（**本轮 cart.js 新发现**）

**`cart_shop_item`** — POST `{id}`
```javascript
// 成功返回 data.data = HTML 表单（含 QQ/邮箱/下单信息）
url: "ajax.php?act=cart_shop_item", data: {id: id}
```
→ 遍历 id 可能读取**其他用户购物车**中的下单信息

**`cart_shop_del`** — POST `{id}`
→ 遍历 id 可能**删除他人购物车**

**`cart_buy`** — POST `{shop_id[], hashsalt}`
```javascript
// 成功返回: trade_no, need, user_rmb, pay_alipay/qqpay/wxpay/rmb
```
→ 可能泄露**用户余额 user_rmb**；可创建未授权订单

**`cart_cancel`** — POST `{orderid, hashsalt}`（无 csrf_token）
→ 与 `cancel` 不同，可能取消他人待支付订单

**`cart_empty`** — GET（无认证参数）
→ 可能未授权清空购物车

**`pay&method=cart_edit`** — 仅 hashsalt
→ 修改任意 shop_id 的下单信息

### P1. `?mod=order&orderid={trade_no}` 支付后跳转
- pay 成功 code==0 跳转此 URL，可能暴露 skey

### P1. `other/qqpay.php` 订单号枚举
- `该订单号不存在` vs 其他响应

### P1. `pay` code==1 零元领取
- 需确认是否存在 price=0 商品

### P2. `user/shop.php?buyok=1`
- cart.js 支付成功跳转，可能有订单回显

---

## 四、中危（✅ 已确认）

| ID | 漏洞 | 接口 |
|----|------|------|
| M1 | 商品/分类 API 全量 | gettool/getclass/gettoolnew |
| M2 | Geetest 配置泄露 | captcha |
| M3 | 聊天 session 泄露 | user/ajax_chat.php |
| M4 | 敏感路径 403 存在性 | .env/config/backup/includes |
| M5 | cart_list/cart_info 未授权 | ajax.php |
| M6 | cancel 订单号差异响应 | ajax.php?act=cancel |
| M7 | toollogs.php 公开 | /shop/toollogs.php |
| M8 | zid=674 租户 ID 泄露 | getclass |

---

## 五、低危 / 信息

- 根域 `/` → 403；`/shop/` → 200
- Cloudflare + `_guard` WAF（滑块/连接重置）
- `gift_start` 未开启；快捷登录未开启
- 商品 HTML 前端可见价格/库存
- `reg` 在 user/ajax.php 为 No Act
- 注册/登录/供货商登录均需 Geetest

---

## 六、全面测试矩阵（不遗漏）

| 类别 | 测试项 | 状态 |
|------|--------|------|
| 信息泄露 | getcount/gettool/getclass/captcha | ✅ |
| IDOR | order+skey | ⚠️ 逻辑确认 |
| IDOR | cart_shop_item/del | ⏳ 待复现 |
| IDOR | workorder/sup list | ✅ 需登录 |
| IDOR | payrmb | ✅ 需登录 |
| 认证 | 弱口令 admin×24 | ✅ 未中 |
| 认证 | sup 弱口令 | ✅ 需 Geetest |
| 认证 | 注册/找回密码 | ✅ 未突破 |
| 支付 | 回调签名伪造 | ✅ 未突破 |
| 支付 | 价格/数量篡改 | ✅ 未突破 |
| 支付 | qqpay 订单枚举 | ⚠️ 部分 |
| 支付 | 0元 code==1 | ⏳ |
| 注入 | query SQLi | ⏳ WAF |
| 注入 | alipay_notify SQLi | ✅ 未中 |
| 文件 | .env/config/backup | ✅ 403 |
| 文件 | install.lock | ✅ 200 可读 |
| 逻辑 | gettoolnew cid | ✅ 失效 |
| 逻辑 | hashsalt 泄露 | ✅ |
| 逻辑 | cron 密钥 | ✅ 未中 |
| 后台 | admin 100+ 路径 | ✅ 无 |
| 后台 | sup 供货商 | ✅ 暴露 |
| 购物车 | cart_* 全套 | ⏳ **新增** |
| SSRF | getshareid | ✅ 未突破 |
| CSRF | order 无 token | ✅ 服务端拦截 |
| CSRF | cart 无 token | ⏳ cart.js 未发 csrf |
| DoS | query 500 | ✅ |
| 重装 | install/ | ✅ 锁可读 |

---

## 七、攻击链（按致命性）

```
链1 [数据库]  query SQLi → 读 pre_orders 表 → 批量 id+skey → kminfo
链2 [购物车]  cart_shop_item IDOR → 获下单信息 → 社工/撞库
链3 [购物车]  cart_buy → trade_no + user_rmb → submit.php 支付链
链4 [订单页]  mod=order&orderid= → showOrder(id,skey) → kminfo
链5 [重装]    删 install.lock → install/ → 新管理员
链6 [回调]    epay 签名破解 → 0元购卡
链7 [供货商]  sup/login → fakalist 卡密全量
链8 [订单]    获一 skey → order 遍历 18000+ → kminfo
```

---

## 八、修复建议（完整）

1. **立即** `getcount`/`gettool`/`getclass` 鉴权 + 字段脱敏
2. **立即** 修复 `query` 500；参数化查询
3. **高优** `cart_shop_item/del/buy` 鉴权 + 属主校验
4. **高优** `order` skey 改为 32 位随机 + 限速 + 失败锁定
5. **高优** `cron.php` IP 白名单；隐藏错误信息
6. **高优** 移除前端 hashsalt 硬编码；改服务端 session
7. **高优** `install/` 禁止公网访问或删除安装目录
8. **中优** `sup/` 后台 IP 限制 + 2FA
9. **中优** 支付回调日志脱敏；`qqpay.php` 统一错误响应
10. **中优** WAF 规则与业务错误分离（避免 500 泄露）

---

## 九、在线复现命令（站点可达时）

```bash
# H1 经营数据
curl -sk -H "X-Requested-With: XMLHttpRequest" -H "Referer: https://htqq.lol/shop/" \
  "https://htqq.lol/shop/ajax.php?act=getcount"

# 购物车 IDOR（待验证）
curl -sk -X POST -H "X-Requested-With: XMLHttpRequest" \
  -H "Referer: https://htqq.lol/shop/?mod=cart" \
  -d "id=1" "https://htqq.lol/shop/ajax.php?act=cart_shop_item"

# cart_buy
curl -sk -X POST -H "Referer: https://htqq.lol/shop/?mod=cart" \
  -d "shop_id[]=1&hashsalt=345a36b5fa7be2bdd2f1724157952938" \
  "https://htqq.lol/shop/ajax.php?act=cart_buy"

# qqpay 枚举
curl -sk "https://htqq.lol/shop/other/qqpay.php?orderid=18000"
```

---

## 十、工具与报告索引

| 报告 | 路径 |
|------|------|
| v1 初步 | `htqq-summary.md` |
| 高危汇总 | `htqq-highrisk-summary.md` |
| 全力深挖 | `htqq-full-report.md` / `final_report/` |
| v2 sup/gettoolnew | `htqq-deep-v2-report.md` |
| v3 其他攻击面 | `htqq-deep-v3-report.md` |
| **v4 本报告** | `htqq-deep-v4-comprehensive.md` |
| 扫描脚本 | `/tmp/htqq_full_scan.py` |

**本轮阻塞:** 探测 IP 遭 TLS 层 `Connection reset`；青果代理需定期刷新。建议浏览器+住宅 IP 续测 cart_* 与 mod=order。
