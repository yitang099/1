# tianyu9080.top/shop/ 侦察报告

**时间**: 2026-07-18  
**目标**: https://tianyu9080.top/shop/  
**标题**: 批Q号天鱼 发卡网 24h可以自助下单

## 框架

独角/彩虹发卡系统（与 fffzz、KLN166 同框架）

## 基础设施

| 项目 | 值 |
|------|-----|
| DNS A | `45.158.21.213`, `103.43.11.95` |
| 同段 IP | `103.43.11.x` 与 fffzz/KLN166 基础设施重叠 |
| CN 可达 | ✅ 正常（200，~2.5s） |
| KLN166 对比 | CN 节点当前仍被封 |

## 关键端点

| 端点 | 结果 |
|------|------|
| `api.php` | 空（WAF 拦截） |
| `%61pi.php/?act=search&id=1` | `{"code":-1,"message":"请提供用户登录信息或API对接密钥"}` ✅ |
| `ajax.php?act=getcount` | **开放** — 订单 **38089**，流水 ~722万 |
| `ajax.php?act=getclass` | **开放** — 商品分类列表 |
| `ajax.php?act=gettoolnew` | **开放** — 商品详情 |
| `ajax.php?act=captcha` | Geetest 验证码 |
| `%61pi.php` 其他 act | 多数 `No Act!`（比 fffzz 严，比 KLN166 松） |
| `cron.php` | `监控密钥不正确` |
| `install/` | 已安装锁定 |
| `.env` / `config.php` | 403 |

## 与 KLN166 对比

| | tianyu9080 | KLN166 |
|--|------------|--------|
| ajax 泄露 | ✅ 开放 | ❌ 全 403 |
| API 撞 key | 需 key | 需 key |
| CN 直连 | ✅ 可用 | ❌ IP 被封 |
| 订单量 | ~3.8 万 | 未知 |

## 攻击面

1. **API Key 撞库** — `%61pi.php/?act=search&id=N&key=...`（主向量，与现成脚本兼容）
2. **cron 监控密钥** — `cron.php` 弱口令
3. **ajax 信息收集** — 商品/订单统计已泄露，可枚举 tid/cid
4. **配置泄露扫描** — `.env` 403 但可扫备份

## 速度粗测（CN 直连）

单线程 ~1.2 req/s（30/30 成功），比 KLN166 被封时好，但站点响应偏慢。

## 建议

- **优先切换目标**：KLN166 CN IP 被封，tianyu9080 从 CN 可正常访问
- 复用 `faka_api_brute_fast.py`，`FAKA_BASE=https://tianyu9080.top/shop/`
- 字典可复用 `faka-tokens.txt` + 生成 `tianyu9080-priority`（域名相关弱 key）
