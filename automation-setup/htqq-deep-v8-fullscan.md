# htqq.lol 深挖 v8 — 全力扫描（隐藏高危专项）

- 时间: 2026-07-13
- 目标: https://htqq.lol/shop/
- HK 扫描: `/data/automation/results/htqq.lol/deep_v8_*` / `deep_v8b_*`
- 脚本: `automation-setup/htqq-v8-fullscan.py`

---

## 执行摘要

**全力扫描后：未发现新的隐藏高危可利用漏洞。**

| 扫描项 | 工具/范围 | 结果 |
|--------|-----------|------|
| 隐藏路径 | 120+ 手工 + ffuf 200~500 条 | 仅已知面（install/config/includes 403） |
| ajax act 枚举 | 80+ act GET/POST | 无新存活 act（均 No Act 或已知） |
| api.php IDOR | 斜杠绕过 × 直连 × 青果 × 源 IP | **全灭 HTTP 000** |
| nuclei critical/high | HK 直连 + 代理 | **0 条** |
| ffuf common-api 300 | HK 直连 | install 301、config 403、index.php 200 |
| 子域 CT | crt.sh | 仅 `*.htqq.lol` / `htqq.lol` |
| probe_rainbow_faka | 青果代理 | 代理间歇失败；api.php 不可达 |
| ThinkPHP 路由 | `index.php?s=/admin` | 同页壳，非后台 |
| JSONP/回调 | `callback=alert(1)` | WAF 拦截 |
| 数组注入 | order/login | 无绕过 |
| 源站 IP 直连 | 156.238.239.16 等 | getcount 正常，**api.php 仍 000** |

---

## 一、HK 自动化全扫（v8）

```
/data/automation/results/htqq.lol/deep_v8_20260713_134549/
```

- 青果代理完整跑完 10 个阶段（路径/ajax/api/user/notify/LFI/cron/order/ffuf/nuclei）
- **findings.json = []**（0 新漏洞）
- 代理环境下大量请求空响应，但直连复测印证结论

### ffuf 命中（v8b 直连）

| 路径 | 状态 | 说明 |
|------|------|------|
| `install` | 301 | 已知重装链 |
| `config` | 403 | 存在性泄露 |
| `index.php` | 200 | 正常入口 |

---

## 二、api.php — 彻底封死（再次确认）

Playbook 最高优先级攻击面对 **htqq.lol 无效**：

```
api.php?act=search&id=1          → 000
api.php/?act=search&id=1         → 000
api.php/?act=search&id=18049     → 000
api.php/?act=siteinfo|classlist  → 000
--resolve 源站IP + Host 头       → api 仍 000，getcount 正常
```

结论：**非斜杠绕过问题，而是 api.php 整文件被网关/WAF 丢弃连接。**

---

## 三、隐藏路径探测（手工 + 字典）

### 不存在 / No Act

`rev_api.php` `orders_dump` `export` `backup` `debug` `phpinfo`  
`user/shop.php` `user/export.php` `user/orders.php`  
`sup/export.php` `sup/download.php`  
`other/return.php` `other/refund.php` `other/epay/epay_notify.php`  
`plugins/` `addons/` `extend/` `thinkphp` `public/index.php`

### 403 存在性（已知，非突破）

`includes/*` `config` `.env` `install/database.sql` `data/backup.sql` `runtime/log`

### 可达但无新利用

| 路径 | 结果 |
|------|------|
| `toollogs.php?action=list&page=1` | 200 仅页面框架，无数据 API |
| `cron.php?do=sitemap` | `监控密钥不正确` |
| `index.php?s=/admin` | 200 同商城壳（动态 cookie 导致 hash 不同，非后台） |
| `ajax.php?act=getcount&zid/uid=` | 与默认相同，无横向分站 |

---

## 四、非常规向量

| 向量 | 结果 |
|------|------|
| JSONP `callback=` | WAF 拦截页 |
| HTTP PUT/DELETE | 空响应 |
| HTTP PATCH getcount | 同 GET 数据（非漏洞） |
| Host: 127.0.0.1 | 正常 JSON |
| pay 价格篡改 `price=0` | CSRF 失败（需有效 token） |
| order 数组注入 `id[]` | 空/WAF |
| CORS Origin: evil.com | 无 ACAO 头 |

---

## 五、实时数据（扫描时）

```json
{
  "orders": "18049",
  "money": 5811621.4,
  "site": "674"
}
```

---

## 六、结论与攻击面收敛

经过 **v1–v8 累计** + 本轮全力扫描（ffuf/nuclei/120+路径/80+act/源IP/api全变种），隐藏高危面已收敛：

### 可直接利用（无新增）

- H1 getcount 经营泄露
- H9 cart_empty 未授权清空
- H10 query 数字单号 DoS

### 理论高危但当前不可利用

- H2 order 卡密 IDOR（需 skey）
- api.php 全站拖库（**本目标不适用**）
- cart_shop_item IDOR（需 shop_id + 库存为 0）
- install 重装（需删锁能力）
- SQLi（WAF + query 500 未出数据）

### 扫描覆盖度

```
路径字典:  faka_admin + common-api + api-paths + 手工 120+
ajax act:  80+ (含 faka-tokens 提取)
工具:      ffuf ×2, nuclei ×2, probe_rainbow, 青果+HK+直连
子域:      crt.sh 无新子域
```

**结论：自动化层面已无未测隐藏面；继续突破只能依赖浏览器真实交互（下单抓 skey）或 0day/源码审计。**

---

## 七、复现命令

```bash
# HK 全扫
source /data/config/proxy.env
python3 /data/automation/htqq-v8-fullscan.py

# ffuf 直连
ffuf -u "https://htqq.lol/shop/FUZZ" -w /data/wordlists/api-paths.txt \
  -mc 200,301,302,403,500 -H "Referer: https://htqq.lol/shop/"

# api.php 验证
curl -sk "https://htqq.lol/shop/api.php/?act=search&id=1" -H "Referer: https://htqq.lol/shop/"
```
