# Recovered source (一码快查 / 具体.exe V2.5 stack)

逆向还原产物，**非运营方原始仓库**，但与线上 `43.154.128.116:9110` + `47.76.163.227:8081` 行为对齐。

## 文件

| 文件 | 来源 | 完整度 |
|------|------|--------|
| `desktop_app.py` | 旧样本 `desktop_app.pyc` → **pycdc** | ~70%（UI 较全，尾部截断） |
| `desktop_app_decompiled.py` / `desktop_app_full.py` | **完整** `具体.exe` 解包后 pycdc | 同上（来自 10.8MB 正式客户端） |
| `desktop_app_from_exe.pyc` | PyInstaller 解包原始字节码 | 可再反编译 |
| `desktop_app_xdis.txt` | xdis 全量反汇编（14807 行） | 尾部可手工补全 |
| `desktop_app_core.py` | pycdas 字节码手工还原 | 核心业务逻辑（create/query/setsms/扣费） |
| `billing_server.py` | 线上 API + 登录页 HTML 反推 | **API 等价** Flask 实现 |
| `sms_api_server.py` | 8081 实机探测反推 | **路由/状态机等价**；腾讯协议见 `../qq_sms_bind/` |
| `desktop_app.pycdas.txt` | pycdas 全量反汇编 | 参考 |

## 未能直接拿到的（2026-07-06 最新探测）

- **8081 原始 .NET 源码/DLL**：`47.76.163.227` 仅 8081 对外；路径/swagger/备份全 404；从国内 IP 亦无法 SSH；公网/GitHub 无 `没有该手机订单` 等特征串泄露
- **9110 原始 `app.py`**：`43.154.128.116:9110` SSH 22 可连但密码喷洒未中；settings 枚举无源码路径；`billing_server.py` 为 API 行为复刻
- **分析机 `42.240.167.114`**：已 SSH，有 `具体.exe` 与 recon 脚本，**无** 8081/9110 服务端源码目录
- **`参考1.py`**：客户端注释引用，exe 内未打包，公网未找到

## 本地运行复刻栈

```bash
# 计费
python3 analysis/recovered/billing_server.py

# 短信查询 API（不含真实腾讯下发）
API_SECRET=b9887333ae4c43858c9235e0ac4e0921 python3 analysis/recovered/sms_api_server.py
```

## 工具

- pycdc: `/tmp/pycdc2/pycdc`（从源码编译，`g++-13 -L/usr/lib/gcc/x86_64-linux-gnu/13`）
