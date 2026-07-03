#!/bin/bash
# 补齐逆向/渗透缺失工具 - 两台服务器通用
set -uo pipefail
LOG=/root/install_gap_complete.log
export DEBIAN_FRONTEND=noninteractive
export GOPATH=/data/go
export GOBIN=/data/go/bin
export PATH="/usr/local/go/bin:/data/go/bin:/data/tools/bin:/data/tools:/usr/local/bin:/opt/ghidra:/opt/dex2jar:/opt/burpsuite:/usr/sbin:/usr/bin:/sbin:/bin"
export PIP_CACHE_DIR=/data/pip-cache
export TMPDIR=/data/tmp
export GOMODCACHE=/data/go/pkg/mod
export GOCACHE=/data/go-build

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
link_bin() {
  local src="$1" name="${2:-$(basename "$1")}"
  [ -e "$src" ] || return 1
  ln -sf "$src" "/usr/local/bin/$name"
  ln -sf "$src" "/data/tools/bin/$name"
  log "linked $name"
}

log "========== INSTALL START $(hostname) =========="
mkdir -p /data/go/bin /data/tools/bin /data/src /data/tmp /data/downloads /usr/local/bin

# ── Go ──────────────────────────────────────────────────────
if [ ! -x /usr/local/go/bin/go ]; then
  log "Installing Go..."
  GO_VER=1.25.11
  curl -fsSL -o /data/tmp/go.tgz "https://go.dev/dl/go${GO_VER}.linux-amd64.tar.gz" || \
  curl -fsSL -o /data/tmp/go.tgz "https://mirrors.aliyun.com/golang/go${GO_VER}.linux-amd64.tar.gz" || true
  if [ -f /data/tmp/go.tgz ]; then
    rm -rf /usr/local/go
    tar -C /usr/local -xzf /data/tmp/go.tgz
    log "Go installed"
  fi
fi

# ── APT ─────────────────────────────────────────────────────
log "APT update & install..."
apt-get update -qq 2>>"$LOG" || true
APT_PKGS=(
  qemu-system-x86 qemu-utils qemu-user-static
  hash-identifier exploitdb
  git build-essential cmake nasm mingw-w64
  ruby-rubygems
  default-jre-headless
)
apt-get install -y -qq "${APT_PKGS[@]}" 2>>"$LOG" || true

# rizin: apt or build wrapper
if ! command -v rizin &>/dev/null || [ ! -x "$(command -v rizin)" ]; then
  apt-get install -y -qq rizin 2>>"$LOG" || true
fi

# ── pip / gem ───────────────────────────────────────────────
log "pip install..."
PIP_PKGS=(frida frida-tools hashid evil-winrm volatility drozer objection ropper ROPGadget one_gadget)
pip3 install --break-system-packages -q "${PIP_PKGS[@]}" 2>>"$LOG" || \
pip3 install -q "${PIP_PKGS[@]}" 2>>"$LOG" || true

log "gem install evil-winrm..."
gem install evil-winrm --no-document 2>>"$LOG" || true

# ── Metasploit (host native) ────────────────────────────────
if ! command -v msfconsole &>/dev/null; then
  log "Installing Metasploit omnibus..."
  # msf 优先 kali 容器；宿主机可用 kali 源: apt install metasploit-framework
  curl -fsSL -o /data/tmp/msfinstall \
    https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb 2>>"$LOG" || true
  if [ -f /data/tmp/msfinstall ]; then
    chmod 755 /data/tmp/msfinstall
    /data/tmp/msfinstall 2>>"$LOG" || true
  fi
fi

# Kali docker 内补齐
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx kali; then
  log "Kali docker: installing core tools..."
  docker exec kali bash -c '
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq metasploit-framework rizin qemu-system-x86 drozer 2>/dev/null
  ' >>"$LOG" 2>&1 || true
fi

# Docker wrappers (备用)
make_wrapper() {
  local name="$1" cmd="$2"
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx kali; then
    cat > "/usr/local/bin/${name}" <<WEOF
#!/bin/bash
exec docker exec -i kali ${cmd} "\$@"
WEOF
    chmod +x "/usr/local/bin/${name}"
    ln -sf "/usr/local/bin/${name}" "/usr/bin/${name}" 2>/dev/null || true
    log "wrapper $name -> kali docker"
  fi
}
command -v msfconsole &>/dev/null || make_wrapper msfconsole msfconsole
command -v msfvenom &>/dev/null || make_wrapper msfvenom msfvenom
command -v rizin &>/dev/null || make_wrapper rizin rizin

# ── dex2jar ─────────────────────────────────────────────────
if [ ! -f /opt/dex-tools-v2.4/d2j-dex2jar.sh ]; then
  curl -fsSL -o /data/tmp/d2j.zip "https://github.com/pxb1988/dex2jar/releases/download/v2.4/dex-tools-v2.4.zip" 2>>"$LOG" || true
  unzip -qo /data/tmp/d2j.zip -d /opt/ 2>>"$LOG" || true
  ln -sfn /opt/dex-tools-v2.4 /opt/dex2jar 2>/dev/null || true
fi

