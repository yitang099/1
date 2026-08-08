# lubanqq.top recon

**Verdict:** ACG-faka **3.5.5** shop（鲁班 / 颜思 @yansi）. Rainbow / YK / `sb.*/api/records` SUCCESS_CASES 全 miss。未拿到卡密。

## Stack

- Theme Dream；支付仅 USDT/TRX（EuPay）
- 4 分类 / 30 SKU；详情接口 `only_user=1`（强制登录购买）
- 现代 query 形态：`{"code":200,"data":{"list":[],"total":0}}`

## SUCCESS_CASES

| Path | Result |
|------|--------|
| Rainbow getcount / ajax | 404 |
| `%61pi.php?act=search` | 404 |
| YK `value=null` | HTML miss |
| `sb/shop/store/api.lubanqq.top/api/records` | 403 / 非 qq898 checker |

## ACG 面

- `POST /user/api/index/query`：免登录；**仅精确匹配** 18 位 `trade_no` 或 `contact`（无前缀）
- `POST /user/api/index/secret`：`orderId=<tradeNo>`；未支付拒绝
- 上游 3.5.x 限流：query ~30/600s/IP，secret ~40/600s/IP
- 登录下单时 `contact` 被替换为 `Str::generateRandStr(16)`（本站 PoC：提交 `idorprobe@qq.com` → 库存字段 `89f429ca6678786b`）

## PoC

- 注册+登录（ddddocr 过验证码）后 `item_id=116` 下单成功  
  `trade_no=941260804231046963`（未支付）
- 未登录可按 `trade_no` / 随机 contact token 查到订单元数据
- 明文联系方式 / 弱口令 contact spray：**0 hit**（与 hao998 对比，本站全 SKU 强制登录）

## 为何喷不到卡密

1. 全站 `only_user` → contact 随机 16 位 → hao998 式 spray 失效  
2. `trade_no = mt_rand(100,999)+ymdHis+mt_rand(100,999)` ≈ 81 万/秒，叠加限流不可爆破  
3. 无 Rainbow/YK 开放检索；无 `sb` records 金路径

## Artifacts

- `results/dump/trade_poc.json` — 未支付订单 PoC  
- `results/dump/priority_quick.json` — 弱 contact 快喷（仅 PoC 自身命中）  
- `results/dump/goods*.json` / `site_info.json`  
- `scripts/lubanqq_recon.py` / `lubanqq_contact_spray.py`
