# fak86.top — 拾玥Q商城

## Verdict
**YKFAKA**。HTTPS 证书挂 `dfqq.xyz`（SNI 不匹配）；**HTTP `http://fak86.top/` 可用**。

**`value=null` 未死**：裸 POST → `请求非法`；带 **Geetest** 后返回订单列表（118 ddid / 9 已发卡），`Query_Km` 可拖卡密。

## SUCCESS_CASES
| 案列 | 结果 |
|------|------|
| mima1314 `value=null` → `Query_Km` | **可用（需 Geetest）** |
| qd93 / 彩虹 ajax | N/A |
| 79yj api search | N/A |

## Dump
1. `GET /Captcha` → `gt=a0c32e16…` + challenge（需 `success=1`）
2. 2captcha 解 Geetest v3
3. `POST /Query.html`：`value=null` + `__token__` + `geetest_*`
4. 列表含 **118** 单（已发卡 9 / 未发卡 109）→ `GET /Query_Km/{ddid}`

| 指标 | 值 |
|------|-----|
| ddids | 118 |
| `#target` 非空 | 9 |
| 去重卡密 | **7** |

## 其它
- 支付：USDT `TJGhSHDkZqF9wATeYPsnVuEFAuGCrQ4qGx`（测试单 ddid `8A35A2887BD8` →「此订单未发卡」）
- TG：`@uu6569`
- 姐妹域证书：`dfqq.xyz`（加载页，未深挖）

## Downloads
http://103.185.249.13:18888/fak86_cards_20260804.tsv

**Kami obtained: true**
