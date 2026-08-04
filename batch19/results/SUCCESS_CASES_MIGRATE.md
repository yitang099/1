# SUCCESS_CASES → batch19 (19 rainbow shops)

Source: `/data/recon/exports/SUCCESS_CASES.md` (tested upfront via Tor)

| Case | Method | Batch result |
|------|--------|--------------|
| **qd93.com** | `/?mod=query&data=` | 抽样无 `showOrder`/`mod=faka` |
| **Rainbow ajax dump** | `ajax.php?act=query` | **18/19 → HTTP 500**；`o898.com` → `data=[]` |
| **79yj / qq1234** | `%61pi.php?act=search&id=` | **18/19 auth**；`qingtianqq1.top` → `订单不存在`（开放但稀疏枚举 0 hit） |
| **tools apikey** | `%61pi.php?act=tools&key=` | oracle 存活；短喷雾 0 hit |
| **mima1314 / 15118** | YKFAKA null | **N/A**（全彩虹） |

**Directly reusable: none. kami_obtained: false.**
