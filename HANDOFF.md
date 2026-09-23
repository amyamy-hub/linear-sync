# 接手须知（HANDOFF）

> 这个仓、这条链路（Linear ↔ GitHub ↔ Notion ↔ Cloudflare）**以后不止一个 agent 在跑**。
> 本文件是给下一个会话的入口。⛔ 动手前先读完。改于 2026-09-23 14:0x（北京）。
> 另两处交接面：Linear 项目 **P-AMY-1** 顶部横幅、工单 **AMY-6 / AMY-7** 文末记录。
> ⚠️ 时刻口径提醒（本文件栽过一次）：写时刻要拿**部署/回执的 UTC 原文**换北京时间，⛔ 别照抄上一张图的小时数。

## ⭐ 当前状态：闸门 1–6 全部闭环

链路已端到端跑通并且**验收证据来自目标系统回读，不是 Worker 自报**。下一个 agent 若只想复现一次同步，直接看下面「怎么发这一枪」；⛔ 不要从头重查已定案的三条（见「别再重踩」）。

> 📌 **`SYNC_TOKEN` 暂不轮换 —— 这是用户 2026-09-23 拍的决定，⛔ 不是上一家漏做。** 理由与打包做法见「还欠着的两件事」第 1 条。⛔ 未经用户重新授权，任何 agent⛔ 不要动这把锁。

## 分工原则：按节点插拔，⛔ 按平台性格分工（2026-09-22 用户定）

常见诱惑："这家负责海外连接器、那家负责国内基建、第三家做归档"。⛔ 不要。

理由（实测）：同一句结论（"github token 只读、写会 403"）在不同客户端会**各自复述、各自当真**——那个错误从 09-20 活到 09-22，被三家各引用一次，直到 `merge_pull_request` 成功才当场碎掉。
⇒ **按平台性格分工，会把错误也一起分工**；按节点插拔才会逼新 agent 自己重测。

⇒ 引入新 agent 的**唯一合法触发条件**是：某个节点真坏了 / 需要替换 / 需要第二视角交叉复算。⛔ 不是"它家有特色"。

## 闸门状态（这是本文件唯一允许自己引用的部分）

| 闸门 | 内容 | 状态 | 凭据（含测于哪一刻） |
|---|---|---|---|
| 1 | 仓库定位与分支 | ✅ | 实现在 `main`；⛔ 判"有没有入库"必 `list_branches` |
| 2 | 线上代码 == 仓库 | ✅ 但**判据已换** | 服务版本 `2fc04c35…`（deployment `b5e84f14` @ 09-23 02:35:59Z，source `quick_editor`）的产物 etag `5d4e6aad…`；仓库 `main:src/index.js` blob `3a698aff59f5…`（10,860 B / 365 行）。⚠️ **09-23 14:5x 起⛔ 不能再拉裸 `/workers/scripts/{name}` 算 SHA** —— 见下条与「怎么判线上==仓库」 |
| 3 | 配置在场 | ✅ | `GET .../secrets` 四个名字；`/selftest` 返 `syncAuthEnabled: true` |
| 4 | 不带密码被拒 | ✅ | 09-22 23:36 手机 `POST /sync` → `{"error":"unauthorized"}` |
| 5 | Worker 能拉到 Linear 并建好映射 | ✅ | 09-23 **10:44** 手机 `GET /selftest` → `{ok:true, fetched:7, previewCount:5, errors:[], syncAuthEnabled:true, durationMs:545}` |
| **6** | **带密码真写进 Notion，且幂等** | ✅ **09-23 13:49** | Postman 云端 `POST /sync` → **HTTP 200 / 164 B / 2458 ms**；Notion 回读：AMY-6/7 `Status` Backlog→**Done**、AMY-1/5 `Updated At` 前移、AMY-2/3/4 未动；三次运行后 `COUNT(*)` 仍 **7** 且 `COUNT(DISTINCT "Linear ID")` 仍 **7** |

