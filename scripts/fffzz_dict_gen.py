#!/usr/bin/env python3
"""Generate fffzz.lol priority API key / SYS_KEY wordlist."""
import hashlib
import itertools
import sys
from pathlib import Path

SEEDS = [
    "fffzz", "FFFZZ", "Fffzz", "fffzzlol", "fffzz666", "fffzz888", "fffzz123",
    "fffz", "fffzlol", "fz", "fzlol", "fff", "fff666",
    "shop", "kami", "faka", "dujiaoke", "caihong", "chfaka", "djk",
    "fffzzshop", "fffzzshoplol", "fffzzvip", "fffzzpro",
]

SUFFIXES = [
    "", "0", "1", "12", "123", "1234", "12345", "123456", "666", "888", "999",
    "2024", "2025", "2026", "520", "1314", "007", "007agent",
    "admin", "api", "key", "token", "secret", "test", "pass", "pwd",
    "Admin", "API", "Key", "Token",
]

PREFIXES = ["", "0", "1", "a", "A", "x", "v", "q", "djk", "api", "key"]

WEAK = [
    "admin", "123456", "password", "apikey", "api_key", "secret", "test",
    "abcdef", "qwerty", "111111", "000000", "888888", "666666",
    "fffzz", "fffzzlol", "fffzz123", "fffzz666", "fffzz888", "fffzzapi",
    "fffzzkey", "fffzztoken", "fffzzadmin", "fffzz2024", "fffzz2025", "fffzz2026",
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
            add(keys, seed + suf.upper(), seed.upper() + suf)
        for pre in PREFIXES:
            for suf in SUFFIXES[:20]:
                add(keys, pre + seed + suf, f"{pre}{seed}{suf}", f"{pre}_{seed}_{suf}")

    # admin/num permutations with fffzz
    for i in range(10000):
        for seed in ("fffzz", "fffzzlol", "fffz"):
            add(keys, f"{seed}{i}", f"{i}{seed}", f"{seed}_{i}", f"admin{i}{seed}", f"{seed}admin{i}")
        if i < 1000:
            add(keys, f"admin{i}", f"admin_{i}", f"api{i}", f"key{i}")

    # md5 / partial md5 (API keys often 32 hex)
    md5_seeds = SEEDS + ["fffzz.lol", "fffzzlol", "shop", "admin", "api", "key", "secret"]
    for s in md5_seeds:
        h = hashlib.md5(s.encode()).hexdigest()
        add(keys, h)
        add(keys, h[:16], h[:24], h[8:24], h.upper(), h[:16].upper())

    for a, b in itertools.product(["fffzz", "admin", "api", "shop", "key"], repeat=2):
        add(keys, a + b, f"{a}_{b}", f"{a}-{b}", a + b + "123", a + b + "666")
        h = hashlib.md5((a + b).encode()).hexdigest()
        add(keys, h, h[:16])

    # 16-32 char alphanumeric patterns (common panel defaults)
    bases = ["fffzz", "fffzzlol", "fffzzapi", "fffzzkey", "fffzz666"]
    tails = ["1234567890abcdef", "abcdef1234567890", "0123456789abcdef"]
    for b in bases:
        for t in tails:
            add(keys, (b + t)[:16], (b + t)[:24], (b + t)[:32])
        for n in ("2024", "2025", "2026", "666666", "88888888", "12345678"):
            add(keys, b + n, (b + n).ljust(16, "0")[:16], (b + n).ljust(32, "0")[:32])

    # uuid-like with fffzz prefix
    for i in range(256):
        hx = f"{i:02x}"
        add(keys, f"fffzz{hx * 8}", f"fffzz{hx * 16}"[:32], f"api{hx * 14}"[:32])

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("fffzz-priority.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(keys, key=lambda x: (len(x), x))
    out.write_text("\n".join(ordered) + "\n", encoding="utf-8")
    print(f"generated {len(ordered)} keys -> {out}")
    from collections import Counter
    lens = Counter(len(k) for k in ordered)
    for ln in sorted(lens)[:16]:
        print(f"  len {ln}: {lens[ln]}")


if __name__ == "__main__":
    main()
