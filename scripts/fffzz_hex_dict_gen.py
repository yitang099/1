#!/usr/bin/env python3
"""Generate 32-char hex API key sample wordlist for fffzz.lol."""
import hashlib
import itertools
import sys
from pathlib import Path

SEEDS = [
    "fffzz", "fffzzlol", "fffzz666", "fffzz888", "fffzz123", "fffzzapi", "fffzzkey",
    "fffzzadmin", "fffzzshop", "fffzz2024", "fffzz2025", "fffzz2026",
    "admin", "api", "key", "secret", "token", "shop", "kami", "faka",
    "dujiaoke", "caihong", "djk", "fffzz.lol", "https://fffzz.lol",
    "C413ED6D", "7I35dzcd",  # proxy biz id patterns
]

SALTS = ["", "0", "1", "123", "666", "888", "salt", "key", "api", "fffzz"]


def md5h(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def sha1h(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:32]


def add(keys: set, *items):
    for s in items:
        s = str(s).strip().lower()
        if len(s) == 32 and all(c in "0123456789abcdef" for c in s):
            keys.add(s)
        elif 16 <= len(s) <= 32 and all(c in "0123456789abcdef" for c in s):
            keys.add(s.ljust(32, "0")[:32])


def main():
    keys: set[str] = set()

    # md5/sha1 of seed combinations
    for seed in SEEDS:
        add(keys, md5h(seed))
        for salt in SALTS:
            add(keys, md5h(seed + salt), md5h(salt + seed), md5h(f"{seed}:{salt}"))
            add(keys, sha1h(seed + salt))
        for i in range(1000):
            add(keys, md5h(f"{seed}{i}"), md5h(f"{i}{seed}"), md5h(f"{seed}_{i}"))

    # md5 of pairs
    for a, b in itertools.product(SEEDS[:12], SEEDS[:12]):
        add(keys, md5h(a + b), md5h(f"{a}:{b}"), md5h(f"{a}_{b}"))

    # uuid-like: fffzz + hex padding
    for i in range(65536):
        hx = f"{i:04x}"
        add(keys, f"fffzz{'0' * 27}{hx}"[-32:], f"fffz{'0' * 28}{hx}"[-32:])
        add(keys, f"{hx}{'0' * 28}fffzz"[:32], md5h(f"fffzz{hx}"))
        if i < 4096:
            hx8 = f"{i:08x}"
            add(keys, md5h(f"fffzz{hx8}"), md5h(f"api{hx8}"), md5h(f"key{hx8}"))

    # common install / default hex patterns
    for prefix in ("fffzz", "admin", "apikey", "secret", "token", "caihong", "dujiaoke"):
        h = md5h(prefix)
        add(keys, h)
        for i in range(256):
            add(keys, md5h(prefix + str(i)), h[:16] + f"{i:016x}"[:16])

    # repeated-nibble weak hex
    for c in "0123456789abcdef":
        add(keys, c * 32)

    # sequential hex blocks
    for start in range(0, 256, 16):
        block = "".join(f"{(start + j) % 256:02x}" for j in range(16))
        add(keys, block * 2, (block * 3)[:32])

    # substr mixes from known md5
    base_hashes = [md5h(s) for s in SEEDS]
    for h in base_hashes:
        add(keys, h)
        for i in range(0, 32, 4):
            add(keys, h[i:] + h[:i])
            add(keys, (h[i:] + h[:i])[:32])

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("fffzz-hex32-sample.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(keys)
    out.write_text("\n".join(ordered) + "\n", encoding="utf-8")
    print(f"generated {len(ordered)} hex32 keys -> {out}")


if __name__ == "__main__":
    main()
