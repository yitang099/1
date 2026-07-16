# hmjf.lol 全盘扫描报告 (v8 full_disk)

- 时间: 2026-07-16
- 脚本: `hmjf_full_disk_scan.py`（跳板机 `/data/automation/bin/`）
- 结果: `/data/automation/results/hmjf.lol/full_disk_20260716/`
- 规模: **1108 请求**，10 阶段

---

## 扫描覆盖

| 阶段 | 内容 |
|------|------|
| [1] 子域枚举 | 50+ 子域 × http/https |
| [2] 根域路径 | robots/sitemap/.git/.env/phpmyadmin 等 |
| [3] shop 大词表 | 80+ 路径含 notify/backup/kami.php 等 |
| [4] 易支付网关 | `api.ttwl66.cn` 全端点 + pid=1003 探测 |
| [5] mod + 参数 | 35 mod × 7 参数变体 |
| [6] ajax 全 act | 60+ act × 5 POST 组合 |
| [7] HTTP 方法 | install.lock/ajax/getshop 等 7 方法 |
| [8] 未授权终检 | getcount/chat/install/cron 等 |
| [9] 端口扫描 | 21/22/80/443/3306/6379/8080 等 |
| [10] 汇总 | discovered 去重 |

---

## 漏洞汇总（按严重度）

### Critical

| 漏洞 | 复现 | v8 状态 |
|------|------|---------|
| **install 可重装** | `GET /shop/install/` → 提示删 lock | ✅ 复现 |
| ~~install.lock DELETE~~ | nginx 405 | ❌ 未复现 |

### High

| 漏洞 | 说明 | v8 状态 |
|------|------|---------|
| **install.lock 可下载** | 内容「安装锁」 | ✅ 复现 |
| **getcount 经营泄露** | orders=**13385**、GMV≈**437.35万**、未授权 | ✅ 复现（+2 单） |
| **客服 send 未授权** | 前序 v4/v7 已确认 | 本轮回测未单独标红 |
| **submit 订单枚举** | trade_no → epay sign | 前序已确认 |

### Medium（ajax 未授权，v8 二次确认）

| act | 响应 |
|-----|------|
| `getcount` | `code:0` + orders/money 全量 |
| `getclass` | 8329B 分类树 |
| `gettoolnew` | 5151B 商品+库存 |
| `cart_info` / `cart_list` | 无需登录 |
| `getleftcount` / `checklogin` | 未授权可访问 |
| `toollogs.php` | 公开上架日志 |

### Info

| 发现 | 说明 |
|------|------|
| 易支付 `api.ttwl66.cn/admin/` | 管理后台登录页暴露 |
| 易支付 pid=1003 | `order/query/settle` → 「商户密钥错误」（pid 存在） |
| 端口 | 仅 **80/443** 开放 |
| 子域 | **无存活**子域（shop/api/pay/admin 等全超时或无效） |

---

## 卡密 / 库存相关（重点）

| 测试 | 结果 |
|------|------|
| `ajax act=kami/kmquery/kmexport/downkm/sendkm/stockkm` | act **存在**，全部 **CSRF token 验证失败** |
| `ajax act=order` + skey | 「验证失败」— skey 算法未破解 |
| `ajax act=query` + trade_no | 未付款单返回空，无 kminfo |
| 全盘词表 `kami.php/card.php/export.php` 等 | 404 或跳转 |
| **kminfo 泄露** | ❌ **未发现** |

结论：卡密导出类接口在代码层存在，但 CSRF + skey 双重保护，**旁路未通**。

---

## 新发现端点（25 个 discovered）

### shop 侧

| 路径 | 大小 | 备注 |
|------|------|------|
| `toollogs.php` | 7172 | 公开 |
| `install/` | 114 | 可重装 |
| `user/login.php` 等 | 4-7K | 开放注册 |
| `other/submit.php` | 835 | 订单枚举入口 |
| `other/qqpay.php` | 63 | 存在 |
| `other/wxpay_notify.php` | 93 | 验签：签名错误 |
| `other/qqpay_notify.php` | 82 | 验签：签名失败 |
| `assets/faka/js/faka.js` | 44817 | 前端逻辑 |

### 易支付网关

| 路径 | 响应 |
|------|------|
| `/` | 首页 9390B |
| `/api.php?act=order/query/settle` | 商户ID不存在（无 pid） |
| `/submit.php` | 未配置商户 |
| `/admin/` | 登录页 |
| `/user/` | 跳转 login.php |

### mod 大页面

| mod | 大小 | 说明 |
|-----|------|------|
| `?mod=so` | 259KB | 站内搜索页 |
| `?mod=fenlei` | 38KB | 分类页 |
| `?mod=cart` | 29KB | 购物车 |
| `?mod=query` | 32KB | 查单页 |

---

## 旁路测试 — 全部未通

| 类别 | 结果 |
|------|------|
| 子域接管 / 隐藏后台 | 无存活子域 |
| .git / .env / backup.zip | 404 |
| cron.php?key=* | 无效 |
| epay notify 伪造到账 | 验签失败 |
| ajax kami/export 无 CSRF | CSRF 拦截 |
| skey 伪造 order | 验证失败 |
| install.lock DELETE | nginx 405 |
| 根域敏感文件 | 无泄露 |

---

## 与历史轮次对比

| 轮次 | 请求 | 新漏洞 |
|------|------|--------|
| v4 other | ~200 | chat send、install |
| v5 crit | ~400 | 无新 Critical |
| v6 full | 1679 | notify 端点 |
| v7 exhaust | 881 | PHPSESSID/CSP |
| **v8 full_disk** | **1108** | **无新可利用漏洞**；确认 epay admin 暴露、卡密 act 存在但 CSRF 保护 |

---

## 卡密挖掘后台（并行）

| 任务 | 进度 | 命中 |
|------|------|------|
| `paid_random_sample` | ~22500/100000 | 0 |
| `paid_full_suffix` | 20260716 02-06 点 | 0 |

---

## 建议后续

1. **卡密**：继续随机采样至 100 万；或撞易支付商户 key → 伪造 notify 触发发卡
2. **install.lock**：尝试备份恢复/上传旁路删 lock（破坏性，需谨慎）
3. **epay admin**：弱口令 / 已知彩虹默认口令（低概率）
4. **HK 报告同步** `103.185.249.13`（待做）
