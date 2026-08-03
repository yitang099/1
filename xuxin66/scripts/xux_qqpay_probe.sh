#!/bin/bash
source /data/config/proxy.env
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
BASE="https://xuxin66.top/shop"
CK=/tmp/xux_qq3.txt
TRADE=20260803075904880
rm -f $CK
curl -sk -x "$PROXY_URL" -c $CK -b $CK --max-time 25 -A "$UA" "$BASE/" -o /dev/null
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" "$BASE/other/submit.php?type=qqpay&orderid=$TRADE" -o /tmp/sub.html
echo SUB=$(wc -c </tmp/sub.html)
grep -o "qqpay.php[^\"']*" /tmp/sub.html || true
curl -sk -x "$PROXY_URL" -b $CK -c $CK --max-time 15 -A "$UA" -e "$BASE/other/submit.php" "$BASE/other/qqpay.php?trade_no=$TRADE" -o /tmp/qq.html
echo QQ=$(wc -c </tmp/qq.html)
python3 - <<'PY'
import re
h=open('/tmp/qq.html',encoding='utf-8',errors='ignore').read()
print(h[:3000])
print('---')
urls=re.findall(r"https?://[^\s\"'<>]+", h)
print('URLS', urls[:15])
print('trade', re.findall(r'trade_no[=:][^\"\s&]+', h)[:10])
print('sign', re.findall(r'sign[=:][a-f0-9]+', h, re.I)[:10])
for f in re.findall(r'<form[\s\S]*?</form>', h, re.I):
    print('FORM', f[:600])
PY
