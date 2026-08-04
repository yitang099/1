# qqhmjy.com recon summary

## Verdict

**IIS/ASP QQ 批发站**，与 `qqfk.net` 顶级域 **首页字节级相同**（IP `219.234.31.186`，CNAME `qqlhmd.gotoip2.com`）。  
**SUCCESS_CASES 无一适用。未拖到 kami。**

## SUCCESS_CASES

| Case | Result |
|------|--------|
| YKFAKA Query.html / null | **404 / N/A** |
| qd93 `mod=query` | 仅回首页 |
| Rainbow ajax/api/tools | **404** |

## Surface

- `kucun.asp` 仅见 `buy.asp?id=212`（标价 0.00）
- 登录：`login.asp` → `chkuser.asp`；客服 QQ `528826870` / 群 `6427879`（同 qqfk apex）

## Cluster

见 PR #47（qqfk.net）。`www.qqfk.net` 为同系更全目录（另一 IP）。

## Artifacts

`FINDINGS.json`、`results/SUCCESS_CASES_MIGRATE.md`、`results/dump/`、`scripts/`  
HK: `/data/recon/qqhmjy.com/`
