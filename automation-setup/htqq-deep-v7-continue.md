# htqq.lol 深挖 v7 — 续测（api.php / 分站 / 新端点）

- 时间: 2026-07-13
- 目标: https://htqq.lol/shop/
- 状态: 自动化 IP 遭 `_guard` 滑块 + TLS reset，部分结论来自冷却窗口内复测

---

## 结论：**无新高危可利用漏洞**

在 v6 的 H1–H10 基础上，本轮按彩虹 Playbook **最高 ROI** 路径继续打，仍未突破卡密全量泄露链。

| 攻击面 | 本轮结果 |
|--------|----------|
| **api.php IDOR（斜杠绕过）** | ❌ 全路径 Connection reset / HTTP 000，**不可利用**（与 qq8.one 不同） |
| order skey 扩展暴力 | ❌ 验证失败 / 连接重置 |
| user/sup ajax 新 act | ❌ 无新存活接口 |
| 分站 zid / 子域 | ❌ 无效 |
| orders_dump / rev_api | ❌ 不存在 |
| 零元 SKU | ⏳ WAF 中断，历史扫描无 price=0 |
| nuclei exposure | ❌ 无新发现 |

---

## 1. api.php IDOR（Playbook P0）— 确认不适用

彩虹 Playbook 核心：`/api.php/?act=search&id=` 斜杠绕过 WAF 拉全站卡密。

**htqq.lol 实测（直连 + 青果代理 + HK 跳板）：**

```bash
# 全部失败 — TLS reset 或空响应
/shop/api.php?act=search&id=1
/shop/api.php/?act=search&id=1
/shop/api.php/?act=search&id=18044
/shop/api.php/?act=siteinfo|classlist|goodslist
/shop/API.php/?act=search&id=1
```

→ 该站 **api.php 整文件被 WAF/网关拦截**，非 qq8.one 型「斜杠绕过即可拖库」。
→ 更新彩虹库条目 M7：**api.php IDOR 不适用（已封死）**。

---

## 2. user/ajax.php 深枚举

有效 CSRF + Session 下存活 act：

| act | 响应 |
|-----|------|
| login | 用户名或密码不能为空 |
| qiandao | 未登录 |
| recharge | 空（WAF） |
| connect | 未开启 QQ 快捷登录 |
| 其他 20+ act | No Act |

**无** `orders` / `orderlist` / `getorder` / `kmlist` 等隐藏接口。

---

## 3. sup/ajax.php + CSRF

| act | 响应 |
|-----|------|
| login | 请先完成验证（Geetest） |
| export/upload/editkm/recharge/record/workorder | No Act |
| list/fakalist（无 CSRF） | No Act / 空 |

供货商卡密接口 **不可未授权访问**。

---

## 4. order skey 续测

- 空值 / `null` / `0` / `undefined` → `验证失败` 或 WAF 空响应
- md5/sha1/hashsalt 组合（id 18000–18044）→ 无命中
- `changepwd` → `站点未开启修改订单密码`
- `apply_refund` → 需有效 skey（未开启自助退款）

---

## 5. 其他探测

| 项目 | 结果 |
|------|------|
| `getleftcount&tid=6` | `{"code":0,"count":"1"}` — 库存信息（低危） |
| `gift_start` | 网站未开启抽奖 |
| `SharePoster` | No Act |
| `share_invitegift_link` | 空/WAF |
| `gettool` SQLi（cid） | WAF 滑块拦截 |
| 子域 www/api/fk/admin 等 | DNS 不存在 |
| `getcount&zid=N` | 无横向分站效果 |
| `rev_api.php` / `orders_dump` | 不存在 |

---

## 6. WAF 影响

本轮后半段 `getcount` 亦返回：

```html
<script src="/_guard/html.js?js=slider_html"></script>
```

→ 自动化扫描频率过高触发封禁；**浏览器 + 住宅 IP** 仍是续测 cart IDOR / 真实下单抓 skey 的前提。

---

## 仍可用的已知高危（v6 清单）

| ID | 漏洞 | 可利用 |
|----|------|--------|
| H1 | getcount 经营泄露 | ✅ |
| H9 | cart_empty 未授权清空 | ✅ |
| H10 | query 数字单号 HTTP 500 | ✅ |
| H2 | order 卡密 IDOR | ⚠️ 需 skey |
| H3–H8 | hashsalt/回调/cron/install/sup/gettoolnew | ⚠️ 辅助/待突破 |

---

## 下一步（唯一剩余致命路径）

1. **浏览器真实支付** tid=6（库存仅剩 1）→ 抓 `trade_no` + `skey`
2. **住宅 IP** 复测 `mod=order&orderid=` 与 `api.php`（排除机房 IP 封禁误判）
3. **低频手工** query 500 根因 + WAF 绕过 SQLi