# ── 符号链接 ────────────────────────────────────────────────
log "Creating symlinks..."
[ -f /opt/dex-tools-v2.4/d2j-dex2jar.sh ] && link_bin /opt/dex-tools-v2.4/d2j-dex2jar.sh dex2jar
[ -f /opt/dex2jar/d2j-dex2jar.sh ] && link_bin /opt/dex2jar/d2j-dex2jar.sh dex2jar
[ -f /data/tools/ligolo-agent ] && link_bin /data/tools/ligolo-agent ligolo-agent
[ -f /data/tools/ligolo-proxy ] && link_bin /data/tools/ligolo-proxy ligolo-proxy
[ -f /data/go/bin/sliver-client ] && link_bin /data/go/bin/sliver-client sliver-client
[ -f /data/go/bin/sliver-server ] && link_bin /data/go/bin/sliver-server sliver-server
[ -f /data/tools/sqlmap/sqlmap.py ] && link_bin /data/tools/sqlmap/sqlmap.py sqlmap
[ -f /data/tools/sqlmap/sqlmap.py ] && link_bin /data/tools/sqlmap/sqlmap.py sqlmap.py
command -v searchsploit &>/dev/null || link_bin /usr/bin/searchsploit searchsploit 2>/dev/null || true

# ── Havoc C2 ────────────────────────────────────────────────
if ! command -v havoc &>/dev/null; then
  log "Building Havoc..."
  if [ ! -d /data/src/Havoc/.git ]; then
    git clone --depth 1 https://github.com/HavocFramework/Havoc.git /data/src/Havoc 2>>"$LOG" || true
  fi
  if [ -d /data/src/Havoc ]; then
    (cd /data/src/Havoc && make ts-build 2>>"$LOG" && make server-build 2>>"$LOG") || true
    for f in /data/src/Havoc/havoc /data/src/Havoc/Build/havoc /data/src/Havoc/build/havoc; do
      [ -f "$f" ] && link_bin "$f" havoc && break
    done
  fi
fi

# ── OpenVAS (Docker) ────────────────────────────────────────
if ! docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx openvas; then
  log "Pulling OpenVAS docker..."
  docker pull mikesplain/openvas 2>>"$LOG" || true
  docker run -d --name openvas -p 9392:9392 --restart unless-stopped mikesplain/openvas 2>>"$LOG" || true
fi

# ── Maltego CE ──────────────────────────────────────────────
if ! command -v maltego &>/dev/null && [ ! -d /usr/local/maltego ]; then
  log "Installing Maltego CE..."
  for url in \
    "https://maltego-downloads.s3.us-east-2.amazonaws.com/linux/Maltego.v4.9.0.deb" \
    "https://maltego-downloads.s3.us-east-2.amazonaws.com/linux/Maltego.v4.8.1.deb"; do
    curl -fsSL -o /data/downloads/maltego.deb "$url" 2>>"$LOG" && break
  done
  if [ -f /data/downloads/maltego.deb ]; then
    dpkg -i /data/downloads/maltego.deb 2>>"$LOG" || apt-get install -f -y -qq 2>>"$LOG" || true
    [ -f /usr/local/bin/maltego ] && log "Maltego installed" || true
  fi
fi

# ── BeEF ────────────────────────────────────────────────────
if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qi beef; then
  docker start beef 2>>"$LOG" || true
elif [ -d /data/c2/beef ]; then
  (cd /data/c2/beef && docker compose up -d 2>>"$LOG") || true
fi

# ── 运行已有补齐脚本 ────────────────────────────────────────
if [ -x /data/tools/install-gap-tools.sh ]; then
  log "Running install-gap-tools.sh..."
  bash /data/tools/install-gap-tools.sh >>"$LOG" 2>&1 || true
fi

# ── PATH ────────────────────────────────────────────────────
cat > /etc/profile.d/data-workspace.sh <<'PROFILE'
export GOPATH=/data/go
export GOBIN=/data/go/bin
export PATH="/usr/local/go/bin:/data/go/bin:/data/tools/bin:/data/tools:/usr/local/bin:/opt/ghidra:/opt/dex2jar:/opt/burpsuite:$PATH"
export PIP_CACHE_DIR=/data/pip-cache
export TMPDIR=/data/tmp
PROFILE
grep -q 'data-workspace' /root/.bashrc 2>/dev/null || echo 'source /etc/profile.d/data-workspace.sh' >> /root/.bashrc

# ── 验证 ────────────────────────────────────────────────────
log "========== VERIFY =========="
TOOLS="msfconsole msfvenom rizin frida frida-ps qemu-system-x86_64 hashid hash-identifier evil-winrm sqlmap dex2jar ligolo-agent ligolo-proxy sliver-client sliver-server volatility volatility3 drozer objection searchsploit havoc maltego spiderfoot go"
for t in $TOOLS; do
  if command -v "$t" &>/dev/null; then
    log "OK  $t -> $(command -v "$t")"
  else
    log "MISS $t"
  fi
done
log "dpkg: $(dpkg -l 2>/dev/null | awk 'NR>5 && $1=="ii"{c++} END{print c+0}')"
log "docker: $(docker ps --format '{{.Names}}' 2>/dev/null | tr '\n' ' ')"
log "========== INSTALL DONE =========="
