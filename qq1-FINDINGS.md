# qq1.lol 深挖报告

**目标**: https://qq1.lol (布衣 QQ 自动发卡)
**时间**: 2026-07-20
**IP**: 45.158.21.213, 103.43.11.95 (CDN)
**技术栈**: PHP + nginx + Geetest 验证码 + 彩虹/发卡系统

## 运营信息
- 运营者: 布衣 (@buyi, @buyiq, @qqkqq)
- Telegram 频道: @QQKZC, @qqkqq
- 关联站点: http://ka1.one (商品分类中引用, 当前不可达)
- 商品类型: QQ账号灰色市场 (国卡、假绑、老号等)

## 已发现入口

| 路径 | 状态 | 说明 |
|------|------|------|
| `/` | 200 | 商品首页 |
| `/user/login.php` | 200 | 用户登录 (Geetest) |
| `/user/reg.php` | 200 | 用户注册 (Geetest) |
| `/user/recharge.php` | 200 | 充值 |
| `/user/findpwd.php` | 200 | 找回密码 |
| `/user/connect.php` | 200 | 第三方登录 (QQ/微信/微博) |
| **`/sup/login.php`** | 200 | **供货商后台登录** (Geetest) |
| `/sup/reg.php` | 200 | 供货商注册 (已关闭) |
| `/sup/findpwd.php` | 200 | 供货商找回密码 |
| `/ajax.php` | 200 | 主站 AJAX API |
| `/api.php` | 200 | API 入口 `{"code":-5,"msg":"No Act!"}` |
| `/sup/ajax.php` | 200 | 供货商 AJAX (仅 login 有效) |
| `/install/` | 200 | 安装程序 (install.lock 存在) |
| `/install/install.lock` | 200 | **安装锁文件可读** (内容: "安装锁") |
| `/cron.php` | 200 | 定时任务 (需监控密钥) |
| `/toollogs.php` | 200 | 上架日志 (当前无记录) |
| `/other/submit.php` | 200 | 支付跳转 (需 type 参数) |

## 未授权信息泄露 (已确认)

### 1. ajax.php?act=getcount — 经营数据泄露
```json
{
  "code": 0,
  "yxts": 262,           // 运行天数
  "orders": "25915",     // 总订单
  "orders1": "25904",    // 已完成
  "orders2": "13",       // 待处理
  "money": 15735178.79,  // 总流水 ~1573万
  "money1": 2298,        // 今日流水
  "site": "478"          // 站点数
}
```
**无需登录，仅需 PHPSESSID + mysid cookie**

### 2. ajax.php?act=getclass — 商品分类
返回完整分类列表 (一手供货专区、包资料辅助、ka1.one 国卡卡位等)

### 3. ajax.php?act=gettoolnew — 商品目录
返回全部在售商品 (当前 9 个)，含 tid/cid/价格/名称

### 4. ajax.php?act=checklogin — 登录状态
返回 `{"code":0}` 无需认证

### 5. ajax.php?act=cart_list — 购物车
返回站点名称等

## 安全测试结果

### 订单查询
- `/?mod=query&data=<订单号>` — 无订单号枚举，需知道订单号或联系方式
- `ajax.php?act=order` — 需 `id` + `skey`，错误 skey 返回 `验证失败`
- `ajax.php?act=changepwd` — 需 CSRF token + id + skey

### SQL 注入
- 订单查询 GET 参数 — 无明显注入 (WAF/过滤)
- 用户登录 POST — 特殊字符触发 WAF 返回 HTML 拦截页
- ajax/query — HTTP 500 (异常但未利用)

### 后台
- `/admin/` — 404
- `/fenzhan/`, `/shequ/` — 404
- **`/sup/`** — 供货商后台 (最有价值突破点)
- 供货商注册已关闭 (`sup/reg.php` → alert 暂不开放)
- 登录需 Geetest 滑动验证 (captcha_type=1)

### 安装程序
- `install/install.lock` 存在且**可直接读取**
- 删除 lock 文件可能允许重装 (未测试，风险操作)

### cron.php
- 所有测试密钥均返回 `监控密钥不正确`

## ajax.php 完整 action 列表

**无需 CSRF (noCsrfActions)**:
getcount, getclass, gettool, gettoolnew, getleftcount, checklogin,
getshuoshuo, getshareid, gift_start, query, order, cart_info, cart_list, captcha

**需 CSRF**:
login, reg, userinfo, pay, notify, upload, config, getorder, orderlist,
getuser, recharge, withdraw, admin, siteinfo, getconfig, getsite, getmoney,
changepwd, apply_refund

## 额外功能模块 (mod 参数)
- `?mod=fenlei` — 商品分类
- `?mod=query` — 订单查询
- `?mod=cutshop` — 砍价商城
- `?mod=groupshop` — 团购
- `?mod=seckill` — 秒杀
- `?mod=coupon` — 优惠券
- `?mod=so` — 商品搜索

## 突破建议 (优先级)

1. **供货商后台 `/sup/login.php`** — Geetest + 弱口令爆破 (需解决验证码)
2. **用户注册 + 充值漏洞** — 注册需 Geetest，充值页待测
3. **订单 skey 算法** — 若 skey 可预测可读取任意订单卡密
4. **install.lock 删除重装** — 高风险，可能重置管理员
5. **cron.php 密钥** — 常见弱密钥字典
6. **关联资产** — ka1.one, 运营者其他站点 (HK 上有 fffzz.lol, htqq.lol 等)

