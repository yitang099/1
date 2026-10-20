# Genspicy Clone (Local v2)

本地复刻 [genspicy.ai](https://genspicy.ai) 用户端功能，**不含支付**。

## 生成是否和线上一致？

**不一致。** 本仓库是 **Mock 生成**：

| 项目 | 线上 Genspicy | 本仓库 |
|------|---------------|--------|
| 推理 / GPU | 真实 workflow（minimax、wan 等） | 无，约 3 秒模拟进度 |
| 输出视频 | 按你的上传图生成新 URL | 本地 ffmpeg 从你的图片生成预览 MP4（非 GPU 换脸） |
| 上传 | CDN + 鉴权 | 本地上传 `/api/media/upload` + 外链 HTTPS |
| API 形态 | `user-generation-content.create/get` + 轮询 | **同名 RPC**，返回字段类似，但后端是内存 + 本地 JSON |

### 要与线上一致的真实生成（D）

官方推理在 `api.genspicy.ai`，本仓库已支持 **Live 模式**（浏览器直连官方 API，CORS 已放行）：

1. 在 [genspicy.ai](https://genspicy.ai) 用**正式账号**登录（需有钻石；**Guest 无法 create**，会 10022）
2. 打开本站 **「真实生成」**（`/user/live-account`），粘贴 Network 里复制的 `Bearer` JWT
3. 验证成功后，模板页 **Generate (Live)** 走官方 `user-generation-content.create/get`

本仓库**不能**代替你注册/付费；也不能在没有官方 Token 的情况下凭空调用 GPU。

## 网站打不开？

这是 **本地站点**，没有公网地址。必须在你自己的电脑上启动：

```bash
cd genspicy-clone    # 必须在含 package.json 的目录
pnpm install
pnpm dev             # 默认 http://localhost:3000
```

浏览器打开：**http://localhost:3000**（不是 genspicy.ai）。

### 不会装环境？先用在线演示（Cloud Agent）

若 Cloud Agent 已为本次任务开启了 **Cloudflare 临时隧道**，助手会在对话里发一个 `https://xxxx.trycloudflare.com` 链接——**用手机或电脑浏览器直接打开即可**，不要填 `localhost`。

> 该链接只在当前 Cloud 会话存活期间有效；关掉 Agent 后需重新生成。

### Windows 用户（Edge 显示「拒绝了连接请求」）

说明 **本机还没启动服务**。Cloud / 隧道里的站点**不会**出现在你电脑的 `localhost` 上。

**一键（推荐）：**

1. 安装 [Node.js LTS 20+](https://nodejs.org/)
2. 克隆仓库并进入 **`genspicy-clone`** 文件夹（或 monorepo 根目录双击 **`start-genspicy-windows.bat`**）
3. **双击 `start-windows.bat`**（首次会自动安装依赖、下载 ffmpeg、构建，约 3–10 分钟）
4. 浏览器会自动打开 **http://127.0.0.1:3000** — **不要关闭黑色命令行窗口**

详细说明见 **[本机打开.md](./本机打开.md)**。

命令行等价：

```powershell
cd 路径\genspicy-clone
pnpm local
```

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
