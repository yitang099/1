# pfqq.net recon summary

## Verdict

`https://pfqq.net/` → `http://xunqq.cn/` gate → Rainbow faka at `http://xunqq.cn/admin/` behind **sec_defend** WAF (`yxts=456`).  
**SUCCESS_CASES 无一复用。ajax query 端点存活但 `data=[]`；自建未支付单仍不泄漏；未拖到 kami。**

## Topology

1. `pfqq.net` (219.234.31.149 / CNAME `qqpifa.gotoip2.com`) → 301/frame → `xunqq.cn`
2. frameset: `/nasgo/` → `/loading/` → `../../../admin/`
3. `/admin/` = sec_defend JSFuck cookie → shop

## SUCCESS_CASES

| Case | Result |
|------|--------|
| qd93 `mod=query&data=` | 页面 OK，无卡密/订单泄漏 |
| ajax `act=query` | `code:0` 但 **`data=[]`**（含自建单后） |
| api `act=search&id=` | `订单不存在`（HTTP 500 body） |
| api `act=tools&key=` | oracle 存活；短 wordlist 无命中 |
| YKFAKA null | N/A |

## Auth / pay

- 注册：`act=reguser` + 图形验证码 + hashsalt（2captcha 可过）
- 下单需登录：`你还未登录` → 登录后可建未支付单（例 `20260804182818749`）
- `mod=faka` 无 skey → `验证失败`；未支付无 kami

## Contacts

TG `@VXQCC` / `t.me/haomaqq`；QQ群 `7229863`；YY `985895`

## Artifacts

`FINDINGS.json`、`results/SUCCESS_CASES_MIGRATE.md`、`results/dump/`、`scripts/`  
HK: `/data/recon/pfqq.net/`