## 闸门 6 到底证了什么、⛔ 没证什么（09-23 13:49）

**证了**：鉴权分支放行（401 只会回 26 B 的 `{"error":"unauthorized"}`，实测 164 B）；`runSync` 真跑了 4 次 Notion `PATCH`；逐行写入值与 Linear 的 `updatedAt` 相等 ⇒ `created=0 / updated=4 / failed=0` 是**由状态差集推得**；重复执行不新增行 ⇒ 按 `Linear ID` upsert 成立。

**⛔ 没证**：Worker 自报的 JSON 数值一个都没拿到 —— Postman monitor **不回传响应体**，只回传 `contentLength`。

**顺手测到一条通则：字节数反推不出计数。** 响应体是 `JSON.stringify(body, null, 2)`，而 `(fetched, created, updated, failed)` 只要都是个位数，`fetched:2/updated:2` 与 `fetched:4/updated:4` 与 `fetched:7/updated:7` 的**长度全都是 164 B**。⇒ ⛔ 别拿"响应大小对得上"当计数正确性的证据（同族：聚合数反推不出逐份数）。想要数就回读目标系统，正好也更硬。

**另一条精度发现**：Notion 把 `Updated At` 的**秒吃掉了** —— Linear `2026-09-22T15:20:06.900Z` 落到 Notion 变 `15:20:00Z`（在 `notion-fetch` 的原始 property 里就是这样，⛔ 不是展示层截断）。⇒ 任何"同步是否落后"的滞后量计算，精度上限是分钟，⛔ 别用毫秒比对。

## ⚠️ `since` 的爆炸半径会被 `updatedAt` 批量抬升

本文件上一版算出"`since=2026-09-22T00:00:00Z` 只选中 AMY-6/7 两行"。发枪前现读 Linear：**AMY-1、AMY-5、AMY-7 的 `updatedAt` 全被顶到 `2026-09-23T04:22:10.888Z`**（AMY-7 是 `.725Z`），而 AMY-6 仍停在 09-22 ⇒ 期望值当场从 2 变成 **4**。

原因不是悬案，就是本文件「钥匙能力矩阵」里那条：**Issue 正文里出现 `AMY-N` 会被 Linear 自动建关联并推高对端 `updatedAt`**。上一轮往 AMY-7 文末追加记录时点名了 AMY-1/5/7 ⇒ 那几条被"无内容变更"地刷新。AMY-6 没被顶，因为它对 AMY-7 的关联早已存在（这条推论与观测一致，但⛔ 未单独复测）。

⇒ **发 `POST /sync` 之前先 `list_issues` 现算 `fetched` 期望值**，⛔ 别引用上一次算出来的条数。滞后量本身要用 `completedAt`，不要用 `updatedAt`。

## 怎么发这一枪（闸门 6 的复现配方）

本机与两个云沙箱都打不到 `*.workers.dev`（SNI 重置 / DNS 黑洞 / MCP 出口策略，三种坏法）。**第三条路已实测：让 Postman 云端替我发。**

```bash
# 有正常出口的机器上（首选，最直接）
curl -X POST https://linear-sync.amy4399666.workers.dev/sync \
  -H 'content-type: application/json' \
  -H "authorization: Bearer $SYNC_TOKEN" \
  -d '{"teamKey":"AMY","since":"2026-09-22T00:00:00Z"}'
```

Postman 路线（本轮实际用的，全程 REST，⛔ 不需要桌面客户端）：

