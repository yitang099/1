# qqduo.com — other pull vectors (post email-spray)

## Still viable

| Vector | Status | Notes |
|--------|--------|-------|
| Email contact spray | **Primary** | Guest buy + plaintext email; ongoing focus spray |
| Query-password on known paid | Partial | 4/14 paid opened with weak/local-part pw; 10 still locked |
| `order/state` tradeNo oracle | Aux | Unauth returns `{id,trade_no,amount,status}` — validates guesses, no secret |

## Probed — not a dump path (now)

### Shared supplier API (`/shared/*`)
- Live: `POST /shared/authentication/connect` with `app_id=<userId>` + MD5 sign(`app_key`)
- Our recon user `uid=2011` connects OK; `/shared/commodity/items` empty (not a supplier)
- `/shared/commodity/query` scoped to `owner=app_id` — no cross-user order IDOR
- UID existence oracle: wrong key → `密钥错误` (users from ~1001+); keys are 16-hex (`strtoupper(md5…)`) — not practical to brute
- Weak key spray on 1001–1020: no hit

### Upstream货源 (`shared_id=1` on all SKUs)
- `shared_code` present (e.g. `B55D028FF38FE727`, `4411A149DB4F3A1D`)
- Upstream `domain` / `app_id` / `app_key` **not exposed** to front
- No `shared_code` overlap in HK dumps (suran888 / qq898 / lubanqq list)
- Same product *names* appear elsewhere — not sufficient to pivot

### Member / business
- `purchaseRecord` / `bill`: own data only
- `commodityOrder` / `card`: needs paid shop level (¥188 / ¥288 / ¥388) — balance required
- `master/commodity`: affiliate price list only (no secrets)

### Classic recon
- `.git` / `.env` / zip/sql backups: soft-404 HTML
- Rainbow / YK / `sb.*/api/records`: miss (already)
- Admin login: no weak default in quick pass (captcha); not pursued further
- Epay gateway `zf.idx7.cn`: third-party cashier, no kami

## Conclusion

No second high-yield pull channel found beyond **email spray + query-password**. Highest ROI remains:

1. Keep expanding `{local}@{qq,163,126}.com` / numeric QQ emails  
2. For each new paid hit, try `password ∈ {local, 123456, local+123, …}`  
3. Optional later: pay for business level only if supplier-side card APIs become necessary (unlikely vs spray cost)
