#!/usr/bin/env python3
"""Generate KLN166.top priority API key wordlist."""
import hashlib
import itertools
import sys
from pathlib import Path

SEEDS = [
    "kln166", "KLN166", "Kln166", "kln", "KLN", "kln166top", "kln166.top",
    "kulinan", "KULINAN", "库利南", "库里南", "kln666", "kln888", "kln123",
    "klnshop", "klnvip", "klnqq", "qqkln", "kln166qq", "kln166shop",
    "shop", "kami", "faka", "dujiaoke", "caihong", "qq", "QQ",
]

SUFFIXES = [
    "", "0", "1", "12", "123", "1234", "12345", "123456", "666", "888", "999",
    "2024", "2025", "2026", "520", "1314",
    "admin", "api", "key", "token", "secret", "test", "pass",
]

PREFIXES = ["", "0", "1", "a", "api", "key", "qq"]

WEAK = [
    "admin", "123456", "password", "apikey", "secret", "test",
    "kln166", "KLN166", "kln166123", "kln166666", "kln166888", "kln166api",
    "kln166key", "kln166admin", "kulinan", "kulinan166", "库里南", "库利南",
    "fffzz", "fffzzlol",  # same operator may reuse
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
        for seed in ("kln166", "kln", "kulinan", "KLN166"):
            add(keys, f"{seed}{i}", f"{i}{seed}", f"{seed}_{i}", f"admin{i}{seed}")
    for s in SEEDS + ["kln166.top", "KLN166.top", "kulinan166"]:
        h = hashlib.md5(s.encode()).hexdigest()
        add(keys, h, h[:16], h[:24], h.upper())
    for a, b in itertools.product(["kln166", "kln", "admin", "api", "qq", "kulinan"], repeat=2):
        add(keys, a + b, f"{a}_{b}", a + b + "123")
        add(keys, hashlib.md5((a + b).encode()).hexdigest())
    bases = ["kln166", "kulinan", "kln166api", "kln166key"]
    for b in bases:
        for n in ("2024", "2025", "2026", "666666", "12345678"):
            add(keys, b + n, (b + n).ljust(16, "0")[:16], (b + n).ljust(32, "0")[:32])
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("kln166-priority.txt")
    ordered = sorted(keys, key=lambda x: (len(x), x))
    out.write_text("\n".join(ordered) + "\n", encoding="utf-8")
    print(f"generated {len(ordered)} -> {out}")


if __name__ == "__main__":
    main()
