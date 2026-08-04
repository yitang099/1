#!/usr/bin/env python3
import json
import re
from pathlib import Path

OUT = Path("/data/recon/hao998/dump")
kami_path = OUT / "contact_kami.tsv"
if not kami_path.exists():
    raise SystemExit("missing contact_kami.tsv")
kami = kami_path.read_text(encoding="utf-8").splitlines()
best = {}
for ln in kami:
    parts = ln.split("\t", 3)
    if len(parts) < 4:
        continue
    tn, kw, pw, secret = parts
    if tn not in best or len(secret) > len(best[tn][3]):
        best[tn] = (tn, kw, pw, secret)
rows = list(best.values())
(OUT / "contact_kami_dedup.tsv").write_text(
    "\n".join("\t".join(r) for r in rows) + "\n", encoding="utf-8"
)
accounts = []
for tn, kw, pw, secret in rows:
    blob = secret.replace("<br/>", "\n").replace("<br>", "\n")
    for line in re.split(r"[\r\n]+", blob):
        line = line.strip()
        if line:
            accounts.append(line)
uniq = sorted(set(accounts))
(OUT / "contact_kami_accounts.txt").write_text("\n".join(uniq) + "\n", encoding="utf-8")
stats = {
    "orders": len(rows),
    "account_lines": len(uniq),
    "hit_keywords": sorted({r[1] for r in rows}),
    "trade_nos": [r[0] for r in rows],
}
(OUT / "contact_kami_stats.json").write_text(
    json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(stats, ensure_ascii=False, indent=2))
for tn, kw, pw, secret in rows:
    n = len([x for x in re.split(r"[\r\n]+", secret.replace("<br/>", "\n")) if x.strip()])
    print(tn, "kw=" + kw, "cards~", n)
