# 链接速查

## 服务器

| 角色 | SSH | 说明 |
|------|-----|------|
| 香港主力机 | `ssh root@103.185.249.13` | 工具、编排、报告 |
| 国内跳板机 | `ssh root@42.240.167.114` | 代理出口、绕过封禁 |

数据目录: `/data`  
环境加载:
```bash
export PATH="/data/venvs/pentest/bin:/data/automation/bin:/data/tools:/data/go/bin:$PATH"
source /data/config/proxy.env 2>/dev/null
source /data/config/automation.env 2>/dev/null
```

---

## 青果代理（国内短效 - 中转池 - 通道提取）

| 项目 | 值 |
|------|-----|
| 提取 API | https://share.proxy.qg.net/get?key=A0165C9B&num=1 |
| Authkey | `A0165C9B` |
| Authpwd | `3130F524EE1D` |
| 代理格式 | `http://A0165C9B:3130F524EE1D@{server}` |
| 配置文件 | `/data/config/proxy.env` |
| 刷新脚本 | `/data/automation/bin/qg-proxy-fetch.sh` |

```bash
# 在国内跳板或香港机执行
/data/automation/bin/qg-proxy-fetch.sh
source /data/config/proxy.env
curl -x "$PROXY_URL" -sk https://目标域名/shop/
```

注意:
- 通道提取仅 1 通道；`NO_AVAILABLE_CHANNEL` 表示通道占用，等 IP 过期自动释放
- IP 短效（建议后台改为 5–10 分钟存活）
- 过期后重新运行 `qg-proxy-fetch.sh`

---

## 跳板链路（HK 工具 + CN 出口）

| 脚本/命令 | 作用 |
|-----------|------|
| `/data/automation/bin/setup-jump-proxy.sh` | 配置 HK→CN SOCKS + 青果上游 |
| `/data/automation/bin/deep-via-jump.sh <域名>` | 经跳板深度探测 |
| `jp-scan <域名>` | 同上（快捷命令） |
| `jp-curl <url>` | 经跳板 curl |
| `proxychains4 -f /data/config/proxychains-jump.conf <cmd>` | 经跳板 SOCKS |

流量路径: `HK 工具 → SSH → CN 跳板 → 青果代理 → 目标`

---

## 自动化 API（香港机本机）

| 服务 | 地址 |
|------|------|
| 扫描 API | http://127.0.0.1:18789/scan |
| 状态 | http://127.0.0.1:18789/status |
| 健康检查 | http://127.0.0.1:18789/health |
| n8n UI | http://127.0.0.1:5678 |
| n8n Webhook | http://127.0.0.1:5678/webhook/recon |
| Ollama | http://127.0.0.1:11434 |
| GVM/OpenVAS | http://127.0.0.1:9392 |

```bash
curl -X POST http://127.0.0.1:18789/scan \
  -H "Content-Type: application/json" \
  -d '{"target":"example.com","mode":"full","async":true}'
```

---

## 报告目录

```
/data/automation/results/<域名>/<时间戳>/
  report.html / report.md
  nuclei.json / subdomains.txt / alive.txt
```

深挖报告:
```
/data/automation/results/<域名>/deep_jp_<时间戳>/
  summary.md / csrf_poc.html / ajax_enum.txt
```

---

## KLN166.top 目标链接（当前案例）

| 用途 | URL |
|------|-----|
| 商城首页 | https://KLN166.top/shop/ |
| Ajax | https://KLN166.top/shop/ajax.php |
| API | https://KLN166.top/shop/api.php |
| 上架日志 | https://KLN166.top/shop/toollogs.php |
| 登录 | https://KLN166.top/shop/user/login.php |
| 注册 | https://KLN166.top/shop/user/reg.php |
| 聊天 Ajax | https://KLN166.top/shop/user/ajax_chat.php |
| WAF 滑块 | https://KLN166.top/_guard/html.js |
| 购买页 | https://KLN166.top/shop/?mod=buy&cid=13&tid=50 |

CSRF 白名单动作（不校验 token）: `order` `query` `cart_info` `cart_list`  
示例: https://KLN166.top/shop/ajax.php?act=query

已有报告:
- `/data/automation/results/KLN166.top/20260712_233552/`
- `/data/automation/results/KLN166.top/deep_jp_20260713_001225/`
- CSRF POC: `.../deep_jp_20260713_001225/csrf_poc.html`
