# WeGame 封号查询

本地工具：读取你提供的 WeGame `data` 文件夹中的登录态，调用腾讯官方 `punish_query` 接口查询 QQ 账号游戏封号记录。

**与木马版区别：** 不窃取、不外传 Cookie，仅在你本机查询。

## 使用

### 方式一：直接运行 Python

```bat
pip install -r requirements.txt
python main.py
```

### 方式二：打包 EXE（Windows）

```bat
build.bat
```

生成 `dist\WeGame封号查询.exe`。

## 界面操作

1. 点击「浏览」选择 WeGame 数据目录（例如 `C:\Program Files (x86)\Tencent\WeGame\data` 或你复制的 data 文件夹）
2. 点击「扫描登录态」，确认列表里出现你的 QQ
3. 输入 QQ 号，点击「查询封号」

## 数据目录要求

工具会在目录内递归查找含 `skey` / `p_skey` 的文件，支持：

| 文件 | 说明 |
|------|------|
| `cookies.ini` / `account.ini` | 手动配置（推荐） |
| `cookies.json` / `session.json` | 导出的 Cookie JSON |
| `Cookies`（SQLite） | 浏览器/客户端 Cookie 库 |
| `*.txt` / `*.log` | 含 Cookie 字符串的文本 |

### cookies.ini 示例

```ini
[account]
uin=123456789
skey=你的skey值
p_uin=o123456789
ptcz=可选
```

> `login.info` 等为 WeGame 加密二进制，无法直接解析。若扫描不到登录态，请从已登录的浏览器或 WeGame 导出 Cookie，或按上表手动建 `cookies.ini`。

## 查询接口

- `https://credit.gamesafe.qq.com/cgi-bin/qq/proxy/punish_query`
- 返回字段：`game_name`、`reason`、`zone`、`start_stmp`、`duration`

## 文件说明

| 文件 | 作用 |
|------|------|
| `main.py` | GUI 主程序 |
| `wegame_data.py` | 扫描 data 目录、解析 Cookie |
| `query_api.py` | 调用 punish_query API |
| `build.bat` | Windows 一键打包 |
