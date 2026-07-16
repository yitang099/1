# 卡密/历史卡密深挖状态

- 时间: 2026-07-16
- 后台: `kami_deep.py` 运行中（跳板机）
- 日志: `/data/automation/results/hmjf.lol/kami_mine_20260716/kami_deep.log`

## 当前结果

**尚未获取到真实卡密（kminfo）**

全站约 13330 笔已付款订单（getcount 泄露），但：
- 已扫到的 trade_no 均为未付款测试单
- getshop 统一返回 `{"code":-1,"msg":"未付款"}`
- query 返回 `没有查询到数据`
- id+skey 暴力 1-5000 暂无命中

## 卡密唯一出口（已验证）

```
已付款 → query页 showOrder(id,skey) → POST ajax.php?act=order → kminfo
或已付款 → getshop.php → kminfo
```

未付款订单**不可能**有卡密。

## v6 新发现（2026-07-16 深挖）

**彩虹同源 skey 算法**：`skey = md5(id + SYS_KEY + id)`

- 撞出 `SYS_KEY` 即可对任意 id 算 skey，不必盲爆破 32hex
- `ajax.php?act=query` POST 应用 `type=1&qq={17位trade_no}`（之前参数字段测错）
- 可用下单 `input`（手机号等）查历史单（若未开 queryorderlimit）
- 历史窗应扩至 **2025-11**（yxts=258天），非仅 20260715-16

脚本：`kami_deep_v6.py` | 报告：`KAMI-NEW-PATHS-v6.md`

## 正在跑的任务

1. id+skey 暴力 id 1-5000 × 50 组弱密钥（**应改用 SYS_KEY 算法**）
2. 20260715-16 全天 trade_no 扫描 + 已付款判定 + 自动提取
3. **v6**：SYS_KEY 爆破 + ajax query 正参 + 258天历史窗

## 查看进度

```bash
ssh root@42.240.167.114
tail -f /data/automation/results/hmjf.lol/kami_mine_20260716/kami_deep.log
cat /data/automation/results/hmjf.lol/kami_mine_20260716/kami_found.json
```

出现 `*** KAMI` 即为命中。
