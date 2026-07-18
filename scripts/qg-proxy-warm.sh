#!/bin/bash
set -euo pipefail
OUT="${1:-/data/automation/results/fffzz.lol/kami_allin_20260717}"
KEY="${QG_AUTHKEY:-C413ED6D}"
PWD="${QG_AUTHPWD:-344F550A6F8B}"
CHANNELS="${QG_CHANNELS:-20}"
mkdir -p "$OUT"
RAW=$(curl -sS --max-time 30 "https://share.proxy.qg.net/get?key=${KEY}&pwd=${PWD}&num=${CHANNELS}&distinct=true")
OUT="$OUT" KEY="$KEY" PWD="$PWD" CHANNELS="$CHANNELS" RAW="$RAW" python3 <<'PY'
import json, os, sys
out = os.environ["OUT"]
key = os.environ["KEY"]
pwd = os.environ["PWD"]
n = int(os.environ.get("CHANNELS", "20"))
d = json.loads(os.environ["RAW"])
if d.get("code") != "SUCCESS":
    print("warmup failed:", os.environ["RAW"][:200], file=sys.stderr)
    sys.exit(1)
for i, item in enumerate(d.get("data", [])[:n]):
    server = item["server"]
    p = f"http://{key}:{pwd}@{server}"
    open(f"{out}/proxy_w{i}.txt", "w").write(p)
    print(f"w{i} {server}")
print(f"warmed {min(len(d.get('data', [])), n)} proxies")
PY
