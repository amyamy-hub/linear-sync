# linear-sync

一个跑在 Cloudflare Workers 上的同步服务：把 Linear 的 issue 同步成 Notion 页面。

## 链路

需求（Notion）-> 任务（Linear）-> 代码（GitHub）-> 运行（Cloudflare）

## 当前状态

骨架阶段，只有一个 `GET /health` 端点。同步逻辑、Linear / Notion 凭证与部署参数在后续提交中补齐。

## 目录

- `src/index.js` — Worker 入口
- `wrangler.toml` — Worker 名与入口配置
