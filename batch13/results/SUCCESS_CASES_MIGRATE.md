# SUCCESS_CASES → batch13 (13 rainbow shops)

Source: `/data/recon/exports/SUCCESS_CASES.md` (tested upfront via Tor)

| Case | Method | Batch result |
|------|--------|--------------|
| **qd93.com** | `/?mod=query&data=` | 抽样站均无 `showOrder`/`mod=faka`；「没有查询到」 |
| **Rainbow ajax dump** | `ajax.php?act=query` | **12/13 → HTTP 500**；`qqx2.cn` → `code:0 data=[]` |
| **79yj / qq1234** | `%61pi.php?act=search&id=` | **全部** `请提供用户登录信息或API对接密钥` |
| **tools apikey** | `%61pi.php?act=tools&key=` | **全部** oracle（空/错密钥）；短喷雾 0 hit |
| **mima1314 / 15118** | YKFAKA null | **N/A** — 全彩虹；`Query.html` 404；null POST 无 `Query_Km` |

**Directly reusable: none. kami_obtained: false.**
