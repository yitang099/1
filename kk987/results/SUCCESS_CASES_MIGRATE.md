# SUCCESS_CASES 迁移对照 — kk987.top/shop/

对照 HK `/data/recon/exports/SUCCESS_CASES.md`。开局即测。

| 案列 | 类型 | 漏洞手法 | kk987 结果 |
|------|------|----------|------------|
| **qd93.com** | 彩虹 | `?mod=query&data={子串}` → showOrder/faka | **不可用**。子串全空；自建未付款 TN `20260803115721164` 精确查也「没有查询到数据」。`ajax query` HTTP 500。 |
| **79yj.com** | 彩虹 `/shop/` | `api.php?act=search&id=` 未授权 IDOR | **不可用**。`%61pi.php?act=search` → 需登录或 API key；`api.php` 不通。 |
| **qq1234.cc** | 同上 | 同上 | **同上** |
| **mima1314.com** | YKFAKA | null → Query_Km | **N/A** |
| **15118.cn** | YKFAKA | 同上 | **N/A** |

**无一可直接复用。**
