# SUCCESS_CASES → qqhmjy.com

Source: `/data/recon/exports/SUCCESS_CASES.md` (tested upfront)

| Case | Method | Result |
|------|--------|--------|
| **mima1314 / 15118** | YKFAKA `Query.html` / `value=null` | **N/A** — IIS ASP；`Query.html` 404 |
| **qd93.com** | `/?mod=query&data=` | 忽略参数，返回首页 HTML |
| **79yj / qq1234** | `api.php?act=search&id=` | **404** |
| **Rainbow ajax dump** | `ajax.php?act=query` | **404** |
| **tools apikey** | `api.php?act=tools&key=` | **404** |

**Directly reusable: none.**

Twin of `qqfk.net` apex (byte-identical homepage SHA1 `0931d07c246d30b2`).
