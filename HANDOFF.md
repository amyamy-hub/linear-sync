# 接手须知（HANDOFF）

> 这个仓、这条链路（Linear ↔ GitHub ↔ Notion ↔ Cloudflare）**以后不止一个 agent 在跑**。
> 本文件是给下一个会话的入口。⛔ 动手前先读完。改于 2026-09-23 12:1x（北京）。
> 另两处交接面：Linear 项目 **P-AMY-1** 顶部横幅、工单 **AMY-6 / AMY-7** 文末记录。
> ⚠️ 本文件上一版把手机自检的时刻写成了“22:44”，实际是**上午 10:44**（部署 `2026-09-23T02:35:59Z` = 北京 10:35:59，相差 8 分钟）。错因：照搬了前一晚 22:36 那张图的小时数。时刻以本行为准。

## ⭐ 分工原则：按节点插拔，⛔ 按平台性格分工（2026-09-22 用户定）

常见诱惑：“这家负责海外连接器、那家负责国内基建、第三家做归档”。⛔ 不要。

理由（实测）：同一句结论（“github token 只读、写会 403”）在不同客户端会**各自复述、各自当真**——那个错误从 09-20 活到 09-22，被三家各引用一次，直到 `merge_pull_request` 成功才当场碎掉。
⇒ **按平台性格分工，会把错误也一起分工**；按节点插拔才会逼新 agent 自己重测。

⇒ 引入新 agent 的**唯一合法触发条件**是：某个节点真坏了 / 需要替换 / 需要第二视角交叉复算。⛔ 不是“它家有特色”。

## 闸门状态（这是本文件唯一允许自己引用的部分）

| 闸门 | 内容 | 状态 | 凭据 |
|---|---|---|---|
| 1 | 仓库定位与分支 | ✅ | 实现在 `main`；⛔ 判“有没有入库”必 `list_branches` |
| 2 | 线上代码 == 仓库 | ✅ | 双方 blob SHA-1 均为 `3a698aff59f5…`（10,860 B / 365 行；09-23 12:1x 现算） |
| 3 | 配置在场 | ✅ | `GET .../secrets` 四个名字；`/selftest` 返 `syncAuthEnabled: true` |
| 4 | 不带密码被拒 | ✅ | 09-22 23:36 手机 `POST /sync` → `{"error":"unauthorized"}` |
| 5 | Worker 自己能拉到 Linear 并建好映射 | ✅ | 09-23 **10:44** 手机 `GET /selftest` → `{ok:true, fetched:7, previewCount:5, errors:[], syncAuthEnabled:true, durationMs:545}` |
| **6** | **真写进 Notion（含幂等）** | ⛔ **未做** | 见下两节 |

## 闸门 5 证明了什么、⛔ 没证明什么

**证明了**：Worker 自己的 `LINEAR_API_KEY` 有效（拉到 7 条，与 Linear 侧独立现读的 7 条对得上）；`SYNC_TOKEN` 在运行时确实有值（不再只是配置面推断）；字段映射对**全部 7 条**都跑通了——因为 `toProperties(issue)` 在 dryRun 分支**之前**执行，不是空转。

**⛔ 没证明**：它**一次都没碰过 Notion**。而且比“没碰”更强：**`errors` 在 dryRun 下是结构性恒空**——全代码只有 `summary.errors.push(...)` 这一处赋值，而它在 `continue` 跳过的 try/catch 里面。⇒ 无论系统多坏，dryRun 的 `errors` 都是 `[]`、`failed` 都是 0。**这不是证据，是常量。**（此条由另一客户端会话 09-23 指出，比本文件上一版“零证据力”的说法更准确。）

⇒ 所以“用 selftest 提前看到 select 报错”这条路**不成立**，闸门 6 必须真写一次才知道。

## 闸门 6 的两件事：地雷与最小爆炸半径

