# KLN166.top/shop 侦察报告

**目标**: https://KLN166.top/shop/  
**测试时间**: 2026-07-12  
**站点品牌**: 库里南 一手QQ号商  
**站点类型**: PHP 自动发卡网（彩虹/同类系统 + `assets/faka` 定制）  
**说明**: 非破坏性初探

---

## 一、站点概况

| 项目 | 信息 |
|------|------|
| 域名 | KLN166.top |
| IP | 103.43.11.241 / 156.238.239.16 / 156.238.239.86 |
| 客服 | Telegram `@abbb` |
| 上货频道 | https://t.me/+0VYxNwihtmIxZWY9 |
| 技术栈 | PHP + Session (`PHPSESSID`, `mysid`, `server_name_session`) |
| 支付 | 微信/支付宝/USDT（费率见公告） |

**与 tianyu9080.top 对比**:
- 同网段 IP（`103.43.11.x`），同一套发卡系统皮肤（`assets/faka/css/css7.css`）
- 路径结构一致：`/shop/`、`/shop/user/`、`/shop/sup/`、`/shop/install/`
- **关键差异**：本站 `ajax.php` 全接口返回 `403`，经营数据 API 已加固；tianyu9080 仅需 Referer 即可拉取 `getcount`/`gettool`

---

## 二、商品与库存（首页 HTML 可见）

首页服务端渲染了商品列表，**无需 API 即可看到价格与库存**。

| 指标 | 数值 |
|------|------|
| 可见商品 | **36** |
| 分类 | **12** |
| 有数字库存的商品 | 12 |
| 可见库存总量 | **905** 件 |
| 库存估值（stock×price） | **约 128 万元**（以余额充值卡密为主） |

**库存 TOP5**:

| tid | 库存 | 价格 | 商品 |
|-----|------|------|------|
| 34 | 338 | 500元 | 网站余额500元充值卡密 |
| 33 | 105 | 300元 | 网站余额300元充值卡密 |
| 32 | 94 | 100元 | 网站余额100元充值卡密 |
| 38 | 82 | 2000元 | 网站余额2000元充值卡密 |
| 39 | 63 | 2500元 | 网站余额2500元充值卡密 |

**主营品类**: 国卡/三网 QQ 老号、虚卡重启换绑号、扫码号、网站余额卡密、TRX 能量租赁（分类 cid=33/34）

---

## 三、已确认问题

### 1. 客服接口未授权发消息（低危）

```
GET  /shop/user/ajax_chat.php?act=get   → {"code":0,"session_id":"..."}
POST /shop/user/ajax_chat.php?act=send  → {"code":0,"msg":"发送成功"}
```

无需登录，伪造 `session_id` 亦可发送。

### 2. 安装目录残留（低危）

`/shop/install/` → 200，提示删除 `install.lock` 可重装。

### 3. 供货商后台暴露（信息）

`/shop/sup/login.php` → 200，标题「供货商登录」。

### 4. 定时任务入口暴露（信息）

`/shop/cron.php` → `监控密钥不正确`

### 5. 首页商品/库存半公开（信息 → 低危）

虽 `ajax.php` 已 403，但首页 HTML 直接渲染 **36 个商品的价格与库存**，竞争对手仍可爬取。

---

## 四、已加固项（对比 tianyu9080）

| 接口 | KLN166 | tianyu9080 |
|------|--------|------------|
| `ajax.php?act=getcount` | **403** | 200，泄露订单/交易额 |
| `ajax.php?act=getclass` | **403** | 200，19 个分类 |
| `ajax.php?act=gettool` | **403** | 200，全量商品+库存 |
| `ajax.php?act=captcha` | **403** | 200 |
| 搜索 SQLi | WAF 拦截 | WAF 拦截 |

**结论**: 本站对 `ajax.php` 做了更严格的 Session/鉴权，**经营数据 API 泄露问题已修复**；但商品信息仍可通过首页 HTML 获取。

---

## 五、其他探测结果

| 测试项 | 结果 |
|--------|------|
| `other/epay_notify.php` | `error`（伪造回调被拒） |
| `other/notify.php` | `No Act` |
| `other/getshop.php?trade_no=1` | `未付款`（与 tianyu9080 相同，不可可靠枚举） |
| `config.php` / `.git` | 403 |
| `?mod=query&data=` | 测试手机号无 `showOrder` 链接 |
| `?mod=so&kw=` SQLi | WAF 拦截 |

---

## 六、路径结构

```
/shop/                    前台首页（商品列表）
/shop/?mod=buy&cid=X&tid=Y   购买页
/shop/?mod=query          订单查询
/shop/user/login.php      会员登录
/shop/user/reg.php        会员注册
/shop/sup/login.php       供货商登录
/shop/install/            安装入口（残留）
/shop/cron.php            定时任务
/shop/other/epay_notify.php  支付回调
```

---

## 七、产出文件

```
/workspace/kln166-recon/
├── security_report.md           # 本报告
├── index.html                   # 首页快照
├── buy.html                     # 购买页快照
└── deep/
    └── products_from_html.json  # 从 HTML 解析的 36 个商品
```

---

## 八、后续可深挖

- [ ] 全分类页面爬取（`?cid=X`）补全隐藏商品
- [ ] 对比 tianyu9080 是否同一后台/数据库
- [ ] 支付回调签名分析
- [ ] 会员注册/登录接口边界测试
