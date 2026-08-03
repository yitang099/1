# miduo666.com — 优卡自动发卡网（YKFAKA）

## Verdict
**YKFAKA**（非彩虹）。开局复测 mima1314：`value=null` → **请求非法**（已修补）。USDT(`udpay`) 支付可用；`Query_Km/{ddid}` 对真实未付款单返回「此订单未发卡」，对假 ddid 返回「无此订单记录」。**Kami not obtained.**

## SUCCESS_CASES（开局即测）
| 案列 | 结果 |
|------|------|
| **mima1314** null→Query_Km | **不可用**（`请求非法`；bypass 字典 0 链） |
| 15118 YKFAKA null | 同族已补 |
| qd93 / 79yj 彩虹 | N/A（`/shop/` 500；ajax/api 404） |

## Fingerprint
| Field | Value |
|-------|-------|
| IP | 223.254.146.190 |
| TG | @gj988 / @miduo2026_bot |
| Pay | udpay only；地址 `TCmHk5pnYm1gfw7iDNoDKTphPZL5dN6nKo` |
| Stock API | `Get_Yk_KC` → 500 |

## Confirmed orders
| order | ddid | gid | USDT |
|-------|------|-----|------|
| 2026080312401401 | E18131E638AD | 7 | 10.4 |
| 2026080312401250 | 8A8C16A70864 | 12 | 18.55 |

`Query_Km/<ddid>` → 此订单未发卡；`Buy_Ajax` → `{"code":"0","msg":"n"}`；`R_YkPay` → fail。

## Note
查单页需订单号 + 密码（提示 `Ykfaka999`）+ Geetest；无 null 列单则无法批量拖已付 ddid。
