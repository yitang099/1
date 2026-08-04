# SUCCESS_CASES migrate — fak86.top

| Case | Expected | Result |
|------|----------|--------|
| mima1314 YKFAKA `value=null` | order list + kami | **HIT** — but **Geetest required**. Bare `value=null` → `请求非法`. With captcha: 118 ddids, 7 unique kami. |
| qd93 `mod=query&data=` | N/A | not Rainbow |
| 79yj `api.php?act=search` | N/A | 404 |

### Note for playbook
On patched-looking YKFAKA shops that return `请求非法` for null, **retry with `/Captcha` + Geetest fields** before marking dead.
