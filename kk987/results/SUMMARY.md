# kk987.top/shop/ — 子心发卡

## Verdict
Rainbow faka, **same template** as xuxin66/xxn7788/yedaoqq (`yxts=276`, build `2025-11-01`, same Geetest `gt`). IPs differ (`156.238.239.*` / `103.43.11.241`). SUCCESS_CASES **none reusable**. Hashsalt unpaid order works; `act=query` HTTP 500; pay dead. **Kami not obtained.**

## SUCCESS_CASES 迁移（开局即测）
| 案列 | 结果 |
|------|------|
| qd93 `mod=query&data=` 子串 | 不可用（空结果；自建 TN 精确查也空） |
| 79yj/qq1234 `api search` IDOR | 不可用（需登录/API key；`api.php` 不通） |
| mima1314 / 15118 YKFAKA null | N/A（非 YKFAKA） |

## Fingerprint
| Field | Value |
|-------|-------|
| Site | 子心发卡 |
| Orders / money | 546 / 226811 |
| Sub-sites | 62 |
| Goods | 17 (4 in stock) |
| TG | @zixin0721；类目提及 @xfjsm_bot |

## Pay / query
- Unpaid TN: `20260803115721164` / `kk987115719` / tid=16 / ¥60
- USDT submit → 已关闭；qqpay → `MCHID_NOT_EXIST`
- `ajax.php?act=query` → **HTTP 500**（同 xxn/yedao）
- getshop「未付款」对假 TN 同样返回（非存在性预言机）

## Oracles
API tools/token/clone、cron、card_check 均可用作密钥喷洒预言机。

## Spray
Jump: `/tmp/kk987_tools_spray.sh` (~15k keys) → `/tmp/kk987_tools_spray.log`
