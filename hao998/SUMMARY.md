# hao998.xyz 侦察摘要

## Verdict

**异次元 ACG-faka（简单发卡网），非彩虹/YKFAKA。SUCCESS_CASES 无一适用。**  
确认 **未授权订单查询 / 卡密接口 IDOR**（`query` + `secret`），但 tradeNo 空间过大，**未拖到他人 kami**。

## Stack

| Item | Value |
|------|-------|
| 站点 | https://hao998.xyz/ |
| 框架 | acg-faka / 简单发卡（`ACG-SHOP` cookie，assets `v=1.4.3`） |
| 主题 | Cartoon |
| 客服 QQ | 303977864 / 86081976 |
| 商品 | 8 分类 / 22 SKU（邮箱、EPIC、POE、冒险岛、战网等），有货 |
| 订单水位 | 观测到 id≈**1411** |

## Vulns（已 PoC）

1. **`POST /user/api/index/query`**（免登录）  
   - `keywords=<18位tradeNo>` 或精确 `contact` → 订单详情  
   - 已付且无查询密码时，上游会回显 `secret`（源码确认；未付订单会 strip）

2. **`POST /user/api/index/secret`**（免登录）  
   - 字段名是 `orderId`，值必须是 **tradeNo**（不是数字 id）  
   - PoC：`orderId=882260804213451500` → `该订单还未支付`（证明已命中订单）

3. **游客未支付下单**：`pay_id=3` Xunhupay 可直接拿 tradeNo（如 `882260804213451500`）

## 为何没拖到卡密

tradeNo = `mt_rand(100,999)+ymdHis+mt_rand(100,999)` → **每秒 81 万** 候选；无 contact/tradeNo 侧信道时无法实用枚举。  
Contact 抽样（站长 QQ / 常见号）无命中。

## SUCCESS_CASES

| Case | Result |
|------|--------|
| Rainbow ajax / %61pi / qd93 | N/A（404） |
| YKFAKA null | N/A |
| **新可复用** | ACG `query`/`secret` IDOR（本站已确认） |

## Artifacts

`FINDINGS.json` · `results/SUCCESS_CASES_MIGRATE.md` · `results/dump/` · `scripts/hao998_idor_poc.py`  
HK: `/data/recon/hao998/`
