# SUCCESS_CASES 迁移对照 — yedaoqq.top/shop/

对照 HK `/data/recon/exports/SUCCESS_CASES.md`（2026-08-01）。  
**初版侦察未系统走案列；本轮已逐条复测。**

| 案列 | 类型 | 漏洞手法 | yedaoqq 结果 |
|------|------|----------|--------------|
| **qd93.com** | 彩虹根路径 | `?mod=query&data={子串}` → `showOrder(id,skey)` → `mod=faka` | **不可用**。子串与精确 TN/联系方式均返回「没有查询到数据」，0×showOrder/faka。自建未付款单 `20260803112308729` / `yedao112305` 同样查不到（未付款不进此列表）。`ajax.php?act=query` 一律 HTTP 500。 |
| **79yj.com** | 彩虹 `/shop/` | `api.php?act=search&id=` 未授权 IDOR | **不可用**。`api.php` 被拦/不通；`%61pi.php?act=search&id=` 恒返回「请提供用户登录信息或API对接密钥」。id=1/100/…/6357 无差别。 |
| **qq1234.cc** | 彩虹 `/shop/` | 同上 api search IDOR | **同上，不可用** |
| **123.taoqqhao.com** | 彩虹 `/shop/` | 同上 | **同上，不可用** |
| **mima1314.com** | YKFAKA | `value=null` → `Query_Km/{ddid}` | **N/A**（非 YKFAKA）。`/Get_Yk_KC.html` / `/Query_Km/` 404/不通 |
| **15118.cn** | YKFAKA | 同 null 链 | **N/A** |

## 结论
成功案列 **无一可直接复用**。与 xuxin66 / xxn7788 同结论，需继续走 API tools key / cron / 登录 / SYS_KEY 线（且 query 500 阻断 skey 离线爆破）。

## 日志
- `success_cases_migrate.log` — 子串 + api search 带
- `success_cases_exact.log` — 已知 TN/input 精确查询
