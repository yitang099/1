#!/usr/bin/env python3
"""生成超大韩国邮箱字典 (目标 500万+)"""
import os
import itertools

OUT = "/workspace/us-campus-recon/dict/emails_kr_xl.txt"

DOMAINS = [
    "naver.com", "gmail.com", "daum.net", "hanmail.net", "kakao.com", "nate.com",
    "us-all.co.kr", "us-campus.co.kr", "usall.co.kr",
    "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "proton.me",
    "live.com", "msn.com",
]

SURNAMES = list(dict.fromkeys([
    "kim", "gim", "lee", "yi", "ri", "park", "pak", "choi", "choe", "chui",
    "jung", "jeong", "joung", "cho", "choo", "chae", "chai", "kang", "gang",
    "yoon", "yun", "yeon", "jang", "chang", "lim", "im", "rhim", "han", "hahn",
    "oha", "oh", "o", "seo", "suh", "seo", "shin", "sin", "shim", "sim",
    "kwon", "gwon", "kweon", "hwang", "whang", "an", "ahn", "ann", "song",
    "sung", "hong", "moon", "mun", "baek", "paek", "bae", "pae", "pe", "nam",
    "roh", "noh", "no", "ko", "go", "gu", "ku", "min", "myun", "myeon",
    "ryu", "ryoo", "yu", "yoo", "you", "jeon", "jun", "chun", "cheon", "cheon",
    "yang", "yangu", "wook", "wook", "ouk", "sun", "seon", "soo", "su", "seo",
    "hyun", "hyeon", "hyon", "ji", "jee", "jin", "jean", "ho", "hoo", "hu",
    "won", "woon", "wun", "bin", "been", "vin", "byn", "eun", "un", "en",
    "hee", "he", "hae", "ae", "a", "mi", "me", "ma", "na", "da", "ta", "te",
]))

GIVEN = list(dict.fromkeys([
    "minjun", "minjoon", "minje", "seo", "seojun", "seojoon", "joon", "jun",
    "junho", "junhyuk", "hyun", "hyeon", "hyunwoo", "hyunjoon", "ji", "jihun",
    "jihoon", "jimin", "jim", "jin", "jinwoo", "jinho", "soo", "su", "soohyun",
    "sooyoung", "young", "yeong", "yong", "yoon", "youn", "ho", "hoon", "hun",
    "hyuk", "hyeok", "woo", "wu", "u", "woong", "ung", "bin", "been", "vin",
    "eun", "eunji", "eunhye", "hee", "he", "hae", "ae", "mi", "mina", "minji",
    "sung", "seong", "song", "jong", "jeong", "jung", "kyung", "gyeong", "gyung",
    "sun", "seon", "son", "won", "woon", "gun", "geon", "hwan", "hwan", "tae",
    "taehyung", "taehyun", "taehun", "jae", "jaehyun", "jaehyung", "jaewon",
    "seojae", "seojaehyung", "sunwoo", "seonwoo", "sungho", "seungho", "sang",
    "sangwoo", "sangho", "dong", "donghyun", "dongho", "minho", "minhyuk",
    "yuna", "yoona", "jiyeon", "jiyun", "jieun", "jiwon", "jiwoo", "hyejin",
    "sujin", "seojin", "eunji", "yewon", "yewon", "chaewon", "haein", "nayeon",
    "dahyun", "dayeon", "soyeon", "soyun", "hayoon", "hayun", "jiu", "jio",
    "ansuho", "taehyung", "seunghyun", "momo", "sana", "mina", "dahyun",
    "subin", "subeen", "yubin", "yubeen", "gahee", "kahee", "bora", "boram",
    "jisoo", "jisoo", "jisuk", "jisook", "myung", "myeong", "myunghee",
]))

PREFIXES = [
    "admin", "dev", "test", "info", "support", "sales", "marketing", "hr", "pr",
    "ceo", "cto", "cfo", "coo", "cmo", "ops", "it", "web", "mail", "email",
    "help", "helpdesk", "security", "privacy", "legal", "finance", "account",
    "accounting", "tax", "edu", "education", "academy", "campus", "school",
    "usall", "usalliance", "alliance", "uscampus", "uscamp", "stock", "invest",
    "investment", "trade", "trader", "trading", "fund", "asset", "capital",
    "wealth", "money", "bank", "banking", "contact", "service", "customer",
    "member", "user", "guest", "demo", "sample", "noreply", "no-reply",
    "manager", "staff", "team", "office", "biz", "business", "partner",
    "thkim", "ansuho", "sunwoo", "yim", "kimsunwoo", "kimsun", "kimsw",
    "leesw", "parksw", "choisw", "financekr", "stockkr", "investkr",
]

NUM_SUFFIX = [""] + [str(i) for i in range(100)] + [
    "123", "321", "007", "888", "999", "000", "111", "222", "333",
    "2020", "2021", "2022", "2023", "2024", "2025", "2026",
    "01", "02", "03", "12", "23", "88", "99", "77", "66",
]

SEP = ["", ".", "_", "-"]


