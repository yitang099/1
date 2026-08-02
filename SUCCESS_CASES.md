# 成功案列总览 → 按剧本破站

> 更新：2026-08-02  
> **剧本库：** `SUCCESS_PLAYBOOK.json`  
> **自动破站：** `break_by_playbook.py`（YKFAKA / 彩虹 query / 彩虹 api 三套路）  
> **跳板一键：** `./break_jump_run.sh`

---

## 成功案列清单（全部）

### A. YKFAKA `value=null` → `Query_Km/{ddid}`

| 目标 | 卡密 | ddid | 状态 | 下载 |
|------|------|------|------|------|
| **mima1314.com** | 14642 | 7197 | ✅ 8/1 仍有效 | http://103.185.249.13:18888/mima1314_cards_20260801.txt |
| **15118.cn** | 165 | 904 | ❌ 8/1 已修 | http://103.185.249.13:18888/15118.cn_cards_20260801.txt |

### B. 彩虹 `mod=query` 子串 → `mod=faka`

| 目标 | pair | 卡 | 状态 | 下载 |
|------|------|-----|------|------|
| **qd93.com**（根路径） | 19 | 13 | ✅ 8/1 仍有效 | http://103.185.249.13:18888/qd93_cards_20260801.txt |

### C. 彩虹 `api.php?act=search&id=` IDOR

| 目标 | 卡密行 | 订单 | 状态 |
|------|--------|------|------|
| **123.taoqqhao.com/shop/** | 1413 | 1653 | 归档成功，站现异常 |
| **qq1234.cc/shop/** | 84 | 179 | 归档成功，getcount 404 |
| **79yj.com** | 115 | 609 | 归档成功，getcount 404 |
| **qq1.lol** | 46442 | — | 6/18 大包 |
| **qq8.one** | 38507 | — | 6/18 大包 |
| **yanzu.lol** | 22262 | — | 6/18 大包 |
| **qw123.lol** | 21705 | — | 6/18 大包 |
| **juzi668.top** | 12313 | — | 6/18 大包 |
| **hmjf.lol** | 16361 | — | 6/18 大包 |
| **baichuan.lol** | 796 | — | 6/18 大包 |

6/18 归档：`/data/recon/exports/api_idor_cards_20260618/`

### D. 彩虹 `%61pi.php` API key（进行中）

| 目标 | 说明 |
|------|------|
| **youhui1998.top/shop/** | 55821 单；跳板 `yh_kami_jp.py` 撞 key，尚无命中 |

---

## 三套破站剧本（按成功记录）

| 剧本 ID | 识别指纹 | 利用链 | 导出脚本 |
|---------|----------|--------|----------|
| `ykfaka_null_km` | YKFAKA / Query.html | null POST → Query_Km | `mima1314_full_export.py` |
| `rainbow_query_faka` | assets/faka + showOrder | query 子串 → faka | `qd93_full_export.py` |
| `rainbow_api_search` | getcount + api.php | id 遍历 search | `faka_api_brute_fast.py` |
| `rainbow_api_key` | %61pi + 请提供API密钥 | key 撞库 | `yh_kami_jp.py` |

---

## 用法

```bash
# 单目标
python3 break_by_playbook.py /tmp/out https://example.com/shop/

# 多目标（国内跳板 + 青果代理）
./break_jump_run.sh
```

---

## 非成功 / 硬站

| 目标 | 说明 |
|------|------|
| xinhe001.lol/shop/ | query/api 0；WAF |
| hm0880.top | 无表面泄露 |
| 95lb.com | 独角 v5 |

复探 JSON：`success_cases_deep.json`
