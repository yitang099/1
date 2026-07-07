# QQ 查绑 — 3 分钟看懂

## 漏洞 / 原理

手机号 + 短信验证 → QQ 内部 wtlogin 返回 TLV 0x543 → 明文 QQ（key_uin）

没有短信验证码 = 拿不到 QQ。必须 Root 手机 + Frida 在验证瞬间截获。

---

## 使用（v1.3.0）

1. **启动 Frida**
2. **一键开始**
3. 手机 QQ → 手机号登录 → **停在输入验证码页**
4. **注入并抓取** → 日志应出现 `已注入 :MSF` 和主进程
5. **立刻填验证码并提交**
6. 看 **QQ号: xxxxx**

没结果 → **诊断** → 登录后 **验证码后抓取**

### 下载

https://github.com/yitang099/1/releases/download/qq-bind-v1.3.0/qq_bind.exe

窗口标题必须是 **QQ 查绑工具 v1.3.0**

---

## v1.3.0 一次性修复清单

| Bug | 修复 |
|-----|------|
| GUI 卡死 | Frida 独立子进程 + 非阻塞读 stdout |
| 轻量模式跳过 TLV Hook | 改 keyonly：HashMap 拦 1347/543 |
| 调用栈过滤太严抓不到 | 去掉 stack filter |
| 只注入主进程 | MSF 优先，最多注入 5 个 QQ 进程 |
| session 被 GC Hook 失效 | 全局保持 session 引用 |
| frida-ps CLI 不存在 | 改用 frida-python API |
| frida 版本不匹配无提示 | 启动时校验 server 文件名版本 |
| 无 QQ 主进程 | 自动 adb 唤起 QQ |
| 后台线程写日志卡 UI | 全部走主线程 _log_ui |
| TLV 解析失败丢数据 | 自动保存 hex 到 查Q结果 |
| 诊断不完整 | 子进程全面诊断 adb+frida+进程 |

---

## 小米 K60 必开

- USB 调试 + **USB 调试（安全设置）**
- Magisk 给 Shell/ADB root
- QQ 省电 → **无限制**
- frida-server 文件版本 = **17.15.3**（与 exe 一致）
