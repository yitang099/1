# xuxin66 订单/卡密深挖结果

## 结论
- **卡密未直接拿到**。关键卡口已打通，缺 SYS_KEY / epay 商户密钥 / 已付订单联系方式。
- 测试单: `20260803075904880`（tid=1310, input=`kami075902`, ¥10, 未付款）
- 支付网关: `api.ttwl66.cn` pid=`1003`
- skey 算法确认: `md5(id + SYS_KEY + id)`（错密钥固定回「验证失败」）

## 已验证攻击面
| 方向 | 结果 |
|------|------|
| hashsalt 下单绕过极验 | 可创建未付款单 |
| act=order + skey | 验证逻辑确认，SYS_KEY 字典撞库进行中 |
| 联系方式 query 喷洒 | 常见字典 0 命中 |
| epay_notify 伪造 | sign 校验有效，610k 字典未中商户 key |
| getshop 历史单 | 邻域/采样未见已付泄漏 |
| payrmb | 需登录余额 |

## 订单事实
- getcount: orders=11240, paid≈11198, 流水≈225万, 运营276天, 分站160
- 未付款只在 `pre_pay`，支付成功后才进 `pre_orders`，故 query 查不到未付款单

## 下一步最有价值
1. 继续/扩大 SYS_KEY 字典（中则直接批量拉 kminfo）
2. 更大 epay 商户 key / 从 ttwl66 侧挖
3. 拿到任意已付用户取卡密码 → showOrder → 反推 SYS_KEY

## 产物
- 服务器: `/data/automation/results/xuxin66.top/deep6f_20260803_074220/`
- 脚本: `/data/automation/bin/xuxin66-deep6*`
