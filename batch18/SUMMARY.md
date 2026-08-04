# Batch18 recon summary（18 shops）

## Verdict

**18/18 彩虹发卡。`qqxbk.vip` 复用 79yj api-search IDOR，已全量拖卡密（184 单 / 2370 unique）。**  
其余 17 站 SUCCESS_CASES 无一复用；多数 `yxts=277` hardened。

## Hit: qqxbk.vip

| Item | Value |
|------|-------|
| Shop | `https://qqxbk.vip/`（根路径，非 `/shop/`） |
| Stack | Rainbow `yxts=194`，orders=184 |
| Vuln | `%61pi.php?act=search&id=N` **无需登录/密钥** |
| Shape | `id=1..184` → `code=0` + `data.订单结果`（QQ----pass----token URL）；`id≥185` → `订单不存在` |
| Dump | **184 cards / 2381 lines / 2370 unique kami** |
| Artifacts | `results/dump/qqxbk_*.json|tsv|txt` |

Ajax query 对本站返回 `data=[]`（空）；卡密来自 api search，不是 ajax dump。

## Table（按单量）

| Site | Orders | yxts | ajax | api search |
|------|--------|------|------|------------|
| dadiqq.com | **173000** | 277 | 500 | auth |
| chuhao.lol | **97813** | 277 | 500 | auth |
| youhui1998.top | 56234 | 277 | 500 | auth |
| tianfei88.lol | 32723 | 277 | 500 | auth |
| qqbizu666.top | 10360 | 277 | 500 | auth |
| lbd.lol | 4256 | 277 | 500 | auth |
| xiaobei.lol | 3801 | 277 | 500 | auth |
| xxn7788.top | 2391 | 277 | 500 | auth |
| byqqdd.top | 1776 | 277 | 500 | auth |
| xdd6689.top | 786 | **1008** | 500 | auth |
| qq857.cc | 392 | 277 | **200 / []** | auth |
| 其余 6 站 | 9–380 | 277 | 500 | auth |
| **qqxbk.vip** | **184** | **194** | 200 / [] | **OPEN IDOR → dumped** |

## SUCCESS_CASES

| Case | Result |
|------|--------|
| qd93 | 抽样无泄漏 |
| ajax dump | 16×500；qq857 / qqxbk → `data=[]` |
| api search | 17×需密钥；**qqxbk 全开并拖完** |
| tools | oracle 全开，短喷雾无命中 |
| YKFAKA null | N/A |

## Artifacts

`FINDINGS.json`、`results/SUCCESS_CASES_MIGRATE.md`、`results/dump/`、`scripts/`  
HK: `/data/recon/batch18/`
