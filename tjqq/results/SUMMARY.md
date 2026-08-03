# tjqq.top 侦察结果

## 结论
**不是彩虹发卡**，而是 **YKFAKA（优卡自动发卡）** 站「天锦 / QQ号批发」。  
首页在售 Trade SKU 抽样库存均为 **0**；`Query_Km` 可未授权访问但已触发限流；**未拿到卡密**。

## 画像
| 项 | 值 |
|----|----|
| 标题 | 首页-QQ号批发 / 天锦QQ号码 |
| 指纹 | `meta author=YKFAKA`，页脚 `© 2026 YKFAKA` |
| IP | `104.129.28.115`（与 xxn7788 彩虹集群不同） |
| 栈 | nginx + ThinkPHP 风格路由 + layui/AmazeUI |
| TG | `@sa444` / 频道 `t.me/tj2299` |
| USDT | `TTdHuX5rEo8ur9HwWc8aYYKuHJgmWtfdEV` |
| 支付 | 商品页仅见 **USDT (`udpay`)** |

## 已确认攻击面
1. **未授权库存接口**：`GET /Get_Yk_KC.html?gid=` → `{"code":200,"msg":"获取成功","kucun":N}`  
2. **未授权查卡路径**：`/Query_Km/{id}`  
   - 无效：`无此订单记录`  
   - 刷多了：`查询失败次数过多,请1小时后再试`  
3. **下单**：`POST /Pay`（`paytype=udpay&gid&count&pass&__token__`）— 无库存时回 `库存不足`  
4. **查单页**：`/Query.html` 字段 `value`+`pass`，默认密码提示 **`Ykfaka999`**，需 `__token__` + Geetest  
5. **登录/注册**：`/User_Login.html` `/User_Reg.html`，缺校验回 `请求非法`

## 与历史批次
HK 上 `ykfaka_bypass_20260801.json` **已收录** `https://tjqq.top`，当时同样无卡密命中。

## 阻塞
- 首页 Trade（36/37/43/52/55/56/61/62 等）库存 0，难建未付款单继续打支付链  
- `Query_Km` 枚举触发 1 小时限流  
- 查单/登录有 Geetest

## 下一步
1. 换出口 IP 后再扫 `gid=1..N` 找非零库存，建单拿真实 orderid  
2. 有单后测 `Query_Km/{id}` / `R_YkPay/{id}` / 默认密 `Ykfaka999`  
3. 2Captcha 打登录/查单 Geetest  
4. 对照其他已破 YKFAKA 站的路径字典（`/Manage/*` 本站 404）
