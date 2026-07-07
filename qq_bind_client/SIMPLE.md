# QQ 查绑 — 3 分钟看懂

## 漏洞 / 原理

手机号 + 短信验证 → QQ 内部返回绑定账号信息 → 明文 QQ（key_uin / saltUin）

- **QQ 9.2.60 以前**：wtlogin TLV 0x543
- **QQ 9.2.60+**：NTLogin（`SsoNTLoginCheckSms`）→ `onGetSaltUinList` → 多账号选择

没有短信验证码 = 拿不到 QQ。必须 Root 手机 + Frida 在验证瞬间截获。

---

## 使用（v1.3.4）

1. **启动 Frida**
2. **一键开始**
3. 手机 QQ → 手机号登录 → **停在输入验证码页**
4. **注入并抓取** → 日志应出现 `已注入 :MSF` 和主进程
5. **立刻填验证码并提交**
6. 若弹出 **「选择账号」** → **必须点选一个 QQ**（不要取消！）
7. 点 **验证码后抓取** 或看 **QQ号: xxxxx**

没结果 → **诊断** → 确认多账号弹窗已选择

### 下载

https://github.com/yitang099/1/releases/download/qq-bind-v1.3.4/qq_bind.exe

窗口标题必须是 **QQ 查绑工具 v1.3.4**

---

## v1.3.4 针对 QQ 9.2.60

| 问题 | 修复 |
|------|------|
| 旧 wtlogin/HashMap Hook 不触发 | 新增 NTLogin `PhoneSmsLogin` / `SaltUin` Hook |
| logcat 无 key_uin | 增加 `onGetSaltUinList` / `saltUin` 模式 |
| device_scrape 全目录 grep 超时 | 定向 `AppUinStoreFile` + strings |
| 用户取消多账号弹窗 | UI 提示必须点选账号 |

---

## 小米 K60 必开

- USB 调试 + **USB 调试（安全设置）**
- Magisk 给 Shell/ADB root
- QQ 省电 → **无限制**
- frida-server 文件版本 = **17.15.3**（与 exe 一致）
