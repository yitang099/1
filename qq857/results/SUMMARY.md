# qq857.cc/shop/ — 自动发卡

## Verdict
Rainbow faka, **yxts=276** / build `2025-11-01` template, but IP **`154.12.22.248`** (not 45.158 cluster). SUCCESS_CASES none reusable. **`act=query` works (HTTP 200)** unlike sibling shops’ 500 — unpaid returns empty `data[]`; needs exact paid 17-digit TN for skey. Pay dead. **Kami not obtained.**

## SUCCESS_CASES（开局即测）
| 案列 | 结果 |
|------|------|
| qd93 子串 query | 不可用 |
| 79yj/qq1234 api search | 不可用（需登录/API key；`api.php` 直连可用但仍鉴权） |
| mima1314 / 15118 YKFAKA | N/A |

## Fingerprint
| Field | Value |
|-------|-------|
| Orders / money | 254 / 84385 |
| Sub-sites | 15 |
| Goods | 6 (all in stock) |
| TG | @aashun66 / @Sm6688_bot |
| kfqq | 123456 |

## Query (notable)
- Unpaid TN/input → `{"code":0,"data":[]}`
- `type=1` non-17-digit → `请输入正确的订单号`
- 80 crafted TN probes → 0 hits
- `mod=query&data=` → empty（无 showOrder）

## Pay
- TN `20260803121954951` / `qq857121952` / tid=6 / ¥75
- USDT/支付宝/微信 → 已关闭；qqpay → `MCHID_NOT_EXIST`

## Spray
`/tmp/qq857_tools_spray.sh` → `/tmp/qq857_tools_spray.log`
