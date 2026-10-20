# Genspicy Clone (Local v2)

本地复刻 [genspicy.ai](https://genspicy.ai) 用户端功能，**不含支付**。

## 生成是否和线上一致？

**不一致。** 本仓库是 **Mock 生成**：

| 项目 | 线上 Genspicy | 本仓库 |
|------|---------------|--------|
| 推理 / GPU | 真实 workflow（minimax、wan 等） | 无，约 3 秒模拟进度 |
| 输出视频 | 按你的上传图生成新 URL | 直接播放模板自带的 `output_media` 示例 |
| 上传 | CDN + 鉴权 | 仅填图片 URL（mock） |
| API 形态 | `user-generation-content.create/get` + 轮询 | **同名 RPC**，返回字段类似，但后端是内存 + 本地 JSON |

若要 **真生成一致**，需要接同一套后端推理服务（本仓库未包含）。

## 网站打不开？

这是 **本地站点**，没有公网地址。必须在你自己的电脑上启动：

```bash
cd genspicy-clone    # 必须在含 package.json 的目录
pnpm install
pnpm dev             # 默认 http://localhost:3000
```

浏览器打开：**http://localhost:3000**（不是 genspicy.ai）。

**自检：**

```bash
curl http://localhost:3000/api/health
```

应返回 `"ok": true`。若 `catalog_source` 为 `sample` 或 `seed`，模板较少但仍能打开。

**常见原因：**

1. 没进 `genspicy-clone` 目录就执行命令  
2. 3000 端口被占用 — 换端口：`PORT=3001 pnpm dev`  
3. 已有 Nuxt 锁 — 关掉旧进程或 `NUXT_IGNORE_LOCK=1 pnpm dev`  
4. 全量模板未导入 — 不影响打开，只影响模板数量；要全库：`pnpm import:templates`（约 17MB，需联网）

**生产模式：**

```bash
pnpm build
pnpm start
```

## 功能概览

- 模板：sample 120 条（仓库自带）/ 全量 `import:templates` 后约 9470 条已发布  
- 探索、Drama、Tools、收藏、创作、延长、Like、联盟（无提现）  
- 数据：`server/data/runtime-store.json`
