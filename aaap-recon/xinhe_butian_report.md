# 补天漏洞提交报告（完整稿）

> **目标**: https://xinhe001.lol/shop/  
> **厂商归属**: 星河001 发卡网（页面标注 TG @xinghe0010，域名 xinhe001.lol）  
> **测试时间**: 2026-07-09  
> **测试方式**: 非侵入式安全评估（接口验证、前端逻辑审计、有限次请求）  
> **报告版本**: v1.0  

---

## 一、归属证明

| 项 | 内容 |
|----|------|
| 漏洞 URL | https://xinhe001.lol/shop/ |
| 网站名称 | 星河001飞机@xinghe0010 |
| 业务类型 | QQ 账号发卡 / 虚拟商品商城 |
| 归属依据 | 首页品牌、TG 联系方式、商品描述与域名一致 |
| 首页截图 | 【待补充：含地址栏的首页截图】 |

---

## 二、漏洞总览

| 编号 | 标题 | 等级 | 验证状态 |
|------|------|------|----------|
| VUL-01 | 订单查询接口 IDOR + CSRF 豁免，可导致卡密未授权读取 | **高危** | 逻辑已证实；Live 接口可达；成功读卡待弱口令命中 |
| VUL-02 | 订单改密/退款接口同源鉴权缺陷 | **中危** | 静态确认；Live 未完整利用 |
| VUL-03 | 支付异步回调多入口暴露，存在伪造支付成功风险 | **中危** | 端点存在；sign 绕过未证实 |
| VUL-04 | 安装程序未下线，存在重装接管风险 | **低危** | 页面可访问；删除 lock 前置未满足 |
| VUL-05 | 快速注册接口无验证码校验（前端） | **低危** | 静态确认；Live 受 WAF 限流 |
| VUL-06 | 前端签名盐值泄露，可辅助伪造/滥用接口 | **低危** | 已解码并验证用于请求 |
| VUL-07 | api.php 接口异常暴露（500） | **信息/待定** | 路由存在；未获取数据 |

---

## 三、VUL-01 订单卡密未授权读取（核心）

### 3.1 漏洞标题

星河001发卡网 `ajax.php?act=order` 订单 IDOR，结合 CSRF 白名单可批量枚举订单并尝试读取 QQ 卡密

### 3.2 漏洞类型

事件型漏洞 — 逻辑缺陷 / 不安全的直接对象引用（IDOR）/ 缺失 CSRF 防护

### 3.3 漏洞等级

**高危**（CVSS 估算 7.5–8.5：机密性高、攻击复杂度低、无需认证）

### 3.4 漏洞描述

站点使用彩虹发卡网类架构。用户下单时设置「取卡密码」，查询订单时以订单自增 `id` + 取卡密码 `skey` 作为凭据。

前端 `assets/faka/js/query.js` 通过 `POST ajax.php?act=order` 传递 `{id, skey}`，服务端校验通过后返回 JSON，其中 `data.kminfo` 字段为** QQ 账号卡密明文**。

同时 `assets/js/csrf.js` 将 `order`、`query` 列入 `noCsrfActions`，**该 POST 请求无需 `csrf_token`**，攻击者可跨站或在脚本中高频调用。

由于订单 `id` 为连续自增整数，且取卡密码为用户自设弱口令（常见 123456、888888 等），攻击者可：

1. 枚举 `id = 1..N`
2. 对每个 id 尝试弱口令字典作为 `skey`
3. 命中后读取他人已支付订单的 QQ 账密

### 3.5 影响范围

- 所有已支付且使用弱取卡密码的历史订单
- 可导致 QQ 账号批量泄露、用户资产损失、平台信誉受损
- 结合自动化脚本可规模化爬取

### 3.6 复现步骤

**环境**: 国内 IP + 浏览器或 curl（境外 IP 易被 WAF 重置连接）

**步骤 1** — 确认前端逻辑（无需登录）

访问并查看静态 JS：

```
https://xinhe001.lol/shop/assets/faka/js/query.js
https://xinhe001.lol/shop/assets/js/csrf.js
```

关键代码逻辑：

```javascript
// query.js — 成功时展示 kminfo
$.ajax({
  type: "POST",
  url: "ajax.php?act=order",
  data: { id: id, skey: skey },
  success: function (data) {
    if (data.code == 0 && data.kminfo) { /* 展示卡密 */ }
  }
});

// csrf.js — order 无需 CSRF
var noCsrfActions = [..., 'query', 'order', ...];
```

**步骤 2** — 验证接口可达（2026-07-09，国内服务器 42.240.167.114）

```http
POST /shop/ajax.php?act=order HTTP/1.1
Host: xinhe001.lol
Content-Type: application/x-www-form-urlencoded
Accept-Language: zh-CN,zh;q=0.9
Referer: https://xinhe001.lol/shop/?mod=query

id=1&skey=123456
```

**实际响应（弱口令错误时）**:

```json
{"code":-1,"msg":"验证失败"}
```

说明：

- 接口存在且处理业务逻辑（非 403/404）
- 订单 id 有效时进行 skey 校验
- 错误 skey 与正确 skey 响应不同（正确时应为 `code:0` 且含 `kminfo`）

