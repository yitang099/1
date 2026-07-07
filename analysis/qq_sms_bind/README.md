# QQ 短信查绑复现（Root 手机）

用 **Root 真机 + Frida** 复现「手机号 + 短信验证码 → 明文 QQ」——这是一码快查 8081 背后的核心技术路径。

## 你要准备什么

| 项目 | 说明 |
|------|------|
| Root 手机 | Magisk 等，已开启 USB 调试 |
| USB 线 | 手机连电脑，`adb devices` 能看到设备 |
| QQ | 安装官方 `com.tencent.mobileqq` |
| 测试手机号 | **必须是你自己的号**，能收短信 |
| 电脑 Python 3.10+ | `pip install -r requirements.txt` |

## 第一步：装 Frida（电脑 + 手机版本要一致）

```bash
cd analysis/qq_sms_bind
pip install -r requirements.txt

# 查看电脑 frida 版本
python3 -c "import frida; print(frida.__version__)"
```

到 https://github.com/frida/frida/releases 下载同版本的  
`frida-server-版本-android-arm64`（多数手机用 arm64）

```bash
# 放到 qq_sms_bind 目录后执行
chmod +x setup_frida_server.sh
./setup_frida_server.sh

# 验证
frida-ps -U
```

## 第二步：离线自测解析器

```bash
python3 replicate_min.py test-parser
# 应输出: parser self-test OK
```

## 第三步：Hook QQ（核心）

```bash
# 方式 A：先手动打开 QQ，再注入（推荐）
python3 run_root_phone.py

# 方式 B：冷启动 QQ 并注入
python3 run_root_phone.py --spawn
```

### 手机上操作（用你自己的号）

1. QQ → **新用户 / 手机号登录**（或找回密码）
2. 输入手机号 → 下一步
3. 收到短信后 **输入验证码**
4. 看电脑终端是否出现：

```text
>>> 明文 QQ: 123456789  (来源: ...)
```

或：

```text
>>> 捕获 TLV543 ...
    解析 QQ: 123456789
```

## 第四步：备用 — logcat 抓 QQ

若 Frida 没输出，试：

```bash
# 清空 logcat，在 QQ 里完成验证后执行
python3 logcat_qq.py --clear
python3 logcat_qq.py

# 或实时监听 60 秒（验证过程中另开终端跑）
python3 logcat_qq.py --watch 60
```

## 第五步：解析已抓到的 hex

```bash
python3 replicate_min.py parse --hex <你的hex> --json
```

## 目录说明

| 文件 | 作用 |
|------|------|
| `run_root_phone.py` | **主入口**，USB Hook QQ |
| `frida_hook.js` | Frida 脚本，截 TLV543 / getKeyUin |
| `parse_qq_bind_uin.py` | 从 protobuf hex 解析 plain QQ |
| `logcat_qq.py` | logcat 备用抓取 |
| `replicate_min.py` | 统一 CLI（test-parser / parse / hook） |
| `setup_frida_server.sh` | 推送并启动 frida-server |

## 常见问题

| 问题 | 处理 |
|------|------|
| `unable to connect to remote frida-server` | 手机端 frida-server 没跑或版本不一致 |
| `ProcessNotFoundError` | 先打开 QQ 或用 `--spawn` |
| Hook 无输出 | QQ 版本太新，类名变了；试换 QQ 8.9.x 或看 `[frida]` 日志 |
| 只有 TLV hex | 用 `replicate_min.py parse --hex ...` |
| 小米/华为 | 需同时开「USB 调试(安全设置)」 |

## 跑通之后做什么（mini-8081）

1. ✅ 能稳定拿到 `plain_qq`
2. 用 ADB/Appium 自动输入手机号 + 验证码
3. 自己写 Flask API：`create` / `setsms` / `query`
4. 一台手机 = 一个 Worker

## 合规

仅对你 **有权测试的手机号** 操作，不要批量查他人号码。