**地雷**：Notion 那个库（`Linear Issues 同步库`）的 `Status` select 只有 **Backlog / Todo**，没有 `Done`；`Labels` 是 multi_select 且 **options 为空**。而 AMY-6 / AMY-7 在 Linear 里已是 Done。Notion 对未知 select 选项是“自动新增”还是“拒绝”，**至今没人测过**。⚠️ 09-21 那次“14 连发稳定 7 页”不算证据——当时全部 issue 的 Status 都是 Backlog/Todo、labels 全空，**根本没经过这条代码路径**。

**判据（三条同时成立）**：行数仍为 7 **＋** AMY-6/7 的 Status 真变成 Done、Updated At 前进 **＋** 响应体 `failed == 0`。只看“页数不变”会把一次部分失败判成通过。

**最小爆炸半径——⛔ 不需要改代码**：`POST /sync` 本来就支持 `since`。取 `{"since":"2026-09-22T00:00:00Z","teamKey":"AMY"}` 时，7 条里**只有 AMY-6 与 AMY-7 会被选中**（其余 5 条停在 09-20），而这两条正好就是踩雷的那两条 ⇒ 一次试水的影响面 = 2 行，且返回的 `fetched` 应为 **2**（这本身就是个自检）。

**但闸门 6 目前真正的堵点不是地雷，是出口**：它需要一发带 `Authorization` 头的 POST，而手机浏览器发不出、本机与云沙箱出不去（见下表）。⇒ 要么手机装一个能跑 curl 的 shell（Termux），要么等一台有出口的机器；⛔ 不要为了绕这个而给 Worker 加“无鉴权写”入口。

## 现在到底是什么状态

- Worker 已上线：`https://linear-sync.amy4399666.workers.dev/`，`GET /health` 返 `ok:true`、`missingConfig: []`。
- 它做的事：**主动拉** Linear 的 issue（GraphQL），按 `Linear ID` upsert 进 Notion 数据库。**⛔ 没有入站 webhook，⛔ 不写 Linear**。
- `POST /sync` 已加鉴权（不带 `Authorization: Bearer $SYNC_TOKEN` → 401，实测）。
- `GET /selftest` 是**无鉴权只读探针**：跑一次 dryRun，⛔ 不写 Notion，但会吃 Linear API 配额并泄露 `fetched` 这个数。它是目前**唯一不需要出口就能验收闸门 3/5 的手段**（手机打开一个链接即可）。

## 带密码怎么发（闸门 6 就靠它）

```bash
curl -X POST https://linear-sync.amy4399666.workers.dev/sync \
  -H 'content-type: application/json' \
  -H "authorization: Bearer $SYNC_TOKEN" \
  -d '{"teamKey":"AMY","since":"2026-09-22T00:00:00Z"}'
```

先加 `"dryRun":true` 跑一次看映射，再去掉跑正式同步。期望 `fetched:2`。⚠️ 头必须叫 `authorization`、值必须是 `Bearer ` + 原文比较，**大小写敏感、不多不少一个空格**。看到 401 先查自己有没有带头，那是锁在正常工作，⛔ 不是“同步坏了”。

## 三条“别再重踩”的实测结论

1. **判“代码有没有入库”必须 `list_branches`。** 09-20 起实现全在 `demo/sync-skeleton`，而 `main` 只有一个 16 行 README 骨架——这个假象骗了两个会话两天。
2. **“线上代码 == 仓库”要算哈希，⛔ 别看版本号。** 拉 `GET /accounts/{acct}/workers/scripts/linear-sync` 的 multipart 正文，按 `blob <len>\0` 算 SHA-1。`VERSION="0.2.0"` 从 `ac9b352` 起就没 bump，证不了构建。
3. **“GitHub↔Linear↔Notion 三向循环”这个担心已被实测否定。** Worker 全文 `mutation` 命中 0 次；Two-way 开启后两侧新增镜像对象 0 条。⛔ 别再为此写“护栏”代码——真该补的是**部署自动化**（见下）。

## 钥匙能力矩阵（省你三小时，⛔ 别当现行值）