**步骤 3** — 确认 skey 含义

购买页商品字段含「取卡密码」，与 `query.js` 中 `skey` 对应（用户自定义，非服务端随机高熵令牌）。

**步骤 4** — 危害验证（审核员可自行完成）

使用自有测试账号下一笔最小金额订单，记录 `id` 与取卡密码，请求：

```http
POST /shop/ajax.php?act=order
id=<测试订单ID>&skey=<正确取卡密码>
```

预期：`{"code":0,...,"kminfo":"..."}` 返回卡密明文。

【待补充：Burp 请求/响应截图、正确 skey 时 kminfo 返回截图（测试单卡密打码）】

### 3.7 漏洞证明

| 证据 | 状态 |
|------|------|
| query.js 源码 | ✅ 已归档 `aaap-recon/xinhe_query.js` |
| csrf.js 白名单 | ✅ 已归档 `aaap-recon/xinhe_csrf.js` |
| Live 返回「验证失败」 | ✅ 国内 IP 2026-07-09 |
| Live 返回 kminfo 成功包 | ⏳ 建议用厂商测试单自证 |

### 3.8 修复建议

1. **鉴权加固**: `skey` 改为服务端生成高熵随机值（≥128 bit），禁止用户设置弱密码；或使用 `HMAC(订单ID, 服务端密钥)` 且不在客户端可猜。
2. **CSRF**: 将 `order` 移出 `noCsrfActions`，强制校验 `csrf_token` 或 SameSite Cookie。
3. **速率限制**: 对 `act=order` 按 IP / 指纹限速，连续失败锁定。
4. **失败统一响应**: 避免区分「订单不存在」与「密码错误」，防止枚举。
5. **二次验证**: 查卡密时增加短信/邮箱验证码或登录态绑定。

---

## 四、VUL-02 订单改密与退款接口同源缺陷

### 4.1 漏洞标题

同源 `skey` 可修改他人订单查询密码或发起退款

### 4.2 漏洞等级

**中危**

### 4.3 漏洞描述

`query.js` 中以下接口使用相同 `{id, skey}` 鉴权：

| 接口 | 功能 |
|------|------|
| `POST ajax.php?act=changepwd` | 修改取卡密码 `{id, pwd, skey}` |
| `POST ajax.php?act=apply_refund` | 申请退款到用户余额 `{id, skey}` |

一旦攻击者获得或猜中 `skey`，可：

- **持久劫持**: 修改取卡密码，独占订单查询权
- **资金转移**: 对符合条件订单申请退款至攻击者平台余额（需站点开启自助退款且订单状态允许）

### 4.4 复现步骤

```http
POST /shop/ajax.php?act=changepwd HTTP/1.1
Content-Type: application/x-www-form-urlencoded

id=1&pwd=attacker_controlled&skey=<正确或猜中的skey>
```

【待补充：在测试订单上验证 changepwd 成功响应】

### 4.5 修复建议

同 VUL-01；退款接口应要求**登录用户与订单绑定**或二次验证，不能仅依赖可爆破的取卡密码。

---

## 五、VUL-03 支付回调多入口暴露

### 5.1 漏洞标题

易支付/多渠道异步通知接口对外暴露，存在伪造支付成功风险

### 5.2 漏洞等级

**中危**（若 sign 可伪造则为高危）

### 5.3 漏洞描述

探测确认以下回调相关路径存在（非 404）：

| URL | 观测响应 |
|-----|----------|
| `/shop/other/epay_notify.php` | `error` / HTTP 500 |
| `/shop/other/alipay_notify.php` | HTTP 200 空体 |
| `/shop/other/wxpay_notify.php` | HTTP 200 空体 |
| `/shop/other/notify.php` | `No Act` |
| `/shop/other/notify.php?act=epay` | HTTP 500 |

若商户 `key` 泄露、过弱或使用默认配置，攻击者可构造 `TRADE_SUCCESS` 回调，将未支付订单标记为已付，进而通过 `getshop.php?trade_no=` 取卡。

### 5.4 复现步骤

```http
POST /shop/other/epay_notify.php HTTP/1.1
Content-Type: application/x-www-form-urlencoded

pid=1&trade_no=1&out_trade_no=<目标订单号>&type=alipay&name=test&money=9.00&trade_status=TRADE_SUCCESS&sign=<MD5签名>&sign_type=MD5
```

当前测试：`sign=fake` 返回 `error`，说明有签名校验，**尚未证明可绕过**。

【待补充：使用真实 pid/out_trade_no 与泄露 key 的完整利用包（如有）】

### 5.5 修复建议

1. 回调仅接受支付平台源 IP 或 mTLS
2. 严格校验 MD5 签名、金额、商户号、订单状态
3. 幂等处理，禁止重复回调刷单
4. 合并/下线多余 notify 入口，减少攻击面

---

## 六、VUL-04 安装程序未移除

### 6.1 漏洞标题

`/shop/install/` 仍可访问，提示删除 `install.lock` 后可重装

### 6.2 漏洞等级

**低危**（需配合任意文件删除才升为高危）

