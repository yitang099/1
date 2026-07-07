# QQ 查绑 Hook 工具（Windows exe）

连接 **Root 手机（如红米 K60 Pro）**，自动检测 ADB、启动 frida-server、注入 QQ Hook，捕获明文 QQ 号。

## 下载

GitHub Actions 构建后从 Releases 下载 `qq_bind.exe`，或本地运行 `build.bat` 打包。

## 使用前准备（一次性）

### 电脑

1. 安装 [Android platform-tools](https://developer.android.com/tools/releases/platform-tools)（含 adb.exe），加入 PATH 或在软件里指定路径
2. `pip install frida frida-tools`（若用源码运行）

### 手机（红米 K60 Pro）

1. Root（Magisk）
2. 开发者选项：**USB 调试** + **USB 调试（安全设置）**
3. 安装 QQ

### exe 同目录放 frida-server

1. 查看 frida 版本：`python -c "import frida; print(frida.__version__)"`
2. 下载 https://github.com/frida/frida/releases 里同版本的  
   `frida-server-版本-android-arm64`
3. 放到 **exe 同目录**（文件名保持原样或改名为 `frida-server`）

## 使用

1. USB 连接手机，选文件传输，允许调试
2. 双击 `QQ查绑Hook.exe`
3. 点 **刷新手机** → **启动 Frida**（首次）
4. 手机上 **打开 QQ**
5. 点 **一键开始 Hook**
6. 在 QQ 里：**手机号登录 → 收短信 → 填验证码**
7. 软件显示 QQ 号，并保存到 `查Q结果` 文件夹

## 说明

- **不能全自动**：短信验证码必须你在手机上输入（腾讯限制）
- 软件自动完成：ADB 检测、frida-server 推送启动、Hook 注入、结果保存
- 仅对你有权测试的手机号使用

## 源码运行

```bash
pip install frida frida-tools
python -m qq_bind_client
```
