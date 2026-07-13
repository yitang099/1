# WeGame 封号查询

软件**自带 `data` 文件夹**。把 WeGame 的 data 内容放进去，输入 QQ 号即可查封号。

## 使用（EXE）

1. 运行 `build.bat` 打包
2. 打开 `dist\WeGame封号查询\`
3. 把 WeGame data **复制到** `data\` 文件夹
4. 双击 `WeGame封号查询.exe`，输入 QQ 号，点「查询封号」

```
WeGame封号查询/
├── WeGame封号查询.exe
└── data/              ← 把你的 WeGame data 放这里
    ├── 使用说明.txt
    └── （WeGame 数据文件）
```

## 使用（Python 开发）

```bat
pip install -r requirements.txt
python main.py
```

开发时 `data` 文件夹在项目根目录 `wegame_ban_query/data/`。

## 界面

- **打开 data 文件夹** — 直接打开自带目录，拖入 WeGame data
- **重新扫描** — 放入新文件后刷新
- **QQ 号 + 查询封号** — 查对应账号封号游戏

## data 里放什么

直接把 WeGame 安装目录下的 `data` 文件夹内容复制进来即可。

若扫不到登录态，在 `data` 里建 `cookies.ini`：

```ini
[account]
uin=123456789
skey=你的skey
p_uin=o123456789
```

## 说明

- 仅本地调用腾讯官方 `punish_query`，不外传 Cookie
- `login.info` 为加密文件，无法直接读；需含 `skey` 的 cookie 文件
