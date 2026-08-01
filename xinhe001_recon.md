# xinhe001.lol/shop 深挖报告

> **更新：** 2026-08-02  
> **状态：** 续挖完成一轮，**未发现卡密泄露**；多出口均被 WAF/风控拦截  
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
| `ajax.php?act=getcount` | ✅ 可用（未封 IP 时） |
| 查单密码 `ajax.php?act=query` | ❌ 常见密码无命中 |
| `cron.php` | ❌ 「监控密钥不正确」 |

---

## 3. 2026-08-02 续挖动作

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

## 4. 结论

- **不是当前可利用目标**：query 子串漏洞已修，api IDOR 未完成验证但被 WAF 严格限速
- 与 qd93 同源 IP 段，属**加固版彩虹**（有 CSRF）
- 续挖需：**全新干净 IP**（非青果已封段）+ 极低速（≥2s/请求）+ 单线程

---

## 5. 脚本

| 文件 | 用途 |
|------|------|
| `xinhe001_probe.py` | 轻量面探测 |
| `xinhe001_deep.py` | 全链深挖（勿高频） |
| `xinhe001_slow_deep.py` | 低速面 + api |
| `xinhe001_api_scan.py` | api IDOR 专项 |
| `xinhe001_proxy_deep.py` | HK 代理轮换深挖 |
