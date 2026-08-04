# SUCCESS_CASES → pfqq.net / xunqq.cn/admin

Source: `/data/recon/exports/SUCCESS_CASES.md` (tested upfront after WAF bypass)

| Case | Method | Result |
|------|--------|--------|
| **qd93.com** | `/?mod=query&data=` substring → faka | Query UI OK；样本联系方式/订单号均 **没有查询到**；无 `showOrder`/卡密块 |
| **Rainbow ajax query dump** | `ajax.php?act=query&page=` | **Live** `{"code":0,...,"data":[]}` — 空数组；自建未支付单后仍空 |
| **79yj / qq1234** | `api.php?act=search&id=` | HTTP 500 body `{"code":-1,"message":"订单不存在"}`（采样 1–20/100/1000） |
| **tools apikey** | `api.php?act=tools&key=` | 空=`确保各项不能为空`；错=`API对接密钥错误`；短喷雾（admin/tg/qq/yy 等）**0 hit** |
| **mima1314 / 15118** | YKFAKA `value=null` | **N/A**（彩虹 `/admin/`，非 YKFAKA） |

**Directly reusable: none.**

### Extra (not SUCCESS_CASES but exercised)

- Pay unauth → `你还未登录`
- Reg+login+pay OK → unpaid `trade_no`；`mod=faka` 无 skey → `验证失败`
- getcount: `orders=0`（公开统计）
