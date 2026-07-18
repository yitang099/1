#!/usr/bin/env python3
"""KLN166 32-hex API key sample wordlist."""
import hashlib
import itertools
import sys
from pathlib import Path

SEEDS = [
    "kln166", "KLN166", "kln166top", "kln166.top", "kulinan", "库里南", "库利南",
    "kln", "kln666", "kln888", "kln166api", "kln166key", "kln166admin",
    "admin", "api", "key", "secret", "qq", "faka",
]


def md5h(s):
    return hashlib.md5(s.encode()).hexdigest()


def add(keys, *items):
    for s in items:
        s = str(s).strip().lower()
        if len(s) == 32 and all(c in "0123456789abcdef" for c in s):
            keys.add(s)


def main():
    keys = set()
    for seed in SEEDS:
        add(keys, md5h(seed))
        for i in range(1000):
            add(keys, md5h(f"{seed}{i}"), md5h(f"{i}{seed}"))
        for salt in ("", "123", "666", "key", "api"):
            add(keys, md5h(seed + salt), md5h(salt + seed))
    for a, b in itertools.product(SEEDS[:10], SEEDS[:10]):
        add(keys, md5h(a + b))
    for i in range(8192):
        hx = f"{i:04x}"
        add(keys, md5h(f"kln166{hx}"), md5h(f"kulinan{hx}"))
    for c in "0123456789abcdef":
        add(keys, c * 32)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("kln166-hex32-sample.txt")
    ordered = sorted(keys)
    out.write_text("\n".join(ordered) + "\n")
    print(f"generated {len(ordered)} -> {out}")


if __name__ == "__main__":
    main()
