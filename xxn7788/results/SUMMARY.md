# xxn7788.top/shop 侦察结果（深挖续）

## 结论
彩虹发卡「小仙女7788」，与 **xuxin66 同 IP / 同 yxts=276**。  
**卡密仍未拿到**。本轮新确认：订单查询接口整站 500、支付通道实装异常、多组密钥预言机、Geetest 可解。

## 站点画像
| 项 | 值 |
|----|----|
| getcount | orders≈2280 / money≈44.5万 / site=32 / gift=null |
| TG | `@xxn778` / `@yiyi778yiyi` / bot `@xxnsmjqrbot` |
| USDT 地址 | `TP6K9oAPhEZhjQD7eUTGFJqXsoentS6y1o` |
| 支付旗标 | qqpay✅ usdt✅；实装：qqpay=`MCHID_NOT_EXIST`，usdt submit=`该支付方式已关闭` |

## 本轮新发现
1. **`ajax.php?act=query` 全变体 HTTP 500**（空 body）  
   - 源码上 `type=1`+17位 tradeno 本可无 cookiesid 返回 `skey`  
   - 线上查询挂掉 → **无法用自建未付款单离线撞 SYS_KEY**
2. **支付实装异常**  
   - qqpay：`MCHID_NOT_EXIST`  
   - USDT 插件：submit 提示已关闭（旗标仍开，疑似改走公告静态地址人工确认）
3. **预言机扩展**  
   - `act=token&key=` → `Invalid key`  
   - `cron.php?key=` → `监控密钥不正确`  
   - `card_check` → `此卡密不存在`  
   - 分站 `user/pass`（goodslist/search）→ `用户名或密码不正确`（弱口令短喷未中）
4. **Geetest / 注册**  
   - `gt=a1017fd4951689c5d20317c165c1c318`；`ajax.php?act=captcha` 可取 challenge  
   - 注册必须带 `reg.php` 的 `hashsalt`（缺则「请刷新页面重试」）  
   - 2Captcha 能出解，但提交 `reguser` 仍「验证失败，请重新验证」（疑似 clientip 与 pre_process 绑定）  
   - 把青果代理交给 2Captcha → `ERROR_CAPTCHA_UNSOLVABLE`
5. **hashsalt 下单仍通**  
   - 新未付款单：`20260803103955319` / input=`kami103954` / tid=524  
6. **invite / gift**  
   - gift 关闭；invite_query 可用但无数据

## 仍在跑
| 任务 | 目标 |
|------|------|
| deep4 | SYS_KEY online spray（`act=order` id≈2277） |
| deep5 | cron key + input spray + 登录面 |
| deep6 | card_check + 分站弱口令 |
| login2 | 2Captcha Geetest 注册/登录 |

## 卡密路径阻塞点
- query 500 → 拿不到 skey → 难离线 SYS_KEY  
- 支付插件不可用 → 难走正规付款拿卡  
- API/cron/SYS_KEY/分站口令喷洒暂无命中  

## 下一步优先
1. 等 2Captcha 登录成功 → `payrmb`/会员单查询/充值面  
2. 稳定 SYS_KEY / cron / apikey 喷洒（降空响应）  
3. 扩大分站凭据与 card_check 字典  
4. 勿再浪费：getshop「未付款」枚举、qd93 子串、假 TN 存在性判断
