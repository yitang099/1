# SUCCESS_CASES → qqfk.net

Source: `/data/recon/exports/SUCCESS_CASES.md` (tested upfront)

| Case | Method | Result |
|------|--------|--------|
| **mima1314 / 15118** | YKFAKA `Query.html` / `value=null` | **N/A** — IIS ASP；`Query.html` 404；无 `index.php` 路由 |
| **qd93.com** | `/?mod=query&data=` | 参数忽略，返回首页 HTML；无 `mod=faka` / 卡密块 |
| **79yj / qq1234** | `api.php?act=search&id=` | **404** |
| **Rainbow ajax dump** | `ajax.php?act=query` | **404** |
| **tools apikey** | `api.php?act=tools&key=` | **404** |

**Directly reusable: none.**

Stack is classic ASP (`buy.asp` / `chkuser.asp` / `member.asp`), outside SUCCESS_CASES playbooks.
