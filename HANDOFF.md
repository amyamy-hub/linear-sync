# 接手须知（HANDOFF）

> 这个仓、这条链路（Linear ↔ GitHub ↔ Notion ↔ Cloudflare）**以后不止一个 agent 在跑**。
> 本文件是给下一个会话的入口。⛔ 动手前先读完。最近一次改动：2026-09-24 01:5x（北京）。
> 另两处交接面：Linear 项目 **P-AMY-1** 顶部横幅、工单 **AMY-6 / AMY-7** 文末记录。
> ⚠️ 时刻口径提醒（本文件栽过一次）：写时刻要拿**部署/回执的 UTC 原文**换北京时间，⛔ 别照抄上一张图的小时数。

## ⭐ 当前状态：闸门 1–6 全部闭环，且 `SYNC_TOKEN` 已轮换并双向验完（09-24）

链路已端到端跑通并且**验收证据来自目标系统回读，不是 Worker 自报**。下一个 agent 若只想复现一次同步，直接看下面「怎么发这一枪」；⛔ 不要从头重查已定案的三条（见「别再重踩」）。

> 🔴 **09-24 凌晨更正（执行位 Qoder CN，全部现算）—— 本节覆盖下方所有与之冲突的旧表述**
>
> 1. **闸门 2 的收据换版了**：服务版本从 `2fc04c35`(#9) 变成 **`5e011838`(#13)**（deployment `67e626d1` @ `2026-09-23T16:53:57Z`，`quick_editor`，100% 流量），etag `b5cc1a50dc085ecd…`，裸下载端点当场取回 **10,860 B / git blob `3a698aff59f5…` = `main:src/index.js`**，dashboard 顶栏同刻显示 `5e011838 (Active) Latest` ⇒ **UI／CF API／哈希三处一致**。⚠️ `drift/known_good.json` 当时还停在 #9 的 etag ⇒ 检测器会把这次**合法部署**报成漂移；改登记值要带上当场收据，⛔ 不是消音。
> 2. ⭐ **新机制事实：「上传未部署」并不无害。** #10（`wrangler versions upload`，9,910 B 打包件 `3e14bb90…`）从未出现在 deployments 里，却**占住了脚本槽位**，被之后每次 dashboard 保存继承 ⇒ **15:27Z–16:53Z 线上跑的就是那份打包件，不是 main**。⇒ 判"线上==仓库"只能在**上传即部署的那一刻**取字节，⛔ 事后无解。
> 3. 🔑 **`SYNC_TOKEN` 轮换完成（两发行为凭据齐了）**（用户 09-23 深夜改口拍定 ⇒ 下面那条"暂不轮换"**作废**）。新值 48 位 hex、前缀 `bd96`，⛔ 不在任何日志或对话里；配置面 4 把全 `secret_text`。行为面 ⭐ **新通**：Postman 网页版带新值 + `{"dryRun":true,"teamKey":"AMY"}` → **200 / `Test Results 6/6` / 173 ms**。⭐ **旧拒**：同一套装置只把 `Authorization` 换成**旧值 `a1f3…8201`**（36 hex，可从本机 `qodercli.log` 的 `fill @e4` 参数位还原）→ **401**，`cf-ray: a3fb48b32d9b85be-hkg`（用户 09-24 00:5x 北京读数）。⇒ 加上早已在场的两发对照（不带密码 → 401，闸门 4；带**故意写错**的 Bearer → 401），锁确实只认新值，⛔ 不是"带什么都放行"，也不是"锁没上所以放行"。⚠️ **这两发的分钟级 UTC 戳我没留**（只留了 `cf-ray` 与 `Test Results` 截图读数）⇒ 下一位要更硬的时序证据就重打，别把我的"深夜窗口"当时间戳引用。**"轮换完成"这四个字从现在起才允许写。**
> 4. ⭐ **第四出口 = Cloudflare 控制台 Quick Editor 右侧的 HTTP 面板**：方法可选 `GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS/QUERY`，有 `+ Add header`，**也有 `Body` 输入框**，而请求由 **Cloudflare 自己发出** ⇒ 能打到 `*.workers.dev`（同刻本机 curl=000、`WebFetch`=fetch failed、CF MCP=403）。实测 `GET /selftest` → `ok:true, fetched:7, preview 5, syncAuthEnabled:true, durationMs:565`。⛔ 撤回我上一轮那句"它发不出 body"——那是把"kimi 的 a11y 快照取不到 iframe 里的控件"写成了"它没有"，**与本文批评过的"我钥匙拿不到≠API不支持"同族，且是我自己第二次犯同一形状**。
> 5. ⚠️ **两处数字更正**：① 401 正文 `content-length` = **29**（`JSON.stringify(body,null,2)` 美化输出正好 29 字节），本文原写的 **26 B 是错的**，而那个数被当成"区分 401/200"的证据用过；测于 `2026-09-23T17:11:30Z`。② `GET .../deployments` **默认只回一页、10 条封顶** ⇒ 本文所有"N 次部署"作废。**但⚠️ 这个数本身也是快照**：09-24 01:44（北京）带 `per_page=100` 现算 **deployments = 12、versions = 13**，而 `result` 里**根本没有 `result_info` 字段**（我横幅上一版写的"`result_info.total_count` = 11"⛔ 取法就是错的，那是 versions 列表另一条路的字段；且 11 是 #13 部署**之前**的数）。⇒ 登记要写"**怎么算 + 算于哪一刻**"，⛔ 不要写"现行值"——这个数每部署一次就 +1。
> 6. ⛔ **轮换 SOP 补一条（我的流程漏洞）**：只规定"值走剪贴板、不进对话"，却没要求**先落一份到用户保管处** ⇒ 第二枚值一度只活在读不出来的 CF secret 里，无法自证"新通"。✅ 正确顺序：**生成 → 先存进保管处 → 粘进 CF（Type 必须选 Secret）→ 立刻把同一枚粘进所有测试环境 → 当场验 200**。中途复制别的东西就会断链（本轮真断过一次）。
> 7. ⚠️ **Windows `clip.exe` 会把含中文的 UTF-8 吃字节**：用它送这份源码，粘进编辑器变成 **357 行 / 38 个错误**（本文那份是 365 行）。✅ 正解：`Get-Content -Raw -Encoding UTF8 | Set-Clipboard`，并且**把剪贴板往返落盘再算一次 git blob SHA-1 与仓库对撞**才算"贴对了"。⛔ 另：dashboard 编辑器的 PROBLEMS 在纯 JS 文件上有常态噪声（6 条 `ts(2304)`），不能当判据。

> ~~📌 **`SYNC_TOKEN` 暂不轮换 —— 这是用户 2026-09-23 拍的决定，⛔ 不是上一家漏做。** 理由与打包做法见「还欠着的两件事」第 1 条。⛔ 未经用户重新授权，任何 agent⛔ 不要动这把锁。~~
> ⇒ **09-24 作废**：用户 09-23 深夜改口拍定轮换，理由是"换完没法验证"这个前提随着出口被打通而消失。原文按"不改只标"的约定留在 `「还欠着的两件事」` 第 1 条。

## 分工原则：按节点插拔，⛔ 按平台性格分工（2026-09-22 用户定）

常见诱惑："这家负责海外连接器、那家负责国内基建、第三家做归档"。⛔ 不要。

理由（实测）：同一句结论（"github token 只读、写会 403"）在不同客户端会**各自复述、各自当真**——那个错误从 09-20 活到 09-22，被三家各引用一次，直到 `merge_pull_request` 成功才当场碎掉。
⇒ **按平台性格分工，会把错误也一起分工**；按节点插拔才会逼新 agent 自己重测。

⇒ 引入新 agent 的**唯一合法触发条件**是：某个节点真坏了 / 需要替换 / 需要第二视角交叉复算。⛔ 不是"它家有特色"。

## 闸门状态（这是本文件唯一允许自己引用的部分）

| 闸门 | 内容 | 状态 | 凭据（含测于哪一刻） |
|---|---|---|---|
| 1 | 仓库定位与分支 | ✅ | 实现在 `main`；⛔ 判"有没有入库"必 `list_branches` |
| 2 | 线上代码 == 仓库 | ✅ **09-24 拿到当场三元组收据** | 服务版本 **`5e011838`(#13)**（deployment `67e626d1` @ `2026-09-23T16:53:57Z`，`quick_editor`，100%）＋产物 etag `b5cc1a50dc085ecd…`＋裸下载端点当场取回 **10,860 B / git blob `3a698aff59f5…` = `main:src/index.js`** 逐字节相同；dashboard 顶栏同刻 `5e011838 (Active) Latest` ⇒ UI／API／哈希三处一致。⚠️ 等价**只在"上传即部署"那一瞬成立**，事后重跑读到的是"最后一次上传"（塌因见顶部横幅第 2 条与「怎么判线上==仓库」） |
| 3 | 配置在场 | ✅ | `GET .../secrets` 四个名字（09-24 全 `secret_text`）；`/selftest` 从运行时报 `syncAuthEnabled: true` |
| 4 | 不带密码被拒 | ✅ **已升级为直读** | ①09-22 23:36 手机截图；②**09-23 深夜由我从 Postman 网页版直发**：不带 `authorization` → **401 / 63 ms / `Test Results 4/4`**（断言含"正文逐字 `{"error":"unauthorized"}`"＋"无 `ok` 字段 ⇒ 根本没进 `runSync`"）；③带**故意写错**的 Bearer → **401 / 62 ms / 3/3**；④**09-24 带旧密钥** → **401 / `cf-ray a3fb48b32d9b85be-hkg`** ⇒ 锁不是"带什么都放行" |
| 5 | 带密码放得进（dryRun） | ✅ **09-24 换锁后复证** | 同一套装置带**新** Bearer + `{"dryRun":true,"teamKey":"AMY"}` → **200 / `Test Results 6/6` / 173 ms**（`ok:true`、`dryRun:true`、`fetched>0`、`preview` 是数组、`created=updated=failed=0` 安全阀）。⚠️ `fetched` 的**具体数字**没入档（响应体在虚拟化编辑器里取不到），只有"＞0"这条断言成立 ⇒ 旧表述"由闸门 6 反推"已作废。另：`GET /selftest`（09-23 10:44 手机、09-24 CF 控制台 HTTP 面板）→ `fetched:7, previewCount:5, errors:[], syncAuthEnabled:true` |
| **6** | **带密码真写进 Notion，且幂等** | ✅ **09-23 13:49** | Postman 云端 `POST /sync` → **HTTP 200 / 164 B / 2458 ms**；Notion 回读：AMY-6/7 `Status` Backlog→**Done**、AMY-1/5 `Updated At` 前移、AMY-2/3/4 未动；三次运行后 `COUNT(*)` 仍 **7** 且 `COUNT(DISTINCT "Linear ID")` 仍 **7** |

## 闸门 6 到底证了什么、⛔ 没证什么（09-23 13:49）

**证了**：鉴权分支放行（401 只会回 **29 B** 的 `{"error":"unauthorized"}`，实测 164 B）；`runSync` 真跑了 4 次 Notion `PATCH`；逐行写入值与 Linear 的 `updatedAt` 相等 ⇒ `created=0 / updated=4 / failed=0` 是**由状态差集推得**；重复执行不新增行 ⇒ 按 `Linear ID` upsert 成立。

> ⚠️ 09-24 勘误：这一句原文写的是"**26 B**"，那个数被当作"区分 401 与 200"的证据引用过。现算正文 `JSON.stringify({error:"unauthorized"},null,2)` = **29 字节**，且实测有一发 401 的 `content-length` 读数就是 **29**（测于 `2026-09-23T17:11:30Z`，cf-ray `a3fb2b4598e3dda0-hkg`）。⇒ 26 是**我抄错的**，⛔ 别再引用。结论本身不受影响（29 ≠ 164，区分仍然成立）。⚠️ 但⛔ 别拿 29 当计数证据 —— 见下面那条"字节数反推不出计数"，同一族。

**⛔ 没证**：Worker 自报的 JSON 数值一个都没拿到 —— Postman monitor **不回传响应体**，只回传 `contentLength`。

**顺手测到一条通则：字节数反推不出计数。** 响应体是 `JSON.stringify(body, null, 2)`，而 `(fetched, created, updated, failed)` 只要都是个位数，`fetched:2/updated:2` 与 `fetched:4/updated:4` 与 `fetched:7/updated:7` 的**长度全都是 164 B**。⇒ ⛔ 别拿"响应大小对得上"当计数正确性的证据（同族：聚合数反推不出逐份数）。想要数就回读目标系统，正好也更硬。

**另一条精度发现**：Notion 把 `Updated At` 的**秒吃掉了** —— Linear `2026-09-22T15:20:06.900Z` 落到 Notion 变 `15:20:00Z`（在 `notion-fetch` 的原始 property 里就是这样，⛔ 不是展示层截断）。⇒ 任何"同步是否落后"的滞后量计算，精度上限是分钟，⛔ 别用毫秒比对。

## ⚠️ `since` 的爆炸半径会被 `updatedAt` 批量抬升

本文件上一版算出"`since=2026-09-22T00:00:00Z` 只选中 AMY-6/7 两行"。发枪前现读 Linear：**AMY-1、AMY-5、AMY-7 的 `updatedAt` 全被顶到 `2026-09-23T04:22:10.888Z`**（AMY-7 是 `.725Z`），而 AMY-6 仍停在 09-22 ⇒ 期望值当场从 2 变成 **4**。

原因不是悬案，就是本文件「钥匙能力矩阵」里那条：**Issue 正文里出现 `AMY-N` 会被 Linear 自动建关联并推高对端 `updatedAt`**。上一轮往 AMY-7 文末追加记录时点名了 AMY-1/5/7 ⇒ 那几条被"无内容变更"地刷新。AMY-6 没被顶，因为它对 AMY-7 的关联早已存在（这条推论与观测一致，但⛔ 未单独复测）。

⇒ **发 `POST /sync` 之前先 `list_issues` 现算 `fetched` 期望值**，⛔ 别引用上一次算出来的条数。滞后量本身要用 `completedAt`，不要用 `updatedAt`。

> 溯源（有另一家说这条规则"是本轮新加的、不该写成文档早就记着"）：该规则首现于 commit **`863583a6` @ 2026-09-23T04:11:17Z**（北京 12:11），前一版 `a0cea544` 里 0 命中；我 13:40 读到的那版 blob `4e1f9182`（10,587 B）里 `推高对端`/`completedAt` 各命中 1 次。⇒ "文档早就记着、我没引用"这个说法在本轮**成立**；对方引的是自己 00:4x 读的 6,746 B 旧快照。⚠️ 同一条教训反过来也适用：**比 blob 之前先比时间戳**，别拿"我读过的那版"当"当时最新的那版"。

## 怎么发这一枪（闸门 6 的复现配方）

本机与两个云沙箱都打不到 `*.workers.dev`（SNI 重置 / DNS 黑洞 / MCP 出口策略，三种坏法）。**第三条路：让 Postman 云端替我发（已实测）；第四条路：Cloudflare 控制台自己的 HTTP 面板（09-24 实测，更近，见钥匙矩阵）。**

```bash
# 有正常出口的机器上（首选，最直接）
curl -X POST https://linear-sync.amy4399666.workers.dev/sync \
  -H 'content-type: application/json' \
  -H "authorization: Bearer $SYNC_TOKEN" \
  -d '{"teamKey":"AMY","since":"2026-09-22T00:00:00Z"}'
```

Postman 路线（**两条不同的路，别混**）：
- **闸门 6（09-23 13:49）** 走的是下面的 **REST + Monitors**（云端定时执行器，结果只回 `contentLength`）。
- **闸门 4/5 的直读、以及换锁的两发（09-23 深夜–09-24）** 走的是 **Postman 网页版手动 Send + Tests 脚本**（能看到 `Test Results n/n`、`content-length`、`cf-ray`，⛔ 看不到响应体内容，因为编辑器虚拟化 ⇒ 长 body 取不出来）。⚠️ 它的 Send 由 **Cloud Agent** 代发，**Cloud Agent 会自己挂**（见钥匙矩阵那行的对照发配方）。
- ⭐ 若只要发**四态鉴权**（不带/带错/带旧/带新）且允许真同步或 dryRun，**Cloudflare 控制台 HTTP 面板是更近的路**（同一浏览器、同一个已登录会话，不需要 Postman 账号）。
全程 REST，⛔ 不需要桌面客户端：

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
   > 🔴 **09-24 修正上面那句"而线上仍是看板那份纯源码"—— 它也不成立。** 实测：15:27Z 那次**只改了一个变量**的 dashboard 保存，把**脚本也换成了 wrangler 那份打包件**（etag `5d4e6aad…`→`00f6b1ca…`，裸端点读到 9,910 B / blob `3e14bb90…` / 不含 `export default`）⇒ **15:27Z–16:53Z 线上跑的就是 #10 那份打包件**。⇒ ⭐ **"上传但不部署"并不无害：它会占住脚本槽位，被之后每次 dashboard 保存继承。** 老配方不只是"会读错"，它读到的**恰好就是线上的**——只是那份不是你以为是的那份。
   > ⇒ 唯一可靠姿势：**在"上传即部署"的那一刻当场配对待登记三元组 `{version_id, etag, 当时的 git blob sha}`**（内容寻址只在那一瞬可得）。#13（`5e011838` @ `2026-09-23T16:53:57Z`）就是本线第一枚这样的收据，blob `3a698aff…` = `main:src/index.js`。
3. **"GitHub↔Linear↔Notion 三向循环"这个担心已被实测否定。** Worker 全文 `mutation` 命中 0 次；Two-way 开启后两侧新增镜像对象 0 条。⛔ 别再为此写"护栏"代码——真该补的是**部署自动化**（见下）。

## 量具级教训（本轮新增，都是"看着像结论其实是自己的工具坏了"）

- **`api.postman.com` 现在挂在 Cloudflare 后面**：用默认 UA `Python-urllib/3.x` 调它 ⇒ **HTTP 403 + Error 1010 "Access denied based on browser signature"**，而同一时刻 curl 的 UA 全通。⇒ 换 HTTP 库先带正常 UA，⛔ 别把 1010 报成"Postman 封号"。
- **不带 `LIMIT` 的 Notion SQL 只回了 2 行**（同一条查询加 `ORDER BY id LIMIT 20` 回 7 行，`COUNT(*)` 也是 7）。⇒ 行列表**必须配一条 `COUNT(*)` 交叉**，否则会把"读到 2 行"当成"库里只有 2 行"。这类假象比空结果危险，因为它回的是**看起来合理的行**。
- **`disabled` 的按钮可能只是 spinner**：Delete API Key 那个按钮 `disabled=""` 且 `innerText` 为空（标签在 `aria-label` 上），我据此判"点不动"。实际提交已经发出去了 —— reload 后表为空、同一个 `GET /me` 从 **200 变 401** 才是真凭据。⇒ 状态判定要看**服务端回读**，⛔ 看按钮。
- **⛔ "Notion 会自动新建 select 选项"这个说法是错的，别再传**（09-23 16:1x 现场重验）。另一家客户端看到库里多了第三个选项 `Done`，归因给"Worker 同步时 Notion 自动建的"，并据此要求把本文件那条改过来。**当场重做的实验否掉了它**：对 AMY-2 那行写一个全新的 select 值 ⇒
  `400 validation_error / Invalid select value for property "Status": "Qoder-自动建选项验证-勿留-20260923" / Value must be one of the following: "Backlog", "Todo", "Done" / If a new select option is needed, the data source must be updated to add it. / request_id: 4ad8f9d9-19ee-456a-b329-a029c0086c95`
  ⇒ 被拒、且 Notion 自己要求"要新选项就去改 data source"。`Done` 之所以已在白名单里，是因为**本文件上面记的那次 `ALTER`（09-23 12:2x 北京）**，⛔ 不是同步自动建的。写这次被拒后回读：AMY-2 仍是 `Todo`、库里仍是 7 行、没有垃圾选项。
  ⚠️ 顺带一条判据教训：**"我看了两次，中间多了个东西"只证明变化发生过，不证明是谁改的**。要说"自动建的"，必须做一次"写一个不存在的值，看它会不会自己长出来"——那才叫实验。
- **`fill` 进 React 受控输入只改 DOM `value`，不改组件 state** ⇒ 表单看到空值、静默不提交。本轮靠"读按钮的 disabled/spinner"定位到这个，最终用 `evaluate` 走原生 setter 或直接换 UI 路径。
- **"派子 agent 独立复算"这件事，在 Qoder 上要打个折**：子会话拿不到本会话的 MCP 连接器（实测其 `mcp.json = {}`），所以它只能验 GitHub 一侧（`gh api` 可用），Linear/Notion/Cloudflare 侧一律"无法判"。⇒ 想真独立复算，得**另开一个客户端会话**（有钥匙的那家），⛔ 别用子 agent 冒充第二双眼睛。本轮它仍然有价值：仓库侧 blob `3a698aff59f5…` 与"三分支实况""`mutation` 0 次"都是它自己算的，且它明确写了哪些没验到、没有抄数。
- **回执 `success:true` 不等于动作发生**（kimi 的 `key_type` 报了 `length:22`，实际页面根本没有那个输入框 —— 它回的是**我传进去的字符串长度**）。
- 🔴 **09-24 · 我的探针打印 `equal: true`，其实是 `undefined === undefined`**：字段名取错 ⇒ 两边都是 `undefined` ⇒ 判据**静默变绿**。✅ 任何"比一比"的探针必须**先把两边的值本身打出来**（长度/前缀即可），再打比较结果；只打 `true/false` 的判据不算判据。
- 🔴 **09-24 · `grep '[!0-9a-f]'` 不是取反**：方括号里的 `!` 就是字面 `!`。用它校验新 token 的字符集，通过与否都毫无意义 ⇒ 正解 `grep -qE '^[0-9a-f]{48}$'`。同族坑：`[--0-9a-f]` 会被当 range。
- 🔴 **09-24 · Windows `clip.exe` 会把含中文的 UTF-8 吃字节**：用它送这份源码，粘进 Monaco 变成 **357 行 / 38 个错误**（原文 365 行）。✅ 正解 `Get-Content -Raw -Encoding UTF8 | Set-Clipboard`，并且**把剪贴板往返落盘、再算一次 git blob SHA-1 与仓库对撞**，才算"贴对了"。（本轮真按 38 个错误点了 Deploy、真弹了错 —— 是这条把一次部署变成了可复算动作。）
- 🔴 **09-24 · dashboard 编辑器的 PROBLEMS 不能当判据**：纯 JS 文件在 CF 的 TS 检查器下有常态噪声（本轮 6 条 `ts(2304) Cannot find name`）。⇒ ⛔ 别拿"有没有红叉"判代码好坏；合法判据只有**行数 ＋ 事后 blob 哈希**。
- 🔴 **09-24 · 候选集是按"我以为钥匙长什么样"构造的，那个形状假设本身没有对照**：我先按"32 位十六进制"筛旧值，**正好把 36 位的真值筛掉**，于是拿两个 UUID/哈希当钥匙试了两发（都 401、无副作用 —— 401 进不去 `runSync`，所以这类试错是安全的）。真值要从 `bridge.py fill @e4 "<值>"` 那个**参数位置**去捞，并核"全 runs 目录该位置只有 1 个不同值"才敢定案。⇒ **按位置筛，⛔ 按长度/字符集筛。**

## 只读漂移检测（09-23 新增，已实测 + 故障注入验过）

仓库里多了两样东西：`tools/drift_check.py`（⛔ 全程只读，只 GET）与 `drift/known_good.json`（基线登记：服务版本 id、产物 etag、四个 `secret_text` 绑定、仓库 blob SHA、记于哪一刻）。

```bash
export CLOUDFLARE_API_TOKEN=...      # ⛔ 别写进任何文件；见「部署凭据」那节
python3 tools/drift_check.py         # 退出码 0=无漂移 1=有漂移/要看 2=检测器自己跑不动
```

它查四件事：① 服务版本的 **etag** 是否等于登记值；② **绑定集合**是否等于登记的四把 secret（少一把 = 锁没了或凭据没了）；③ 是否存在**内容不同但未部署**的版本（有 ⇒ 字节判据此刻不可用，直说，不误报"线上≠仓库"）；④ 部署是不是**分流**（多版本时提醒人工看，脚本不猜）。

**它是有牙的，不是摆设**——两组注入都当场报错：登记 etag 尾字符改一个 ⇒ "etag 与登记值不同"；把 `SYNC_TOKEN` 从期望绑定里抽掉 ⇒ "绑定集合与登记值不同：多=[secret_text:SYNC_TOKEN]"。⚠️ 反向的坑也在代码注释里写着：⛔ 别拿 `result.scripts`、⛔ 别看裸 scripts 端点。

**09-23 夜间的判定**：`⚠️ 有一个未部署的版本 #10（a7ba0f39，wrangler 传的打包件）与服务版本内容不同、绑定相同`。⇒ **用户 09-23 拍：这条告警当时就让它亮着**，⛔ 不要为了让检测器变绿去改登记值。（脚本提示里那句"确认线上正确后改登记值"针对的是**etag/绑定真变了**的情形，⛔ 不是给"消音"开的口子。）

> 🔴 **09-24 补一条，⛔ 别引用上面那句"下次真部署会自然覆盖"** —— 那句**错了**：`drift/known_good.json` 里没有东西会自动更新，**每次合法部署之后必须有人手动改登记值**。#13 部署后检测器登记的还是 #9 的 etag `5d4e6aad…` ⇒ 它会把**我们自己刚做的带收据部署**报成漂移。
> ⇒ **"灯红"现在有两种成因**：① 真漂移；② 合法部署后没更新基线。判之前先看 `deployments[0]` 的时刻与已知部署动作对不对得上。
> ✅ 09-24 01:4x（北京）已把基线更新为 **#13 三元组**（version_id `5e011838-ab37-4da9-8214-4ce91eb5f54d` / etag `b5cc1a50dc085ecd…` / blob `3a698aff…`），与本文同一次推送；json 里带 `receipt` 与 `history` 两段，写明"**这是带收据的更新，⛔ 不是消音**"。#10 那个未部署版本仍如实登记在 `known_undeployed_versions` 里 ⇒ 检测器**继续**报它。
> 🔴 09-24：那个"未部署版本 #10"的**存在本身**已被证明会造成真实事故（见顶部横幅第 2 条：它占住脚本槽位、被后续 dashboard 保存继承 ⇒ 15:27Z–16:53Z 线上跑的就是它）。当时"让灯亮着"的裁决针对的是**告警噪音**，⛔ 不是"打包件可以留在槽位里"。**下次动手时优先把它清掉或用一个从 main 部署的版本盖过它**（`wrangler versions upload` 只上传不部署的那条路，在这条链路上已被证明不是无害操作）。

## 部署凭据（09-23 新铸，以及"只检测不切流量"这个决定）

- Cloudflare **Account API Token** `deploy-linear-sync-30d`：权限⛔ 只有一条 `Individual Workers Editor`，且只作用于 `linear-sync`；**2026-10-24 自动过期**。值的存放：本机 `%LOCALAPPDATA%\cf_deploy_token.txt`（0600）。⛔ 不进仓库、不进聊天、不进任何 agent 的 prompt。
- **实测过的边界**：读 `linear-sync` settings 200 ✅｜新建别的 Worker 403 ✅｜删 `linear-sync` 403 ✅｜读 Pages 403 ✅｜⚠️ **列出账号下所有 scripts 是 200**（per-worker 作用域⛔ 没挡住列举，只挡住内容）—— 别把这把钥匙当成"账号级隔离"。
- `wrangler 4.136.3 whoami` 用它登录成功；`versions upload` 实测**四个 `secret_text` 全部保留**（官方也写 *secrets are never deleted by deployments*；会被删的是 `vars`，本 Worker 的 env 本来就是空）⇒ "自动部署会洗掉凭据"这个担心已被实测否定。
- **用户 09-23 拍：只做检测，不切流量。** 理由（写在 `versions upload` 的输出里）：真切过去之后线上就是**构建产物**，"字节与仓库相同"这个判据永久作废，得换成"从 commit X 构建"的来源证法（版本可带 tag/annotation，方向是这个，⛔ 尚未落地）。要重启这个话题，就是"我要 CI 自动部署了"那一刻。


## 两处对本文的更正 + 一条独立性口径（09-23 晚，WorkBuddy 国际版提出，已自验）

**更正一（我的错）**：本文与一次口头汇报里说过"worker UUID 拿不到、按版本取字节是 API 边界"。**前半句错**：那是把"我这把钥匙不行"说成了"这条路不行"。实测 —— 窄钥匙 `GET /accounts/{a}/workers/workers` = **403 / code 10000**；全局钥匙同一路径 = **200**，`id = 927d6c0d93bc407e99fdec24e5b350f5`。⚠️ 而且**不必走 beta**：旧端点 `GET /accounts/{a}/workers/scripts` 的返回里就带 `"tag": "927d6c0d93bc…"`；同一条记录还有 `deployed_on`（服务版本部署时刻）与 `modified_on`（最后一次上传时刻）—— 两者之差就是"线上多久没动"的现成读数。
　根因写在这里防重犯：当时的脚本用 `.get("result") or []`，把 **403 / 空列表 / 字段形状不符** 渲染成同一张脸 ⇒ ⛔ 探针不许吞状态码。
　**后半句仍成立**：新 API `GET /workers/workers/{uuid}/versions/{vid}` 只回元数据（`sources:null`、`modules:null`）⇒ "按版本取字节"确实无只读取法。**封死的是内容，不是身份。**

**更正二（措辞）**：`etag` 不是"未变"的保证，而是**一串采样点**。登记写法应是"截至 <时刻> 经 <N> 次独立采样未见变化"。当时三次：06:5xZ、08:2xZ（均窄钥匙）、08:3xZ（WorkBuddy），值都是 `5d4e6aad…`；⛔ 采样点之间是盲区。

> ⚠️ 09-24 追加两件事：① 那串 `5d4e6aad…` **已经作废** —— #13 部署后服务版本的 etag 是 `b5cc1a50…`，⛔ 别拿旧采样点当"未变"的证据。② 我上一轮说过"改配置（dashboard 只保存 Settings/Variables）会让 etag 变 ⇒ etag 零信息"，**那句撤回**：实测 15:27Z 那次"只改变量"的保存**确实换了脚本**（etag `5d4e6aad…`→`00f6b1ca…`），而 16:14Z 那次"把 plain_text 改成 Secret"的保存 etag **没变**。⇒ etag 确实跟踪脚本变化，只是它跟的是"最后上传的那份"，不是"你以为存上去的那份"。
> ③ ⛔ `etag` **不等于**文件哈希：`resources.script.etag` 是 64 hex 的产物指纹，而 `sha256(main:src/index.js)` 是另一个值，两者永远对不上 ⇒ 它只答"还是不是同一份东西"，答不了"那份东西等不等于仓库"。**要与仓库对撞只能算 git blob SHA-1，而那只在"上传即部署"那一瞬可取。**

**红线（文档逐字，别再试）**：`wrangler deploy` / Workers Builds / **Workers Script Upload API（`PUT /workers/scripts/{name}`）三者都会立即把新版本部署到 100% 流量** ⇒ ⛔ 谁都不许拿那条 PUT 做"不切流量的实验"。安全的只有 `wrangler versions upload`（文档原话 *not deployed immediately*；#10 的 `source: wrangler` + `annotations.workers/triggered_by = version_upload` 即为证）。

**独立性口径（别把账记浮）**：今晚参与方只有 **两家产品** —— Qoder CN（执行方：仓库、HANDOFF、Notion 库结构均出自它）与 WorkBuddy 国际版（复算方）。Qoder 派出的子会话**同产品、且拿不到 MCP 连接器**，⛔ 不计为第二双眼睛。⇒ "两家互相印证"独立的是**读数**，⛔ 不独立的是**前提**（同一份由一家写的交接面 + 同一个 Notion 库）。下结论用这句话，⛔ 不要写"三家交叉验证"。附带一例：判别"Notion 会不会自动建 select 选项"的那发实验里，假选项名叫 `Qoder-自动建选项验证-勿留-20260923` —— 它是**被反驳方的同源证据**，⛔ 不是自我印证，但确实出自同一只手。

## 现在到底是什么状态

- Worker 已上线：`https://linear-sync.amy4399666.workers.dev/`，`GET /health` 返 `ok:true`、`missingConfig: []`。
- 它做的事：**主动拉** Linear 的 issue（GraphQL），按 `Linear ID` upsert 进 Notion 数据库。**⛔ 没有入站 webhook，⛔ 不写 Linear**。
- `POST /sync` 有鉴权且**正反两面都已实测**：不带 → 401；带**故意写错**的 → 401；带**旧密钥**（轮换后）→ 401；带**当前密钥** → 200 + 真写（Postman 云端，09-23 13:49）。⇒ 四态全测过，锁只认当前值。
- `GET /selftest` 是**无鉴权只读探针**：跑一次 dryRun，⛔ 不写 Notion，但会吃 Linear API 配额并泄露 `fetched` 这个数。它是唯一不需要出口就能验收闸门 3/5 的手段（手机打开一个链接即可）。⚠️ 它的 `errors:[]` 与 `failed:0` 在 dryRun 下是**结构性常量**，⛔ 不是证据。

## 还欠着的事

1. ~~**`SYNC_TOKEN` 暂不轮换（09-23 用户拍板，⛔ 这是决定不是待办）。~~ ✅ **09-24 已轮换并双向往复验证完毕**（凭据见顶部横幅第 3 条）。原文整段保留如下，因为**它给出的那条纪律仍然有效**，而且这条线上一度把它当"当前状态"引用。
   > 不换的理由（当时）：换完就没法验证，而"一把没人验过的锁"比"一把已知泄露面的锁"更坏 —— 验证要重新走一遍上面的出口流程。⇒ 要换必须由用户重新授权，且**必须与验证打包**：先建新值→立刻发一枪→确认 200→再登记新值的取法。⛔ 不要只换不验。
   > **09-24 实测补充（打包做法要再加两步）**：① **生成后第一件事是存进用户保管处**（密码管理器），不是先粘 CF —— 只"走剪贴板、不进对话"会留下"值只活在读不出来的 secret 里"的死局，导致无法自证"新通"（本轮真断过一次，复制别的东西就断链）。② **dashboard 的 `Add variable` 默认类型是 Text 不是 Secret** —— 落错类型时它会从 `GET /secrets` 里消失、而 `GET /settings` 的 `bindings` **把值原样返回**（等于把钥匙挂给任何能读配置的人）。判"设没设上"看 `/secrets` 的名字列表，判"是不是明文"看 `settings.bindings[].type`；好在 Edit 界面可以改类型，不必删了重建。③ **判据是"新通 ＋ 旧拒"两发，⛔ 一发都不算**：Worker 的 `authorized()` 写的是 `if (!env.SYNC_TOKEN) return true` ⇒ **没设 secret 时它也回 200**，所以"带新值打出 200"单独不构成"新钥匙正确"的证据（也可能是锁根本没上），必须同时留一发不带密码 → 401 的对照。
2. **仓库与线上之间仍然没有自动链路（这是**决定**，不是缺能力）。** **deployments = 12、versions = 13**（09-24 01:44 北京带 `per_page=100` 现算 `len(result.deployments)`；⚠️ 本文原写"9 条"作废，裸 `GET .../deployments` **默认只回一页、10 条封顶**，且这个端点**不返回 `result_info`** ⇒ 只能翻页或拉满 `per_page` 后 `len()`，而⛔ 别把 `len()` 当总数如果没确认过分页）。12 条 deployment 的 source 只有 `dash_template` / `quick_editor` / `dash`；⚠️ 但那 13 个 **version** 里有 1 个是 `wrangler` 传的（#10，未部署）⇒ ⛔ 别再引用"wrangler 一次没跑过"。`wrangler` 可用（token 与 `versions upload` 都验过，见上两节），但用户 09-23 拍**只做只读检测、不切流量**。⇒ 现在治漂移的手段是 `tools/drift_check.py`（能发现"线上被动过"和"凭据少了一把"），⛔ 不是"push 即上线"。要换成自动部署，前提是先把"线上==仓库"的判据从字节比对换成来源证明（版本 tag 记 commit），否则漂移只是换了个看不见的方向。⚠️ 09-24 新增代价：**没有自动链路 ⇒ 闸门 2 只能靠部署那一刻留三元组收据**，事后无法证明；而它现在每次合法部署都要**手改 `known_good.json`**（见「只读漂移检测」那节的红色补充）。

次要遗留：**`feat/selftest-probe` 分支已删**（09-23，走 `gh api -X DELETE .../git/refs/heads/...`；删前证 `ahead_by=0`、无独有文件、PR #3 `merged=true`，删后回读分支列表 + 阴性对照）。⚠️ 顺带纠正一条旧说法："github 连接器没有删分支工具"⛔ 不等于"agent 删不掉" —— `gh` 与连接器是**两套凭据**，这把本来就能写。剩下的技术债只有一条：`Labels` 是 multi_select 且 options 为空 —— 用户 09-23 定性为**薛定谔的雷**，⛔ 不预先造选项（猜不到名字），等真要做"标签同步"时再一起补；当前 7 条 issue 的 labels 全空所以不触发（错误原文与 request_id 已记在 AMY-7）。

## 钥匙能力矩阵（省你三小时，⛔ 别当现行值）

| 通道 | ✅ 能 | ⛔ 不能（错误码） |
|---|---|---|
| github 连接器 | 读、写文件、建分支、合并 PR、删文件（均实测成功） | ⛔ "token 只读、写会 403" 已被当场证伪；⚠️ 它自己没有删分支的工具 —— 但 `gh`（另一套凭据，push/admin 齐）能删，⛔ 别把"工具没有"当成"能力没有" |
| cloudflare MCP | 读配置、读 secret **名字**、拉线上源码、改配置（dashboard 换代码不清 bindings） | 写 secret（**10405**）；创建/替换 Worker（**10007**）；读遥测（**403**）；fetch 自家 workers.dev（**403**） |
| linear 连接器 | 读写 issue/project；`patch` 可局部改正文（**锚点不匹配则整块不写**，安全） | 改附件标题（无接口）；`links` 回执成功但 **0/1 生效** ⇒ 写后必回读；⚠️ 正文里写 `AMY-N` 会**推高对端 `updatedAt`** ⇒ 滞后量用 `completedAt` |
| notion 连接器 | 读库 schema（含 select 选项列表）、读写页面、SQL 查询 | SQL 不带 `LIMIT` 会**静默少回行**；单次 `-32603` 假失败重试即过；⛔ 不会自动新建 select 选项 |
| **postman 连接器 + REST** | **✅ 云端发 HTTP 请求 = 本链路第一个不需要手机的出口**；collections/environments/monitors 全套 REST 可用；网页版能带 `Authorization` ＋ raw JSON body ＋ 断言（`Test Results n/n`） | `/run/collection` 已 404；monitor 结果无响应体；⛔ 默认 UA 被 Cloudflare 1010 拦；⚠️ **网页版 Send 实际由 Cloud Agent 代发，它自己会挂**（09-23 深夜报 `Unable to reach the Cloud Agent`，**连不需要密码的 `GET /health` 对照发也失败** ⇒ 判"是发弹机坏了不是端点死了"靠的就是这条对照发） |
| ⭐ **Cloudflare 控制台 Quick Editor 右侧 HTTP 面板** | **✅ 第四出口，且比 Postman 更近**：请求由 **Cloudflare 自己发出** ⇒ 打得到 `*.workers.dev`；方法下拉 `GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS/QUERY`，有 `+ Add header`，**也有 `Body` 输入框** ⇒ 四态鉴权（不带／带错／带旧／带新）＋ `dryRun` 原则上可在**同一个面板**里发完 | ⚠️ **它发的是"预览 URL"还是"线上路由"，本轮没做判别实验** ⇒ 用之前先拿一发 `GET /` 与线上对照（若刚粘了新代码还没 Deploy，两者会给出不同答案）。⚠️ 面板在 **iframe** 里 ⇒ kimi/bsk 的 a11y 快照**取不到它的控件 ref**（只能用户手点）。⚠️ **别把"我的量具看不见"写成"它不存在"** —— 我本轮就这么错过一次，且错误前一句还写在本文里 |
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
⇒ ⚠️ **Windows 命令行上限 32,767 字符**：用 `gh api -X PUT ... -f content="$(base64 -w0 f)"` 推 **>21 KB** 的文件会**静默失败**（`Argument list too long` 被吞进变量 ⇒ 看起来"没报错=成功"）。本轮连失两次才发现。✅ 正解：把 payload 写成 JSON 文件再 `gh api --input payload.json`；并且⛔ 不要把 `2>&1` 塞进变量后就不看内容 —— 每次写操作后**独立回读远端 sha** 才算成。

## 变更约定

- 登记按"原文不改、文末追加"——但⛔ 只读前 20 行一定读到过期快照，所以**更正必须同时放顶部横幅**。
- 每条结论都要写"**怎么测的 + 测于哪一刻**"，⛔ 不要只写"现行值"。
- 写操作回执成功不算落盘，**必回读**；回读接口本身也要跑阳性对照（本轮：正则扫本地文件 0 命中 ⇒ 同一正则打在会话日志上必须命中，否则那个 0 不算数）。
- ⛔ 本地记忆（各客户端自己的 memory 目录）**不是交接面**——它是每家一份的。要别人不重踩，必须写进本文件或 Linear。
- 凭据：⛔ 不把 secret 值写进本文件、聊天记录或任何 agent 的 prompt；需要用时**从落盘点直接取**，只打印长度与前缀。

## 09-24 凌晨执行记录（闸门 2 重做 + 换锁闭环 + 第四次改判出口）

**这一轮做了什么**（执行位 Qoder CN；关键读数由**用户亲手发出并回读**，见下面独立性账）：

1. **闸门 2 从"未定"打成"有当场收据"**：把 `main:src/index.js` 整份粘进 Quick Editor → Deploy → **立刻**取字节。三元组 `{version_id 5e011838…, etag b5cc1a50…, blob 3a698aff59f5…}`，deployment `67e626d1` @ `2026-09-23T16:53:57Z`。UI／CF API／哈希三处同刻一致。
   - 粘贴前先做**剪贴板往返校验**：`Set-Clipboard` → 落盘 → 算 blob SHA-1 → 与仓库对撞（10,860 B / `3a698aff…` ✅）。第一次用 `clip.exe` 送，字节被吃 ⇒ 357 行 / 38 个错误，那发 Deploy 真失败了。
2. **`SYNC_TOKEN` 轮换闭环**：新通 **200 / 6-6 / 173 ms**；旧拒 **401 / `cf-ray a3fb48b32d9b85be-hkg`**；对照在场（不带 → 401、带故意写错 → 401）。⇒ **"轮换完成"允许写了**。
3. **出口从三条变四条**：新增 Cloudflare 控制台 Quick Editor 的 HTTP 面板（有 Body 框）。⇒ 上一版那句"表单/面板发不出 body"是**我的错**，见下面撤回账。
4. **`drift/known_good.json` 基线更新到 #13 三元组**（与本文同一次推送），并在文件里写明"带收据的更新，⛔ 不是消音"。#10 那个未部署版本仍如实在场 ⇒ 检测器**继续**报它。
5. **推送前又现算了一遍复核**（09-24 01:44 北京 = `2026-09-23T17:44Z`，用的都是只读 GET）：`deployments[0]` 仍是 #13 @ 16:53:57Z；`versions/5e011838…` 的 `resources.script.etag` 仍是 `b5cc1a50…`；裸下载端点的 `index.js` 段仍是 **10,860 B / blob `3a698aff…`**（含 `export default`）；绑定 4×`secret_text`；`deployments = 12`、`versions = 13`。⇒ 距部署约 **45 分钟**、这**第 4 次采样**未见变化。⚠️ 表述按新纪律写成采样点序列，⛔ 不写连续的"未变"。

**⭐ 这一轮最值钱的三条机制结论**（都可复算、都不依赖本文件任何旧数字）：

- **"上传未部署"会占住脚本槽位**：`wrangler versions upload` 生成的版本虽从未进 deployments，却被之后每次 dashboard 保存继承 ⇒ 15:27Z–16:53Z 线上跑的其实是那份打包件。⇒ **闸门 2 只能"当场留收据"，⛔ 事后无解**；这条直接决定了"要不要 CI"这个话题的优先级。
- **`authorized()` 里那句 `if (!env.SYNC_TOKEN) return true`** ⇒ "带新值打出 200"**单独**不构成证据（也可能是锁根本没上）。**轮换判据必须是两发**：新通 ＋ 旧拒，且保留一发不带密码的 401 做对照。任何只看一色的轮换登记都应当判"未完成"。
- **日志即密钥库**：`~/.qoder-cn/logs/runs/*/qodercli.log` 会原样记下每次 `tool.requested` 的完整 args，包括我驱动浏览器时 `bridge.py fill @e4 "<值>"` 的那个 `<值>` ⇒ 生产端点的钥匙等于明文躺在日志里，任何能读该目录的 agent 都能捞出来。⇒ 凡"用桥去 dashboard 填凭据"，一律假定该值**永久落盘**；换锁顺带把历史日志里那些明文副本变成废字符串（比删日志彻底，因为 `file-history` 里还有文档快照）。

**⛔ 我这一轮的撤回账（四条，全在同一夜被抓出来）** —— 写在这里是因为它们的**形状**比内容值钱：

| 我说过的 | 真相 | 错在哪一类 |
|---|---|---|
| "CF 面板发不出 body" | 它有 Body 框，用户截图给我看的 | **把"我的量具看不见 iframe"写成"它不存在"** —— 本轮第二次，且我前一轮刚在本文批评过同族错误 |
| "这台机没有 wrangler 路，要走得新铸写钥匙" | 交接面早就登记了 `deploy-linear-sync-30d`，值在 `%LOCALAPPDATA%\cf_deploy_token.txt`，`whoami` 验过 | **没读自己写的交接面就下结论**（同族："我钥匙拿不到 ≠ API 不支持"） |
| "改配置会让 etag 变 ⇒ etag 零信息" | 15:27Z 那次确实换了脚本（etag 变），16:14Z 只改类型的没换 | **一次观察就归纳成规律**，样本 n=1 |
| "预期 sha 应该是 X"（凭记忆） | 现算不是 `3a698aff…`，本地那份才是 | **把快照当现行值**——违反铁律 2 的正是我自己 |

⇒ 三次把我揪出来的都不是我自己：一次是用户截图，一次是用户转述另一家的实验，一次是现算。**⇒ 这条线的"独立复算"仍然欠着**，见下面待办。

**独立性账（本轮怎么记才不浮）**：闸门 2 的收据里，**Deploy 那一下是用户手点的**、字节是我算的；换锁的两发，**Send 与读数是用户做的**、值是我生成的。⇒ 这比"五步同一双手"好一档，但⛔ 仍不是独立复算：判据、登记文案、本文全部出自一只手。**真正没做的还是那一条 —— 让没有上下文、且有 Linear＋Notion 两把钥匙的那家（WorkBuddy 国际版）按「复验配方」独立重跑闸门 6**（它该当验收方，⛔ 不该当执行方：它没有出口）。

**待办（按优先级，⛔ 都别当"上一家漏做"，是排过的）**：
1. **交给第三方独立复算闸门 6**（配方：`list_issues` 现算 `fetched` 期望 → 发一枪 → Notion 侧 `COUNT(*)`＋逐行 `Status`/`Updated At` 差集回读）。它报的每个数字必须两端现算，⛔ 不许引用本文。
2. **测试窗口收尾时删临时件**：Postman 集合 `7d541dd3…` 与环境 `aa1c742f…` 按用户决定**保留**（当前测试窗口是 WorkBuddy 国际版，其他 Agent 未接入），但里面必须是**新值**；⛔ 窗口一结束就删，留着就是"任何能读该账号的人手里有一把生产钥匙"。
3. **新值另存**：48-hex 新值目前只有三处副本（CF secret 读不出 / Postman 环境 / 用户手里）⇒ 提醒用户**立刻**存一份进密码管理器，误删环境就得再换一次。
4. **`/selftest` 去留未决**：它是唯一不需要出口就能验收闸门 3/5 的手段，但**无鉴权**且会吃 Linear 配额、泄露 `fetched`。用户倾向保留；⛔ 别顺手给它加写路径。
5. **`Labels` 那颗雷**：multi_select 且 options 为空 ⇒ 谁在 Linear 贴第一个标签就撞 400，而"页面数不变"这个老判据会把部分失败判成通过（原文与 request_id 在 AMY-7）。用户 09-23 定性：⛔ 不预先造选项。
6. **CI/自动部署**：仍然"只检测不切流量"（用户决定）。要重启这个话题的触发条件是"我要 CI 自动部署了"，而前置工作是**把判据从字节比对换成来源证明**（版本 tag/annotation 记 commit），否则漂移只是换了个看不见的方向。
7. ⭐ **未部署版本 #10 怎么处理 —— 等用户裁，⛔ 谁也别擅自动手**。09-23 的"让告警亮着"是在还不知道"上传未部署会占脚本槽位"时拍的；今天这条机制成立后，那个裁决的前提变了（详见「只读漂移检测」节的红色补充）。三个选法：① 从 main 走一次带收据的部署把它盖掉（**代价：又一次 100% 流量切换＋要重新留三元组**）；② 保持现状、把告警的成因写清楚（**本轮选的就是这个**）；③ 删掉那个版本 —— ⛔ 我没查到 CF 有"删单个 version"的只读可验证接口，⛔ 别凭想象做。
