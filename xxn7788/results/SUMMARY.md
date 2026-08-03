# xxn7788.top/shop 侦察结果

## 结论
彩虹发卡站「小仙女7788」，与 **xuxin66.top 同 IP 集群**（`45.158.21.213` / `103.43.11.95`），运营天数同为 **yxts=276**，高度同源运营。  
**卡密未拿到**；已打通 hashsalt 下单与未授权商品/站点信息泄露。

## 站点画像
| 项 | 值 |
|----|----|
| 站名 | 小仙女7788 |
| 指纹 | `assets/faka/` 彩虹发卡 |
| getcount | orders=**2277**，paid=2277，money≈**44.16万**，site=32，gift=null |
| 客服 QQ | `123456`（占位） |
| TG | `@xxn778` / `@yiyi778yiyi` |
| USDT | `TP6K9oAPhEZhjQD7eUTGFJqXsoentS6y1o` |
| 支付 | qqpay✅ USDT✅ / alipay❌ wx❌ |
| 商品 | 92 个（QQ 扫码老号等），价约 ¥10–190 |

## 成功案列迁移
| 手法 | 结果 |
|------|------|
| qd93 子串 query | ❌ 无 showOrder |
| `%61pi.php?act=search` 未授权 | ❌ 需登录或 API key |
| `%61pi.php?act=tools&key=` | ✅ 密钥预言机可用（错 key 明确回错） |
| siteinfo / classlist / goodslist | ✅ **未授权可读** |

## 已验证攻击面
1. **未授权 API 信息泄露**：`%61pi.php?act=siteinfo|classlist|goodslist`
2. **hashsalt 下单**：`?mod=buy&tid=` → JS `csrf_token` + JSFuck `hashsalt` → `ajax.php?act=pay`
3. **测试未付款单**：`trade_no=20260803101139692`，取卡密码 `kami101138`，tid=524
4. API key 短字典喷洒暂无命中（进行中/可扩大）

## 与 xuxin66 对比
| | xuxin66 | xxn7788 |
|--|---------|---------|
| 订单规模 | ~11240 / 225万 | 2277 / 44万 |
| 同源 | 同 IP、同 yxts | 同 |
| API tools 预言机 | ✅ | ✅ |
| goodslist 未授权 | （此前未重点） | ✅ 确认 |
| 下单 | ✅ | ✅ |

## 下一步
1. 扩大 API key / SYS_KEY 字典（同集群可共用方法论）
2. 已付 trade_no：`query type=1` / 支付回跳路径
3. 支付侧：qqpay / USDT notify 伪造（需商户 key）
4. 用 2Captcha 打登录面

## 产物（HK）
- `/data/automation/results/xxn7788.top/`
