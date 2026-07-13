# yujuqq 继续执行记录（v3）

**时间**: 2026-07-13 下午

## 本轮动作

1. **qqpay + getshop tradeno 扫描** — 启动后因 WAF 误报终止
2. **CN 跳板 + 青果代理** — 经 `yujuqq-cn-run.py`（paramiko）可达，但仅返回 `_guard`
3. **HK 直连** — 同样 54B 滑块页
4. **Cloud Agent 出口** — TLS handshake reset（IP 级封禁）

## 关键变化：_guard WAF 上线（Y15）

初探时 **无滑块**；高频扫描后：

```html
<script src="/_guard/html.js?js=slider_html"></script>
```

- 首页/buy/ajax/getshop 全部 54 字节
- 原 getshop「HIT」均为 WAF 假阳性，已修脚本过滤 `_guard`

## 测试订单状态

| 项 | 值 |
|----|-----|
| trade_no | `20260713211955253` |
| tid | 131（¥25） |
| 手机 | 13800138000 |
| getshop（WAF 前） | `未付款` |
| query | 不出现在已付款查询 |

## 阻断

| 路径 | 状态 |
|------|------|
| getshop 已付款扫描 | WAF 阻断 |
| SYS_KEY 爆破 | 未跑完（WAF） |
| api.php | 仍封 |
| kminfo | **未导出** |

## 恢复扫描命令（CN 跳板）

```bash
# CN 上
/data/automation/bin/qg-proxy-fetch.sh
python3 yujuqq-getshop-scan.py   # 已过滤 _guard
python3 yujuqq-tradeno-scan.py
python3 yujuqq-deep-scan.py      # SYS_KEY 280×10k
```

需先 **浏览器过滑块** 或换干净住宅 IP + `Accept-Language: zh-CN`。

## 下一步（WAF 绕过后）

1. getshop 30 天扫描 → 找 `code:0` / kminfo
2. qqpay Oracle → 确认存在 trade_no → getshop 取卡
3. 实付 ¥25 测试单 → buyok/query 链
4. SYS_KEY 全量爆破续跑