def write_batch(f, localparts: set, domains=DOMAINS):
    n = 0
    for lp in localparts:
        for d in domains:
            f.write(f"{lp}@{d}\n")
            n += 1
    return n


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    total = 0
    seen = set()

    with open(OUT, "w") as f:
        # 1) 前缀 × 数字后缀
        batch = set()
        for p in PREFIXES:
            for s in NUM_SUFFIX:
                lp = f"{p}{s}"
                if lp not in seen:
                    seen.add(lp)
                    batch.add(lp)
        total += write_batch(f, batch)
        print(f"[1] prefixes: {len(batch):,} localparts -> +{len(batch)*len(DOMAINS):,}", flush=True)
        batch.clear()

        # 2) 姓+名 全组合 × 少量后缀
        for sur in SURNAMES:
            for giv in GIVEN:
                for sep in SEP:
                    for suf in ["", "1", "12", "88", "123", "2024", "2025"]:
                        for combo in [f"{sur}{sep}{giv}{suf}", f"{giv}{sep}{sur}{suf}",
                                      f"{sur}{giv}{suf}", f"{giv}{sur}{suf}"]:
                            if 3 <= len(combo) <= 40 and combo not in seen:
                                seen.add(combo)
                                batch.add(combo)
                if len(batch) >= 50000:
                    total += write_batch(f, batch)
                    batch.clear()
        if batch:
            total += write_batch(f, batch)
            batch.clear()
        print(f"[2] name combos done, total={total:,}", flush=True)

        # 3) 姓 + 4位数字 (0000-9999) 前20大姓
        for sur in SURNAMES[:25]:
            for n in range(10000):
                for fmt in [f"{sur}{n}", f"{sur}{n:04d}"]:
                    if fmt not in seen:
                        seen.add(fmt)
                        batch.add(fmt)
                if len(batch) >= 100000:
                    total += write_batch(f, batch)
                    batch.clear()
        if batch:
            total += write_batch(f, batch)
            batch.clear()
        print(f"[3] surname+digits done, total={total:,}", flush=True)

        # 4) 名 + 3-4位数字 前40名
        for giv in GIVEN[:40]:
            for n in range(1000):
                lp = f"{giv}{n}"
                if lp not in seen:
                    seen.add(lp)
                    batch.add(lp)
            for n in range(10000):
                lp = f"{giv}{n:04d}"
                if lp not in seen:
                    seen.add(lp)
                    batch.add(lp)
                if len(batch) >= 100000:
                    total += write_batch(f, batch)
                    batch.clear()
        if batch:
            total += write_batch(f, batch)
            batch.clear()
        print(f"[4] given+digits done, total={total:,}", flush=True)

        # 5) 双字母+数字 韩国常见缩写
        for a in "abcdefghijklmnopqrstuvwxyz":
            for b in "abcdefghijklmnopqrstuvwxyz":
                for n in range(1000):
                    lp = f"{a}{b}{n}"
                    if lp not in seen:
                        seen.add(lp)
                        batch.add(lp)
                if len(batch) >= 200000:
                    total += write_batch(f, batch)
                    batch.clear()
        if batch:
            total += write_batch(f, batch)
            batch.clear()
        print(f"[5] 2letter+digits done, total={total:,}", flush=True)

        # 6) 姓.名.数字 韩国邮箱常见
        for sur in SURNAMES[:15]:
            for giv in GIVEN[:30]:
                for n in ["", "1", "12", "88", "2024", "2025"] + [str(x) for x in range(100)]:
                    for combo in [f"{sur}.{giv}{n}", f"{sur}{giv[0]}{n}", f"{sur[0]}{giv}{n}"]:
                        if 3 <= len(combo) <= 35 and combo not in seen:
                            seen.add(combo)
                            batch.add(combo)
                    if len(batch) >= 100000:
                        total += write_batch(f, batch)
                        batch.clear()
        if batch:
            total += write_batch(f, batch)
            batch.clear()
        print(f"[6] dotted names done, total={total:,}", flush=True)

        # 7) 姓 + 出生年 1970-2010
        for sur in SURNAMES[:35]:
            for year in range(1970, 2011):
                for fmt in [f"{sur}{year}", f"{sur}{year%100:02d}", f"{sur}.{year}",
                            f"{sur}_{year}", f"{sur}{year}1", f"{sur}{year}88"]:
                    if fmt not in seen:
                        seen.add(fmt)
                        batch.add(fmt)
                if len(batch) >= 100000:
                    total += write_batch(f, batch)
                    batch.clear()
        if batch:
            total += write_batch(f, batch)
            batch.clear()
        print(f"[7] birthyear done, total={total:,}", flush=True)

        # 8) 三字母缩写 + 4位数字 (韩国邮箱常见 kim1234 类扩展)
        letters = "aehjklpmsw"
        for a in letters:
            for b in letters:
                for c in letters:
                    for n in range(10000):
                        lp = f"{a}{b}{c}{n:04d}"
                        if lp not in seen:
                            seen.add(lp)
                            batch.add(lp)
                    if len(batch) >= 200000:
                        total += write_batch(f, batch)
                        batch.clear()
        if batch:
            total += write_batch(f, batch)
            batch.clear()
        print(f"[8] 3letter+4digit done, total={total:,}", flush=True)

        # 9) 手机号样式 localpart (010xxxxxxxx)
        for n in range(0, 100_000_000, 7):  # 步进采样约1400万
            lp = f"010{n:08d}"
            if lp not in seen:
                seen.add(lp)
                batch.add(lp)
            if len(batch) >= 200000:
                total += write_batch(f, batch)
                batch.clear()
        if batch:
            total += write_batch(f, batch)
            batch.clear()
        print(f"[9] phone-style localparts done, total={total:,}", flush=True)

    print(f"\n完成: {OUT}")
    print(f"总条数: {total:,}")
    print(f"文件大小: {os.path.getsize(OUT)/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
