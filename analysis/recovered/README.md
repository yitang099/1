# Recovered source (一码快查 / 具体.exe V2.5 stack)

逆向还原产物，**非运营方原始仓库**，但与线上 `43.154.128.116:9110` + `47.76.163.227:8081` 行为对齐。

## 文件

| 文件 | 来源 | 完整度 |
|------|------|--------|
| `desktop_app.py` | `desktop_app.pyc` → **pycdc** | ~70%（UI 较全，尾部截断） |
| `desktop_app_core.py` | pycdas 字节码手工还原 | 核心业务逻辑（create/query/setsms/扣费） |
| `billing_server.py` | 线上 API + 登录页 HTML 反推 | **API 等价** Flask 实现 |
| `sms_api_server.py` | 8081 实机探测反推 | **路由/状态机等价**；腾讯协议见 `../qq_sms_bind/` |
| `desktop_app.pycdas.txt` | pycdas 全量反汇编 | 参考 |

## 未能直接拿到的

- **8081 原始 .NET DLL**：`47.76.163.227` 无文件泄露、SSH/SMB 不可利用；公网无同名源码
- **9110 原始 .py**：同上；`billing_server.py` 为功能复刻
- **`参考1.py`**：客户端注释引用，未在样本/泄露中找到

## 本地运行复刻栈

```bash
# 计费
python3 analysis/recovered/billing_server.py

# 短信查询 API（不含真实腾讯下发）
API_SECRET=b9887333ae4c43858c9235e0ac4e0921 python3 analysis/recovered/sms_api_server.py
```

## 工具

- pycdc: `/tmp/pycdc2/pycdc`（从源码编译，`g++-13 -L/usr/lib/gcc/x86_64-linux-gnu/13`）