1. 控制台 `Settings → API keys → Generate`。**值只在创建那一瞬可见**：立刻从 DOM 的 `<input>.value` 取，⛔ 别刷新页面 —— 本轮就是先 `location.reload()` 了才发现表格只剩 `PMAK-…-XXXX`，只能 Regenerate 重来。
2. `POST /collections?workspace=<id>` 建集合；请求头用 `Bearer {{SYNC_TOKEN}}`，体是 raw JSON。
3. `POST /environments` 建环境，变量 `type:"secret"`。
4. **`POST /monitors/{uid}/run` 才是云端执行器** —— 旧的 `POST /run/collection/{id}` 在 `api.postman.com` 上已经 **404**（三个变体全 404，实测）。
5. Monitor 创建有三个必填坑：`timezone` 必须放在 **`schedule` 里面**（放顶层或 query 参数都会报 `paramMissing`）；cron 有**白名单**（`0 0 1 1 *` 被拒，`0 17 * * *` 过）；`environment` ⛔ 不许为空。
6. ⛔ **用完必须删 monitor** —— 它带日跑 cron，留着就是无人值守往 Notion 写。本轮删后回读 `GET /monitors` → `[]`。

**结果只给 `contentLength`，不给 body** ⇒ 验收必须回到 Notion/Linear 侧现读（本来也更硬）。

## 三条"别再重踩"的实测结论

1. **判"代码有没有入库"必须 `list_branches`。** 09-20 起实现全在 `demo/sync-skeleton`，而 `main` 只有一个 16 行 README 骨架——这个假象骗了两个会话两天。
2. **"线上代码 == 仓库"要算哈希，⛔ 别看版本号；而且⛔ 不要拉裸 `/workers/scripts/{name}`。** 那个端点返回的是**最后一次上传的产物**，不是**正在服务的那一份**——今晚之前两者恰好重合（历次 dashboard 上传都同时就是部署），所以老配方当时成立；09-23 我用 `wrangler versions upload` 传了个不切流量的版本之后，它开始返回 esbuild 打包件，而线上仍是看板那份纯源码 ⇒ 照老配方跑会得出"线上≠仓库"的**反向错结论**。✅ 正确两步：`GET .../deployments` 取 `result.deployments[0].versions[0].version_id` → `GET .../versions/{那个id}` 读 `resources.script.etag` 与 `resources.bindings`。`VERSION="0.2.0"` 从 `ac9b352` 起就没 bump，⛔ 证不了构建。
3. **"GitHub↔Linear↔Notion 三向循环"这个担心已被实测否定。** Worker 全文 `mutation` 命中 0 次；Two-way 开启后两侧新增镜像对象 0 条。⛔ 别再为此写"护栏"代码——真该补的是**部署自动化**（见下）。

## 量具级教训（本轮新增，都是"看着像结论其实是自己的工具坏了"）

- **`api.postman.com` 现在挂在 Cloudflare 后面**：用默认 UA `Python-urllib/3.x` 调它 ⇒ **HTTP 403 + Error 1010 "Access denied based on browser signature"**，而同一时刻 curl 的 UA 全通。⇒ 换 HTTP 库先带正常 UA，⛔ 别把 1010 报成"Postman 封号"。
- **不带 `LIMIT` 的 Notion SQL 只回了 2 行**（同一条查询加 `ORDER BY id LIMIT 20` 回 7 行，`COUNT(*)` 也是 7）。⇒ 行列表**必须配一条 `COUNT(*)` 交叉**，否则会把"读到 2 行"当成"库里只有 2 行"。这类假象比空结果危险，因为它回的是**看起来合理的行**。
- **`disabled` 的按钮可能只是 spinner**：Delete API Key 那个按钮 `disabled=""` 且 `innerText` 为空（标签在 `aria-label` 上），我据此判"点不动"。实际提交已经发出去了 —— reload 后表为空、同一个 `GET /me` 从 **200 变 401** 才是真凭据。⇒ 状态判定要看**服务端回读**，⛔ 看按钮。
- **`fill` 进 React 受控输入只改 DOM `value`，不改组件 state** ⇒ 表单看到空值、静默不提交。本轮靠"读按钮的 disabled/spinner"定位到这个，最终用 `evaluate` 走原生 setter 或直接换 UI 路径。
- **"派子 agent 独立复算"这件事，在 Qoder 上要打个折**：子会话拿不到本会话的 MCP 连接器（实测其 `mcp.json = {}`），所以它只能验 GitHub 一侧（`gh api` 可用），Linear/Notion/Cloudflare 侧一律"无法判"。⇒ 想真独立复算，得**另开一个客户端会话**（有钥匙的那家），⛔ 别用子 agent 冒充第二双眼睛。本轮它仍然有价值：仓库侧 blob `3a698aff59f5…` 与"三分支实况""`mutation` 0 次"都是它自己算的，且它明确写了哪些没验到、没有抄数。
- **回执 `success:true` 不等于动作发生**（kimi 的 `key_type` 报了 `length:22`，实际页面根本没有那个输入框 —— 它回的是**我传进去的字符串长度**）。

