# 接手须知（HANDOFF）

> 这个仓、这条链路（Linear ↔ GitHub ↔ Notion ↔ Cloudflare）**以后不止一个 agent 在跑**。
> 本文件是给下一个会话的入口。⛔ 动手前先读完。改于 2026-09-22 23:5x（北京）。
> 另两处交接面：Linear 项目 **P-AMY-1** 顶部横幅、工单 **AMY-6 / AMY-7** 文末记录。

## ⭐ 分工原则：按节点插拔，⛔ 按平台性格分工（2026-09-22 用户定）

常见诱惑：“这家负贵海外连接器、那家负贵国内基建、第三家做归档”。⛔ 不要。

理由（今晚实测）：同一句结论（“github token 只读、写会 403”）在不同客户端会**各自复述、各自当真**——那个错误从 09-20 活到 09-22，被三家各引用一次，直到本轮 `merge_pull_request` 成功才当场碎掉。
⇒ **按平台性格分工，会把错误也一起分工**；按节点插拔才会逼新 agent 自己重测。

⇒ 引入新 agent 的**唯一合法触发条件**是：某个节点真坏了 / 需要替换 / 需要第二视角交叉复算。⛔ 不是“它家有特色”。

| 节点 | 当前状态 | 什么时候才换人接 |
|---|---|---|
| 仓库与代码 | ✅ 实现已合并（`628cef6`）；⛔ 本文不钉 HEAD commit 号——钉了就一定会过期（包括本文自己），HEAD 请 `list_commits` 现查 | 几乎不需要 |
| 部署（仓库→线上） | ⚠️ **无自动链路**，8 次全走 dashboard | ✅ 这就是最该找帮手的一环（接 `wrangler` / Workers Builds） |
| Linear 登记 | ✅ 三勾关闭、横幅已就位 | 需要独立复验时（⛔ 不许引用本文数字） |
| Notion 落点 | ✅ 字段映射已定 | 同上 |
| 端点可达性 | ⚠️ 只有用户手机能打到 | 新 agent **自带出口**时（这是真价值，不是特色） |

## 现在到底是什么状态

- Worker 已上线：`https://linear-sync.amy4399666.workers.dev/`，`GET /health` 返 `ok:true`、`missingConfig: []`。
- 它做的事：**主动拉** Linear 的 issue（GraphQL），按 `Linear ID` upsert 进 Notion 数据库。**⛔ 没有入站 webhook，⛔ 不写 Linear**。
- `POST /sync` **已加鉴权且实测拦得住**（23:36 手机验）：不带密码回 401。
- ⚠️ **唯一从未跑过的一环：带密码的同步能不能成功。** 加锁之后没人验过。

## 带密码怎么发（下一个 agent 请先干这件）

```bash
curl -X POST https://linear-sync.amy4399666.workers.dev/sync \
  -H 'content-type: application/json' \
  -H "authorization: Bearer $SYNC_TOKEN" \
  -d '{"dryRun":true,"teamKey":"AMY"}'
```

先 `dryRun` 看映射，再去掉 `dryRun` 正式同步。期望 `fetched/created/updated/failed` 四个数对得上。
看到 401 先查自己有没有带 `Authorization` 头，那是锁在正常工作，⛔ 不是“同步坏了”。
⚠️ 头必须叫 `authorization`、值必须是 `Bearer ` + 原文比较，**大小写敏感、不多不少一个空格**。

## 三条“别再重踩”的实测结论

1. **判“代码有没有入库”必须 `list_branches`。** 09-20 起实现全在 `demo/sync-skeleton`，而 `main` 只有一个 16 行 README 骨架——这个假象骗了两个会话两天。现在已合并（`628cef6`），但同类坑会再发生。
2. **“线上代码 == 仓库”要算哈希，⛔ 别看版本号。** 拉 `GET /accounts/{acct}/workers/scripts/linear-sync` 的 multipart 正文，按 `blob <len>\0` 算 SHA-1；当前应等于 `6579b51ccf0f746737df8278dd39042cf0838750`。`VERSION="0.2.0"` 从 `ac9b352` 起就没 bump，证不了构建。
3. **“GitHub↔Linear↔Notion 三向循环”这个担心已被实测否定。** Worker 全文 `mutation` 命中 0 次；Two-way 开启到 23:0x 两侧新增镜像对象 0 条。⛔ 别再为此写“护栏”代码——真该补的是**部署自动化**（见上表）。

## 钥匙能力矩阵（省你三小时，⛔ 别当现行值）

| 通道 | ✅ 能 | ⛔ 不能（错误码） |
|---|---|---|
| github 连接器 | 读、写文件、合并 PR、删文件（均实测成功） | —— ⛔ “token 只读、写会 403” 已被当场证伪 |
| cloudflare MCP | 读配置、读 secret **名字**、拉线上源码、改配置 | 写 secret（**10405**）；读遥测（**403**）；fetch 自家 workers.dev（**403**） |
| linear 连接器 | 读写 issue/project；`patch` 可局部改正文 | 改附件标题（无接口）；`links` 回执成功但 **0/1 生效** ⇒ 写后必回读 |
| qca 云沙箱 | 跑 shell、有外网 | 到 workers.dev（`allowed_hosts: []` 不可改 ⇒ DNS 黑洞 `108.160.166.9`） |
| 用户本机 | 校园网常规出口 | 到 workers.dev（**SNI 重置**）；⛔ 开不了 VPN |
| **用户手机 + VPN** | ✅ 目前**唯一**能打到这个端点的设备 | 浏览器发不出 `Authorization` 头 ⇒ 只能测“不带密码”那一半 |

计费提醒：⚠️ **“模型限免”≠“这次调用免费”**。qca 一次探针实测 1.01 积分 = model 0.29 + **sandbox_runtime 0.71**；而 `list_models` 里该模型根本没有 `price_factor` 字段 ⇒ ⛔ 只看 price_factor 会漏掉沙箱运行时这一半。

## ⚠️ 工具陷阱：`create_or_update_file` 是**整份替换**

09-22 23:53 实测：只传一行表格内容去“改一行”，它把整个 HANDOFF.md 从 6,036 B **覆成 160 B**，回执还是成功。
⇒ 改这个文件必须**整份重发**。要局部改，⛔ 用这个工具，改用 git 本地提交或先 `get_file_contents` 拉全文再改。
⇒ 判据：回执里的 `size` 与 `content.sha`。本次靠 `size: 160` 当场发现并复原。

## 真存在的风险（当前未处置）

**仓库与线上之间没有任何自动链路。** 8 次部署的 source 只有 `dash_template` / `quick_editor` / `dash`，`wrangler` 一次都没跑过，secrets 也是手贴的。⇒ 今天“线上==main”是**手抄对上了**，不是机制保证的。要治漂移，下一步是接上 `wrangler deploy`（或 Workers Builds 跟 Git 绑），⛔ 不是给 `/health` 加个 commit 字段（那只能让漂移可见）。

## 变更约定

- 登记按“原文不改、文末追加”——但⛔ 只读前 20 行一定读到过期快照，所以**更正必须同时放顶部横幅**。
- 每条结论都要写“**怎么测的 + 测于哪一刻**”，⛔ 不要只写“现行值”。
- 写操作回执成功不算落盘，**必回读**；回读接口本身也要跑阳性对照。
- ⛔ 本地记忆（各客户端自己的 memory 目录）**不是交接面**——它是每家一份的。要别人不重踩，必须写进本文件或 Linear。
- ⛔ 文档里不要钉自己的 HEAD commit 号（包括本文件）——它在你写下它的那一秒就已开始过期。
