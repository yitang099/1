# SUCCESS_CASES migrate notes — lubanqq.top

## Negative (do not retry blindly)

- Rainbow `getcount` / `ajax.php` / `%61pi.php?act=search` → 404 on this host
- YKFAKA `value=null` → not YK
- `*.lubanqq.top/api/records` → 403 nginx, not 异次元 checker dump

## ACG 3.5.5 hardened pattern (new)

When **all SKUs are `only_user=1`** on acg-faka ≥3.x:

1. Guest trade returns `请先登录后再购买哦`
2. Logged-in trade **rewrites** `contact` to `Str::generateRandStr(16)` before insert
3. `query` matches **exact** `^\d{18}$` trade_no **or** exact contact string
4. Therefore **plaintext / weak-contact spray (hao998/suran888 playbook) does not apply**

Confirm with one unpaid self-order:

```
POST /user/api/order/trade  item_id=<id>&pay_id=<id>&num=1&contact=test@x.com&device=0
# (session required)
→ tradeNo
POST /user/api/index/query  keywords=<tradeNo>
→ contact field is 16-char rand, not submitted value
POST /user/api/index/query  keywords=test@x.com
→ empty
```

## Still-valid IDOR (needs trade_no)

- Unauth `query` + `secret` by known 18-digit trade_no
- For `status=1` and empty order password, upstream returns `secret` inside query list (no extra secret call)
- Practical acquisition still blocked by trade_no entropy + IP throttle unless another leak provides trade_no

## Trade API gotcha

- Modern Dream/acg.js uses **`item_id`**, not `commodity_id` (`getPostData` → `item_id`)
- Wrong field → `请选择商品`

## Suggested triage order for future ACG targets

1. Fingerprint version + `only_user` ratio via `commodityDetail`
2. If many guest (`only_user=0`) SKUs with sales → contact spray (hao998)
3. If all `only_user=1` → skip contact spray; look for sb/records, shared upstream, or other leaks
4. Always keep Rainbow/YK probes for dual-stack hosts
