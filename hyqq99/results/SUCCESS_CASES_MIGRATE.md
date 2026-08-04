# SUCCESS_CASES → hyqq99.com/shop

Source: `/data/recon/exports/SUCCESS_CASES.md` (tested upfront)

| Case | Method | Result |
|------|--------|--------|
| **qd93.com** | `/?mod=query&data=` substring → faka | Query UI OK；样本 **没有查询到**；无 `showOrder` / `mod=faka` 泄漏 |
| **Rainbow ajax query dump** | `ajax.php?act=query&page=` | **HTTP 500**（与 yxts≈276 集群 hardened 行为一致） |
| **79yj / qq1234** | `%61pi.php?act=search&id=` | `请提供用户登录信息或API对接密钥` |
| **tools apikey** | `%61pi.php?act=tools&key=` | 空=`确保各项不能为空`；错=`API对接密钥错误`；短喷雾（hysc99/hyqq99/admin…）**0 hit** |
| **mima1314 / 15118** | YKFAKA `value=null` | **N/A**（彩虹 `/shop/`） |

**Directly reusable: none.**

Live shop: `orders≈12649`, pay CSRF+hashsalt works (unpaid TN only; no kami without pay/skey).
