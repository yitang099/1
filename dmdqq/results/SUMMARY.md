# dmdqq.cc — 哆咪哆商城

## Verdict
**YKFAKA**（IP `107.174.100.167`，HTTPS 正常）。查单带 **Geetest + 查单密码**。

**`value=null` 不可用**：裸 POST → `请求非法`；Geetest + `pass=Ykfaka999` → **`无记录`**（已空/已补）。  
**Kami not obtained。**

## SUCCESS_CASES
| 案列 | 结果 |
|------|------|
| mima1314 / fak86 `value=null`(+Geetest) | **不可用**（无记录） |
| qd93 / 79yj 彩虹 | N/A |

## 其它要点
- 下单强制设置查单密码；Query 的「订单编号」= **商户单号 ddid**（12hex），不是 `20…` 流水号
- 测试单：`60AC57D4064E` / `2026080417451725`，pass `Ykfaka999` → 可查到未付元数据；`Query_Km` →「此订单未发卡」
- USDT：`TH4HEXkVKgGiRBVWE7cGBbyZqB4BzPesLE`
- TG：`@yexihua`；QQ：`3905357653`
- 会员：`/User_Login.html`、`/User_Reg.html` 存在（未拖出卡密）

## Artifacts
`dmdqq/FINDINGS.json`、`results/probe/`（Query / null / pay / ddid query）、`dump/STATS.json`
