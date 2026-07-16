# hmjf.lol 全类型漏洞穷尽扫描报告 (v7 exhaust)

- 时间: 2026-07-16
- 脚本: `hmjf_vuln_exhaust_v7.py`
- 结果: `/data/automation/results/hmjf.lol/vuln_exhaust_20260716/results.json`
- 规模: **881 请求**，**14 大类 / 60+ 子项**，一项不漏

---

## 扫描矩阵（全类型覆盖）

| 类型 | 测试量 | 结果 | 说明 |
|------|--------|------|------|
| **A. 信息泄露** | 54 路径 | 未发现新泄露 | config/.git/备份/phpinfo 均 403/404 |
| **B. XSS 反射** | 8 payload × 8 入口 | **WAF 全拦截** | so/query/buy/login 等 |
| **B. XSS 存储** | 6 payload → 客服 send | **WAF 拦截** | 危险字符过滤 |
| **B. SSTI** | `{{7*7}}` | **不存在** | 无模板注入 |
| **C. SQLi 报错** | 14 payload × 9 入口 | **不存在** | 无 SQL 报错回显 |
| **C. SQLi 盲注** | SLEEP(3) 等 | **不存在** | 响应时间 <3s |
| **C. SQLi 登录绕过** | 14 payload | **误报** | 页面含 script 非登录成功 |
| **D. SSRF** | 14 URL × 3 act | **不存在** | getshareid 需 hashsalt |
| **E. LFI/RFI** | 11 payload × 7 路径 | **不存在** | php://filter 等无效 |
| **F. 开放重定向** | 7 payload × 6 入口 | **不存在** | epay_return/login 等 |
| **G. CORS** | 4 Origin 预检 | **安全** | 无 ACAO 反射 |
| **G. CSP** | 响应头检查 | **缺失** | 无 Content-Security-Policy |
| **G. HSTS** | 响应头 | **已配置** | max-age=31536000 |
| **G. X-Frame-Options** | 响应头 | **SAMEORIGIN** | 防点击劫持 |
| **G. X-Content-Type-Options** | 响应头 | **需确认** | 部分响应未带 |
| **H. Cookie PHPSESSID** | 标志检查 | **缺 HttpOnly/Secure** | 会话劫持风险 |
| **H. Cookie mysid** | 标志检查 | **Secure+HttpOnly** | 正常 |
| **H. 用户枚举** | login/findpwd | **未发现差异** | |
| **H. 会话固定** | 登录前后对比 | **未确认** | |
| **I. 业务逻辑 HPP** | tid 重复/数组 | **不可利用** | CSRF/验证失败 |
| **I. JSON 支付** | application/json | **不可利用** | |
| **I. 负 ID / 超长参数** | order/query | **不可利用** | query 超长 → 403 |
| **J. CRLF 注入** | %0d%0a | **不存在** | |
| **J. Host 投毒** | Host/X-Forwarded-Host | **不存在** | |
| **K. NoSQL 注入** | $gt/$ne | **不存在** | |
| **K. 命令注入** | ;id\|$(id) | **不存在** | |
| **K. XXE** | wxpay_notify XML | **不存在** | |
| **L. 速率限制** | 客服 20 连发 | **弱限制** | 15s 内 9/20 成功 |
| **M. 支付回调伪造** | epay/wx/qq notify | **验签失败** | 无法绕过到账 |
| **N. 未授权接口** | 11 端点复测 | **确认泄露** | 见下表 |

---

## 确认漏洞（按类型归类）

### 严重 / 高（已知 + 本轮复测确认）

| 类型 | 漏洞 | 等级 |
|------|------|------|
| 重装/配置 | install 可重装 + install.lock 可下载 | **Critical** |
| 信息泄露 | getcount 经营数据（orders≈13383, GMV≈437万） | **High** |
| 信息泄露 | submit 订单枚举 + epay sign 泄露 | **High** |
| 认证绕过 | 客服 `ajax_chat.php?act=send` 未授权 | **High** |
| 信息泄露 | getclass/gettoolnew/cart/toollogs 未授权 | **Medium** |

### 本轮新确认（安全配置类）

