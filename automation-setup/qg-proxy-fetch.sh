#!/bin/bash
# 青果短效代理-中转池-通道提取 自动获取代理
KEY="${QG_AUTHKEY:-A0165C9B}"
PWD="${QG_AUTHPWD:-3130F524EE1D}"
CACHE="/data/config/qg-proxy.cache"
ENV_FILE="/data/config/proxy.env"

RESP=$(curl -s "https://share.proxy.qg.net/get?key=${KEY}&num=1")
CODE=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('code',''))" 2>/dev/null)

if [ "$CODE" = "SUCCESS" ]; then
  SERVER=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data'][0]['server'])")
  AREA=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data'][0].get('area',''))")
  DEADLINE=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data'][0].get('deadline',''))")
  echo "$SERVER" > "$CACHE"
  echo "$DEADLINE" > "${CACHE}.deadline"
elif [ "$CODE" = "NO_AVAILABLE_CHANNEL" ]; then
  QRESP=$(curl -s "https://share.proxy.qg.net/query?key=${KEY}")
  QCODE=$(echo "$QRESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('code',''))" 2>/dev/null)
  if [ "$QCODE" = "SUCCESS" ]; then
    SERVER=$(echo "$QRESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data'][0]['server'] if d.get('data') else '')" 2>/dev/null)
    if [ -n "$SERVER" ]; then
      AREA=$(echo "$QRESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data'][0].get('area',''))")
      DEADLINE=$(echo "$QRESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data'][0].get('deadline',''))")
      echo "[*] 通道占用，复用在用IP: $SERVER" >&2
    fi
  fi
  if [ -z "${SERVER:-}" ] && [ -f "$CACHE" ]; then
    SERVER=$(cat "$CACHE")
    echo "[!] 提取失败($CODE)，使用缓存: $SERVER" >&2
  fi
elif [ -f "$CACHE" ]; then
  SERVER=$(cat "$CACHE")
  echo "[!] 提取失败($CODE)，使用缓存: $SERVER" >&2
else
  echo "[!] 提取失败: $RESP" >&2
  exit 1
fi

[ -n "${SERVER:-}" ] || { echo "[!] 无可用代理" >&2; exit 1; }

export PROXY_URL="http://${KEY}:${PWD}@${SERVER}"
export PROXY_PROVIDER=qingguo
export PROXY_AUTHKEY="$KEY"
export QG_AUTHKEY="$KEY"
export QG_AUTHPWD="$PWD"
export PROXY_SERVER="$SERVER"

cat > "$ENV_FILE" << EOF
# 青果短效代理-中转池-通道提取 (自动更新)
# 提取 API: https://share.proxy.qg.net/get?key=${KEY}&num=1
PROXY_PROVIDER=qingguo
QG_AUTHKEY=${KEY}
QG_AUTHPWD=${PWD}
PROXY_SERVER=${SERVER}
PROXY_URL=${PROXY_URL}
PROXY_AREA="${AREA:-unknown}"
PROXY_DEADLINE="${DEADLINE:-unknown}"
EOF
chmod 600 "$ENV_FILE"

echo "PROXY_URL=$PROXY_URL"
echo "AREA=$AREA DEADLINE=$DEADLINE"
