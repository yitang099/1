# yedaoqq.top /shop/ — 椰岛发号网

## Verdict
Rainbow faka on the **same cluster** as xuxin66 / xxn7788 (`45.158.21.213` / `103.43.11.95`, `yxts=276`). Unauth goods/siteinfo work; hashsalt unpaid orders work; **`act=query` → HTTP 500** blocks skey/SYS_KEY offline crack; pay channels dead (USDT closed, qqpay `MCHID_NOT_EXIST`). **Kami not obtained.**

## Fingerprint
| Field | Value |
|-------|-------|
| Site | 椰岛发号网 |
| Build | 2025-11-01 |
| Orders / money | 6357 / ≈104.8万 |
| Sub-sites | 88 |
| Goods | 28 (10 in stock) |
| TG | @yedaoqq1 / t.me/qqyedao / t.me/yedaoqq1 |

## Confirmed surfaces
- `%61pi.php?act=siteinfo|classlist|goodslist` unauth
- API tools key oracle (empty / wrong messages)
- cron / clone / token / card_check oracles
- Geetest login `gt=a1017fd4951689c5d20317c165c1c318` (same as xxn7788)

## Pay path
1. `?mod=buy&tid=28` → JSFuck `hashsalt` + `csrf_token`
2. `ajax.php?act=pay` with `inputvalue` → unpaid TN
3. Test TNs: `20260803112308729` / `yedao112305`; `20260803112820111` / `yedao112819`
4. USDT submit → `该支付方式已关闭` (announce still pushes USDT, no address)
5. qqpay → `MCHID_NOT_EXIST`
6. `getshop` / USDT status → `未付款` for any TN-looking value (not an existence oracle)

## Blocker: query HTTP 500
Same-session `ajax.php?act=query` (tradeno or input) returns **HTTP 500** empty body. Without `skey`, cannot offline-crack `SYS_KEY` via `skey=md5(id+SYS_KEY+id)`.

## Spray
Jump: `/tmp/yedao_tools_spray.sh` against merged API key dicts. Brand sample keys: 0 hits.

## Next angles
1. Wait / check tools key spray hit → `orders` / `search` / kami
2. cron / clone key sprays (shared dicts with xxn)
3. Admin login via 2Captcha + sticky client IP (xxn pattern failed on clientip bind)
4. Re-check query if host patches 500
