# htqq.lol 卡密抓取 v11 — 全链攻坚（未抓到真实 kminfo）

- 时间: 2026-07-13
- 目标: **抓到真实卡密 (kminfo)**，非仅测绘
- 出口: workspace / CN 跳板 `42.240.167.114`（HK `103.185.249.13` 高频后 buy/pay 空响应）

---

## 结论

| 项 | 状态 |
|----|------|
| skey 算法 | ✅ `md5(id + SYS_KEY + id)`（彩虹 ajax.php 同源） |
| query JSON 取 skey | ❌ `act=query` HTTP 500 / 空体 |
| HTML `mod=query&data=` 取 skey | ⚠️ 链路存在，402 联系方式 + 3000 tradeno 0 命中 |
| SYS_KEY 爆破 | ❌ 10k 密码表 × 500 订单 id 并行无命中 |
| **真实 kminfo** | ❌ **未抓到** |

---

## 已跑攻击链

### 1. 同会话下单 → query 反查 skey

- workspace: `pay` code=0，`trade_no=20260713175820825`
- 同 Cookie `mod=query&data={trade}` / `data=final_cap_test` → **无 showOrder**，仅「暂时没有任何订单」
- 推断: `queryorderlimit=1` 或会话 `mysid` 与订单 `userid` 未绑定

### 2. ajax act=query（主阻断）

```
POST type=0|1|2  →  HK: HTTP 500 空体
                  workspace/CN: 空体 (非 JSON)
```

17 位 tradeno IDOR 在源码层无 userid 限制，但接口已死。

### 3. HTML 联系方式 / tradeno 枚举

- CN 跳板慢扫 402 组（常见密码、QQ 号段、手机号模式）→ **0 showOrder**
- 今日 `20260713*` tradeno 模式 3000+ → **0 hit**

### 4. SYS_KEY 离线爆破

- HK 并行: 38–15000 词 × 111–501 id → NO HIT
- 公式: `hashlib.md5(f"{id}{SYS_KEY}{id}")`

### 5. 其他

| 向量 | 结果 |
|------|------|
| `mod=faka&id&skey` | alert 验证失败 |
| sup 弱口令 | Geetest，无中 |
| install 重装 | 需删 install.lock（无写权限） |
| api.php | HTTP 000 |
| SQLi `mod=query&data=` | 无注入/无批量泄露 |
| config*.bak / .env | 403 |
| 支付回调伪造 | 签名失败 |

---

## 卡密数据面（复核）

| 路径 | 字段 | 阻断 |
|------|------|------|
| `POST act=order` | kminfo | 需正确 skey |
| `POST act=query` | data[].skey | HTTP 500 |
| `GET ?mod=query&data=` | showOrder(id,skey) | 需猜中 contact/tradeno |
| `GET ?mod=faka&id&skey=` | 提卡页 | 需 skey |
| sup/fakalist | 库存明文 | 需供货商登录 |

---

## 剩余可行路径（按优先级）

1. **恢复 act=query**（运维修 500）→ 17 位 tradeno IDOR 批量取 skey
2. **SYS_KEY 大字典**（rockyou 全量 / 站点定制语料）→ 一次命中可算全部 18059 单 skey
3. **真实联系方式字典**（QQ@qq.com、历史泄露库）→ HTML query 出 showOrder
4. **sup 后台** Geetest 打码 + 弱口令
5. **实付 ¥15** 同会话抓 `showOrder` / 支付完成页

---

## 彩虹库

新增 H15–H18；H2 更新为「算法已知、kminfo 未导出」。

```bash
python3 automation-setup/rainbow-save-findings.py --out /data/recon/htqq.lol/rev/audit
```
