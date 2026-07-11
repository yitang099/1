# tianyu9080.top/shop 深度安全测试报告

**目标**: https://tianyu9080.top/shop/  
**测试时间**: 2026-07-11 ~ 2026-07-12  
**站点类型**: PHP 自动发卡网（彩虹/同类系统 + `assets/faka` 定制）  
**说明**: 非破坏性测试，未进行暴力破解、真实支付与拖库

---

## 一、执行摘要

本轮深挖在初版基础上完成 **全站 120 个商品** 的 API 拉取、库存估值、支付回调探测、订单接口边界测试与隐藏路径扫描。确认 **3 个中危 + 2 低危 + 若干信息级** 问题；订单号枚举经复核为 **误报**（`getshop.php` 对绝大多数输入均返回相同响应）。

| 等级 | 数量 | 关键发现 |
|------|------|----------|
| 中危 | 3 | 经营数据泄露、商品/库存 API 未授权、全量商品目录可爬取 |
| 低危 | 2 | 客服未授权发消息、`install/` 残留 |
| 信息 | 4 | 供货商后台暴露、cron 入口、USDT 地址、支付回调路径 |

---

## 二、站点架构

| 组件 | 信息 |
|------|------|
| 技术 | PHP + Session (`PHPSESSID`, `mysid`) |
| IP | 103.43.11.95 |
| CDN/WAF | 宝塔 CDN + WAF（搜索 SQLi 拦截） |
| 前台 | `/shop/` 商品/下单/查询 |
| 会员 | `/shop/user/` |
| 供货商后台 | `/shop/sup/login.php` |
| 支付 | `ajax.php?act=pay` → `other/submit.php` |
| 回调 | `other/epay_notify.php`（签名校验存在） |
| 定时任务 | `cron.php`（需密钥） |
| 验证码 | Geetest / Vaptcha / 图形验证码 |

**鉴权边界（重要）**:
- 无 `Referer: https://tianyu9080.top/shop/` → 统一 `403`
- 有 Referer 但 **无 Session Cookie** → `getcount` / `gettool` / `getclass` 仍可访问
- 订单详情 `ajax.php?act=order` → 需正确 `id` + `skey`

---

## 三、已确认漏洞

### 1. 经营数据未授权泄露（中危）

**接口**: `GET /shop/ajax.php?act=getcount`  
**条件**: 仅需 `Referer` 头，**无需 Session、无需登录**

**PoC**:
```bash
curl -sk -4 -H "Host: tianyu9080.top" \
  -H "Referer: https://tianyu9080.top/shop/" \
  -H "X-Requested-With: XMLHttpRequest" \
  "https://103.43.11.95/shop/ajax.php?act=getcount"
```

**实测响应**:
```json
{
  "code": 0,
  "yxts": 254,
  "orders": "37416",
  "orders1": "37416",
  "orders2": "25",
  "money": 7090298.92,
  "money1": 4429.99,
  "site": "502",
  "gift": null,
  "cart_count": "0"
}
```

**泄露内容**: 累计订单 37,416 笔、交易额约 709 万元、今日 25 单、运营 254 天。

**修复**: 限制为管理员/供货商登录后可访问，或移除敏感字段。

---

### 2. 商品目录与库存全量 API 泄露（中危）

**接口**:
| 接口 | 说明 |
|------|------|
| `ajax.php?act=getclass` | 19 个分类 |
| `ajax.php?act=gettool&cid=X` | 按分类返回商品详情 |
| `ajax.php?act=gettoolnew` | 精选/最新商品（9 条） |

**条件**: 仅需 Referer，无需登录。

**泄露字段**: `tid, cid, name, price, stock, sales, isfaka, inputs, desc, min, max, prices, goods_sid`

**实测规模**（`deep/all_products.json`）:

| 指标 | 数值 |
|------|------|
| 商品总数 | **120** |
| 有库存字段的商品 | 108 |
| 库存总量 | **7,601** 件 |
| 库存估值（stock×price） | **约 57.1 万元** |
| 自动发卡商品（isfaka=1） | 9 |

**库存 TOP5**:
| tid | 库存 | 单价 | 商品 |
|-----|------|------|------|
| 1524 | 2201 | 70 | 全新满月自养月亮扫PC |
| 998 | 965 | 15 | 美卡真棒邮箱 1-4年 |
| 232 | 720 | 18 | 美卡真棒邮箱 5-10年 |
| 231 | 510 | 14 | 美卡真棒混合等级 |
| 646 | 224 | 165 | 原始卡回流扫码单太号 |

**危害**: 竞争对手可实时监控定价、库存、热销商品；结合 `getcount` 可完整还原经营画像。

**修复**: 商品列表接口增加登录或 Token 鉴权；库存字段对前台脱敏（仅显示「有货/缺货」）。

---

### 3. 在线客服未授权发消息（低危）

**接口**:
- `GET /shop/user/ajax_chat.php?act=get` → 返回 `session_id`
- `POST /shop/user/ajax_chat.php?act=send` → `{"code":0,"msg":"发送成功"}`

**条件**: 无需登录；伪造 `session_id` 亦可发送。

**危害**: 客服消息轰炸、垃圾广告。

**修复**: 验证码 + 频率限制 + Session 绑定。

---

### 4. 安装入口未关闭（低危）

**路径**: `/shop/install/`（200）

> 您已经安装过，如需重新安装请删除 install/install.lock 文件后再安装！

**危害**: 配合文件删除漏洞可重装接管。

**修复**: 删除整个 `install/` 目录。

---

