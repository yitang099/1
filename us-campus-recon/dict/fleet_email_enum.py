#!/usr/bin/env python3
"""
多进程 + 多IP 邮箱枚举编排器

用法:
  # 单机多进程 (同IP, 约1.2-1.3x加速)
  python3 fleet_email_enum.py --dict emails_kr_large.txt --workers 4

  # 多IP: 准备 proxies.txt 每行一个代理, 每个worker绑定不同IP
  python3 fleet_email_enum.py --dict emails_kr_large.txt --proxies proxies.txt

  # 手动指定代理列表
  python3 fleet_email_enum.py --dict emails_kr_large.txt \\
    --proxy http://1.2.3.4:8080 --proxy http://5.6.7.8:8080
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
WORKER_SCRIPT = SCRIPT_DIR / "fast_email_enum.py"


def load_lines(path: str) -> list[str]:
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def split_dict(emails: list[str], n: int) -> list[list[str]]:
    """均分字典为 n 片"""
    size = math.ceil(len(emails) / n)
    return [emails[i * size : (i + 1) * size] for i in range(n) if emails[i * size : (i + 1) * size]]


def run_worker(
    worker_id: int,
    emails: list[str],
    concurrency: int,
    proxy: str,
    out_dir: Path,
) -> dict:
    shard_path = out_dir / f"shard_{worker_id:03d}.txt"
    out_path = out_dir / f"hits_{worker_id:03d}.json"
    log_path = out_dir / f"worker_{worker_id:03d}.log"

    with open(shard_path, "w") as f:
        f.write("\n".join(emails) + "\n")

    cmd = [
        sys.executable, str(WORKER_SCRIPT),
        "--dict", str(shard_path),
        "--concurrency", str(concurrency),
        "--out", str(out_path),
        "--report-every", "999999",
    ]
    if proxy:
        cmd.extend(["--proxy", proxy])

    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0

    with open(log_path, "w") as f:
        f.write(proc.stdout)
        if proc.stderr:
            f.write("\n--- stderr ---\n")
            f.write(proc.stderr)

    if proc.returncode != 0:
        return {
            "worker_id": worker_id,
            "error": proc.stderr[-500:] if proc.stderr else "unknown",
            "scanned": len(emails),
            "hits": [],
            "elapsed_sec": round(elapsed, 1),
            "rate_per_sec": 0,
            "proxy": proxy or None,
        }

    with open(out_path) as f:
        data = json.load(f)
    data["worker_id"] = worker_id
    return data


def merge_results(worker_results: list[dict], out_path: str, dict_path: str):
    all_hits = []
    seen = set()
    total_scanned = 0
    total_elapsed = max(r.get("elapsed_sec", 0) for r in worker_results) if worker_results else 0

    for r in worker_results:
        total_scanned += r.get("scanned", 0)
        for h in r.get("hits", []):
            email = h["email"] if isinstance(h, dict) else h
            if email not in seen:
                seen.add(email)
                all_hits.append(h if isinstance(h, dict) else {"email": email})

    fleet_rate = total_scanned / total_elapsed if total_elapsed else 0
    merged = {
        "target": "https://us-campus.co.kr",
        "mode": "fleet",
        "dict": dict_path,
        "workers": len(worker_results),
        "scanned": total_scanned,
        "hits": all_hits,
        "hit_count": len(all_hits),
        "wall_elapsed_sec": round(total_elapsed, 1),
        "fleet_rate_per_sec": round(fleet_rate, 1),
        "per_worker": [
            {
                "id": r.get("worker_id"),
                "proxy": r.get("proxy"),
                "scanned": r.get("scanned"),
                "hits": r.get("hit_count", len(r.get("hits", []))),
                "rate_per_sec": r.get("rate_per_sec"),
                "elapsed_sec": r.get("elapsed_sec"),
                "error": r.get("error"),
            }
            for r in worker_results
        ],
    }
    with open(out_path, "w") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged


def main():
    parser = argparse.ArgumentParser(description="多进程/多IP邮箱枚举编排")
    parser.add_argument("--dict", default=str(SCRIPT_DIR / "emails_kr_large.txt"))
    parser.add_argument("--workers", type=int, default=0, help="进程数(默认=代理数或CPU核数)")
    parser.add_argument("--concurrency", type=int, default=200, help="每进程并发")
    parser.add_argument("--proxies", default="", help="代理列表文件, 每行一个")
    parser.add_argument("--proxy", action="append", default=[], help="可多次指定代理")
    parser.add_argument("--out-dir", default=str(SCRIPT_DIR / "fleet_out"))
    parser.add_argument("--out", default=str(SCRIPT_DIR / "fleet_hits.json"))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    emails = load_lines(args.dict)
    if args.limit:
        emails = emails[: args.limit]

    proxies = list(args.proxy)
    if args.proxies:
        proxies.extend(load_lines(args.proxies))

    n_workers = args.workers or (len(proxies) if proxies else os.cpu_count() or 4)
    n_workers = max(1, n_workers)
    shards = split_dict(emails, n_workers)

    # 代理分配: worker i 用 proxies[i % len(proxies)], 无代理则空
    worker_proxies = []
    for i in range(len(shards)):
        if proxies:
            worker_proxies.append(proxies[i % len(proxies)])
        else:
            worker_proxies.append("")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"字典: {args.dict}")
    print(f"总量: {len(emails):,}  workers: {len(shards)}  每worker并发: {args.concurrency}")
    if proxies:
        print(f"代理: {len(proxies)} 个 (每worker绑定不同IP)")
    else:
        print("代理: 无 (同IP多进程, 加速有限)")
    print(f"输出: {args.out}")
    print("-" * 50)

    t0 = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=len(shards)) as pool:
        futures = {
            pool.submit(run_worker, i, shard, args.concurrency, worker_proxies[i], out_dir): i
            for i, shard in enumerate(shards)
        }
        for fut in as_completed(futures):
            wid = futures[fut]
            r = fut.result()
            results.append(r)
            status = "ERR" if r.get("error") else "OK"
            print(
                f"[worker-{wid:02d}] {status} proxy={r.get('proxy') or 'local'} "
                f"scanned={r.get('scanned',0):,} rate={r.get('rate_per_sec',0)}/s "
                f"hits={r.get('hit_count', len(r.get('hits',[])))}",
                flush=True,
            )

    results.sort(key=lambda x: x.get("worker_id", 0))
    merged = merge_results(results, args.out, args.dict)
    wall = time.time() - t0

    print("-" * 50)
    print(f"完成: {merged['scanned']:,} 条  命中 {merged['hit_count']}  "
          f"墙钟 {wall:.0f}s  舰队速度 {merged['fleet_rate_per_sec']}/s")
    print(f"合并结果: {args.out}")
    if merged["hits"]:
        print("命中:")
        for h in merged["hits"]:
            e = h["email"] if isinstance(h, dict) else h
            print(f"  {e}")


if __name__ == "__main__":
    main()
