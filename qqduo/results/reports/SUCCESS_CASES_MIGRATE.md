# SUCCESS_CASES migrate — qqduo.com

## Positive pattern (ACG guest + email)

When acg-faka has:

- `only_user=0` (guest buy)
- `contact_type=2` (email)
- version retains plaintext contact (not login-randomized)

Then:

1. Spray `weak@qq.com` / `weak@163.com` / `weak@126.com` / `{n}@qq.com`
2. Query exact email via `/user/api/index/query`
3. Secret via **`tradeNo`** + order query password (`password_status=1` common)

Contrast **lubanqq** (3.5.5, all `only_user=1`): contact randomized → this spray dies.

## API notes

- Trade field: `item_id` (3.3 Dream/Cartoon)
- Secret field: `tradeNo` (orderId returns 未查询到 on this host)
- Query shape: `{code:200,data:{list,total}}`
- No useful Rainbow/YK/sb paths here

## Password

All SKUs here force query password. Prefer trying: local-part, `123456`, email, `local+123`. Many orders still resist weak lists — contact hit ≠ kami.
