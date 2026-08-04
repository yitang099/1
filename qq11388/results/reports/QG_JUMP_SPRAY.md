# 太白 — 跳板 + 青果 20 线程

## 结论

**可以。** 太白（`shopping.qq11399.vip`，ACG 3.5.6）有强 IP 限流（约 30/600s），单 IP 喷雾不可用。正确拓扑：

```
HK 控制机 → CN 跳板(跑脚本) → 青果短效代理池(≤20 通道) → 太白
```

## 实测

| 路径 | 结果 |
|------|------|
| HK → 青果 → 太白 | SSL/Proxy 全失败 |
| 跳板直连 → 太白 | 通，但单 IP 很快 `请求过于频繁` |
| 跳板 → 青果 → 太白 | **通**（部分 IP 存活期短，需轮换） |

青果通道约 20 条；`get?num=20` 在通道占满时返回 `NO_AVAILABLE_CHANNEL`，用 `query` 复用 + 到期后重新 `get`。短效 IP deadline ~1 分钟，脚本每 ~18s 刷新。

## 运行

跳板：`/root/taibai/scripts/taibai_qg_spray.py`

```bash
OUT=/root/taibai/dump WORKERS=12 ALLOW_DIRECT=0 RESUME=1 TZ=Asia/Shanghai \
  python3 /root/taibai/scripts/taibai_qg_spray.py
```

- `WORKERS=12~20`：与通道数对齐，过高会挤在少数存活出口上触发限流
- `ALLOW_DIRECT=0`：跳板 IP 已热时关闭直连兜底
- 节流时对单代理 cooldown，失效代理踢出池

## 进度（部署时）

见 `results/dump/contact_state.json`；已有命中/卡密见 `contact_hits.json` / `contact_kami.json`。
