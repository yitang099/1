# qq9888.vip — 大商QQ批发

## Verdict
同 IP `24.233.15.253`（与 fak86/dfqq 一族）：
- **HTTP** → YKFAKA「大商QQ批发」（主店）
- **HTTPS** → 证书 `dfqq.xyz` +「正在加载中」；背后有彩虹式 `api.php`

**SUCCESS_CASES 无一复用，Kami not obtained。**

## SUCCESS_CASES
| 案列 | 结果 |
|------|------|
| mima1314 / fak86 `value=null`(+Geetest) | 裸 → `请求非法`；+Geetest+`Ykfaka999` → **仅 1 笔（本机测试未付单）**，非批量 |
| 79yj `api.php?act=search&id=` | HTTPS 有接口，但 1..200+ 全 `订单不存在` |
| tools `key=` oracle | 存活（空/错密钥可区分）；小词表 **0 hit** |
| qd93 ajax query | HTTPS ajax `403`；HTTP 无 ajax |

## 站点要点
- 查单：Geetest + 每单密码；有货约 8 款（最低约 ¥15）
- 测试单：`3E3447C391C1` / USDT `TCA67FBYBHKH2rUczzMgwNdgdbF7Y643M5`
- TG：`@dsf09001`；群 `t.me/qqw5090708`；QQ：`350579669`

## Artifacts
`qq9888/FINDINGS.json`、`results/probe/`、`dump/STATS.json`
