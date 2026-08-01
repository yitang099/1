# xinhe001.lol/shop 深挖报告

> **更新：** 2026-08-02（青果海外隧道 + Session 突破）  
> **状态：** **getcount/首页已打通**（海外隧道 + 先访问首页拿 cookie）；**仍无卡密泄露**；`api.php` 仍被 WAF 空响应  
> **栈：** 彩虹发卡 `/shop/`（星河001）

---

## 1. 站点概况（末次成功复探 2026-08-01）

| 项 | 值 |
|----|-----|
| URL | https://xinhe001.lol/shop/ |
| 源站 IP | `103.43.11.95` / `45.158.21.213`（同 hm0880/jinku） |
| 总订单 | **5718**（+1） |
| 成交额 | **约 101.73 万** |
| 加固 | `csrf.js` + `csrf_token` |

---

## 2. 漏洞面复测结果

| 向量 | 结果 |
|------|------|
| `?mod=query&data=` 子串（qd93 类） | ❌ 「没有查询到数据」，0 `showOrder` |
| `api.php?act=search&id=` | ⚠️ 一测即 **连接重置**（WAF） |
| `toollogs.php` | ❌ 普通 HTML，无订单 |
| `ajax.php?act=getcount` | ✅ **需先访问首页拿 `PHPSESSID`+`mysid`**；裸请求 403 |
| 查单密码 `ajax.php?act=query` | ❌ 常见密码无命中 |
| `cron.php` | ❌ 「监控密钥不正确」 |

---

## 3. 2026-08-02 多向量深挖（第二轮）

### 已跑向量（`xinhe001_multi_deep.py` 设计）

| # | 向量 | 结果 |
|---|------|------|
| 1 | 表面：`toollogs` / `mod=query` / `mod=so` / 分页 | 待测（无可用出口） |
| 2 | 子串 `data=1/138/888` | 历史：❌ |
| 3 | 查单密码 GET + `ajax.php?act=query`（60 组） | 历史：❌ |
| 4 | `api.php` IDOR：`search/order/query/kmmail` ×40 单 | WAF 重置（未跑完） |
| 5 | `ajax.php?act=order` skey 碰撞 ×30 单 | 未测（无连接） |
| 6 | 买单链 `ajax.php?act=pay` + `epay_notify` 伪造 | 未测（无连接） |
| 7 | `cron.php` 密钥字典 | 历史：❌ |
| 8 | `user/ajax_chat.php` 等旁路 | 未测 |
| 9 | `mod=faka` 提卡（若有 pair） | 无 pair |

### 出口扫描统计

| 方式 | 轮数 | 可连首页 | 卡密泄露 |
|------|------|----------|----------|
| 青果代理 + requests（multi_deep） | **30** | **0** | ❌ |
| 青果代理 + curl（curl_scan） | **50** | **0** | ❌ |
| 青果代理 + requests（proxy_deep） | **10** | **0** | ❌ |
| 云机 / HK 直连 | — | 封/超时 | ❌ |
| CN 跳板 | — | 超时 | ❌ |
| 源站 IP `103.43.11.95` | — | 首页 OK 后 ajax **403** | ❌ |

常见失败：`SSL EOF`、`risk-control.yunkv.com`（省级风控）、`Connection reset`

产物：
- `/data/automation/results/xinhe001.lol/deep_20260801/multi_deep.json`
- `/data/automation/results/xinhe001.lol/deep_20260801/curl_scan.json`
- `/data/automation/results/xinhe001.lol/deep_20260801/proxy_deep.json`

**CARD_LEAK = false（全轮次）**

---

## 4. 2026-08-01 续挖（第一轮）

| 出口 | 结果 |
|------|------|
| 云机直连 | ❌ IP 已封（Connection reset） |
| HK 主力直连 | ❌ 超时 / getcount 403 |
| CN 跳板 124.248.67.170 | ❌ 连接超时 |
| 源站 IP + Host 头 | 首页 OK，**ajax 403**，api 随后被封 |
| HK 青果代理 ×10 轮 | ❌ 全轮 SSL/EOF 失败 |
| 广东代理 HTTP | ❌ 跳转 `risk-control.yunkv.com`（省级风控） |

产物：`/data/automation/results/xinhe001.lol/deep_20260801/proxy_deep.json` → **CARD_LEAK=false**

---

## 4. 2026-08-02 青果全球隧道 + Session 突破

| 方法 | 结果 |
|------|------|
| 海外隧道裸调 `getcount` | ❌ `code:403` |
| **先 GET 首页 → 带 cookie 调 API** | ✅ `getcount code:0`，5718 单 |
| 青果 JP 粘性 `-A-JP-T-300-S-*` | ✅ 首页 79KB，session 稳定 |
| HK 直连 + session | ❌ getcount 仍 403（HK IP 在黑名单） |
| 源站 IP + Host | ❌ ajax 403（无 session 亦无效） |
| `mod=query&data=*` / 查单密码 30 组 | ❌ 0 `showOrder` |
| `api.php?act=search&id=` | ❌ 空响应 / 连接重置（WAF） |
| `ajax.php?act=query` POST | 空响应（疑似同层拦截） |

隧道配置：`overseas-us.tunnel.qg.net:16538`，AuthKey `15E27ADA`（业务 `iaahtjho`）

产物：`/data/automation/results/xinhe001.lol/qg_overseas_20260801/tunnel_deep.json`

**关键结论：** 之前判「API 全 403」是**未带 session**；真正挡卡密的是 **query 漏洞已修 + api WAF**，不是隧道没买对。

---

## 5. 结论

- **不是当前可利用目标**：qd93 式 query 子串已修；api IDOR 被 WAF 空响应，未能验证
- 与 qd93 同源 IP 段，属**加固版彩虹**（CSRF + session 门禁）
- **可行续挖路径**：仅「青果海外隧道 + 首页 session」；极低速单线程 `api.php`（≥5s/次）；或住宅池隧道；或 Vultr 东京直连对比
- **不可行**：HK/上海直连、国内青果池、无 session 裸请求

---

## 6. 脚本

| 文件 | 用途 |
|------|------|
| `xinhe001_qg_tunnel.py` | **青果海外隧道 + session**（推荐） |
| `xinhe001_probe.py` | 轻量面探测 |
| `xinhe001_deep.py` | 全链深挖（勿高频） |
| `xinhe001_slow_deep.py` | 低速面 + api |
| `xinhe001_api_scan.py` | api IDOR 专项 |
| `xinhe001_proxy_deep.py` | HK 国内青果池（xinhe 不适用） |
