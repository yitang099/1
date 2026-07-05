import os
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def log(msg, log_file=None):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    path = log_file or os.path.join(BASE, "captcha_auto.log")
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
