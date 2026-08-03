# shenyuan.lol recon summary

## Verdict

彩虹 `/shop/`「自动发卡 / 深渊【QQ号商】」，`yxts=276` / build `2025-11-01`，IP `45.158.21.213` / `103.43.11.95`。  
**SUCCESS_CASES 无一复用。全站 0 单、货全空 → 无可拖 kami。**

## SUCCESS_CASES

| Case | Result |
|------|--------|
| qd93 | 不可用 |
| api search | 需登录/API key |
| YKFAKA null | N/A |

## Surface

- Root `/` 403；店在 `/shop/`
- `%61pi.php` 可用（goodslist/siteinfo）；`api.php` 直连异常
- `ajax.php?act=query` → **HTTP 500**
- Pay：CSRF + JSFuck hashsalt 可用；`tid=21` → 库存不足
- Geetest 集群共用 `gt=a1017…c318`
- TG：`@Sy_5889` / `@Damai66666666`

## Artifacts

`FINDINGS.json`、`results/SUCCESS_CASES_MIGRATE.md`、`results/goods_summary.json`、`scripts/`