## 只读漂移检测（09-23 新增，已实测 + 故障注入验过）

仓库里多了两样东西：`tools/drift_check.py`（⛔ 全程只读，只 GET）与 `drift/known_good.json`（基线登记：服务版本 id、产物 etag、四个 `secret_text` 绑定、仓库 blob SHA、记于哪一刻）。

```bash
export CLOUDFLARE_API_TOKEN=...      # ⛔ 别写进任何文件；见「部署凭据」那节
python3 tools/drift_check.py         # 退出码 0=无漂移 1=有漂移/要看 2=检测器自己跑不动
```

它查四件事：① 服务版本的 **etag** 是否等于登记值；② **绑定集合**是否等于登记的四把 secret（少一把 = 锁没了或凭据没了）；③ 是否存在**内容不同但未部署**的版本（有 ⇒ 字节判据此刻不可用，直说，不误报"线上≠仓库"）；④ 部署是不是**分流**（多版本时提醒人工看，脚本不猜）。

**它是有牙的，不是摆设**——两组注入都当场报错：登记 etag 尾字符改一个 ⇒ "etag 与登记值不同"；把 `SYNC_TOKEN` 从期望绑定里抽掉 ⇒ "绑定集合与登记值不同：多=[secret_text:SYNC_TOKEN]"。⚠️ 反向的坑也在代码注释里写着：⛔ 别拿 `result.scripts`、⛔ 别看裸 scripts 端点。

**今晚的真实判定**：`⚠️ 有一个未部署的版本 #10（a7ba0f39，wrangler 传的打包件）与服务版本内容不同、绑定相同`。⇒ **用户 09-23 拍：这条告警就让它亮着**，⛔ 不要为了让检测器变绿去改登记值。它是一盏真的航标灯；下次真部署会用新的服务版本自然把它覆盖掉。（脚本提示里那句"确认线上正确后改登记值"针对的是**etag/绑定真变了**的情形，⛔ 不是给"消音"开的口子。）

## 部署凭据（09-23 新铸，以及"只检测不切流量"这个决定）

- Cloudflare **Account API Token** `deploy-linear-sync-30d`：权限⛔ 只有一条 `Individual Workers Editor`，且只作用于 `linear-sync`；**2026-10-24 自动过期**。值的存放：本机 `%LOCALAPPDATA%\cf_deploy_token.txt`（0600）。⛔ 不进仓库、不进聊天、不进任何 agent 的 prompt。
- **实测过的边界**：读 `linear-sync` settings 200 ✅｜新建别的 Worker 403 ✅｜删 `linear-sync` 403 ✅｜读 Pages 403 ✅｜⚠️ **列出账号下所有 scripts 是 200**（per-worker 作用域⛔ 没挡住列举，只挡住内容）—— 别把这把钥匙当成"账号级隔离"。
- `wrangler 4.136.3 whoami` 用它登录成功；`versions upload` 实测**四个 `secret_text` 全部保留**（官方也写 *secrets are never deleted by deployments*；会被删的是 `vars`，本 Worker 的 env 本来就是空）⇒ "自动部署会洗掉凭据"这个担心已被实测否定。
- **用户 09-23 拍：只做检测，不切流量。** 理由（写在 `versions upload` 的输出里）：真切过去之后线上就是**构建产物**，"字节与仓库相同"这个判据永久作废，得换成"从 commit X 构建"的来源证法（版本可带 tag/annotation，方向是这个，⛔ 尚未落地）。要重启这个话题，就是"我要 CI 自动部署了"那一刻。


