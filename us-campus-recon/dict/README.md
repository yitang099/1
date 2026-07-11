# us-campus 邮箱枚举字典 & 脚本

## 文件说明

| 文件 | 大小 | 说明 |
|------|------|------|
| `emails_kr_large.txt` | **102 万条 / 21MB** | 韩国定向邮箱大字典 |
| `fast_email_enum.py` | 脚本 | 80 并发高速枚举 |
| `gen_emails_kr.py` | 生成器 | 可重新生成/扩展字典 |

## 字典构成

- **85,718** 个本地部分（localpart）
- **12** 个域名：
  - `naver.com` `gmail.com` `daum.net` `hanmail.net` `kakao.com` `nate.com`
  - `us-all.co.kr` `us-campus.co.kr` `usall.co.kr`
  - `outlook.com` `hotmail.com` `yahoo.com`
- 组合：韩国姓名字典 + 企业前缀 + 数字后缀

## 使用方法

```bash
# 全量扫描（约 1.5~2 小时，80 并发）
python3 fast_email_enum.py

# 指定字典路径
python3 fast_email_enum.py --dict /你的路径/emails_kr_large.txt

# 测试前 1000 条
python3 fast_email_enum.py --limit 1000

# 调整并发（推荐 50~80）
python3 fast_email_enum.py --concurrency 80

# 结果输出到
# dict/enum_hits.json
```

## 命中判断

只打 `POST /login/login` 一个接口：
- `비밀번호가 일치하지 않습니다` → **已注册**
- `이메일 또는 비밀번호를 다시 입력해 주세요` → 未注册

## 预计速度

| 并发 | 速度 | 扫完 102 万 |
|------|------|-------------|
| 80 | ~160 个/秒 | ~1.8 小时 |
| 50 | ~90 个/秒 | ~3 小时 |

## 重新生成字典

```bash
python3 gen_emails_kr.py
```
