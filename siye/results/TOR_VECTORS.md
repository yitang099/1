# siye.lol — Tor vectors (no-buy)

## Egress

- Workspace / HK direct / jump: TLS RST on whole `yxts=276` cluster (`103.43.11.95` / `45.158.21.213`)
- Qingguo tunnel + share pool: CONNECT ok but HTTPS broken / key issues
- **Works:** HK Tor `socks5h://127.0.0.1:9050` + `Accept-Language: zh-CN`

## User register (success)

- `POST /shop/user/ajax.php?act=reguser` with Geetest (2Captcha) + JSFuck `hashsalt`
- Accounts: `sy825511` (zid 126), `sy825661` (zid 127) / `SyTest9x!`
- Panel is distributor-style (签到/充值/工单/分站), **not** order/kami admin

## Panel IDOR

- `user/ajax.php` order/kmlist/record → `No Act` or `403`
- No unauth/user-session kami dump from panel

## Tools apikey spray (running)

- Oracle: `GET /shop/%61pi.php?act=tools&limit=1&key=`
  - wrong → `API对接密钥错误`
  - empty → `确保各项不能为空`
- Wordlist: top 20k (brand + prior faka/epay keys), ASCII-only
- Runner: HK `/tmp/siye_spray/spray_tor.sh` → `/data/automation/results/siye.lol/spray/`
- Rate ~0.4 rps via Tor; hits logged to `hits.jsonl`

## Still open

- Finish Tor tools spray / expand wordlist if miss
- Login (`pass`+Geetest+hashsalt) → `uset.php` for any key UI (unlikely for zid user)
- Soft-target pivot if apikey never hits
