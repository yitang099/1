# siye.lol recon summary

## Verdict

彩虹 `/shop/`「自动发卡」，`yxts=276` / build `2025-11-01`，IP `103.43.11.95` / `45.158.21.213`。  
**~2967 单 / 68.3 万**；SUCCESS_CASES 无一复用；**query 500**；USDT 可付，kami 未拿到。

## SUCCESS_CASES
无一复用（qd93 / api search / YKFAKA）。

## Pay
- CSRF + JSFuck hashsalt 下单成功（有货 tid 8/9/10/41/75）
- **USDT-TRC20 可用**：`TPwqwKSiYasBVRt7V8VivXde7UADE2U3rT`
- qqpay：MCHID 错误；支付宝/微信关闭

## In-stock (sample)
| tid | stock | price | name |
|-----|-------|-------|------|
| 8 | 244 | 0.60 | 邮箱绑定钉钉 |
| 75 | 144 | 45 | 全新三网注册卡 |
| 9 | 24 | 200 | 充值卡密 |
| 10 | 19 | 500 | 充值卡密 |
| 41 | 3 | 89 | 美国飞机号 |

TG：`@siyeo`

## Tor follow-up (2026-08-04)

- Direct egress dead (cluster RST). HK Tor works.
- User reg OK (`reguser` + Geetest); panel has no kami IDOR.
- Tools apikey spray running on HK Tor (top 20k); see `results/TOR_VECTORS.md`.

## Dig update (2026-08-04 later)
- Login OK; pay creates TN; **skey only after payment**
- Query not qd93-vulnerable; tools spray still 0 hits (~3.5k+)