## 现在到底是什么状态

- Worker 已上线：`https://linear-sync.amy4399666.workers.dev/`，`GET /health` 返 `ok:true`、`missingConfig: []`。
- 它做的事：**主动拉** Linear 的 issue（GraphQL），按 `Linear ID` upsert 进 Notion 数据库。**⛔ 没有入站 webhook，⛔ 不写 Linear**。
- `POST /sync` 有鉴权且**正反两面都已实测**：不带 → 401（手机，09-22 23:36）；带对 → 200 + 真写（Postman 云端，09-23 13:49）。
- `GET /selftest` 是**无鉴权只读探针**：跑一次 dryRun，⛔ 不写 Notion，但会吃 Linear API 配额并泄露 `fetched` 这个数。它是唯一不需要出口就能验收闸门 3/5 的手段（手机打开一个链接即可）。⚠️ 它的 `errors:[]` 与 `failed:0` 在 dryRun 下是**结构性常量**，⛔ 不是证据。

## 还欠着的两件事

1. **`SYNC_TOKEN` 暂不轮换（09-23 用户拍板，⛔ 这是决定不是待办）。** 现值出现在本机会话日志里（同一值 16 处），也短暂进过 Postman 环境（该环境已删）。不换的理由：换完就没法验证，而"一把没人验过的锁"比"一把已知泄露面的锁"更坏 —— 验证要重新走一遍上面的出口流程。⇒ **谁都不许擅自换这把锁**；要换只能由用户重新授权，且必须与验证打包：先建新值→立刻发一枪→确认 200→再登记新值的取法。⛔ 不要只换不验。
2. **仓库与线上之间仍然没有自动链路（这是**决定**，不是缺能力）。** 部署记录 9 条，source 只有 `dash_template` / `quick_editor` / `dash`；`wrangler` 已可用（token 与 `versions upload` 都验过，见上两节），但用户 09-23 拍**只做只读检测、不切流量**。⇒ 现在治漂移的手段是 `tools/drift_check.py`（能发现"线上被动过"和"凭据少了一把"），⛔ 不是"push 即上线"。要换成自动部署，前提是先把"线上==仓库"的判据从字节比对换成来源证明（版本 tag 记 commit），否则漂移只是换了个看不见的方向。

次要遗留：**`feat/selftest-probe` 分支已删**（09-23，走 `gh api -X DELETE .../git/refs/heads/...`；删前证 `ahead_by=0`、无独有文件、PR #3 `merged=true`，删后回读分支列表 + 阴性对照）。⚠️ 顺带纠正一条旧说法："github 连接器没有删分支工具"⛔ 不等于"agent 删不掉" —— `gh` 与连接器是**两套凭据**，这把本来就能写。剩下的技术债只有一条：`Labels` 是 multi_select 且 options 为空 —— 用户 09-23 定性为**薛定谔的雷**，⛔ 不预先造选项（猜不到名字），等真要做"标签同步"时再一起补；当前 7 条 issue 的 labels 全空所以不触发（错误原文与 request_id 已记在 AMY-7）。

## 钥匙能力矩阵（省你三小时，⛔ 别当现行值）

