#!/usr/bin/env python3
"""经 CN 跳板 + 青果代理执行 yujuqq 扫描命令."""
from __future__ import annotations

import sys

import paramiko

HOST = "42.240.167.114"
USER = "root"
PASS = "DX4LmrDaPfd9"


def run(cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=20)
    try:
        _, stdout, stderr = c.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        return stdout.channel.recv_exit_status(), out, err
    finally:
        c.close()


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else (
        "source /data/config/proxy.env 2>/dev/null || /data/automation/bin/qg-proxy-fetch.sh; "
        "source /data/config/proxy.env; "
        "CK=/tmp/yj_cn.ck; "
        "curl -sk -m 25 -x \"$PROXY_URL\" -c $CK -b $CK -A 'Mozilla/5.0' -H 'Accept-Language: zh-CN' "
        "'https://yujuqq.top/shop/' -w 'home:%{http_code}\\n' -o /dev/null; "
        "curl -sk -m 20 -x \"$PROXY_URL\" -b $CK -H 'X-Requested-With: XMLHttpRequest' "
        "-H 'Referer: https://yujuqq.top/shop/' 'https://yujuqq.top/shop/ajax.php?act=getcount'; echo; "
        "curl -sk -m 15 -x \"$PROXY_URL\" -b $CK "
        "'https://yujuqq.top/shop/other/getshop.php?trade_no=20260713211955253'; echo"
    )
    code, out, err = run(cmd)
    print(out)
    if err:
        print(err, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
