# linear-sync

一个跑在 Cloudflare Workers 上的同步服务：把 Linear 的 issue 同步成 Notion 页面。

## 链路

需求（Notion）-> 任务（Linear）-> 代码（GitHub）-> 运行（Cloudflare）

## 端点

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 服务说明与可用端点 |
| GET | `/health` | 健康检查，返回版本与缺失的配置项 |
| POST | `/sync` | 拉取 Linear issue 并 upsert 到 Notion 数据库 |

`POST /sync` 的 body 可省略，支持三个可选字段：

```json
{ "dryRun": true, "since": "2026-09-01T00:00:00Z", "teamKey": "ENG" }
```

- `dryRun` — 只做拉取与字段映射，不写入 Notion，返回前 5 条预览
- `since` — 只同步 `updatedAt` 晚于该时刻的 issue
- `teamKey` — 只同步以 `<teamKey>-` 开头的 issue

返回 `{ ok, fetched, created, updated, failed, errors, durationMs }`。

## 配置

secrets（用 `wrangler secret put <NAME>` 写入，不要提交到仓库）：

- `LINEAR_API_KEY` — Linear personal API key
- `NOTION_TOKEN` — Notion integration token
- `NOTION_DATABASE_ID` — 目标 Notion 数据库 ID

可选变量：

- `LINEAR_TEAM_KEY` — 默认的 team key 过滤
- `NOTION_VERSION` — Notion API 版本，默认 `2022-06-28`
- `SYNC_TOKEN` — 若设置，`POST /sync` 需带 `Authorization: Bearer <token>`

## Notion 数据库字段映射

目标数据库需要以下属性，名称需完全一致：

| Notion 属性 | 类型 | 来源 |
| --- | --- | --- |
| `Name` | title | `issue.title` |
| `Linear ID` | rich_text | `issue.id`（upsert 的去重键） |
| `Identifier` | rich_text | `issue.identifier` |
| `Status` | select | `issue.state.name` |
| `Assignee` | rich_text | `issue.assignee.name` |
| `Labels` | multi_select | `issue.labels` |
| `URL` | url | `issue.url` |
| `Updated At` | date | `issue.updatedAt` |
| `Description` | rich_text | `issue.description`（超 2000 字符按上限自动分片，不截断） |

## 部署

```bash
wrangler secret put LINEAR_API_KEY
wrangler secret put NOTION_TOKEN
wrangler secret put NOTION_DATABASE_ID
wrangler deploy
```

## 验收标准

1. `GET /health` 返回 `ok: true`，且 `missingConfig` 为空
2. `POST /sync` 带 `{"dryRun": true}` 返回 `fetched > 0` 且预览字段映射正确
3. `POST /sync` 正式执行后，Linear issue 在 Notion 数据库中一一对应；重复执行不产生重复页面，只更新已有页面
4. 单个 issue 写入失败不影响整批，失败明细出现在 `errors` 中

## 目录

- `src/index.js` — Worker 入口（无外部依赖，纯 `fetch`）
- `wrangler.toml` — Worker 名与入口配置