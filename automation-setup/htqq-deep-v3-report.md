# htqq.lol 深挖 v3 — 其他致命漏洞（排除 sup 撞库 / 下单抓 skey）

- 时间: 2026-07-13
- 范围: 除供货商撞库、真实下单外的全部攻击面
- HK 路径: `/data/automation/results/htqq.lol/deep_v3_20260713/`

---

## 本轮测试方法

- ffuf / nuclei（HK）
- 200+ ajax act 枚举
- 100+ admin 路径字典（xiaoyewl/houtai888 等）
- mod= / index.php 参数 LFI 模糊
- user/ other/ install/ 全目录
- 价格篡改 / 购物车 / payrmb IDOR / SSRF
- order skey 绕过（空值/类型混淆/hashsalt）
- 支付回调签名绕过
- 敏感文件路径绕过

**限制:** 高频请求触发 `_guard` WAF（滑块验证 + 连接重置），需低速单请求测试。

---

## 新发现 — 高危/致命候选

### F1. `query` 接口全量 HTTP 500 崩溃

```bash
curl -sk -X POST -H "X-Requested-With: XMLHttpRequest" \
  -d "type=1&kw=18000" \
  "https://htqq.lol/shop/ajax.php?act=query"
# → HTTP 500, body 空
```

- 所有正常参数均 500，**订单查询功能完全不可用**
- 含 SQL 关键字时 WAF 拦截（200 + 拦截页），说明后端有漏洞可能但被 WAF 盖住
- **影响:** 可用作 DoS；若 WAF 绕过则可能存在 SQLi → 数据库全读

---

### F2. 支付后跳转 `?mod=order&orderid={trade_no}` — 潜在订单泄露面

**源码:** `assets/faka/js/faka.js` 第 851 行

```javascript
// pay 成功 code==0
window.location.href = './?mod=order&orderid=' + data.trade_no;
```

- 支付成功后浏览器跳转到订单页，URL 带 `trade_no`
- 若 `trade_no` 可预测或枚举 → 可能在该页面暴露 `skey` / `showOrder()` 调用
- **待验证:** WAF 恢复后测试 `?mod=order&orderid=18010` 等（本轮被限流中断）

---

### F3. `other/qqpay.php` 订单号探测

```
GET /shop/other/qqpay.php?orderid=18000
→ 该订单号不存在，请返回来源地重新发起请求！
```

- 支付接口对订单号有**差异化响应**（与 getshop 统一返回"未付款"不同）
- 可用于判断订单号是否存在 / 格式是否正确
- **攻击链:** 订单号枚举 → qqpay 跳转 → 支付状态探测

---

### F4. 0 元领取路径 — `pay` 返回 `code==1`

**源码:** `faka.js`

```javascript
} else if (data.code == 1) {
    alert('领取成功！');
    window.location.href = '?buyok=1';
}
```

- `code==1` 为**免费领取成功**分支（无需跳转支付）
- `code==2` 才触发 Geetest
- 若存在 price=0 的商品且后端未校验 → **0 元购卡**
- cid=8 为「网站余额-卡密余额充值」分类，需确认是否有 0 元 SKU

---

### F5. 安装锁可读 + 重装接管链（致命前提链）

```
GET /shop/install/install.lock → 200 "安装锁"
GET /shop/install/            → 200 "删除 install.lock 后可重装"
```

- 安装锁文件**内容可读**
- 安装向导对公网开放
- **致命条件:** 需先找到任意**文件删除/写入**漏洞（LFI、上传、路径穿越等）
- 重装 = 新建管理员账号 = **全站接管**

---

### F6. 框架核心源码路径存在（403）

| 路径 | 意义 |
|------|------|
| `includes/authcode.php` | 加密/授权核心 |
| `includes/common.php` | 全局初始化 |
| `includes/config.php` | 数据库配置 |

- 403 但确认存在，配合 LFI/备份泄露可直达数据库凭据
- `.env.bak` / `config.php.bak` / `ajax.php.bak` 等同理

---

### F7. 直接支付接口暴露

| 接口 | 响应 |
|------|------|
| `other/alipay.php` | 当前支付接口未开启 |
| `other/wxpay.php` | 当前支付接口未开启 |
| `other/qqpay.php` | 订单号探测（见 F3） |
| `other/submit.php` | 200 支付跳转页 |
| `other/epay_notify.php` | 200 error |
| `other/notify.php` | No Act |

- 支付链路完整暴露，签名绕过仍未成功
- epay 空 sign / 无 sign 均返回 `error`

---

### F8. `gettoolnew` cid 过滤完全失效（API 逻辑漏洞）

- 任意 `cid` 返回相同 9 个商品
- `gettool` 正常工作，49 SKU 全量可拉
- 不影响机密性但说明**后端校验缺失**，同类逻辑漏洞可能存在于 pay/cancel

---

## 已测试但未突破

| 项目 | 结果 |
|------|------|
| 主站 admin（100+ 字典） | 未发现，仅 sup/ |
| mod= LFI（passwd/php://filter） | WAF 滑块，无 LFI |
| pay 价格篡改（price/money/coupon） | 验证失败 |
| pay num=-1/0/99999 | 验证失败 |
| cart_add/buy | 验证失败 |
| order skey 空值/类型混淆/hashsalt | 验证失败 |
| payrmb IDOR | 需登录 |
| SSRF getshareid | 验证失败 |
| alipay_notify SQLi | 无延迟 |
| epay 空签名 | error |
| user reg/findpwd | reg act 不存在；findpwd 需验证码 |
| zid 多租户 | 无差异 |
| user qiandao | 需登录 |
| 弱口令 admin 等 | 需 Geetest |

---

## 致命漏洞优先级（排除 sup/skey 路径）

| 优先级 | 漏洞 | 致命性 | 下一步 |
|--------|------|--------|--------|
| P0 | query HTTP 500 → WAF 绕过 SQLi | 数据库全读 | 手工编码绕过 WAF |
| P0 | install 重装链 | 全站接管 | 找文件删除/上传点 |
| P1 | mod=order&orderid 泄露 skey | 卡密直读 | 低速枚举 trade_no |
| P1 | qqpay 订单号枚举 | 辅助 IDOR | 差异化响应批量测 |
| P1 | pay code==1 零元商品 | 免费购卡 | 筛 price=0 SKU |
| P2 | 支付回调签名破解 | 0 元购 | 逆向 epay 签名算法 |
| P2 | includes/config LFI | DB 凭据 | 备份/路径穿越 |

---

## 实时快照

```json
{
  "orders": "18015",
  "money": 5802210.4,
  "money1": 6760,
  "waf": "_guard slider",
  "admin_found": false,
  "sup_backend": true,
  "fatal_unexploited": ["query_sqli", "install_reinstall", "mod_order_leak", "zero_price_pay"]
}
```
