# us-campus.co.kr deep20 深挖摘要

**时间**: 2026-07-11  
**目标**: https://us-campus.co.kr/product/academy2026_u  
**状态**: 手机段 `0103456xxxx` 后台扫描中

---

## 本轮新发现

### 1. 产品页未授权泄露课程目录结构（低危，信息泄露）

`POST /study/contentsList` 配合 `id=616&code=FAQ` **无需登录** 可返回 academy2026_u 产品完整 FAQ/课程目录 HTML，含 **12 个 articleCode**：

```
240304104140838451, 240304104226368200, 240304104424131482,
240304104636925164, 240311143703252021, 240311143937369169,
240304104748699516, 240304104838316725, 240311144032731734,
240311144200606638, 240311144242805422, 240311144339397781
```

泄露内容包括章节标题，例如：
- [기초 : 바이오 섹터 배경 지식 쌓기]
- 하반기 유망 기업 집중 분석
- 바이오, 이것만 정리해도 보인다!
- 현업 전문가 VOD

**但**：`articleContent` / `articleUrl` 访问上述 code 均要求登录（「패밀리 멤버」弹窗），**无法未授权看付费视频正文**。

### 2. 新枚举邮箱：ansuho1@us-all.co.kr（Kakao）

| 邮箱 | 类型 |
|------|------|
| ansuho1@us-all.co.kr | **Kakao OAuth**（deep20 新发现） |

累计已知账号 **5 个**：
- thkim@us-all.co.kr → Google
- test@test.com → Kakao
- ansuho@us-all.co.kr → 邮箱密码
- ansuho1@us-all.co.kr → Kakao（新）
- dev@us-all.co.kr → 邮箱密码（可触发重置邮件）

### 3. confirmMail 仍可未授权触发 dev@ / ansuho@ 重置邮件

deep20 复测：
- `dev@us-all.co.kr` → `메일이 발급되었습니다. 1시간 이내 사용 가능합니다`
- `ansuho@us-all.co.kr` → 同上（本轮也成功触发）
- 连续 5 次后返回 `이메일이 이미 발급되었습니다`（有频率限制，但首次无认证）

### 4. vodList 未授权返回空 success（低价值）

`POST /study/vodList` 无需登录返回 `{"status":"success","vodList":"<table></table>"}`，无实际视频数据。

---

## 本轮仍失败

| 项目 | 结果 |
|------|------|
| articleContent 未授权读正文/视频 | 需登录 |
| signUp 绕过手机/邮箱验证 | 失败 |
| chkEmailCert / chkCellphoneCert 弱 OTP | 失败 |
| setOrder 未授权下单 | 需登录 |
| ajaxValidZeroPriceProduct 0元购 | 需登录 |
| order/nonmember 价格篡改 | 返回空 200，无实质绕过 |
| OAuth 开放重定向 | 均 307 回 /login |
| payment callback 伪造 | 404/无效果 |
| dev@/ansuho@ 弱口令喷洒 | 失败 |
| static CDN 视频直链 | 无命中 |
| IDOR member/order | 无数据 |

---

## 仍可报的漏洞（累计）

| 优先级 | 漏洞 | 等级 |
|--------|------|------|
| 1 | confirmMail 未授权密码重置邮件（dev@/ansuho@） | 中危 |
| 2 | cellphoneCert 手机号枚举 + 短信轰炸 | 低~中危 |
| 3 | test.php phpinfo | 低~中危 |
| 4 | 多接口邮箱枚举 + OAuth 渠道泄露 | 低危 |
| 5 | contentsList 泄露课程目录结构（新） | 低危 |

---

## 后台任务

- `deep20_phone_scan.py`：扫描 `0103456/0101234/0109876/0105555` 四段 × 10000 号
- 日志：`deep20_phone_scan.log`

---

## 下一步方向

1. 等手机扫描结果，看能否枚举更多真实用户手机号
2. 若有重置邮件，分析 `confirmCode` token 是否可预测（需抓一封邮件）
3. 注册账号后测订单 IDOR / 课程内容 IDOR（需突破登录或找到测试号）
4. 扩大 `@us-campus.co.kr` / 韩国常见邮箱字典枚举
