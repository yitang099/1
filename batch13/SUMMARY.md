# Batch13 recon summary（13 shops）

## Verdict

**13/13 均为彩虹发卡（yxts=277 同代）。SUCCESS_CASES 无一复用。未拖到 kami。**

## Table

| Site | Orders | ajax query | api search | tools oracle |
|------|--------|------------|------------|--------------|
| kaka1880.xyz/shop | 13941 | HTTP 500 | auth | yes |
| db866.lol/shop | 0 | HTTP 500 | auth | yes |
| xy0088.top/shop | 14382 | HTTP 500 | auth | yes |
| wxr699.top/shop | 13077 | HTTP 500 | auth | yes |
| qqhaoma.top/shop | 183 | HTTP 500 | auth | yes |
| hm0880.top/shop | **28215** | HTTP 500 | auth | yes |
| suqi777.top/shop | 11377 | HTTP 500 | auth | yes |
| **qqx2.cn/** | 1214 | **200 / data=[]** | auth | yes |
| pinzun668.top/shop | 1024 | HTTP 500 | auth | yes |
| zzqq.lol/shop | 1941 | HTTP 500 | auth | yes |
| xsh168.top/shop | 1558 | HTTP 500 | auth | yes |
| fendou.lol/shop | 13856 | HTTP 500 | auth | yes |
| hmjf.lol/shop | 13939 | HTTP 500 | auth | yes |

## SUCCESS_CASES

| Case | Batch result |
|------|----------------|
| qd93 | 抽样均「没有查询到」 |
| ajax query dump | 12 站 HTTP 500；qqx2 存活但空数组 |
| api search | 全部需登录/API key |
| tools key | 全部 oracle 存活；短喷雾无命中 |
| YKFAKA null | N/A（Query.html 404） |

## Notes

- `qqx2.cn` 为根路径店（非 `/shop/`），TG `@FCCUU`
- `http://` 三站（hm0880/suqi777/xsh168）API 需走 HTTPS
- 与 hyqq99/shenyuan 同 hardened 代际

## Artifacts

`FINDINGS.json`、`results/SUCCESS_CASES_MIGRATE.md`、`results/dump/{BATCH,SUMMARY,DEEP}.json`、`scripts/`  
HK: `/data/recon/batch13/`
