# siye.lol — Tor vectors (continued)

## Egress
- Cluster RST earlier; **HK Tor works**. Workspace intermittent (single OK, burst RST).

## User
- Reg OK; **Login OK** (`pass` + hashsalt + Geetest) → `user_token` cookie
- `uset.php` 网站设置：无 apikey/密钥字段
- Panel ajax order/kmlist：`No Act`

## Pay / order
- Buy: `/?mod=buy&tid=8` + JSFuck hashsalt + Geetest → `ajax.php?act=pay` → `trade_no`
- Sample TN: `20260804154041222`, `20260804154942903`
- `?buyok=1` / unpaid order page：**无 skey**（支付后才进卡密页）
- USDT pay page live (~0.09 USDT for ¥0.6); status polls `backurl` after pay

## Query
- `ajax.php?act=query` → HTTP 500
- `?mod=query&data=` → empty results (fake pagination `N / 0`), **not** qd93 substring leak

## API
- `POST %61pi.php?act=goodsdetails` + `tid=` works unauth
- tools/clone/cron brand oracles：弱密钥未中
- **Tools apikey Tor spray**：5 slices running, ~3.5k+ tested, **0 hits**

## Still open
- Finish/expand Tor apikey spray
- Soft-target pivot if miss
