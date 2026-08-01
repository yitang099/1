# xinhe001.lol/shop 深挖报告

> **日期：** 2026-08-01  
> **状态：** 表面无卡密泄露；深挖因 WAF 中断  
> **栈：** 彩虹发卡 `/shop/`（星河001 @xinghe0010）

---

## 1. 目标信息

| 项 | 值 |
|----|-----|
| URL | https://xinhe001.lol/shop/ |
| 源站 IP | `103.43.11.95` / `45.158.21.213`（同 jinku/hm0880 段） |
| getcount | orders=**5717**，money≈**101.7 万** |
| CSRF | `csrf.js` + 页面 `csrf_token` |
| 客服 | 站内 `user/ajax_chat.php` |

---

## 2. 已测漏洞面

| 向量 | 结果 |
|------|------|
| `?mod=query&data=1` 子串越权（qd93 类） | ❌ 返回「没有查询到数据」，**无他人订单** |
| 子串 `1/11/123/888/13x/139/150…` | ❌ 0 条 `showOrder` |
| `toollogs.php` | ❌ 空 |
| `ajax.php?act=getcount` | ✅ 可用 |
| `ajax.php?act=query/order/pay`（裸 GET） | 403 |
| `cron.php` | 「监控密钥不正确」 |
| `mod=buy tid=34` | ✅ 有 hashsalt，pay 链未跑完（WAF） |

---

## 3. 与 qd93 对比

| | qd93.com | xinhe001.lol |
|--|----------|----------------|
| 路径 | 根 `/` | `/shop/` |
| query 子串拖单 | ✅ 可拖他人单 | ❌ 已修/未暴露 |
| csrf.js | 无 | **有** |
| 规模 | 526 单 | **5717 单** |

同源站 IP 段，疑为同运营商升级修补版彩虹。

---

## 4. 深挖中断原因

- 连续探测后云机/HK/CN 均 **连接重置/超时**
- 全量 pwd 扫（150+）触发封禁
- 脚本：`xinhe001_deep.py`（pay/notify/api/cron/pwd）已备好，需 **冷却 + 低速 + CN 代理** 续跑

---

## 5. 待续（站点恢复后）

1. 低速 pwd 扫（`query_pwd_list.txt`，≥1s 间隔）
2. `tid=34` pay 链 → `trade_no` → notify 伪造
3. `api.php` 近 20 单 IDOR
4. cron 密钥小字典

产物目录（计划）：`/data/automation/results/xinhe001.lol/deep_20260801/`

---

## 6. 脚本

- `xinhe001_probe.py` — 轻量面探测
- `xinhe001_deep.py` — 全链深挖（勿高频）
