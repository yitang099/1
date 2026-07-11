#!/usr/bin/env python3
"""生成韩国手机号大字典"""
import os
import sys

DICT_DIR = "/workspace/us-campus-recon/dict"

# 韩国手机号段
# 010: 主力 (1亿)
# 011,016,017,018,019: 旧号段 (各1000万)
PREFIXES_010 = ["010"]  # 全量
PREFIXES_LEGACY = ["011", "016", "017", "018", "019"]

# 高命中前缀（基于实测 deep21 命中段 + 常见模式）
HOT_PREFIXES = [
    # 已确认命中段
    "0103456", "0102024", "0102222", "0103333",
    "01020241", "01020243", "01020244", "01020245", "01020249",
    "01020250", "01020251", "01020254", "01020258", "01020260",
    "01020261", "01020264", "01020265",
    "01022221", "01022223", "01022225", "01022228", "01022229",
    "01033332", "01034560", "01034561", "01034563", "01034564",
    # 年份/重复数字段
    "0101234", "0102025", "0102026", "0102020", "0102021", "0102022", "0102023",
    "0104444", "0105555", "0106666", "0107777", "0108888", "0109999",
    "0100000", "0101111", "0101000", "0102000", "0103000", "0104000",
    "0105000", "0106000", "0107000", "0108000", "0109000",
    "0101010", "0102020", "0103030", "0104040", "0105050",
    "0101212", "0101313", "0101414", "0101515", "0101616",
    "0101717", "0101818", "0101919",
    # 运营商常见号段前4位
    "0102", "0103", "0104", "0105", "0106", "0107", "0108", "0109",
    "01020", "01021", "01022", "01023", "01024", "01025",
    "01030", "01031", "01032", "01033", "01034", "01035",
    "01040", "01041", "01042", "01043", "01044", "01045",
    "01050", "01051", "01052", "01053", "01054", "01055",
    "01060", "01061", "01062", "01063", "01064", "01065",
    "01070", "01071", "01072", "01073", "01074", "01075",
    "01080", "01081", "01082", "01083", "01084", "01085",
    "01090", "01091", "01092", "01093", "01094", "01095",
]

# 已知命中号 ±radius 邻域扫描
SEED_PHONES = [
    "01012345678", "01034564321", "01000000000",
    "01034560419", "01034560988", "01034560073", "01034560161",
    "01020241176", "01020243087", "01020244081", "01020245236",
    "01022221015", "01022225208", "01033332149",
]


def gen_range(path: str, prefix: str, start: int, end: int):
    """生成 prefix + 8位中的后几位"""
    # prefix 如 010 -> 需要8位后缀 -> 010xxxxxxxx
    # prefix 如 0103456 -> 需要4位后缀
    suffix_len = 11 - len(prefix)
    count = 0
    with open(path, "w") as f:
        for i in range(start, end):
            phone = f"{prefix}{i:0{suffix_len}d}"
            f.write(phone + "\n")
            count += 1
            if count % 5_000_000 == 0:
                print(f"  {path}: {count:,} ...", flush=True)
    return count


def gen_full_010(path: str):
  """010 全段 00000000-99999999 = 1亿"""
  print(f"生成 010 全量 -> {path}", flush=True)
  return gen_range(path, "010", 0, 100_000_000)


def gen_hot(path: str):
    """高命中前缀段"""
    total = 0
    with open(path, "w") as f:
        for hp in HOT_PREFIXES:
            suffix_len = 11 - len(hp)
            for i in range(10 ** suffix_len):
                f.write(f"{hp}{i:0{suffix_len}d}\n")
                total += 1
    return total


def gen_targeted(path: str, radius: int = 500):
    """已知命中号前后邻域（高价值小字典）"""
    seen = set()
    total = 0
    with open(path, "w") as f:
        for seed in SEED_PHONES:
            base = int(seed)
            for delta in range(-radius, radius + 1):
                phone = f"{base + delta:011d}"
                if phone not in seen and phone.startswith("010") and len(phone) == 11:
                    seen.add(phone)
                    f.write(phone + "\n")
                    total += 1
    return total


def gen_legacy(path: str):
    """011/016/017/018/019 各1000万"""
    total = 0
    with open(path, "w") as f:
        for pfx in PREFIXES_LEGACY:
            print(f"  legacy {pfx}...", flush=True)
            for i in range(10_000_000):
                f.write(f"{pfx}{i:07d}\n")
                total += 1
                if total % 10_000_000 == 0:
                    print(f"    {total:,}", flush=True)
    return total


def main():
    os.makedirs(DICT_DIR, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "hot"):
        p = f"{DICT_DIR}/phones_kr_hot.txt"
        n = gen_hot(p)
        print(f"phones_kr_hot.txt: {n:,} ({os.path.getsize(p)/1024/1024:.1f} MB)\n", flush=True)

    if mode in ("all", "010"):
        p = f"{DICT_DIR}/phones_010_full.txt"
        n = gen_full_010(p)
        print(f"phones_010_full.txt: {n:,} ({os.path.getsize(p)/1024/1024:.1f} MB)\n", flush=True)

    if mode in ("all", "legacy"):
        p = f"{DICT_DIR}/phones_legacy.txt"
        n = gen_legacy(p)
        print(f"phones_legacy.txt: {n:,} ({os.path.getsize(p)/1024/1024:.1f} MB)\n", flush=True)

    if mode in ("all", "targeted"):
        p = f"{DICT_DIR}/phones_kr_targeted.txt"
        n = gen_targeted(p, radius=1000)
        print(f"phones_kr_targeted.txt: {n:,} ({os.path.getsize(p)/1024:.1f} KB)\n", flush=True)

    if mode == "sample":
        # 每段采样：010 全段每100个取1个 = 100万
        p = f"{DICT_DIR}/phones_010_sample1pct.txt"
        with open(p, "w") as f:
            for i in range(0, 100_000_000, 100):
                f.write(f"010{i:08d}\n")
        print(f"phones_010_sample1pct.txt: 1,000,000", flush=True)

    if mode == "sample10":
        # 每10个取1个 = 1000万
        p = f"{DICT_DIR}/phones_010_sample10pct.txt"
        with open(p, "w") as f:
            for i in range(0, 100_000_000, 10):
                f.write(f"010{i:08d}\n")
        print(f"phones_010_sample10pct.txt: 10,000,000", flush=True)


if __name__ == "__main__":
    main()