## 2026-07-20 攻击进展

### P1: 供货商后台 `/sup/`
- Geetest 滑动验证必须完成，`captcha_type=1`
- 无 captcha 时返回 `请先完成验证`；空字段返回 `验证失败，请重新验证`
- 弱口令 spray (10用户×31密码) 全部被 captcha 拦截，无密码错误回显
- `sup/reg.php` 已关闭注册
- `sup/qrlogin.php` 可获取 QQ 二维码 (找回密码流程)
- Selenium 爆破脚本: `qq1-sup-brute.py`

### P2: 订单 skey
- `hashsalt` 为动态 JSFuck 混淆值，每页不同，非固定密钥
- 常见 md5 模式 (id+salt) 未命中
- **突破**: `ajax.php?act=pay` 可无 Geetest 创建订单 (有库存商品)
  - 测试订单: `trade_no=20260720145603146` (tid=131, 99元)
- 未付款订单无法通过 query 查询，`ajax.php?act=order` 需正确 skey
- skey 在付款完成后才在 query 页 `showOrder(id,skey)` 中暴露

### P3: findpwd
- `sup/findpwd.php` 使用 QQ 扫码找回 (`qrlogin.js`)
- `sup/qrlogin.php?do=getqrpic` 无需认证可获取二维码

### P4: cron.php / 支付回调
- cron 常见密钥字典未命中
- 支付回调端点存在: `epay_notify.php`, `alipay_notify.php`, `wxpay_notify.php`, `qqpay_notify.php`
- `qqpay_notify.php` 返回 `签名失败` (有签名校验)
- `epay_notify.php` 返回 `error`
- 支付跳转: `other/submit.php?type=alipay&orderid=<trade_no>` → `alipay.php`

## 2026-07-20 第四轮深挖 (deep4/infra)

### 新探测方向与结果

| 方向 | 结果 |
|------|------|
| 403 bypass (config/includes/备份) | 全部 403/404，无读取 |
| getshuoshuo (uin+hashsalt) | **HTTP 500** 崩溃（非空 QQ 号），潜在后端 bug，未出数据 |
| getrizhi / share_invite / SharePoster | 服务端 `No Act` 已禁用 |
| reg/recharge ajax | `reg` 无此 act；recharge 需登录 |
| query WAF bypass | 多种编码均空响应/拦截 |
| trade_no/getshop 窗口爆破 | 近 3h 无已付款泄漏 |
| upload (php/jpg) | 无成功上传 |
| 关联站 fffzz/hmjf/htqq/kln166 | 全部 404 下线 |
| 源站端口 8080/8888/3306/6379 | TCP 开放但服务 reset/超时，疑似蜜罐/防火墙 |
| sup qrlogin 轮询 | `getqrpic` 可用，`qrlogin` 返回 saveOK=2（待扫码） |
| Wayback/CT 子域 | 仅首页，无历史泄漏 |

### 技术修正
- **pay 必填字段**: `inputvalue`（飞机号），非 `contact`；配合假 Geetest 可下单
- **getshuoshuo 参数**: `uin` 非 `qq`；`hashsalt` 必须来自当前页
- 测试订单: `trade_no=20260720222507453`（未付款）

### 仍值得推进的方向
1. **sup QR 登录劫持** — 需实时轮询 qrsig（社交/钓鱼向量）
2. **运营者定向 API 密钥** — 缩小字典重跑 `%61pi.php`
3. **2Captcha 充值** — 恢复 sup 后台弱口令爆破
4. **epay 回调伪造** — HK 连通性恢复后重试

## 2026-07-20 getshuoshuo 专项深挖 (round 1-3)

### 结论：**非 SQLi，是后端 QQ 说说 API 崩溃**

| uin 值 | HTTP | 响应 |
|--------|------|------|
| `""`, `"0"`, `" 0"`, `"0 "`, `"\t0"` | 200 | `{"code":-5,"msg":"QQ号不能为空"}` |
| `"00"`, `"1"`, `"10000"`, `"0.0"`, `"+0"` 等 | **500** | 空 body |
| SQLi payload (`'`, `SLEEP`, `UNION`) | 000/500 | WAF 断连或崩溃，**无时间盲注** |

### 关键发现
1. **hashsalt 不校验**：`uin=0` 时任意/空 hashsalt 均返回 200
2. **HPP**：`uin=10000&uin=0` → 取最后一个，仍返回空 QQ 错误；`uin=0&uin=10000` → 500
3. **根因**：非零 uin 会调用 QQ 说说接口，失败时 PHP 未捕获异常直接 500
4. **不可利用取数**：无法通过类型混淆/HPP/数组注入让有效 QQ 返回说说数据

### 脚本
- `qq1-shuoshuo-fuzz.py` — 跳板机+QG 代理自动化 fuzz
- 结果：`results/qq1.lol/shuoshuo_report.json`, `shuoshuo_round2.log`

## szbx1.cn 进度 (附带)
- rockyou w0 (part_aa): **已完成**, 2 hits
- rockyou w1 (part_bc): ~91% (8.7M/9.5M), 0 hits
- admin weak dict brute: 运行中 (1559词已完成, 0 hit)