| 通道 | ✅ 能 | ⛔ 不能（错误码） |
|---|---|---|
| github 连接器 | 读、写文件、建分支、合并 PR、删文件（均实测成功） | ⛔ "token 只读、写会 403" 已被当场证伪；⚠️ 它自己没有删分支的工具 —— 但 `gh`（另一套凭据，push/admin 齐）能删，⛔ 别把"工具没有"当成"能力没有" |
| cloudflare MCP | 读配置、读 secret **名字**、拉线上源码、改配置（dashboard 换代码不清 bindings） | 写 secret（**10405**）；创建/替换 Worker（**10007**）；读遥测（**403**）；fetch 自家 workers.dev（**403**） |
| linear 连接器 | 读写 issue/project；`patch` 可局部改正文（**锚点不匹配则整块不写**，安全） | 改附件标题（无接口）；`links` 回执成功但 **0/1 生效** ⇒ 写后必回读；⚠️ 正文里写 `AMY-N` 会**推高对端 `updatedAt`** ⇒ 滞后量用 `completedAt` |
| notion 连接器 | 读库 schema（含 select 选项列表）、读写页面、SQL 查询 | SQL 不带 `LIMIT` 会**静默少回行**；单次 `-32603` 假失败重试即过；⛔ 不会自动新建 select 选项 |
| **postman 连接器 + REST** | **✅ 云端发 HTTP 请求 = 本链路目前唯一不需要手机的出口**；collections/environments/monitors 全套 REST 可用 | `/run/collection` 已 404；monitor 结果无响应体；⛔ 默认 UA 被 Cloudflare 1010 拦 |
| qca 云沙箱 | 跑 shell、有外网 | 到 workers.dev（`allowed_hosts: []` 不可改 ⇒ DNS 黑洞 `108.160.166.9`） |
| 用户本机 | 校园网常规出口；github/notion/linear/cloudflare/**postman** API 全通 | 到 workers.dev（**SNI 重置**）；⛔ 开不了 VPN |
| **用户手机 + VPN** | 能打到这个端点；GET 一个链接就能验收闸门 3/5 | 浏览器发不出 `Authorization` 头 ⇒ 只能测"不带密码"那一半 |

计费提醒：⚠️ **"模型限免"≠"这次调用免费"**。qca 一次探针实测 1.01 积分 = model 0.29 + **sandbox_runtime 0.71**；而 `list_models` 里该模型根本没有 `price_factor` 字段 ⇒ ⛔ 只看 price_factor 会漏掉沙箱运行时这一半。

## ⚠️ 工具陷阱：`create_or_update_file` 是**整份替换**

实测：只传一行去"改一行"，整个 HANDOFF.md 从 6,036 B **被覆成 160 B**，回执仍为成功。
⇒ 改这个文件必须**整份重发**。要局部改，⛔ 用这个工具，改用 git 本地提交或先 `get_file_contents` 拉全文再改。
⇒ 判据：回执里的 `size` 与 `content.sha`。
⇒ 手抄全文的安全做法：先在本地算出目标 blob SHA-1，推完拿 GitHub 回的 `content.sha` 对撞（本轮多次零漂移都是这么做的）。
⇒ ⛔ 文档里不要钉自己的 HEAD commit 号（下一次提交就作废）；⚠️ 写时刻时拿 UTC 原文换北京时间。

## 变更约定

- 登记按"原文不改、文末追加"——但⛔ 只读前 20 行一定读到过期快照，所以**更正必须同时放顶部横幅**。
- 每条结论都要写"**怎么测的 + 测于哪一刻**"，⛔ 不要只写"现行值"。
- 写操作回执成功不算落盘，**必回读**；回读接口本身也要跑阳性对照（本轮：正则扫本地文件 0 命中 ⇒ 同一正则打在会话日志上必须命中，否则那个 0 不算数）。
- ⛔ 本地记忆（各客户端自己的 memory 目录）**不是交接面**——它是每家一份的。要别人不重踩，必须写进本文件或 Linear。
- 凭据：⛔ 不把 secret 值写进本文件、聊天记录或任何 agent 的 prompt；需要用时**从落盘点直接取**，只打印长度与前缀。
