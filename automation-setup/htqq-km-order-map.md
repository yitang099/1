# htqq.lol 卡密 / 订单数据在哪里？

- 时间: 2026-07-13
- 目标: https://htqq.lol/shop/
- 当前订单量: **18052**（getcount）
- 扫描: CN 跳板 + `Accept-Language: zh-CN`

---

## 一、一句话结论

| 数据类型 | 存在位置 | 未授权能否拿到卡密 |
|----------|----------|-------------------|
| **卡密明文 (kminfo)** | `ajax.php?act=order` + **skey** | ❌ 需 skey |
| **全站卡密库** | `sup/fakalist.php`（供货商后台） | ❌ 需登录+Geetest |
| **彩虹 api.php IDOR** | `/shop/api.php/?act=search&id=` | ❌ 本目标 HTTP 000 封死 |
| **订单元数据** | `?mod=query&data=` / getcount | ⚠️ 仅统计/查询页，无卡密 |
| **付款状态** | `other/getshop.php?trade_no=` | ⚠️ 仅「未付款/已付」 |

**卡密不在 getcount/gettool 里，核心钥匙是每笔订单的 `skey`。**

---

## 二、卡密明文出口（最高价值）

### 2.1 `POST ajax.php?act=order` → `data.kminfo`

源码 `assets/faka/js/query.js` L62-63：

```javascript
} else if (data.kminfo) {
    item += '...以下是你的卡密信息...' + data.kminfo;
}
```

调用链：

```
showOrder(id, skey)
  → POST ajax.php?act=order  { id: 内部订单号, skey: 订单密钥 }
  → 成功时 JSON 含 kminfo（卡号/密码明文）
```

| 参数 | 说明 | 示例 |
|------|------|------|
| `id` | 内部自增订单 ID | `18052` |
| `skey` | 订单查询密钥（下单/付款后生成） | 未知，暴力未中 |
| `trade_no` | 对外交易号（≠ id） | `20260713163107742` |

实测：`id=18040~18055` + 20+ skey 模式 → 全部 `{"code":-1,"msg":"验证失败"}`

```bash
curl -sk -H "Referer: https://htqq.lol/shop/?mod=query" \
  -d "id=18052&skey=TEST" \
  "https://htqq.lol/shop/ajax.php?act=order"
```

---

## 三、订单查询面（拿 skey 的入口）

### 3.1 页面查询 — `GET ?mod=query&data=`

**正确参数是 `data`，不是 `kw`。**

```html
<form action="?" method="get">
  <input type="hidden" name="mod" value="query"/>
  <input type="text" name="data" placeholder="订单号或联系方式"/>
</form>
```

| 查询值 | 结果 |
|--------|------|
| 未付款 trade_no | `没有查询到数据` |
| 内部 id 18052 | `没有查询到数据` |
| 无 Cookie 最近订单 | `您暂时没有任何订单哦！` |
| 同会话下单未付款 | 最近订单表仍 **empty** |

有结果时，表格「操作」列会调 `showOrder(id,'skey')`，**skey 出现在 HTML/JS 里** — 这是除暴力外最可能的 skey 来源。

### 3.2 Ajax 查询 — `POST ajax.php?act=query`

```javascript
// 常见格式（彩虹系）
{ type: 1, qq: "订单号或trade_no" }   // type=1 订单号
{ type: 2, qq: "邮箱或手机" }          // type=2 联系方式
```

成功时返回可触发 `showOrder` 的数据；本目标经 CN 代理时常空响应/403，偶发 `请输入正确的订单号`。

### 3.3 订单支付页 — `GET ?mod=order&orderid={trade_no}`

- 未付款：支付 UI，**无 kminfo**
- 页面含「卡密」字样是指**付款后跳转卡密页**，不是直接泄露
- 付款成功后 `faka.js` 跳转 `?mod=order&orderid=` + `data.trade_no`，可能内嵌 skey（需真实付款验证）

---

## 四、卡密库存 / 订单后台（需登录）

| 路径 | 数据 | 未授权 |
|------|------|--------|
| `sup/fakalist.php` | **供货商卡密库存**（未售出卡密池） | JS 跳 login |
| `sup/list.php` | 供货商订单列表 | JS 跳 login |
| `sup/ajax.php?act=login` | 登录 API | 需 Geetest |
| `user/login.php` | 用户会员订单 | 需账号 |

供货商登录后是**全站卡密库**最可能所在，但 Geetest + 密码阻断。

---

## 五、仅元数据 / 非卡密接口

| 接口 | 返回内容 | 含卡密？ |
|------|----------|---------|
| `ajax.php?act=getcount` | orders=18052, money=581万, site=674 | ❌ |
| `ajax.php?act=gettool&cid=` | 49 个 SKU 名称/价格 | ❌ |
| `ajax.php?act=getleftcount&tid=` | 库存数字（与 HTML 不一致） | ❌ |
| `other/getshop.php?trade_no=` | `{"code":-1,"msg":"未付款"}` | ❌ |
| `toollogs.php` | 商品上架日志 | ❌ |
| 首页 `/shop/` HTML | tid/价格/库存 | ❌ 无卡密 |

---

## 六、已封死 / 不适用

| 攻击面 | 状态 |
|--------|------|
| `api.php/?act=search&id=` 彩虹 P0 IDOR | HTTP 000（直连/代理/源 IP 156.238.239.16 均失败） |
| `rev_api.php` / `km.php` / `export.php` | 404 |
| `includes/ajax.php` | 403 |
| 支付回调伪造发卡 | 签名失败 |
| query 数字订单号 | HTTP 500 DoS（H10），非数据泄露 |

---

## 七、数据模型（推断）

```
pre_order 表
  ├─ id          内部号 (18052)
  ├─ trade_no    交易号 (20260713163107742)
  ├─ skey        查询密钥 ← 拿卡密必须
  ├─ inputvalue  取卡密码（用户填的联系方式/密码）
  ├─ tid         商品 ID
  └─ status      0=未付 1=已付 ...

pre_km / faka_km 表（卡密池）
  └─ 通过 sup/fakalist 管理，付款后写入 order.kminfo
```

---

## 八、拿卡密的可行路径（按优先级）

```
P0  真实付款一笔 → 抓 order 页 / query 页里的 showOrder(id,skey) → POST act=order → kminfo
P1  知道他人 trade_no + 取卡密码(inputvalue) → ?mod=query&data= 联系方式查询
P2  sup 后台突破（Geetest+弱口令）→ fakalist 全库
P3  skey 算法逆向 / 大规模暴力（18000+ 订单，已测常见模式未中）
P4  api.php 网关绕过（当前全灭）
```

---

## 九、本次实测凭证

| 项 | 值 |
|----|-----|
| 测试 trade_no | `20260713163107742`（未付款） |
| query&data= | `没有查询到数据` |
| getshop | `未付款` |
| act=order id=18052 | `验证失败` |

脚本: `automation-setup/htqq-km-order-scan.py`
