# Faka 渗透工具包 `/data/tools/faka/`

## 工具总览（35+）

### 指纹 / 总控 / 探测
| 脚本 | 用途 |
|------|------|
| `faka_fingerprint.py` | 自动识别：彩虹/异次元/Pisces/赤马 |
| `faka_run.py` | 指纹 → 工具链（`--full` 完整链） |
| `faka_probe.sh` | 统一探测入口（自动选 probe 脚本） |
| `pyfaas_probe.sh` | 赤马一键探测 |
| `probe_rainbow_faka.sh` | 彩虹一键探测 |
| `probe_yiciyuan.sh` | 异次元一键探测 |
| `probe_pisces_faka.sh` | Pisces 一键探测 |
| `faka_nuclei.sh` | nuclei 发卡模板扫描 |
| `faka_dirscan.sh` | feroxbuster + faka 字典 |

### cookie / skey 链（`/cookie/`）
| 脚本 | 用途 |
|------|------|
| `cookie/rainbow_skey_harvest.py` | 彩虹登录/查单/showOrder |
| `cookie/crack_qq_cookie.py` | 从 .body/JS 提取 skey 对 |
| `cookie/geetest_2captcha.py` | Geetest 2captcha 求解 |

### 彩虹发卡
| 脚本 | 用途 |
|------|------|
| `rainbow_idor.py` | api.php IDOR + 斜杠 bypass |
| `rainbow_order_dump.py` | ajax.php?act=order 拖卡 |
| `rainbow_export.py` | 卡密导出 txt |
| `skey_chain.py` | skey 全链（harvest→order→idor） |
| `skey_exploit_queue.py` | 统一 skey 队列 |
| `yanzu_idor_worker.py` | 并行 order+skey 爆破 |

### 异次元 ACG
| 脚本 | 用途 |
|------|------|
| `acg_idor.py` | 订单 IDOR / secret |
| `acg_login_brute.py` | 后台登录 + ddddocr/Geetest |
| `acg_query_brute.py` | 订单查询 OCR |
| `acg_shared_probe.py` | shared_code 上游探测 |
| `order_enum.py` | trade_no 枚举 |
| `sb_subdomain_scan.py` | sb 子域探测 |
| `sb_records_dump.py` | sb /api/records 翻页拖库 |
| `scan_acg_batch.py` | ACG 批量指纹 |
| `epay_key_brute.py` | 易支付 KEY 爆破 |
| `epay_extract.sh` | 支付页 sign 提取 |
| `notify_forge.py` | 支付回调伪造 |

### 赤马 pyfaas
| 脚本 | 用途 |
|------|------|
| `shop_token_scan.py` | token 扫描 |
| `shop_token_scan_async.py` | aiohttp 高并发 |
| `pay_order_brute.py` | Pay/order + Shop/getGoodsPrice |
| `merchant_scan.py` | merchantApi 批量（内置 apis 列表） |

### Pisces
| `pisces_dump.py` | orderSearch 拖库 + orderDetail CDK |

### 通用
| `cors_scan.py` / `thinkphp_scan.py` / `js_api_extract.py` / `cf_session.py` / `proxy_pool.py` |

## 快速开始

```bash
cd /data/tools/faka
bash setup_complete.sh

# 自动探测
bash faka_probe.sh https://zhanghao9.com
bash faka_probe.sh https://qq8.one --full
bash faka_probe.sh https://s.sggyx.com xiaoy --full

# 完整链
python3 faka_run.py https://zhanghao9.com --full --trade-seeds 903260704032647527

# 彩虹 skey 全链
python3 skey_chain.py -H qq8.one --body-dir /data/recon/qq8.one/api --contact QQ123
python3 rainbow_order_dump.py -u https://qq8.one --pairs-file out/crack_skey_report.json

# 异次元 sb 拖库
python3 sb_records_dump.py qq898.vip --discover --max-pages 1000

# nuclei + 目录爆破
bash faka_nuclei.sh https://zhanghao9.com
bash faka_dirscan.sh https://zhanghao9.com
```

## 数据文件
- `data/merchant_apis.txt` — merchantApi 路径
- `data/targets_acg.txt` — ACG 批量目标
- `data/proxy_pool.env` — 多隧道代理池
- `cookie/2captcha.env` — 2验证码 key（本地配置，勿提交）

## 兼容别名
`pisces_order_dump` `export_txt` `yiciyuan_records_dump` `scan_all_bodies` `faka_chain` `auto_capture` `qq8_skey_chain`

## 一键收尾
```bash
bash /data/tools/faka/finish_gaps.sh
```
