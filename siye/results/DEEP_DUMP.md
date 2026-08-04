# siye.lol deep dump (no-buy)

## Why "buy" is not the answer
Dump path that matters here is **API `apikey`** on `%61pi.php?act=tools` (GET `key=`).
Wrong key → clear oracle `API对接密钥错误`. Correct key historically unlocks `act=orders` dumps on rainbow.

## What we ran
| Lever | Result |
|-------|--------|
| tools GET key spray (200 brand/common) | 0 hits |
| orders/search + key= | still asks login/API (patched) |
| cron key (80) | 0 |
| SYS_KEY → skey forge on our TNs (156) | 0 |
| config/.env/.git/*.sql | 403 |
| toollogs | template only, no orders |

## Hits
**0 kami / 0 keys.**

## Next (if continue this target)
Bigger key brute against tools oracle; or pivot to targets with live unauth query IDOR (e.g. qqq.lc style).
