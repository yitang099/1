# 2020999.cn → www.15118.cn

## Verdict
**YKFAKA「qq小号自助购买平台」**。`2020999.cn` 301 到 `https://www.15118.cn/`（同 IP `154.201.82.180`）。

**mima1314 / 15118 系 `Query.html value=null` IDOR：存活。** 已批量拖单并抽出 `#target` 卡密。

## SUCCESS_CASES
| 案列 | 结果 |
|------|------|
| mima1314 `POST /Query.html value=null` → `Query_Km/{12hex}` | **可用（LIVE）** |
| 15118 null（SUCCESS_CASES Aug1 标死） | **复测复活**，仍约 904 ddid |
| qd93 / 彩虹 ajax | N/A（非彩虹） |

## Dump
1. `GET /Query.html` → `__token__`
2. `POST /Query.html`：`value=null&page=1&__token__=...`（Referer: Query.html）→ ~2.6MB，**904** 个 `Query_Km/{ddid}`
3. `GET /Query_Km/{ddid}` 同会话 → 订单详情 / `#target`

| 指标 | 值 |
|------|-----|
| ddids | 904 |
| `#target` 非空 | 108 ddid / 110 行 |
| 清洗后凭证行（去客服占位） | **74** |
| 已付但 `#target` 空 | ~786（联系客服/手动接码类） |

## Downloads
- 全量 `#target`：http://103.185.249.13:18888/2020999_15118_cards_20260804.tsv
- 清洗卡密：http://103.185.249.13:18888/2020999_15118_kami_clean_20260804.tsv

## Artifacts
`2020999/FINDINGS.json`、`results/dump/`（`ddids.txt`、`cards_final.tsv`、`cards_kami_clean.tsv`、`STATS.json`）、`scripts/`

**Kami obtained: true**