### 5. 供货商后台路径暴露（信息）

**路径**: `/shop/sup/login.php`（200，标题「供货商登录」）

- 登录需 Geetest 验证码（`{"code":2,"msg":"请先完成验证"}`）
- `sup/ajax.php` 未授权 act 均返回 `No Act` 或 `403`

**修复**: 随机路径 + 登录限速 + IP 白名单。

---

## 四、复核后排除的误报

### `other/getshop.php?trade_no=` 订单枚举 — 不成立

初测认为多个 `trade_no` 返回 `{"code":-1,"msg":"未付款"}` 可判断订单存在。复核发现：

| trade_no | 响应 |
|----------|------|
| 空、`0`、`1`、`99999999`、`ORDER_NOT_FOUND` | 均返回 `未付款` |
| `abc`、`37416abc` | 空响应（非标准 JSON） |

**结论**: 该接口对绝大多数输入返回相同 JSON，**无法区分订单是否存在**，不构成可靠枚举漏洞。

### `ajax.php?act=findorder` / `orderinfo` — 未启用

带 CSRF 测试返回 `{"code":-4,"msg":"No Act"}`，接口在本站未开放。

---

## 五、已测试但未突破

| 测试项 | 结果 |
|--------|------|
| 订单详情 `ajax.php?act=order` | 需正确 `id` + `skey`，否则 `验证失败` |
| 支付跳转 `other/submit.php?orderid=` | 测试订单均显示「订单号不存在」 |
| 下单 `ajax.php?act=pay` | 需 CSRF + Geetest/Vaptcha |
| 支付回调 `other/epay_notify.php` | 伪造签名返回 `fail`/`error`，校验存在 |
| `ajax.php?act=getshuoshuo` | 需有效 `hashsalt`，否则 `验证失败` |
| `ajax.php?act=getrizhi` | `No Act`（未启用） |
| 订单查询 `?mod=query&data=` | 测试手机号/邮箱/订单号均无 `showOrder` 链接 |
| 搜索 SQLi `?mod=so&kw=` | WAF 拦截（「输入内容存在危险」） |
| `config.php` / `.env` / `.git` | 403 |
| 用户 `user/ajax.php?act=reg` | `No Act` |
| 供货商 `sup/ajax.php` 各 act | `No Act` 或需验证码 |

---

## 六、隐藏路径与回调探测

| 路径 | 状态 | 响应 |
|------|------|------|
| `cron.php` | 200 | `监控密钥不正确` |
| `other/epay_notify.php` | 200 | `error`（伪造回调被拒） |
| `other/notify.php` | 200 | `No Act` |
| `other/alipay_notify.php` | 200 | 空 |
| `other/usdt_notify.php` | 404 | — |
| `admin/login.php` | 404 | — |
| `install/` | 200 | 安装提示 |

**支付链路**:
```
ajax.php?act=pay → orderid
  → other/submit.php?type=alipay|wxpay|usdt&orderid=XXX
  → 第三方支付
  → other/epay_notify.php（签名校验）
```

---

## 七、其他信息暴露

| 信息 | 位置 |
|------|------|
| USDT 收款地址 | 首页公告 `TYGdQE9K4AtoQa41EGxxtUBnvM18kHTM97` |
| Telegram 客服 | `@t111y`、`@T008Ybot` |
| 微信/支付宝费率 | 首页公告 5% |
| CSRF Token | 页面 JS 变量（配合 Session 使用） |

---

## 八、风险评级汇总

| 优先级 | 漏洞 | 等级 |
|--------|------|------|
| 1 | `getcount` 泄露订单量/交易额（无需 Cookie） | **中危** |
| 2 | `gettool`/`getclass` 全量商品+库存 API | **中危** |
| 3 | 客服接口未授权发消息 | 低危 |
| 4 | `install/` 目录残留 | 低危 |
| 5 | `sup/` 后台路径暴露 | 信息 |
| 6 | `cron.php` 入口暴露 | 信息 |

---

## 九、加固建议

1. **立即**: `getcount` 仅后台可访问；前台去掉交易额/订单数
2. **立即**: `gettool` 库存字段脱敏或加鉴权
3. **立即**: 删除 `/shop/install/`
4. **短期**: 客服接口加验证码 + 频率限制
5. **短期**: 供货商后台改随机路径
6. **中期**: `cron.php` 改密钥 + IP 白名单
7. **中期**: 全站 API 统一鉴权（避免 Referer-only 绕过）

---

## 十、产出文件

```
/workspace/tianyu9080-recon/
├── security_report.md          # 本报告（深度版）
├── deep/
│   ├── all_products.json       # 120 个商品全量
│   ├── getclass.json           # 19 个分类
│   ├── gettool_cid*.json       # 按分类商品
│   ├── gettoolnew.json         # 精选商品
│   ├── inventory_summary.json  # 库存统计
│   ├── trade_no_enum.json      # 订单号探测（已复核为误报）
│   ├── probe_results.json      # 综合探测结果
│   ├── probe_log.txt           # 探测日志
│   ├── sup_login.html          # 供货商登录页
│   └── c.jar                   # 测试 Session
├── faka.js, query.js, login.js # 前端逻辑
└── *.html                      # 页面快照
```

---

## 十一、后续可深挖（需额外授权）

- [ ] 支付回调签名算法逆向（需合法测试环境）
- [ ] 供货商/用户弱口令（需明确授权范围）
- [ ] `install.lock` 删除后的重装链（需文件写入漏洞配合）
- [ ] 真实下单后 `skey` 泄露链路验证