| 类型 | 漏洞 | 等级 |
|------|------|------|
| 会话安全 | **PHPSESSID 缺少 HttpOnly + Secure** | **Medium** |
| 会话安全 | mysid 有 Secure+HttpOnly（正常） | 信息 |
| 安全头 | **无 CSP**（XSS 若绕过 WAF 影响更大） | **Low** |
| 可用性 | 客服 send 弱速率限制（9/20/15s） | **Low-Medium** |
| 支付 | wxpay_notify / qqpay_notify 存在但**验签** | 信息 |

---

## 误报（已手工排除）

| 扫描器报警 | 实际情况 |
|------------|----------|
| SQLi 登录绕过 ×14 | 登录页统一返回含 `script` 的 HTML，非成功登录 |
| SSTI ×3 | `{{7*7}}` 未在响应中算出 49 |
| 缺少 HSTS/XFO | 手工 `curl -I` 确认 **存在** |
| install.lock DELETE | nginx 405 |

---

## 全端点未授权复测（N 阶段）

| 端点 | 未授权可访问 | 敏感数据 |
|------|-------------|----------|
| `ajax.php?act=getcount` | 是 | **orders/money** |
| `ajax.php?act=getclass` | 是 | 全部分类 |
| `ajax.php?act=gettoolnew` | 是 | 商品+库存 |
| `ajax.php?act=getleftcount` | 是 | 计数 |
| `user/ajax_chat.php?act=get` | 是 | session_id |
| `user/ajax_chat.php?act=send` | 是 | 可发消息 |
| `toollogs.php` | 是 | 上架日志 |
| `install/install.lock` | 是 | 安装锁内容 |
| `install/` | 是 | 重装提示 |
| `cron.php` | 是 | 需 key |
| `?mod=cart` | 是 | 购物车页 |

---

## 支付回调全类型（M 阶段）

| 回调路径 | 存在 | 伪造到账 |
|----------|------|----------|
| `other/epay_notify.php` | 是 | 否（error） |
| `other/wxpay_notify.php` | 是 | 否（签名错误） |
| `other/alipay_notify.php` | 是 | 否（空响应） |
| `other/qqpay_notify.php` | **新发现** | 否（签名失败） |
| `other/notify.php` | 是 | No Act |

---

## 未测试 / 不适用

| 类型 | 原因 |
|------|------|
| HTTP 请求走私 | 需特殊隧道环境 |
| WebSocket | 站点未使用 |
| GraphQL | 无接口 |
| JWT/OAuth | 无 |
| 子域接管 | 仅测主域 hmjf.lol/shop |
| 移动客户端 | 无 APK |
| 社会工程 | 超出范围 |

---

## 总结

**按漏洞类型穷尽扫完后：**

- **无新的 Critical 可利用链**（无 SQLi/XSS/SSRF/LFI/XXE/RCE/支付绕过）
- **新确认安全配置问题**：PHPSESSID 缺 HttpOnly/Secure、无 CSP、客服弱限速
- **最严重仍是**：install 重装链、getcount/submit 泄露、客服未授权 send
- **WAF 有效拦截**：XSS、部分 SQLi、危险字符

---

## 修复建议（按优先级）

1. **删除或限制 `/install/`** 对外访问
2. **getcount / getclass 等** 加认证或下线
3. **客服 send** 加登录 + 验证码 + 速率限制
4. **PHPSESSID** 设置 `HttpOnly; Secure; SameSite=Lax`
5. **添加 CSP** 头降低 XSS 风险
6. **submit** 订单存在性检查改为统一错误信息

---

## 复现命令

```bash
# Cookie 问题
curl -sI 'https://hmjf.lol/shop/' | grep -i set-cookie

# CSP 缺失
curl -sI 'https://hmjf.lol/shop/' | grep -i content-security

# 客服速率
for i in $(seq 1 20); do curl -s -X POST 'https://hmjf.lol/shop/user/ajax_chat.php?act=send' -d "content=test$i"; done

# qqpay 回调
curl -s -X POST 'https://hmjf.lol/shop/other/qqpay_notify.php' -d 'out_trade_no=TEST&trade_state=SUCCESS'
```
