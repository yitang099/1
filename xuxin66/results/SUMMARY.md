# xuxin66 订单/卡密深挖结果

## 结论
- **卡密仍未拿到**。成功案列（qd93 子串 / qq8 api IDOR / YKFAKA / acg-faka secret）均不可直接复用；已转向同源集群新方向。
- 测试单: `20260803075904880`（tid=1310, input=`kami075902`, ¥10, 未付款）
- 支付网关: `api.ttwl66.cn` pid=`1003`
- skey: `md5(id + SYS_KEY + id)`；错密钥固定「验证失败」

## 成功案列迁移结果

| 案列 | 手法 | xuxin66 |
|------|------|---------|
| qd93.com | `mod=query&data=` 子串 | ❌ 精确匹配，短数字无 showOrder |
| 79yj / qq1234 | `api.php?act=search&id=` 未授权 | ⚠️ `%61pi.php` 可达，但需登录或 API key |
| mima1314 | YKFAKA `Query_Km` | ❌ 路径 404 |
| shopping.qq898 | acg-faka `/secret` | ❌ 非同框架 |
| fffzz / hmjf | 同彩虹卡死态 | 同缺口（SYS_KEY / 联系方式） |

## deep7 新突破（可利用面）

| 方向 | 结果 |
|------|------|
| `%61pi.php?act=tools&key=` | ✅ 可用 API key 预言机：错→`API对接密钥错误`，空→`确保各项不能为空` |
| `%61pi.php?act=search` | 定制鉴权：`请提供用户登录信息或API对接密钥`（stock 源码无此句） |
| `other/usdt-trc20/status.php` | ⚠️ 存在；**假单也回「未付款」**，仅「付款成功」有意义（USDT 已付） |
| 同源 IP | 与 youhui1998 / piguqq 同集群 `45.158.21.213` / `103.43.11.95` |
| `query type=1` 17 位订单号 | 源码不按 userid 过滤；撞到已付 `pre_orders.tradeno` 可直接拿 skey |
| card_check | 开着但要 CSRF；iskami 路径需页面 token |
| gift / invite / api IDOR 无 key | 关闭或需密钥 |

## 进行中
- **API key 喷洒**（跳板自刷新青果）：`/tmp/xux_keyspray2.sh` → `/tmp/xux_key3.log`，字典 ~4032
- 命中后立即 `act=search&id=` 拉单 / 再算是否可出卡密

## 订单事实
- getcount: orders=11240, paid≈11198, 流水≈225万, 运营276天, 分站160
- 未付款只在 `pre_pay`，支付成功后才进 `pre_orders`

## 下一步优先级
1. 等/扩大 API key 字典（`act=tools` 预言机已通）
2. 扩大 SYS_KEY（中则批量 kminfo）
3. 已付 trade_no：`query type=1` / getshop（勿信 USDT「未付款」存在性）
4. 2Captcha 注册后探余额 / payrmb

## 产物
- 服务器: `/data/automation/results/xuxin66.top/deep7_*`、`/tmp/xux_key3.log`
- 脚本: `/data/automation/bin/xuxin66_deep7*`、`xuxin66_apikey_batch.sh`、跳板 `/tmp/xux_keyspray2.sh`