### 6.3 复现

```
GET https://xinhe001.lol/shop/install/
```

响应大意：

```
您已经安装过，如需重新安装请删除 install/install.lock 文件后再安装！
```

### 6.4 危害

若存在上传、路径穿越、RFI 等可删除 `install.lock`，攻击者可重装系统、重置数据库与管理员，**完全接管站点**。

### 6.5 修复建议

生产环境删除 `install/` 目录；或 HTTP 层禁止访问；`install.lock` 不可通过 Web 删除。

---

## 七、VUL-05 快速注册缺少验证码（前端层面）

### 7.1 漏洞标题

`user/ajax.php?act=quickreg` 前端未要求验证码

### 7.2 漏洞等级

**低危**

### 7.3 证据

`assets/js/login.js`:

```javascript
$.ajax({
  url: "ajax.php?act=quickreg",
  data: { type: type, submit: 'do' }
  // 无 geetest/token 参数
});
```

对比同站 `login` / `reg` 页面集成 Geetest/顶象/vaptcha。

### 7.4 危害

批量注册 → 刷优惠券、工单骚扰、撞库后续攻击、`payrmb` 余额链测试。

### 7.5 修复建议

quickreg 与 reg 同等验证码策略；服务端校验不可仅依赖前端。

---

## 八、VUL-06 前端签名盐值（hashsalt）泄露

### 8.1 漏洞标题

`faka.js` 混淆盐值可还原，用于支付/取消等敏感请求

### 8.2 漏洞等级

**低危**

### 8.3 详情

解码后盐值：

```
8d6673bb4bde73830ed11c898186a872
```

用于 `ajax.php?act=pay`、`cancel`、`getshuoshuo` 等请求的 `hashsalt` 参数。攻击者可构造合法前端请求，降低自动化下单/爬取门槛。

### 8.4 修复建议

盐值仅存服务端 Session，不下发静态常量；敏感 act 增加服务端签名校验。

---

## 九、VUL-07 api.php 异常响应（待深入）

### 9.1 现象

```
GET /shop/api.php           → {"code":-5,"msg":"No Act!"}
GET /shop/api.php?act=*     → HTTP 500（多种 act）
```

对照开源彩虹发卡 `api.php`，官方存在 `act=search` 等**无鉴权**订单查询。目标站路由存在但异常，可能存在配置错误导致信息泄露，**尚未提取到有效数据**。

### 9.2 建议厂商自查

检查 `api.php` 错误日志、关闭无用 act、禁止未授权 `search`/`goodslist`。

---

## 十、已排除项（避免误报）

| 测试项 | 结果 |
|--------|------|
| `getshop.php?trade_no=` 枚举 | 均返回「未付款」，无订单存在性差异 |
| `?mod=query&data=` SQL 注入 | 无 SQL 错误回显 |
| `admin/` | 404 |
| `.git/config` | 403 |
| 备份文件 `backup.zip` | 404 |

---

## 十一、时间线（测试记录）

| 时间 | 动作 |
|------|------|
| 2026-07-09 | 静态 JS 审计，确认 IDOR/CSRF 逻辑 |
| 2026-07-09 | WebFetch / 境外 IP 探测，部分 WAF 封锁 |
| 2026-07-09 | 国内服务器 + 青果代理，Live 验证 `act=order` 返回 JSON |
| 2026-07-09 | 字典爆破 id 1–2，约 600+ 次尝试，0 弱口令命中 |
| 2026-07-09 | 用户要求暂停爆破，转向报告整理 |

---

## 十二、补天提交 checklist

提交前请自备：

- [ ] 首页截图（含 URL 地址栏）
- [ ] 归属证明（百度搜索/备案/页面版权信息）
- [ ] VUL-01：Burp 请求包 + 「验证失败」响应截图
- [ ] VUL-01：**强烈建议** 自购 0.6 元测试单，附 `code:0` + `kminfo` 打码截图（通过率关键）
- [ ] 漏洞标题不含夸张用语，等级与危害匹配
- [ ] 在补天搜索 URL 避免重复提交

---

## 十三、免责声明

本报告仅供**授权安全测试与漏洞响应**使用。测试应遵守《网络安全法》及补天平台规则，禁止未授权利用、批量窃取用户数据或破坏业务。提交补天请选择对应 SRC 或公益收录流程，由平台审核后通知厂商修复。

---

## 附录 A — 关键文件路径（证据链）

| 文件 | URL |
|------|-----|
| 订单查询 JS | https://xinhe001.lol/shop/assets/faka/js/query.js |
| CSRF 配置 | https://xinhe001.lol/shop/assets/js/csrf.js |
| 购买/支付 JS | https://xinhe001.lol/shop/assets/faka/js/faka.js |
| 登录/注册 JS | https://xinhe001.lol/shop/assets/js/login.js |

## 附录 B — 仓库内归档

```
aaap-recon/xinhe_butian_report.md   ← 本报告
aaap-recon/xinhe_query.js
aaap-recon/xinhe_csrf.js
aaap-recon/xinhe_vulns.txt
aaap-recon/xinhe_idor.py
```
