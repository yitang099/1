# hmjf.lol 旁路漏洞完整扫描报告 (v6 full)

- 时间: 2026-07-16
- 脚本: `hmjf_vuln_full_scan.py`（跳板机 `/data/automation/bin/`）
- 结果: `/data/automation/results/hmjf.lol/vuln_full_20260716/results.json`
- 规模: **1679 请求**，10 个阶段全覆盖

---

## 扫描覆盖范围

| 阶段 | 内容 | 数量级 |
|------|------|--------|
| [1] path brute | 路径字典 + 备份后缀 + rainbow 常见路径 | ~120 路径 |
| [2] ajax acts | 60+ act × 7 种 POST/GET 组合 | ~420 |
| [3] api + user/ajax | api.php 25 act；user/ajax.php 15 act | ~200 |
| [4] mod fuzz | 40+ mod × 6 参数变体 | ~240 |
| [5] notify bypass | 10 条 notify 路径 × epay 参数伪造 | ~80 |
| [6] HTTP methods | install.lock DELETE/PUT/PATCH | ~15 |
| [7] cron keys | 500 组密钥 | 500 |
| [8] chat bypass | 7 act × 多种 post | ~50 |
| [9] act 编码旁路 | 大小写/空字节等 | ~10 |
| [10] 头旁路 | X-Forwarded-For / X-Original-URL 等 | ~14 |

另手工补扫：`other/*.php` 全目录、支付类型 submit、wxpay_notify、mod=cart/fenlei。

---

## 确认漏洞（按严重度）

### Critical

| 漏洞 | 说明 | 复现 |
|------|------|------|
| **install 可重装** | `/shop/install/`、`install/index.php` 对外可访问，提示删 lock 重装 | `curl https://hmjf.lol/shop/install/` |
| ~~install.lock 可 DELETE~~ | **误报**：实测 nginx 返回 `405`，lock 仍在 | `curl -X DELETE` → 405 |

### High

| 漏洞 | 说明 |
|------|------|
| **install.lock 可下载** | `GET /shop/install/install.lock` → 「安装锁」 |
| **客服 send 未授权** | `POST user/ajax_chat.php?act=send` → 发送成功 |
| **getcount 经营泄露** | 全扫描复现：orders=**13383**、GMV≈**437万**、未授权 |
| **submit 订单枚举+sign** | 有效 trade_no 泄露 epay 跳转 URL |

### Medium

| 漏洞 | 说明 |
|------|------|
| 客服 get 未授权 | 返回 session_id |
| cart_info / cart_list 未授权 | 无需 CSRF |
| getclass / gettoolnew 未授权 | 分类+商品库存 |
| toollogs 公开 | 上架日志 |
| mod=cart 购物车页 | 可访问，ajax 下单仍受 CSRF/极验保护 |
| ~~getcount 头旁路~~ | **误报**：getcount 本就不要求特殊头，任何头都能访问 |

---

## 新发现端点（无直接利用）

| 路径 | 响应 | 备注 |
|------|------|------|
| `other/wxpay_notify.php` | XML `签名错误` | 微信回调存在，**有验签** |
| `other/alipay_notify.php` | 空体 200 | 存在，未绕过 |
| `other/wxpay.php` / `alipay.php` | 接口未开启 | |
| `other/qqpay.php` | 订单不存在 | 可枚举 |
| `other/notify.php` | No Act | |
| `api.php` | `No Act!` | 全 act  fuzz 无数据 |
| `user/ajax.php` | login 空参报错；recharge 需登录 | |
| `?mod=cart` | 购物车页 200 | |
| `?mod=fenlei` | 分类页 200 | |
| `ajax cart_add` / `submit` | **No Act** | 本站未启用该 act |

---

## 旁路测试 — 全部未通

| 类别 | 测试 | 结果 |
|------|------|------|
| 支付 | price/num 篡改、payrmb、无 hashsalt | CSRF/验证失败/极验 |
| notify | epay/wxpay/alipay/qqpay 伪造到账 | error / 签名错误 |
| SSRF | getshareid 127.0.0.1 | 验证失败 |
| IDOR | chat session_id、ajax order 弱 skey | 无效 |
| 认证 | user/record 未登录读数据 | 无数据泄露 |
| 文件 | download.php、config 备份后缀 | 404/403 |
| 方法 | DELETE install.lock | **405** |
| cron | 500 密钥 | 未命中 |
| admin | 头旁路 X-Original-URL | 无效 |
| act 编码 | ORDER、pay%00 | 无效 |
| SQLi/LFI | mod/query/download | WAF/404 |

---

## 与历史扫描对比

| 项目 | v4/v5 | v6 full |
|------|-------|---------|
| 请求数 | ~200-400 | **1679** |
| ajax act 覆盖 | 部分 | **60+ 全表** |
| notify 旁路 | epay_notify 仅 | **10 条路径** |
| other/ 目录 | 部分 | **全文件名枚举** |
| cron | 20-30 key | **500 key** |
| 新 Critical | 无 | 无（DELETE 误报已排除） |

---

## 结论

**完整扫完后，旁路未发现比 `install` 重装链更严重且可直接利用的新漏洞。**

实战优先级仍为：
1. **install 重装**（需写权限删 lock — 本轮未发现 DELETE/PUT 旁路）
2. **易支付 sign 撞库** → 伪造 notify
3. **getcount + submit 枚举** → 情报收集
4. **客服未授权** → 骚扰/社工

---

## 监控命令

```bash
# 扫描日志
tail -f /data/automation/results/hmjf.lol/vuln_full_20260716/run.log

# 结果 JSON
cat /data/automation/results/hmjf.lol/vuln_full_20260716/results.json | python3 -m json.tool | less
```
