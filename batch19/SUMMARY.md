# Batch19 recon summary（19 shops）

## Verdict

**19/19 彩虹发卡。SUCCESS_CASES 无一复用。未拖到 kami。**  
多数 `yxts=277` hardened；例外 `xinhe001.lol` `yxts=2919`。

## Table（按单量）

| Site | Orders | ajax | api search |
|------|--------|------|------------|
| kln166.lol | **132747** | 500 | auth |
| tianyu9080.top | 39813 | 500 | auth |
| kpba.shop | 32712 | 500 | auth |
| xihongqq.top | 21435 | 500 | auth |
| qw123.lol | 18957 | 500 | auth |
| maomao888.top | 15508 | 500 | auth |
| xuxin66.top | 11273 | 500 | auth |
| jinyin1818.top | 9790 | 500 | auth |
| xinhe001.lol | 5889 (yxts=2919) | 500 | auth |
| 其余 10 站 | 5–3193 | 500* | auth† |

\* `o898.com` ajax **200 / data=[]**  
† `qingtianqq1.top` search **开放**（`订单不存在`），稀疏 ID 枚举 **0 单**

## SUCCESS_CASES

| Case | Result |
|------|--------|
| qd93 | 抽样无泄漏 |
| ajax dump | 18×500；o898 空数组 |
| api search | 18×需密钥；qingtian 开放但空 |
| tools | oracle 全开，短喷雾无命中 |
| YKFAKA null | N/A |

## Artifacts

`FINDINGS.json`、`results/SUCCESS_CASES_MIGRATE.md`、`results/dump/`、`scripts/`  
HK: `/data/recon/batch19/`
