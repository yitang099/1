# hmjf.lol 严重漏洞深挖补充报告 (v5)

- 时间: 2026-07-16
- 范围: 支付逻辑、epay 伪造、SSRF、认证绕过、IDOR、重装链、彩虹特有接口
- 脚本: `hmjf_vuln_crit_v5.py`、`pay_probe.py`、`ssrf_probe.py`、`cancel_probe.py`、`user_abuse_probe.py`

---

## 结论：**未发现比 install 重装更严重的可利用漏洞**

本轮在已有发现基础上做了针对性加深，**未拿到新的 Critical 级可利用链**（价格篡改、epay 伪造到账、SSRF 读内网、未授权取消他人订单等均失败）。

---

## 当前最严重漏洞（按实战影响排序）

### 1. install 重装链（Critical）— 仍为顶部风险

- `/shop/install/` 对外可访问
- 提示删除 `install/install.lock` 即可重装
- lock 文件可下载（9 字节「安装锁」）
- `POST install/index.php` 仍被锁拦截，**但若有任意写权限删 lock → 全站接管**（SYS_KEY、数据库、管理员）

### 2. getcount 经营数据泄露（High/Critical 商业影响）

- `POST ajax.php?act=getcount` 无认证
- 实时：orders=13377、已付款 13330、GMV≈437万、运行 258 天

### 3. submit 订单枚举 + 易支付 sign 泄露（High）

- 17 位 trade_no 可枚举存在性
- 有效单返回完整 epay URL（pid=1003、sign、money）

### 4. 客服 API 未授权（High/Medium）

- `act=send` 无登录即发消息（已复测确认）
- `act=get` 返回 session_id（**非 IDOR**：传 `session_id=68` 仍分配新会话 73，无法读他人记录）

---

## 本轮加深测试 — 未通项

| 测试项 | 结果 |
|--------|------|
| 价格篡改 `pay` + CSRF + hashsalt=256 | `验证失败`（需页面会话 + 极验/验证码） |
| 余额支付 `pay_type=rmb` | 同上，注册用户余额为空也无法绕过 |
| epay_notify 词表撞 sign | 全部 `error`，getshop 仍「未付款」 |
| getshareid SSRF（127.0.0.1 / metadata） | `验证失败`（hashsalt 服务端校验） |
| cancel 他人订单 | 返回「订单号不存在/未知」，**未能取消** |
| ajax query 联系方式枚举 | 仍全空 |
| chat IDOR | **不存在**（忽略 session_id 参数） |
| getgoods / pay / workorder | CSRF 拦截 |
| install POST 强制重装 | 仍提示删 lock |
| user/ajax.php 未授权读卡密 | 仅 login 空参报错，recharge 需登录 |
| 开放注册 | 可注册账号，但 user 页面本次探测返回空体（代理/会话问题待查） |
| cron key 扩展词表 | 未命中 |
| LFI / 备份文件 | 403/404 |
| gift_start 抽奖 | `网站未开启抽奖功能` |

---

## 新信息点（非 Critical，可供后续）

1. **hashsalt 机制**：前端为 JS 混淆表达式，Node 求值 = `256`；单独传 256 **不足以**绕过 pay/getshareid（还需同会话 CSRF + 验证码）
2. **极验 captcha 泄露**：`ajax.php?act=captcha` 无认证返回 `gt` + `challenge`（信息泄露，需配合打码平台才可能辅助下单）
3. **cancel 字段差异**：`orderid` vs `trade_no` 报错不同，但未构成越权
4. **epay_return**：无 sign 时弹「验证失败」并跳转 `?buyok=1`（**非到账**，仅前端跳转）
5. **user/ajax.php**：存在，多数 act 返回 `No Act` 或需登录

---

## 仍值得继续的方向（若还要挖更严重）

1. **install.lock 写权限**：是否有别接口能删/覆盖 lock（文件上传、备份恢复）— 本轮未发现
2. **易支付商户 key**：收集更多 sign 样本做大词表/规则逆推 — 仍是最接近「伪造到账」的路径
3. **极验 + pay 自动化**：有账号.session + 打码 → 再测 price/num 篡改
4. **全站 price=0 商品**：扫全分类 `getgoods`（需有效 CSRF）找免费领取逻辑
5. **子域/旁站**：`api.ttwl66.cn` 商户后台若弱口令（非本域）

---

## 复现（本轮确认仍有效）

```bash
# 最严重：install
curl 'https://hmjf.lol/shop/install/'
curl 'https://hmjf.lol/shop/install/install.lock'

# 经营数据
curl -X POST 'https://hmjf.lol/shop/ajax.php?act=getcount'

# 客服未授权
curl -X POST 'https://hmjf.lol/shop/user/ajax_chat.php?act=send' -d 'content=test'

# 极验信息
curl -X POST 'https://hmjf.lol/shop/ajax.php?act=captcha'
```
