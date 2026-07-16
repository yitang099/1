# qq8.one 全盘扫描报告

- 时间: 2026-07-16
- 目标: https://qq8.one（熊猫QQ 自动发卡，彩虹同源）
- 脚本: `qq8_full_disk_scan.py`
- 结果: `/data/automation/results/qq8.one/full_disk_20260716/`
- 规模: **1322 请求**，12 阶段

---

## 站点概况

| 项目 | 数据 |
|------|------|
| 站名 | 熊猫QQ 飞机@aiqq 四字id |
| 程序 | 彩虹发卡 `faka`（与 hmjf.lol 同源） |
| 部署 | 根域（无 `/shop` 子路径） |
| 订单量 | **30,464**（扫描时 +1） |
| GMV | **≈1490.6 万** |
| 运营 | 258 天，site_id=542 |
| CDN | 有，安全头较全（HSTS 等） |
| 易支付 | 同 hmjf，`api.ttwl66.cn` |

---

## 扫描覆盖

| 阶段 | 内容 |
|------|------|
| [0] 会话预热 | 访问首页拿 Cookie |
| [1] 子域 | 50+ 子域 → **无存活** |
| [2] 根路径 | install/.git/.env 等 |
| [3] 目录词表 | 80+ faka 常见路径 |
| [4] 易支付 | ttwl66.cn 全端点 + pid 探测 |
| [5] mod 参数 | 35 mod × 7 变体 |
| [6] ajax act | 60+ act × 5 POST |
| [7] 冷/热对比 | 无 Referer vs 有 Referer |
| [8] HTTP 方法 | install.lock/chat/getcount |
| [9] 未授权终检 | getcount/chat/install |
| [10] 订单枚举 | 200 次随机 trade_no 采样 |
| [11] 端口 | 仅 80/443 |

---

## 漏洞汇总

### Critical

| 漏洞 | 复现 | 状态 |
|------|------|------|
| **install 可重装** | `GET /install/` → 提示删 lock | ✅ 确认 |
| ~~install.lock DELETE~~ | nginx 405 | ❌ |

### High

| 漏洞 | 说明 | 状态 |
|------|------|------|
| **install.lock 可下载** | 返回「安装锁」 | ✅ 确认 |
| **getcount 经营泄露** | 带 Cookie+Referer 即返回 orders/GMV | ✅ 1322 次扫描复现 |
| **getclass/gettoolnew 未授权** | 商品分类+库存全量（会话内） | ✅ |
| **客服 send 未授权** | `POST user/ajax_chat.php?act=send` → 发送成功 | ✅ 手工复现 |
| **submit 订单枚举** | 有效单跳转支付，无效返回「不存在」 | ✅ |
| **cart_info/cart_list** | 未登录可读 | ✅ |

### Medium

| 漏洞 | 说明 |
|------|------|
| Referer 伪防护 | 裸请求 ajax 返回 403；访问首页后同样泄露 |
| toollogs.php 公开 | 上架日志 |
| PHPSESSID 缺 HttpOnly | mysid 有 HttpOnly+Secure |
| 开放注册 | `/user/reg.php` 200 |

### Info

- 易支付 `api.ttwl66.cn/admin/` 后台暴露
- 子域无存活；端口仅 80/443
- notify 端点存在，验签未绕过

---

## 卡密 / 账号泄露（重点）

| 测试 | 结果 |
|------|------|
| `kami/kmquery/kmexport/downkm/sendkm/stock` | act 存在，**CSRF 拦截** |
| `order` + 伪造 skey | 「验证失败」 |
| `query` + trade_no | 未付款单无数据 |
| 200 次随机订单枚举 | **0 命中已付款单** |
| **kminfo / 账号明文** | ❌ **未发现** |

结论：QQ 账号类卡密与 hmjf 相同，导出接口有 CSRF + skey 保护，旁路未通。

---

## 与 hmjf.lol 对比

| 维度 | qq8.one | hmjf.lol |
|------|---------|----------|
| 体量 | 3万单 / 1490万 | 1.3万单 / 437万 |
| 裸 ajax | 403 | 直接 200 |
| 会话内 ajax | 同样泄露 | 同样泄露 |
| install 重装 | ✅ | ✅ |
| 客服 send | ✅ 未授权 | ✅ |
| 卡密 CSRF | ✅ 拦截 | ✅ |
| 安全头 | 更全 | 较弱 |

qq8.one 多了一层 Referer 门槛，**实质防护提升有限**。

---

## 旁路 — 全部未通

- 子域 / 备份文件 / .git / .env
- epay notify 伪造到账
- ajax 卡密导出无 CSRF
- skey 伪造 order
- cron.php 密钥
- 200 次订单随机采样

---

## 产出文件

- `scripts/qq8_full_disk_scan.py`
- `scripts/qq8_full_disk_results.json`
- `scripts/QQ8-FULL-DISK-REPORT.md`
