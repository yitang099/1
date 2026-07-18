#!/usr/bin/env python3
"""Generate tianyu9080.top priority API key wordlist."""
import hashlib
import itertools
import sys
from pathlib import Path

SEEDS = [
    "tianyu", "TIANYU", "Tianyu", "tianyu9080", "TIANYU9080", "tianyu9080top",
    "tianyu9080.top", "天鱼", "批Q", "tianyuqq", "ty9080", "ty", "TY",
    "tianyushop", "tianyufaka", "tianyukami", "t008y", "T008Y", "t008ybot",
    "shop", "kami", "faka", "dujiaoke", "caihong", "qq", "QQ",
    "kln166", "fffzz", "fffzzlol",
]

SUFFIXES = [
    "", "0", "1", "12", "123", "1234", "12345", "123456", "666", "888", "999",
    "2024", "2025", "2026", "520", "1314", "9080",
    "admin", "api", "key", "token", "secret", "test", "pass",
]

PREFIXES = ["", "0", "1", "a", "api", "key", "qq", "ty"]

WEAK = [
    "admin", "123456", "password", "apikey", "secret", "test",
    "tianyu", "tianyu9080", "tianyu9080123", "tianyu666", "tianyu888",
    "tianyuapi", "tianyukey", "tianyuadmin", "天鱼", "ty9080", "ty9080api",
    "fffzz", "kln166",
]


def add(keys: set, *items):
    for s in items:
        s = str(s).strip()
        if 1 <= len(s) <= 64:
            keys.add(s)


def main():
    keys: set[str] = set()
    for w in WEAK:
        add(keys, w, w.upper(), w.lower())
    for seed in SEEDS:
        add(keys, seed)
        for suf in SUFFIXES:
            add(keys, seed + suf, suf + seed, f"{seed}_{suf}", f"{seed}-{suf}")
        for pre in PREFIXES:
            for suf in SUFFIXES[:15]:
                add(keys, pre + seed + suf, f"{pre}{seed}{suf}")
    for i in range(10000):
        for seed in ("tianyu9080", "tianyu", "ty9080", "TIANYU9080"):
            add(keys, f"{seed}{i}", f"{i}{seed}", f"{seed}_{i}", f"admin{i}{seed}")
    for s in SEEDS + ["tianyu9080.top", "TIANYU9080.top"]:
        h = hashlib.md5(s.encode()).hexdigest()
        add(keys, h, h[:16], h[:24], h.upper())
    for a, b in itertools.product(["tianyu", "tianyu9080", "admin", "api", "qq", "ty"], repeat=2):
        add(keys, a + b, f"{a}_{b}", a + b + "123")
        add(keys, hashlib.md5((a + b).encode()).hexdigest())
    bases = ["tianyu9080", "tianyu", "tianyuapi", "tianyukey", "ty9080"]
    for b in bases:
        for n in ("2024", "2025", "2026", "666666", "12345678", "9080"):
            add(keys, b + n, (b + n).ljust(16, "0")[:16], (b + n).ljust(32, "0")[:32])
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tianyu9080-priority.txt")
    ordered = sorted(keys, key=lambda x: (len(x), x))
    out.write_text("\n".join(ordered) + "\n", encoding="utf-8")
    print(f"generated {len(ordered)} -> {out}")


if __name__ == "__main__":
    main()