| 通道 | ✅ 能 | ⛔ 不能（错误码） |
|---|---|---|
| github 连接器 | 读、写文件、建分支、合并 PR、删文件（均实测成功） | ⛔ “token 只读、写会 403” 已被当场证伪；⚠️ 但没有删分支工具 |
| cloudflare MCP | 读配置、读 secret **名字**、拉线上源码、改配置（dashboard 换代码不清 bindings） | 写 secret（**10405**）；创建/替换 Worker（**10007**）；读遥测（**403**）；fetch 自家 workers.dev（**403**） |
| linear 连接器 | 读写 issue/project；`patch` 可局部改正文（**锦点不匹配则整块不写**，安全） | 改附件标题（无接口）；`links` 回执成功但 **0/1 生效** ⇒ 写后必回读；⚠️ 正文里写 `AMY-6` 会被自动建关联并**推高对端 `updatedAt`** ⇒ 做滞后量要用 `completedAt`，⛔ 用 `updatedAt` |
| notion 连接器 | 读库 schema（能看到 select 选项列表）、读写页面 | 本会话曾出现 `notion-get-teams` / `notion-search` 单次 `-32603` 假失败，重试即过 |
| qca 云沙箱 | 跑 shell、有外网 | 到 workers.dev（`allowed_hosts: []` 不可改 ⇒ DNS 黑洞 `108.160.166.9`） |
| 用户本机 | 校园网常规出口；github/notion/linear/cloudflare API 全通 | 到 workers.dev（**SNI 重置**）；⛔ 开不了 VPN（Clash Verge 只剩 2025-10 的残留配置，无订阅） |
| **用户手机 + VPN** | ✅ 目前**唯一**能打到这个端点的设备；GET 一个链接就能验收闸门 3/5 | 浏览器发不出 `Authorization` 头 ⇒ 只能测“不带密码”那一半；闸门 6 需 Termux 或等价 shell |

计费提醒：⚠️ **“模型限免”≠“这次调用免费”**。qca 一次探针实测 1.01 积分 = model 0.29 + **sandbox_runtime 0.71**；而 `list_models` 里该模型根本没有 `price_factor` 字段 ⇒ ⛔ 只看 price_factor 会漏掉沙箱运行时这一半。

## ⚠️ 工具陷阱：`create_or_update_file` 是**整份替换**

实测：只传一行去“改一行”，整个 HANDOFF.md 从 6,036 B **被覆成 160 B**，回执仍为成功。
⇒ 改这个文件必须**整份重发**。要局部改，⛔ 用这个工具，改用 git 本地提交或先 `get_file_contents` 拉全文再改。
⇒ 判据：回执里的 `size` 与 `content.sha`。本次靠 `size: 160` 当场发现并复原。
⇒ 手抄全文的安全做法：先在本地算出目标 blob SHA-1，推完拿 GitHub 回的 `content.sha` 对撞（本轮两次都是这么做到零漂移的）。

## 真存在的风险（当前未处置）

**仓库与线上之间没有任何自动链路。** 9 次部署的 source 只有 `dash_template` / `quick_editor` / `dash`，`wrangler` 一次都没跑过。⇒ 今天“线上==main”是**手抄对上了**（而且有 SHA 证明），但机制上不保证。要治漂移，下一步是接上 `wrangler deploy` 或 Workers Builds 跟 Git 绑（dashboard 已提示“Connect your Git repository”），⛔ 不是给 `/health` 加 commit 字段（那只能让漂移可见）。

## 变更约定

- 登记按“原文不改、文末追加”——但⛔ 只读前 20 行一定读到过期快照，所以**更正必须同时放顶部横幅**。
- 每条结论都要写“**怎么测的 + 测于哪一刻**”，⛔ 不要只写“现行值”。
- 写操作回执成功不算落盘，**必回读**；回读接口本身也要跑阳性对照。
- ⛔ 本地记忆（各客户端自己的 memory 目录）**不是交接面**——它是每家一份的。要别人不重踩，必须写进本文件或 Linear。
- ⛔ 文档里不要钉自己的 HEAD commit 号（包括本文件）——它在你写下它的那一秒就已开始过期。
- ⚠️ 写时刻时**别照抄上一张图的小时数**（本文件就这么错过一次 12 小时）。拿不到原始时间就说“未记”，也别推。
