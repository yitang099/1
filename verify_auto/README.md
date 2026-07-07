# 两步验证助手 v0.4.1

同一窗口两步点击验证（选图 + 最慢动球）。

## 下载（Windows）

[GitHub Release verify-auto-v0.4.1](https://github.com/yitang099/1/releases/tag/verify-auto-v0.4.1) 下载 `verify_auto.exe`，双击运行。

或从 Actions → **Build Verify Auto EXE** → Artifacts 下载。

## 当前功能

| 功能 | 说明 |
|------|------|
| 第1步按词选图 | OCR 读提示词 + 词库按图匹配 |
| 第2步最慢动球 | 帧差分只追踪会动的球，忽略装饰球 |
| 词库学习 | 手动存图到 `library/`，或「从勾收录」「从圈收录」 |
| 蓝色勾/圈识别 | 点击后自动识别选中标记并入库 |
| 小窗随机位置 | 框选一次记布局，全屏 OCR 自动跟位置 |
| 后台点击 | Windows 消息点击，默认不移动鼠标 |
| F8 一键全流程 | 第1步 → 确定 → 第2步 → 确定 |

## 首次使用

1. 弹出验证小窗
2. 框选：**提示文字区**、**图片网格区**、**第2步球区域**、**确定按钮**
3. 手动过几次，点「从勾收录」「从圈收录」积累词库
4. **F8** 全自动

## 源码运行

```bash
pip install -r verify_auto/requirements.txt
python -m verify_auto
```

## 合规

仅用于本地有权测试。
