# qqfk.net recon summary

## Verdict

**IIS 10 + 经典 ASP QQ 批发站**（非 YKFAKA / 非彩虹）。  
**SUCCESS_CASES 无一适用/可复用。未拖到 kami。**

## Hosts

| Host | IP | Role |
|------|-----|------|
| `qqfk.net` | 219.234.31.186 | 较瘦 ASP 首页 |
| `www.qqfk.net` | 103.43.189.139 | 主站：`buy.asp` / `kucun.asp` 有货目录 |

## SUCCESS_CASES

| Case | Result |
|------|--------|
| YKFAKA `Query.html` / null | **404 / N/A** |
| qd93 `mod=query` | 仅回首页，无 query 逻辑 |
| Rainbow `ajax.php` / `api.php` | **404** |

## Surface

- 商品：`buy.asp?id=`（kucun 见 171–210 等 30 个）
- 下单：`saveprofile.asp?action=ordertb&id=`
- 登录：`login.asp` → `chkuser.asp`（需图形码）
- `manage/` 404；`inc/` 403

## Sister note

首页链出的 `www.qqwxpf.com` frameset → **`xunqq.cn`**（与 pfqq.net 同一彩虹店，见 PR #46）。

## Artifacts

`FINDINGS.json`、`results/SUCCESS_CASES_MIGRATE.md`、`results/dump/`、`scripts/`  
HK: `/data/recon/qqfk.net/`
