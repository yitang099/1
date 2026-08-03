# SUCCESS_CASES → shenyuan.lol

Source: `/data/recon/exports/SUCCESS_CASES.md` (tested upfront)

| Case | Method | Result |
|------|--------|--------|
| **qd93.com** | `/?mod=query&data=` substring → faka | Query page OK; **no** `showOrder` / `mod=faka` leak |
| **79yj / qq1234** | `api.php?act=search&id=` | `%61pi.php` → `请提供用户登录信息或API对接密钥`；`api.php` blocked |
| **mima1314 / 15118** | YKFAKA `value=null` | **N/A**（彩虹 `/shop/`） |

**Directly reusable: none.**

Site is empty: `orders=0`, all card goods `stock=0`.
