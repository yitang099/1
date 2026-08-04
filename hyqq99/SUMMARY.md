# hyqq99.com/shop recon summary

## Verdict

彩虹 `/shop/`「海洋QQ游戏商城」`yxts=277`，IP `45.158.21.213` / `103.43.11.95`，公开统计 **~1.26 万单**。  
**SUCCESS_CASES 无一复用。未拖到 kami。**

## SUCCESS_CASES

| Case | Result |
|------|--------|
| qd93 `mod=query&data=` | 页面 OK，样本均「没有查询到」 |
| ajax `act=query` | **HTTP 500**（ hardened，同 shenyuan 系） |
| api `act=search`（`%61pi.php`） | **需登录/API key** |
| tools apikey | oracle 存活；短喷雾 0 hit |
| YKFAKA null | N/A |

## Surface

- Root `/` 403；店在 `/shop/`
- `getcount` 需 `Origin`；HK 直连易超时，Tor 可用
- Pay：CSRF + JSFuck hashsalt；未支付单例 `20260804192252175`（tid=93）
- `cron.php` 监控密钥不正确；`toollogs.php` 200
- TG：`@hysc99` / `@hysc9999`

## Artifacts

`FINDINGS.json`、`results/SUCCESS_CASES_MIGRATE.md`、`results/dump/`、`scripts/`  
HK: `/data/recon/hyqq99.com/`
