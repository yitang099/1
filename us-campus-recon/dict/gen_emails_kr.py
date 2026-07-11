#!/usr/bin/env python3
"""生成 us-campus 邮箱枚举大字典"""
import itertools
import os

OUT = "/workspace/us-campus-recon/dict/emails_kr_large.txt"

# 韩国常见姓（罗马音）
SURNAMES = [
    "kim", "lee", "park", "choi", "jung", "joon", "jun", "cho", "choo", "chae",
    "kang", "yoon", "yun", "jang", "lim", "im", "han", "oha", "oh", "seo",
    "shin", "kwon", "hwang", "an", "ahn", "song", "hong", "moon", "mun",
    "baek", "paek", "bae", "pae", "nam", "roh", "noh", "ko", "go", "gu",
    "ku", "min", "ryu", "yu", "yoo", "jeon", "chun", "cheon", "yang", "wook",
    "wook", "sun", "soo", "su", "hyun", "hyeon", "ji", "jin", "min", "ho",
]

# 常见名（罗马音）
GIVEN = [
    "minjun", "seo", "joon", "jun", "hyun", "hyeon", "ji", "jin", "soo", "su",
    "young", "yeong", "yong", "ho", "hoon", "hun", "woo", "wu", "u", "bin",
    "been", "vin", "eun", "un", "hee", "he", "ae", "a", "mi", "me",
    "na", "da", "tae", "te", "sung", "seong", "song", "jong", "jeong", "jung",
    "kyung", "gyeong", "sun", "seon", "won", "woon", "gun", "geon", "hwan",
    "taehyung", "taehyun", "jaehyung", "jaehyun", "seojae", "sunwoo", "yeseong",
    "ansuho", "taehyung", "seungho", "donghyun", "sangwoo", "minho", "jihoon",
    "yuna", "jiyeon", "jieun", "minji", "hyejin", "sujin", "eunji", "yewon",
    "haein", "nayeon", "chaeyoung", "dahyun", "momo", "sana", "mina",
]

# 通用前缀（企业/职能）
PREFIXES = [
    "admin", "dev", "test", "info", "support", "sales", "marketing", "hr",
    "ceo", "cto", "cfo", "coo", "ops", "web", "mail", "help", "helpdesk",
    "security", "privacy", "finance", "account", "accounting", "edu", "edu",
    "academy", "campus", "usall", "usalliance", "alliance", "stock", "invest",
    "trade", "trader", "fund", "asset", "capital", "wealth", "money", "bank",
    "contact", "service", "manager", "staff", "team", "office", "biz",
    "business", "partner", "customer", "member", "user", "guest", "demo",
    "thkim", "ansuho", "sunwoo", "yim", "lim", "kimsw", "kimsunwoo",
]

# 数字后缀
SUFFIXES = ["", "1", "2", "3", "12", "88", "99", "123", "007", "01", "02",
            "2020", "2021", "2022", "2023", "2024", "2025", "2026",
            "77", "89", "00", "11", "22", "33"]

# 域名（韩国金融平台用户优先）
DOMAINS = [
    "naver.com",       # 韩国最大
    "gmail.com",
    "daum.net",
    "hanmail.net",
    "kakao.com",
    "nate.com",
    "us-all.co.kr",    # 目标公司员工
    "us-campus.co.kr",
    "usall.co.kr",
    "outlook.com",
    "hotmail.com",
    "yahoo.com",
]

def gen_localparts():
    seen = set()
    # 前缀直出
    for p in PREFIXES:
        for s in SUFFIXES:
            lp = f"{p}{s}" if s else p
            if lp not in seen:
                seen.add(lp)
                yield lp
    # 姓名组合
    for sur in SURNAMES:
        for giv in GIVEN:
            for combo in [f"{sur}{giv}", f"{giv}{sur}", f"{sur}.{giv}", f"{sur}_{giv}",
                          f"{sur}{giv[0]}", f"{giv}{sur[0]}"]:
                if combo not in seen and 3 <= len(combo) <= 30:
                    seen.add(combo)
                    yield combo
            for suf in ["", "1", "12", "88", "123", "2024", "2025"]:
                for combo in [f"{sur}{giv}{suf}", f"{giv}{sur}{suf}"]:
                    if combo not in seen and len(combo) <= 35:
                        seen.add(combo)
                        yield combo
    # 姓 + 数字
    for sur in SURNAMES:
        for n in range(0, 100):
            for fmt in [f"{sur}{n}", f"{sur}{n:02d}", f"{sur}{n:03d}"]:
                if fmt not in seen:
                    seen.add(fmt)
                    yield fmt
    # 单名
    for giv in GIVEN:
        for suf in SUFFIXES:
            lp = f"{giv}{suf}" if suf else giv
            if lp not in seen and len(lp) >= 3:
                seen.add(lp)
                yield lp

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    count = 0
    with open(OUT, "w") as f:
        for lp in gen_localparts():
            for domain in DOMAINS:
                email = f"{lp}@{domain}"
                f.write(email + "\n")
                count += 1
    print(f"生成完成: {OUT}")
    print(f"总条数: {count:,}")
    # 统计
    with open(OUT) as f:
        lines = f.readlines()
    from collections import Counter
    doms = Counter(l.split("@")[1].strip() for l in lines)
    print("域名分布:")
    for d, c in doms.most_common():
        print(f"  @{d}: {c:,}")

if __name__ == "__main__":
    main()
