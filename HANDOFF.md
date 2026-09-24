# 接手须知（HANDOFF）

> 这个仓、这条链路（Linear ↔ GitHub ↔ Notion ↔ Cloudflare）**以后不止一个 agent 在跑**。
> 本文件是给下一个会话的入口。⛔ 动手前先读完。最近一次改动：2026-09-24 07:5x（北京）。⚠️ 这一轮跨了一次约 6 小时的空闲，凡本文写"本轮/刚才"的时刻，以它自带的 UTC 戳为准（见顶部横幅第 10 条）。
> 另两处交接面：Linear 项目 **P-AMY-1** 顶部横幅、工单 **AMY-6 / AMY-7** 文末记录。
> ⚠️ 时刻口径提醒（本文件栽过一次）：写时刻要拿**部署/回执的 UTC 原文**换北京时间，⛔ 别照抄上一张图的小时数。

> 🔴 **09-25 凌晨更正（窗口 A 现算 ＋ 第二窗口交叉复算，全部带取法与时刻）—— 本节覆盖下方所有与之冲突的表述**
>
> 0. ⚠️ **本文表格里每一个 ✅ 的读法当场降级**：它只代表"**那一刻、该取法下两个值相等**"，⛔ 不代表"现行值"。这条新规的直接起因就是下面第 1 条——三个带 ✅ 的数已经过期了一整天。
> 1. 🔴 **「独立复算 · WorkBuddy 国际版」那张表（第 430/431/433 行）三个值已过期，且当场挂着 ✅**：现算 `main` HEAD = `9b2270239d9bc121ad6126fd07d3797ca432a6a1`（committer `2026-09-24T15:20:02Z`）、HEAD tree = `9d46e389329756e667669f1e2c3fa9d25c6322f3`（取法 `GET /git/commits/main` → `.commit.tree.sha`，⛔ 走 `git/trees/{ref}` 会拿到 commit 号）、commit 数 = **42**（`?per_page=100` page1=42 / page2=0，翻页到空才算数）。测于 `2026-09-24T16:26:53Z`（窗口 A，匿名 REST）与 `16:58:54Z`（第二窗口，`gh api` 独立取法）⇒ 两端一致。原文三个旧值**保留不抹**，就地加更正注。⚠️ 这两个新值同样是快照：判"仓库有没有被动过"只认你此刻重跑。
> 2. ⚠️ **"该端点不返回 `result_info`" 这句话要限域**（本文此前两种说法并存，不限域就会孵化成一次假更正）：`GET .../scripts/{name}/deployments` 与 `.../versions` 的 **`result_info` 在信封顶层就有**（`{page,per_page,count,total_count,total_pages}`，实测 deployments 12 / versions 13 均单页即全量，测于 `2026-09-24T16:25:27Z`）；而裸 `GET .../workers/scripts`（列脚本那一发）顶层**确实没有**。⇒ 判"拉全没拉全"优先用顶层 `total_count`，⛔ 别把某个端点的形状推广到同类端点，更⛔ 因此退回用 `len()` 猜总数。
> 3. ⚠️ 裸 `.../workers/scripts` 的元素里**既没有 `name` 也没有 `script` 字段**：脚本名在 **`id`**，Worker UUID 在 `tag`（实测 `id=linear-sync`、`tag=927d6c0d…`，`2026-09-24T17:07Z`）。本文旧版"元素名字段是 `script`"⛔ 错，已改。
> 4. ⛔ **别再往任何派工单里写"你自己发一发 `workers.dev`"**：这台机两家合采 **0/25**（第二窗口 0/23 @ `16:59–17:01Z`；窗口 A 0/2 @ `17:06:50Z`），一个 200 都没有。**致命层是 SNI，不是 DNS**：`--resolve` 钉住真 CF IP 之后 TCP 通、但 **ClientHello 里那个域名被 RST** ⇒ ⛔ hosts 文件 / 钉 IP / DoH 全治不了；DNS 拿到 Meta 段投毒答案（`157.240.10.32`、`185.60.216.169` ⇒ 值逐次变、**族不变**）只是它前面的一层。代理已双向排除（`--noproxy '*'` ＋ 注册表 `ProxyEnable=0`）。⇒ 能发这一枪的只剩**用户手点**：CF 控制台 Quick Editor 右侧 HTTP 面板（可带 `Authorization` ＋ Body）或手机 + VPN。⚠️ 另一条呈现纪律：**"目标"与"对照"的读数⛔ 不许混成一条裸序列**——本线就有人把 `000/200/000/200` 里的两个对照 200 读成"你们命中过两次"，凭空长出一条不存在的冲突。分目标报**成功率 ＋ `remote_ip`**。
> 5. 🔒 **独立性口径补一条硬的**：**同一安装的第二会话⛔ 不是第二双眼睛**，而且"派工单一个预期值都不给"在同安装下**结构上不可执行**——实测全机只有**一份** `~/.qoder-cn/settings.json`（25 条连接器、字段只有 `type/url/qoder_url`、九个凭据形态子串全 `False`、`mcp.json` 为空）、本项目只有**一个** `projects/<prj>/memory/`（一方改它，另一方会话开头就收到"外部修改"通知）、会话正文落成同安装可读的 `.jsonl`、"私有基线"在对方 `cwd` 下 `ls` 直接可见。⇒ **新准入判据**：不同安装目录 / 不同凭据 / 不同网络出口，**三条至少中两条，且其中必须含"出口"或"凭据"之一**；同安装另一窗口 = 中 0 条。⇒ 可操作探针：`gh api user` 的 login ＋ 安装目录路径 ＋ `sha256(settings.json)` 能证"不同安装"（⛔ 证不了"不同凭据"）；`api.ipify.org` ＋ ASN 现算能证"不同出口"（建议当硬判据）。⇒ 凭据值⛔ 不进对话/文档，**凭据指纹也⛔ 不进文档**（只许报"相同/不同"）。
> 6. ✅ 两处旧表述现在**可算**，不必再靠一次采样撑着：① `authorized()` 第一行是 `if (!env.SYNC_TOKEN) return true;` ⇒ **哪天 `SYNC_TOKEN` 被删，`/sync` 会静默从 401 变成全开放**——不报错、不改版本、`/health` 一切正常。⇒ "不带密码 → 401"那一发是**锁在场的阳性证据**，⛔ 不是可有可无的例行检查，这条进"别再重踩"。② 401 正文 `JSON.stringify({error:"unauthorized"},null,2)` 逐字符数出来正好 **29 B**（本文旧值 26 B 已更正，此处给的是算式而非读数）。⛔ 字节数仍不许当计数证据。
> 7. ⚠️ **`/selftest` 是一条无鉴权的远端触发器**（现读线上源码：`pathname === "/selftest"` → `runSync(env, {dryRun:true, teamKey:"AMY"})`，`2026-09-24T17:1xZ`）：它绕开 `authorized()` ⇒ 用它**永远验不到**"带密码放得进"（本文"⛔ 不用它代替闸门 5"这条决定被代码证实）；但它**会真发一次 Linear GraphQL 查询且不设密码** ⇒ 配额与滥用面在场。**去留等用户裁**，⛔ 任何 agent 不要擅自加锁、删除或改代码。
> 8. ⭐ **闸门 6 的判据升级**（取代本文"跑三次比页数仍为 7"那句作为主判据）：`dryRun` 与真写**必须同 body**——`since` 决定扫描集，不带即全量（代码：`const since = options.since ? Date.parse(options.since) : NaN`，仅 `!Number.isNaN(since)` 才过滤）。于是 `dryRun` 那一发的 `preview` 就是**机器在同一刻、同一把钥匙下算出的 E4 预测** ⇒ 真写之后的实际差集去和 `preview` 对撞，差值才是闸门 6 的产物。⛔ 人脑从旧读数推出来的"预期哪几行动"不算预期值。代码依据：`if (dryRun) { … }` 提前返回，真实写在 `PATCH`（约 247 行）与 `POST`（约 253 行）那两处。

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

> 8. 🐛 **漂移检测器自己有个盲区，已修**：旧版只把**最新版**与服务版本比 ⇒ 一旦再来一次合法部署（#13），旧的未部署版本 #10 就**从告警里消失**——**灯灭了不是雷拆了，是探测器看不见它了**。而且它那句收尾"且没有未部署的上传"在此刻是**假话**（明明还有 #10）。✅ 现改为：扫**全部 versions**、与**所有 deployments** 里出现过的 version_id 求差集，逐个比内容；豁免只在登记里明示（`known_undeployed_versions` + `kept_intentionally: true`），⛔ 不靠"看不见"；再加一枚能力戳 `detector_min_version`，登记要求的比脚本新就 `exit=2` 拒跑。**七组测试矩阵（1 绿 / 5 红 / 1 拒跑，外加"旧版复现假绿"对照）**见「只读漂移检测」节。
> 9. ⚠️ **本轮自己的量具事故一枚**：第一次跑测试矩阵时我用 `... | tail -14; echo "exit=$?"` ⇒ **`$?` 拿到的是 `tail` 的退出码**，六组里**本该报红的五组全显示 `exit=0`**。当时那一眼看过去就是"检测器全瞎"，我差点照此上报。✅ 正解：先 `> file 2>&1`，再 `$?`，然后才读文件。**"期望零退出的对照组不是可选项"这条老规矩，今天是以镜像形式咬的我：不是对照组漏了，是对照组的退出码被管道吃掉了。**
> 10. ⚠️ **又一处"时刻口径"事故，坏法是新的**：本节第 8 条与「只读漂移检测」那节我先写的"测于 02:1x–02:2x 北京"是**照会话进度估的钟点**，真值是 **07:4x 北京 = `2026-09-23T23:4xZ`**（已就地改正）。根因：这一轮中间隔了约 **6 小时空闲**（`17:49Z` 推完第一次、`23:45Z` 才推第二次），而我拿"我干了多久"当"现在几点"。⇒ **落笔写时刻前先 `date -u` 现取**，⛔ 别按上下文里上一条的时间推。本文件已为这个坑立过一次规矩（"写时刻要拿部署/回执的 UTC 原文换北京时间"），今天补第二种坏法：**空闲会让"我以为的现在"整段漂移，且毫无征兆。**
> 11. 🔒 **新增一条决定（用户 09-24 拍）**：同步是**覆盖式**，Linear 是唯一真源 —— Notion 侧的人工改动会被下一次同步按 Linear 覆写，不检测、不合并、不告警。⇒ 详细后果（⛔ 别编辑那 10 个字段、`Updated At` 的含义被这个决定改变、无备份）见新节「🔒 决定」。
> 12. 🔴 **我自己的一条误判，就地更正**：上一版我根据 Postman 列表端点的 `createdAt == updatedAt` 断定"那套临时件里大概率还是旧值"，并据此把"新值副本只剩两处"写进了待办。⛔ 错了 —— **列表接口的 `updatedAt` 不反映 `type: secret` 值的改动**，我把一个**没测过语义的字段**当成了已知。用户在界面上看过：环境里就是当前那把（`bd96` 开头）。⇒ 教训进「量具级教训」：**判"有没有被改过"之前，先确认这个时间戳字段跟的是哪一类改动。**

> ~~📌 **`SYNC_TOKEN` 暂不轮换 —— 这是用户 2026-09-23 拍的决定，⛔ 不是上一家漏做。** 理由与打包做法见「还欠着的事」第 1 条。⛔ 未经用户重新授权，任何 agent⛔ 不要动这把锁。~~
> ⇒ **09-24 作废**：用户 09-23 深夜改口拍定轮换，理由是"换完没法验证"这个前提随着出口被打通而消失。原文按"不改只标"的约定留在 `「还欠着的事」` 第 1 条。

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
- 🔴 **09-24 · 把没测过语义的字段当已知**：我看见 Postman 列表接口返回 `createdAt == updatedAt`，就断定"这套临时件创建后从没被改过"⇒ 再推出"里面还是旧密钥"。⛔ 错了：列表接口回的是**元数据**，`type: secret` 的值改动**不反映在它的 `updatedAt` 上**（用户在界面上确认里面就是当前那把，前缀 `bd96`）。⇒ 用任何时间戳字段下"有没有被动过"的结论之前，先回答一句：**这个字段跟的是哪一类改动？** 同族：把 `len()` 当总数、把 `etag` 当文件哈希、把 `/health` 的 `version` 当构建证明。
- 🔴 **09-24 · 候选集是按"我以为钥匙长什么样"构造的，那个形状假设本身没有对照**：我先按"32 位十六进制"筛旧值，**正好把 36 位的真值筛掉**，于是拿两个 UUID/哈希当钥匙试了两发（都 401、无副作用 —— 401 进不去 `runSync`，所以这类试错是安全的）。真值要从 `bridge.py fill @e4 "<值>"` 那个**参数位置**去捞，并核"全 runs 目录该位置只有 1 个不同值"才敢定案。⇒ **按位置筛，⛔ 按长度/字符集筛。**

## 只读漂移检测（09-23 新增，已实测 + 故障注入验过）

仓库里多了两样东西：`tools/drift_check.py`（⛔ 全程只读，只 GET）与 `drift/known_good.json`（基线登记：服务版本 id、产物 etag、四个 `secret_text` 绑定、仓库 blob SHA、记于哪一刻）。

```bash
export CLOUDFLARE_API_TOKEN=...      # ⛔ 别写进任何文件；见「部署凭据」那节
python3 tools/drift_check.py         # 退出码 0=无漂移 1=有漂移/要看 2=检测器自己跑不动
```

它查四件事：① 服务版本的 **etag** 是否等于登记值；② **绑定集合**是否等于登记的四把 secret（少一把 = 锁没了或凭据没了）；③ 是否存在**内容不同但未部署**的版本（有 ⇒ 字节判据此刻不可用，直说，不误报"线上≠仓库"）；④ 部署是不是**分流**（多版本时提醒人工看，脚本不猜）。

> ⚠️ 09-24：第 ③ 件事的**实现**换过一版（旧版只看"最新版"，会漏；下文有矩阵）。第 ④ 件事⛔ 仍未覆盖逐条比对，只提示。

**它是有牙的，不是摆设**——注入当场报错：登记 etag 尾字符改一个 ⇒ "etag 与登记值不同"；把 `SYNC_TOKEN` 从期望绑定里抽掉 ⇒ "绑定集合与登记值不同：多=[secret_text:SYNC_TOKEN]"。⚠️ 反向的坑也在代码注释里写着：⛔ 别拿 `result.scripts`、⛔ 别看裸 scripts 端点。
> ⚠️ 09-24：这句当时只验了**两组**，而"有牙"这个结论**掩盖了第 ③ 项的一个盲区**（旧版只比最新版 ⇒ 有一种情形它必然沉默）。完整七组见下一小节。⇒ 教训：**判据的"能报错"不等于"每条判据都覆盖全域"**，逐条问一句"什么输入会让它闭嘴"。

**09-23 夜间的判定**：`⚠️ 有一个未部署的版本 #10（a7ba0f39，wrangler 传的打包件）与服务版本内容不同、绑定相同`。⇒ **用户 09-23 拍：这条告警当时就让它亮着**，⛔ 不要为了让检测器变绿去改登记值。（脚本提示里那句"确认线上正确后改登记值"针对的是**etag/绑定真变了**的情形，⛔ 不是给"消音"开的口子。）

> 🔴 **09-24 补一条，⛔ 别引用上面那句"下次真部署会自然覆盖"** —— 那句**错了**：`drift/known_good.json` 里没有东西会自动更新，**每次合法部署之后必须有人手动改登记值**。#13 部署后检测器登记的还是 #9 的 etag `5d4e6aad…` ⇒ 它会把**我们自己刚做的带收据部署**报成漂移。
> ⇒ **"灯红"现在有两种成因**：① 真漂移；② 合法部署后没更新基线。判之前先看 `deployments[0]` 的时刻与已知部署动作对不对得上。
> ✅ 基线已更新为 **#13 三元组**（version_id `5e011838-ab37-4da9-8214-4ce91eb5f54d` / etag `b5cc1a50dc085ecd…` / blob `3a698aff…`）。分两次推：`01:49 北京` 那一次推 HANDOFF ＋ 三元组基线，`07:45 北京` 那一次补上检测器修复与能力戳 `detector_min_version`（⇒ 那两次推送之后，仓库里这三个文件互相自洽）。json 里带 `receipt` 与 `history` 两段，写明"**这是带收据的更新，⛔ 不是消音**"。#10 那个未部署版本仍如实登记在 `known_undeployed_versions` 里。⚠️ 我这一版原话写的是"⇒ 检测器会**继续**报它"——**那句站不住了，见下一节：它不会继续报，它是看不见。**
> 🔴 09-24：那个"未部署版本 #10"的**存在本身**已被证明会造成真实事故（见顶部横幅第 2 条：它占住脚本槽位、被后续 dashboard 保存继承 ⇒ 15:27Z–16:53Z 线上跑的就是它）。当时"让灯亮着"的裁决针对的是**告警噪音**，⛔ 不是"打包件可以留在槽位里"。**下次动手时优先把它清掉或用一个从 main 部署的版本盖过它**（`wrangler versions upload` 只上传不部署的那条路，在这条链路上已被证明不是无害操作）。

### 🔴 09-24 实测：检测器"只比最新版"的盲区 ＋ 修好后的七组矩阵

**发现过程**（全程只读）：把基线更新到 #13 之后再跑**旧版**检测器 ⇒ **`exit=0`，并打印"判定：无漂移（…且没有未部署的上传）"**。而同一时刻现算 `versions = 13`、`deployments = 12`、这 12 条 deployment 只覆盖 **12 个** version_id ⇒ **明明还有 1 个从未进过 deployment 的版本（#10 `a7ba0f39`）**。根因在代码里：旧版只取 `versions[0]`（**最新**那个）跟服务版本比 ⇒ #13 一部署，#10 就掉出比较范围。**⇒ 灯灭不等于雷拆；那句收尾在此刻是字面假话。**

**修法**：`deployments?per_page=100` 全量 → 收集**所有** deployment 里的 `version_id` 成集合；`versions?per_page=100` 全量 → 取**差集** = 从未部署过的版本；逐个拉 `resources.script.etag` 与绑定跟服务版本比 ⇒ 内容相同就如实归"同字节重传，不算漂移"，内容不同就报红。**豁免只认登记里的 `known_undeployed_versions[].kept_intentionally == true` 的 id 前缀**，⛔ 不靠"看不见"。另加一枚**能力戳**：登记里的 `detector_min_version` 比脚本的 `TOOL_REVISION`（当前 `2026-09-24-scan-all-undeployed`）新 ⇒ **`exit=2` 拒跑**，防的就是"拿旧副本跑出一盏假绿灯"。

**七组矩阵**（首轮**带 `$?` 事故**的那次跑在 09-24 01:5x 北京；修正取码方式后的**有效一轮**在 **07:4x 北京 = `2026-09-23T23:4xZ`**。同一把只读凭据、同一份真实登记打底，⛔ 全程不碰线上；退出码一律 `cmd > f 2>&1; echo $?` 采）：

| # | 输入 | 期望 | 实测（把判据原文抄回来） |
|---|---|---|---|
| 1 | 真实登记（含 #10 豁免 ＋ 能力戳） | 0 ＋ 点名"有意保留" | ✅ `exit=0`：`未部署版本 #10 a7ba0f39（source=wrangler）已在登记里明示「有意保留」` |
| 2 | `known_undeployed_versions` 清空 | 1 ＋ 点名 #10 | ✅ `exit=1`：`有一个未部署且未登记豁免的版本 #10（a7ba0f39，source=wrangler）…etag不同/绑定相同` |
| 3 | `artifact_etag` 尾字符翻转 | 1 ＋ 理由必须是 etag | ✅ `exit=1`：`etag 与登记值不同`，**且豁免行同时在场** ⇒ 两个判据互不遮蔽 |
| 4 | 从 `expected_bindings` 抽掉 `SYNC_TOKEN` | 1 ＋ 理由必须是绑定 | ✅ `exit=1`：`绑定集合与登记值不同：多=['secret_text:SYNC_TOKEN'] 缺=无` |
| 5 | 豁免前缀写成 `deadbeef`（不匹配） | **仍须 1** | ✅ `exit=1` 点名 #10 ⇒ 豁免不是"有条目就免检" |
| 6 | 前缀对但 `kept_intentionally: false` | **仍须 1** | ✅ `exit=1` 点名 #10 ⇒ 要显式旗标，只列名字不算 |
| 7 | `detector_min_version` 写成 `2099-01-01-…` | **2（拒跑）** | ✅ `exit=2`：`登记要求的检测器能力 … 比本脚本新 ⇒ 拒跑` |
| 对照 | **旧版**脚本打在真实登记 | 应报红却报绿 | ✅ `exit=0` 且输出含"没有未部署的上传"（`grep -c` = 1）⇒ **盲区实证**，不是推断 |

⇒ 组 5、6、7 是**豁免与能力戳各自的阴性对照**：没有它们，"绿"同样可以只是"匹配写得太宽"或"跑的是旧副本"。
⇒ ⚠️ 采退出码那一下先踩了一次自家老坑：第一轮用 `cmd | tail -14; echo "exit=$?"` ⇒ **`$?` 是 `tail` 的**，七组**全显示 0**（本该 1 或 2 的六组也显示 0），差点把矩阵报成"检测器全瞎"。✅ 正解：`cmd > f 2>&1; echo $?`，然后再读 `f`。（对应本文件「期望零退出的对照组不是可选项」那条纪律，这次是以镜像形式咬我的。）
⇒ ⚠️ 还有一条**没被测到的**：分流部署（`deployments[0].versions` 多于 1 个）时本脚本只提示、⛔ 不逐条比对。这仍是已知缺口，别把 `exit=0` 读成"流量切分也检查过了"。

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

## 🔒 决定（2026-09-24 用户拍）：同步是**覆盖式**，Linear 是唯一真源

**拍的是什么**：Notion 侧被人工改过的字段，下一次同步**按 Linear 覆写回去**，不做冲突检测、不做合并、不弹告警。这条以前只是"代码碰巧这么写"，从现在起它是**显式决定**。⛔ 谁再想改成"跳过 / 报警"就是改决定，要重新拍。

**代码实物**（现读 `src/index.js`，⛔ 不是推断）：`toProperties()` 一次交回整页 **10 个字段**（`Name` / `Linear ID` / `Identifier` / `Status` / `Assignee` / `Labels` / `URL` / `Updated At` / `Description`），命中已有页面就走 `PATCH /pages/{id}`。而 `since` 是**可选**的 —— `options.since ? Date.parse(...) : NaN`，`NaN` 让过滤条件恒假 ⇒ **不带 `since` 就是全量覆盖**。

**三条衍生后果（不写清，这个决定只有一半人被通知到）**：

1. ⛔ **别在 Notion 里编辑那 10 个字段**。要加人工标注就**新建列**（不在 `toProperties()` 里的列不会被碰），⛔ 别复用被同步的列。
2. ⚠️ **这个决定改变了 `Updated At` 的含义**：它写的是 Linear 的 `issue.updatedAt`，但一次全量同步会把 7 行统统重写 ⇒ 它只能读作"**该工单最后一次在 Linear 侧变动**"，⛔ 读不出"这行 Notion 页面最后一次被谁改"。再叠加一条已登记规则（**正文里点名 `AMY-N` 就会推高对端 `updatedAt`**）⇒ 这个字段会被"内容没变的刷新"顶动。**判同步滞后要用 `completedAt`，⛔ 用 `Updated At`。**
3. **覆盖是静默的、没有备份**。⇒ 最便宜的容错⛔ 不是加合并逻辑（那会引入我们从没设计过的三方语义），而是**同步前抓一份 Notion 快照**（一条只读 SQL 就够）。现在没做，登记为可选加固。

**⚠️ 在这条决定下，`Status` 那颗雷比 `Labels` 更近**。本轮现读到的两边口径：
- Linear `list_issue_statuses(team=Amy-agent)` @ 09-24 09:5x 北京 回了 **5 条**：`In Review` / `Canceled` / `Done` / `Duplicate` / `Todo`。⚠️ 这份清单里⛔ 没有 `Backlog`、也⛔ 没有 `In Progress`，而库里 7 行目前正带着 `Backlog`/`Todo`/`Done` ⇒ **说明这个接口回的不是工作流全集**（默认档可能不单列）⇒ ⛔ 别拿它当"AMY 一共这几档"。
- Notion 侧 `Status` 的**选项白名单本轮未能现算**：`notion-fetch` 连打三次都 `-32603 / did not complete`（同族假失败，先前重试即过，这次没救回来）。⇒ 下面用的是 **09-23 那次 `ALTER` 的登记值**（`Backlog`:blue / `Todo`:green / `Done`:gray）作**快照**，⛔ 不许当现行值。

⇒ 后果链：`Status` 是 10 个被覆盖字段之一 ⇒ 有人把工单拖到一个 Notion 白名单里没有的档（例如 `In Review`），那条就 400 `failed`，而**页面数不变**、覆盖式又没有告警 ⇒ 得到的是"一行既没被覆盖、也没人知道"。⇒ 拆法与 `Labels` 不同：**状态名是可读的、确定的**，所以可以现在补齐选项，⛔ 不用改 Worker、不碰线上。**动手前置条件**：① 先现读一次 Notion schema 拿到当前白名单与各 option id（⛔ 整表 `ALTER` 有清空风险，本文件登记过取基线的配方）；② 再决定映射策略——是"每个 Linear 档都建一个 Notion 档"，还是"未知档折叠到 `Todo` 并在错误列记账"。**这两条都要用户点头。**

## 🔍 第二项检查：Notion `Status` 白名单 ⊇ Linear 可用档（09-24 上午立案，配方已入仓 `drift/status_gap_recipe.md`）

**为什么需要它**：`Status` 是"覆盖式同步"那 10 个字段之一，而 Notion 的 select ⛔ 不会自动长选项（09-23 定案）。⇒ 有人把工单拖到白名单外的档，那条就 400 `failed`、**页面数不变**、覆盖式又不告警 ⇒ 得到"一行既没被覆盖、也没人知道"。补完选项**也不是一劳永逸**：Linear 随时能加档 ⇒ 所以要有常驻检查。

**本轮现算的差集**（北京 10:0x，三路全只读）：
- Notion 白名单 = `Backlog`(blue) / `Todo`(green) / `Done`(gray) —— `notion-fetch` 第四次才成功（前三次 `-32603` 假失败）。⛔ 不再引用 09-23 的登记快照。
- Linear 可用档：`list_issue_statuses(Amy-agent)` 回 5 条（`In Review`/`Canceled`/`Done`/`Duplicate`/`Todo`）；`list_issues` 在用的是 `Done`×2 / `Todo`×4 / **`Backlog`×1** ⇒ 并集 6 档。
- ⇒ **确定差集 3 档：`In Review` / `Canceled` / `Duplicate`**；⚠️ **`In Progress` 未确证**（两个来源都没有，但它是 Linear 默认档）⇒ ⛔ 不靠"大概率"往生产表里加档。

**两条新量具事实（都进「量具级教训」这一族）**：
1. ⚠️ **清单类接口⛔ 不许当全集**：`list_issue_statuses` 连**正在被一张工单使用**的 `Backlog` 都没列出来 ⇒ 单用它算差集会**漏报**（算出来"只缺 3 档"，实际可能缺 4 档）。⇒ 必须与"实际在用的值"求并集；配方里写成了硬步骤，并配了一条故障注入：**只用单来源重跑，差集会变小** —— 那一次变小就是这条教训的现场证明。
2. ⚠️ **探针能不能脚本化，取决于钥匙在哪台机器上**：`drift_check.py` 能做成本地脚本，是因为用户单独铸过一把 CF token 落在本机；**Notion / Linear 的凭据只存在于 Cloudflare 的 secret 里、本机没有**（secret 按设计永不可读）⇒ 这条检查现在**只能是"带连接器的客户端按配方执行"**，⛔ 不能假装写一个 `python tools/status_gap.py` 就算有了检查（写了跑不动 = 假安全）。要实体化，前置条件是用户愿意落一把 Notion/Linear 只读 key 到本机。

**当前处置（用户 09-24 勾选：补三档 ＋ 写检查 ＋ 先确证 `In Progress`）**：`ALTER` 是**整表替换**语义 ⇒ 改两次表就要冒两次"清空/重建"的风险 ⇒ 我的排法是**等 `In Progress` 确证之后一次加齐**（基线已在本轮取到：三个 option 的名字/颜色/id），本轮⛔ 不动表。⇒ 需要用户在 Linear 界面上看一眼 AMY 工作流里到底有没有 `In Progress` 这一档（⚠️ 截图只截工作流那一块，别把 cookie / token / 完整 URL 带进来）。

## 🔌 09-24 10:2x 三条现场事实（一次浏览器尝试 + 一次连接器掉线 + 一条判据自我推翻）

1. ⛔ **Linear 的团队"Statuses"页在浏览器桥下读不出来**（别再试）。用 `imu-lib-bridge/bridge.py`（后端 kimi，`status` 显示 kimi/bsk 都可用）实测：
   - `/settings/team/AMY/workflow` 与 `/settings/team/<teamId>/workflow` 都**落到团队通用设置页**（页面里出现 `Default home view`、`Danger zone`，没有状态行）。
   - 侧栏里那一条的**文字是 `Statuses`**，⛔ 不是 Workflow；`click @e15` 回执 `{success:true, tag:"A", text:"Statuses"}`，但**快照与 `extract` 都取不到状态行**。
   - ⚠️ 我一度以为"快照没变"是量具坏了，因为两次快照**字节数完全相同（5,923）**。用一条独立证据排除掉：中途 `navigate` 之后快照变成 68 B 的 `Loading…` ⇒ **快照确实是活的**，那个"相同"是真的没导航成功。⇒ 记法：**判"我的读数量具坏没坏"，要给量具本身造一个它必然变化的一次观测。**
2. ⚠️ **Notion 连接器从我这侧掉了**：`mcp_list(keyword="notion")` → `total: 0`，服务清单里也没有 `notion`。⇒ 后果：**`ALTER` 与"复读 schema 取基线"这两步现在都做不了**。⇒ 本轮之前那次成功的 schema 读（四次才成功）是目前唯一的基线来源，已在 `drift/status_gap_recipe.md` 与 HANDOFF 里（三个 option 的名字/颜色/id）。⚠️ 这是本文件"连接器花名册整晚在漂"的又一次现场；判"有没有"只认 `mcp_list` 的 total，⛔ 别认上一次的成功。
3. 🔴 **我自己推翻自己刚才那条"等 `In Progress` 确证再一次加齐"**：代价不对称 —— 多加一档而 Linear 从不用，代价≈0（下拉里多一个灰选项）；少一档而有人拖上去，代价是**静默 400、页面数不变、无人告警**。⇒ 正确做法不是花轮次去确证，而是**一次加四档：`In Progress` / `In Review` / `Canceled` / `Duplicate`**。
   ⇒ 复盘一句：我当时的理由"不靠大概率往生产表加档"在**证据层**没错，⛔ 但被我用到了一个**风险不对称**的选择上 —— 证据洁癖的正确用法是"别把未证的事写成已证"，而不是"在未证但代价不对称的选项上选贵的那边"。

## 🔑 09-24 下午：Notion 只读钥匙已铸成并落盘（差最后一步"共享给库"）

**做成了什么**（全程我用 kimi 桥驱动用户已登录的 Edge，⛔ 值没进过对话/日志）：

| 项 | 结果 |
|---|---|
| 内部连接 | `status-gap-read`，id `3e530d6b-1b59-8144-a223-0027809470c2`（`/developers/connections/…`） |
| 能力 | **读取内容 = true；更新内容 / 插入内容 / 读取评论 / 插入评论 = false**（点完再读 `aria-pressed` 复核，翻转保持）⇒ 是真只读 |
| 令牌 | 50 字符 `ntn_1…38pE`，落在 `%LOCALAPPDATA%\notion_read_key.txt`；`icacls /inheritance:r /grant:r <用户>:F`；下载目录那份已删 |
| 取值的通道 | 剪贴板走不通：`Get-Clipboard` 连抛 8 次、退到 `[Windows.Forms.Clipboard]` 再试 5 次 ⇒ `CLIPBOARD_UNREADABLE`（这台机的 shell 读不到剪贴板）。✅ 换成**页面内 `Blob` + `<a download>`**，文件落到 Edge 的下载目录（`D:\Download`），我再用 Python 搬进 `LOCALAPPDATA`。⇒ 值全程⛔ 不经对话、不经我的 stdout |

**⛔ 未完成的一步**：库还没共享给这个连接。API 说得很直白：
```
GET /v1/databases/3e230d6b1b598196ad25c1b867bc9c3b   → 404 object_not_found
msg: Could not find database with ID: …  Make sure the relevant pages and databases
     are shared with your integration "status-gap-read".
```
⇒ 所以差集探针现在跑必然是 404，⛔ 别当"Notion 挂了"。剩下的是页面上 `共享` / `操作` → 添加连接 那一下，我这侧 CDP 点击对这两个顶栏按钮没生效（同一招在能力开关上是生效的 ⇒ 是这两个按钮的问题，不是通道坏了）。

> 🔴 **09-24 傍晚更正上面这句归因**："我这侧 CDP 点击对这两个顶栏按钮没生效 ⇒ 是这两个按钮的问题"⛔ 说早了。真相是**标签页不同**：你打开共享面板的是你自己的标签页，而我驱动的是我新建的那个（kimi 桥的 `list_tabs` 只覆盖会话内标签页 ⇒ 我这边整个 DOM 里根本没有那个面板，`仅限受邀者访问`/`发布`/`高阶` 一个都扫不到）。⇒ 判据补一条：**"点了没反应"要先分清是"我读太早"、"目标在视口外"、还是"我根本在看另一个标签页"**——这三种病今天各犯过一次。
>
> ✅ **09-24 傍晚裁定（用户）：这把只读钥匙保留、标记"待共享"、⛔ 不删除，也⛔ 不为它升级 Notion 付费版。**
> 理由记全：它没有活跃风险面（只读、值只在本机一个文件、ACL 收到当前用户、从未进过对话或日志）；删掉等于把"铸一把真只读钥匙"这件事的进展一起丢掉。而共享入口在付费墙后（截图实证：`立即升级` / `无可用属性`），⛔ 不值得为一条检查买订阅。
> ⇒ 由此定下**固定口径**：⛔ 现在不要写 `tools/status_gap_check.py` —— 钥匙未共享，脚本必然 404，写了就是登记一件做不到的事。差集检查现阶段**只由带 Notion 连接器的客户端按 `drift/status_gap_recipe.md` 执行**；哪天共享上了（免费途径：由库的所有者把页面直接共享给该连接，或将来换到支持的工作计划）再实体化。
> ⚠️ 防呆照旧：钥匙在 `%LOCALAPPDATA%\notion_read_key.txt`。⛔ 任何 agent 不要打印它、不要贴进聊天、不要经浏览器桥代填；要证明它还在，只打印长度与前 4 后 4。

**四条量具级实测（都会救下一个人几小时）**：

1. ⭐ **"点不动"的真因常常是坐标在视口外，不是事件被吞**。判据一行：`document.elementFromPoint(x,y) === null`。本轮两颗开关的 y 是 740/790、`innerHeight=717` ⇒ 点的是空白；`scrollIntoView({block:"center"})` 之后同一条 CDP 点击立刻生效。**我先前把病因判成 `visibilityState:"hidden"` + Notion 只认 `isTrusted`，⛔ 错了**——而且错的证据我手里早就有（那次 `element@pt` 就打印了 `None`），却先挑了个更漂亮的解释。
2. ⚠️ **CDP 点击的坐标必须是视口内**；扩展的 `click/mouse_click` 吃 CSS 选择器或 `@e` ref，⛔ 不吃坐标；真坐标点击要 `cdp Input.dispatchMouseEvent`（mousePressed+mouseReleased，`clickCount:1`）。
3. 🔣 **Notion 的 data source 端点要 `Notion-Version: 2025-09-03`**：`2022-06-28` 下 `/v1/data_sources/{id}` 直接 `invalid_request_url`，`2024-03-01` 报 `missing_version`。⇒ 404 `object_not_found` 反而说明端点与版本对了，是权限问题。
4. 🌐 这台机到 Notion API：curl 默认 HTTP/2 有 **1/8 失败**，加 `--http1.1` 后 **8/8 拿到 401/正常应答**；`app.notion.com` 5/5 通。⇒ 上一轮那三次 `Connection was reset` 是**抖**，我据此差点写成"本机到不了 Notion API"——⛔ 那是没采样够就下结论（本文件第 N 次同族）。

**下一步（顺序固定）**：① 把库共享给 `status-gap-read`（页面上一下）→ ② `GET /v1/databases/{db}` 取到 `Status` 全部选项与 option id → ③ 写 `tools/status_gap_check.py`（Notion 白名单 vs `drift/linear_statuses.json` 并集，报差集；带**故障注入**：塞一个假档名必须亮、只喂单来源必须报"来源不全"）→ ④ 补 Notion 的 `In Progress / In Review / Canceled / Duplicate` 四个选项——⚠️ 这一步⛔ 用这把只读钥匙做不了（它按设计就不能写），仍要等 Notion 连接器回来或由你在界面加。

## ✅ 09-24 傍晚：`Status` 三档已补齐（写操作 + 两件独立回读通过）

**动了什么**：给 Notion 库 `Linear Issues 同步库` 的 `Status` 加上 **`In Review`:yellow / `Canceled`:gray / `Duplicate`:brown**，原有三档保持。走的是**回来的 Notion 连接器**（⛔ 不是那把只读钥匙——它按设计没有写权限，而且还没共享给库）。
```
ALTER COLUMN "Status" SET SELECT('Backlog':blue,'Todo':green,'Done':gray,
                                 'In Review':yellow,'Canceled':gray,'Duplicate':brown)
```

**两件回读（都独立于写操作那次的响应，⛔ 不看写回执）**：

| 验什么 | 基线（ALTER 前现读） | ALTER 后独立回读 | 判 |
|---|---|---|---|
| 旧 option 未被重建 | `Backlog=…ZGFhMzk0NzEt…`、`Todo=…NzE3ZDI1ZDEt…`、`Done=…Njc5YzQ2ZWUt…` | 三个 id **逐字符相同** | ✅ |
| 行未被清空 | `AMY-1..4=Todo`、`AMY-5=Backlog`、`AMY-6/7=Done`（7 行） | 聚合回读 `Todo 4 / Backlog 1 / Done 2` = **7** | ✅ |

⇒ 差集从 3 档缩到 **0**（在已确证的档范围内）。`Labels` 那颗雷⛔ 原样留着（options 仍为 `[]`，名字猜不到，不预造）。

**`In Progress` 的处置：不加，并写清为什么**：
- 我在浏览器里点到的 `/settings/project-statuses` 显示 `Backlog / Planned / In Progress / Completed / Canceled` —— ⚠️ 那是**项目**工作流，⛔ 不是工单工作流；Worker 只同步 issue ⇒ 与本报告无关。
- API 侧 `list_issue_statuses(Amy-agent)` 回 5 条（`In Review`/`Canceled`/`Done`/`Duplicate`/`Todo`），⛔ 不含 `Backlog`，而 `Backlog` 正被 AMY-5 使用 ⇒ **这个接口不是全集**（已在 `drift/status_gap_recipe.md` 记为硬规则）。
- ⇒ 我的**推断**（⛔ 不是确证）：AMY 工单的 `started` 档被命名成 `In Review`，所以没有 `In Progress`。加上"命名可改、随时可加档"这件事本身不可穷举 ⇒ **正确处置不是把选项表补到完备，而是让探针常驻**：`Linear 可用档 − Notion 白名单 ≠ ∅` 就亮灯。

**两条过程中的量具教训（都值一次复犯）**：
1. ⚠️ **"点了没反应"有两次是假的，都是我读得太早**。Linear/Notion 这类 SPA 导航后 DOM 要 6–12 秒才换；我按 3–5 秒读，读到的是旧页面，于是判成"点击无效/路由不存在"，还差点据此去写"这个页面在桥下不可读"。⇒ 判据：**先 `list_tabs` 看 URL**（它比 DOM 快照便宜且权威），URL 变了就是导航成功，内容再等。本轮 `project-statuses` 那页就是这么发现的——我先前断言"侧栏 Statuses 点了没动"⛔ 错了。
2. ⚠️ **`notion-query-data-sources` 会连吃 `-32603 did not complete`**（本轮 2 次），换**聚合口径**（`GROUP BY` 而不是逐行）就过了。⇒ 同一条查询失败时，先换形状再怀疑数据。

**探针现状（别当已交付）**：`tools/status_gap_check.py` ⛔ 还没写，因为那把只读钥匙**尚未被共享给库**（`GET /v1/databases/…` 仍 404 `object_not_found`，报文点名要 share 给 `status-gap-read`），而 Notion 的"页面级访问权限"入口在**付费墙**后面（截图实证：`立即升级` / `无可用属性`）。⇒ 现阶段差集检查只能由**带 Notion 连接器的客户端按 `drift/status_gap_recipe.md` 执行**；要它变成离线脚本，得先解决共享这一步。

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
5. **部署之后又现算了几遍复核**（用的全是只读 GET）。采样点序列（时刻全部 `date -u` 现取，⛔ 不是估的）：
   - `2026-09-23T16:53:57Z` —— 部署本身（＝收据的来源）
   - `17:44:10Z`（北京 01:44）—— `deployments[0]` 仍是 #13；`versions/5e011838…` 的 `resources.script.etag` 仍是 `b5cc1a50…`；裸下载端点的 `index.js` 段仍是 **10,860 B / blob `3a698aff…`**（含 `export default`）；绑定 4×`secret_text`；`deployments = 12`、`versions = 13`。⇒ 距部署 **50 分钟**
   - `23:4xZ`（北京 07:4x）—— 检测器修复后的矩阵跑，同批字段仍一致。⇒ 距部署 **约 6.8 小时**
   - `23:54:19Z`（北京 07:54）—— 把**推上 main 的那份脚本 ＋ 那份登记**原样下载回来跑 ⇒ `exit=0`，逐字段仍一致。⇒ 这一发才算"推送件与线上判定同源自洽"
   ⚠️ 写成**采样点序列**而不是连续的"未变"：`17:44Z → 23:4xZ` 之间隔了 **6 小时**的会话空闲。这 6 小时的**结论**是"两端读数一致 ＋ 服务版本 id 仍是 `5e011838…`、`deployments[0]` 仍是 `67e626d1` @ 16:53:57Z" ⇒ 期间**没有发生过新的部署**（有的话 `deployments[0]` 必然是新的一条）；⛔ 但我拿不到那 6 小时的连续观测，只有两端。

6. **顺手把检测器的盲区修了**（起因就是上一条复核：新基线跑出来是绿的，而绿得不对劲）。七组矩阵＋旧版假绿对照见「只读漂移检测」节。⚠️ 这是本文件本轮**唯一一次改代码**（`tools/drift_check.py`，⛔ 不碰 Worker、不碰线上、不切流量），且改的是**只读检测器**本身。

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
   > ✅ **09-24 08:3x 部分完成（只读轮，见文末「独立复算 · WorkBuddy 国际版」节）**：闸门 1 由它对撞通过。**闸门 2/3 它没钥匙 ⇒ 未覆盖**；闸门 4/5/6 本轮按用户决定不下发凭据、不开出口 ⇒ 仍未做。⇒ **"整条链路被两家复算过"这句现在还不成立**，被复算的只有仓库面。
2. **测试窗口收尾时删临时件**：Postman 集合 `7d541dd3-01a6-4e9b-a5b5-c09cd353f0ad` 与环境 `aa1c742f-86ae-4a80-a492-1477c3139c91` 按用户决定**保留**（当前测试窗口是 WorkBuddy 国际版，其他 Agent 未接入），但里面必须是**新值**；⛔ 窗口一结束就删，留着就是"任何能读该账号的人手里有一把生产钥匙"。
**⚠️ 09-24 09:3x 现算清点（只用列表端点）**
```
GET /workspaces                       → 1 个团队空间 9412c1c9-75bc-45ae-8330-833bdafe38c8
GET /workspaces/…/collections         → 7d541dd3-01a6-4e9b-a5b5-c09cd353f0ad "gate45-probe-20260923-QODER"
                                         createdAt == updatedAt == 2026-09-23T08:46:41Z
                                         （同表另有一个 09-21 的 "My Collection"，⛔ 不是本轮建的，别误删）
GET /environments                     → aa1c742f-86ae-4a80-a492-1477c3139c91 "gate45-probe-20260923"
                                         createdAt 08:46:37Z / updatedAt 08:46:38Z
```
⛔ **本步只用列表端点**：`getEnvironment` / `getCollection` 会把变量值与请求头**原样返回** ⇒ 一调，凭据就进会话记录，直接违反本文件"值不进聊天/日志"那条。这条对任何一家客户端都成立：**metadata 可以读，值不能读。**

> 🔴 **09-24 09:5x 更正：我上面写的"两件从未被编辑 ⇒ 里面大概率仍是旧值"⛔ 是错的。** 用户在界面上看过：**环境里就是当前那把（前缀 `bd96`、48 位）。**
> 错在哪一族：我把**列表端点的 `updatedAt`** 当成了"这份东西有没有被改过"的判据，而 Postman 列表接口回的是元数据，⛔ **`type: secret` 的值改动不反映在它的 `updatedAt` 上**。这个字段语义我**没测过就当已知用了** —— 与 `len()` 当总数、`etag` 当文件哈希同族（见「量具级教训」）。
> ⇒ 回滚两条推论：① "新值只剩两处副本"**作废**，仍是三处（CF secret / Postman 环境 / 用户手上）；② "存密码管理器是唯一容错手段"**降回建议**（仍该做，但不是抢救）。
> ⇒ **删不删的判据换掉**：⛔ 别再拿时间戳推"它是不是旧钥匙"。要判这套临时件里是不是活钥匙，只有两条路——用户在界面上用眼睛看（本次就是这么定的），或**打一发带它的请求看 200 还是 401**（那属于闸门 5，需要出口）。
> ⇒ 用户的裁定是**条件式**的："若存旧密钥副本就删" ⇒ 条件不成立 ⇒ **集合与环境都保留**（当前测试窗口还要用）。⚠️ 保留的代价写清楚：**任何能登进这个 Postman 账号的人，手里就有一把能写生产 Notion 的活钥匙** ⇒ **窗口一关就删**，这条不变。

3. ✅ **新值另存 —— 已完成（09-24 用户自报："之前你让我存了 `bd96` 了"）**。48-hex 新值现有**三处**副本：
   CF secret（按设计读不出来）／ Postman 环境 `aa1c742f-86ae-4a80-a492-1477c3139c91`（09-24 用户在界面上
   确认前缀 `bd96` ⇒ 是当前值）／ **用户的密码管理器**。
   > ⚠️ **这一条⛔ 无法由 agent 复验**：密码管理器不在任何我能读的接口后面，采信依据只有用户一句自报。
   > ⇒ 登记时**别把它写成"已验证"**，写成"用户自报完成"。要真验只能反过来做：下次需要取值时能不能取出来。
   > ⚠️ 同一轮的教训仍留着：我曾据 Postman 列表接口的 `createdAt == updatedAt` 推断"环境里是旧值"，
   > ⛔ 错 —— 列表接口回的是元数据，`type: secret` 的值改动不反映在 `updatedAt` 上。

4. **`/selftest` 去留未决**：它是唯一不需要出口就能验收闸门 3/5 的手段，但**无鉴权**且会吃 Linear 配额、泄露 `fetched`。用户倾向保留；⛔ 别顺手给它加写路径。
5. **`Labels` 那颗雷**：multi_select 且 options 为空 ⇒ 谁在 Linear 贴第一个标签就撞 400，而"页面数不变"这个老判据会把部分失败判成通过（原文与 request_id 在 AMY-7）。用户 09-23 定性：⛔ 不预先造选项。
6. **CI/自动部署**：仍然"只检测不切流量"（用户决定）。要重启这个话题的触发条件是"我要 CI 自动部署了"，而前置工作是**把判据从字节比对换成来源证明**（版本 tag/annotation 记 commit），否则漂移只是换了个看不见的方向。
7. ⭐ **未部署版本 #10 怎么处理 —— 等用户裁，⛔ 谁也别擅自动手**。09-23 的"让告警亮着"是在还不知道"上传未部署会占脚本槽位"时拍的；今天这条机制成立后，那个裁决的前提变了（详见「只读漂移检测」节的红色补充）。三个选法：① 从 main 走一次带收据的部署把它盖掉（**代价：又一次 100% 流量切换＋要重新留三元组**）；② **本轮先按这个走**：登记为 `kept_intentionally` 并写清代价 ⇒ 把"看不见导致的灭灯"换成"明示的豁免"，检测器仍逐个点名它；③ 删掉那个版本 —— ⛔ 我没查到 Cloudflare 有"删单个 version"的接口，⛔ 别凭想象做（要动先现读 OpenAPI 确认端点存在）。

## 独立复算 · WorkBuddy 国际版 · 09-24 08:3x（只读轮，第一家外部客户端交回来的东西）

**它跑的是什么**：本文件之外的《派工单 · 配方重跑》——⛔ 单里故意一个预期值都不给，它算，我同一时刻现算对撞。它全程 `GET`、零写入，并明确拒绝用 `wrangler.toml` 里的 `[secrets] required=[…]` 冒充"线上现状读数"（**这个拒绝是对的**：那是仓库里的要求清单，不是线上事实）。

**闸门 1 对撞结果（它 08:34:53Z 现算 vs 我 00:38:47Z 现算，差 4 分钟）**

> ⚠️ 09-25 补全日期：那两发是 `2026-09-24T08:34:53Z` 与 `2026-09-24T00:38:47Z`。本文件今夜跨了 09-24→09-25 两天，⛔ 无日期的 `…Z` 时刻会被读错一天。

| 项 | 它报的 | 我现算 | 判 |
|---|---|---|---|
| `main` HEAD | `f9b99ff8ce3ca6de2d9f6b33e40b909b094c2330` | 同 | ✅ ⚠️ **值已过期**：09-25 现算 `9b2270239d9bc121ad6126fd07d3797ca432a6a1`（committer `2026-09-24T15:20:02Z`），见顶部横幅第 1 条 |
| HEAD tree | `162744d54039e6f9c571dbda58cad3c04f5ff499` | 同（取法见下方⚠️） | ✅ ⚠️ **值已过期**：09-25 现算 `9d46e389329756e667669f1e2c3fa9d25c6322f3`（走 `GET /git/commits/main` 的 `.commit.tree.sha`） |
| 分支 | 2 条：`main`、`demo/sync-skeleton` | 同 | ✅ ⚠️ **这条今夜复算仍成立**（窗口 A 与第二窗口 `gh api` 两取法各 2 条，测于 `16:26:53Z` / `16:58:54Z`） |
| commit 数 | 32 | 32（`per_page=100` 页满前即全量） | ✅ ⚠️ **值已过期**：09-25 现算 **42**（`page1=42` / `page2=0`，翻页到空；两取法一致）。⛔ 别拿"第一页长度"当总数——这一格当时恰好等于总数，是巧合 |
| 六个 blob 的 size+SHA-1 | 全列 | **六个逐项全等** | ✅ |

⇒ **"没人偷偷推 main"这一条从此有两只眼睛了**。但要说清它独立在哪：独立的是**取法与算术**（它走 `curl` 直取 REST，不走 MCP 包装）；⛔ 不独立的是**数据源** —— 同一份公开仓库，谁读都是那份。⇒ 这一格关掉的是"读错/算错/被静默改过"，⛔ 不是"两家各自掌握证据"。

**⭐ 这一轮最值钱的不是它的对撞，是它自报的那个 bug**：它第一次算 blob 时**六个文件返回同一个 106 字节的 SHA**。根因＝`curl` 失败不抛错，脚本读了**上一次成功响应留下的同名文件**，把"分支列表"的字节当成六个文件内容去哈希。⇒ 同族老坑（本文件上面记过：子进程零输出、空输入也有合法哈希、`len()` 当总数）的新变体：**"哈希算出来了"不证明"哈希来自本次抓取"**。
它的修法值得抄进任何脚本：**唯一临时文件名 + 退出码与 HTTP 码双校验 + 跨调用断言"不同 URL 不得得到相同字节"**。最后那条是它自己加的阳性对照，也正是把这类静默失败逼出来的唯一办法。

**⚠️ 顺带记一条我这侧的量具坑**（对撞时才暴露）：`GET /git/trees/{ref}?recursive=1` 返回对象的 `.sha` **回的是我传进去的那个 ref 解析后的对象号（commit sha）**，⛔ 不是 tree sha。要 tree sha 必须走 `GET /git/commits/{sha}` 取 `.tree.sha`。我第一版对撞脚本据此打出的"tree 不等"是**假差异** —— 先 `Object.keys` 再取数这条老规矩又一次没执行到位。

**它报的一条环境事实，我这侧复验后降级**：它发现 `%APPDATA%\xdg.config\.wrangler\` 存在、且路径里⛔ 没有它自己的 `-ai` 段 ⇒ 按边界纪律**只报路径与事实、未读内容**（这个处置本身✅ 对，保留）。我这侧只读地查了：该目录只有 `metrics.json`（132 B）＋ `logs/`（6 个日志），⛔ 没有 `config/`、没有任何 token 形态文件；拿本机那把部署钥匙（`deploy-linear-sync-30d`）的内容去 `grep -rlF` 这一整目录 ⇒ **0 文件命中、0 次命中**，同一串打在自己的落盘文件上阳性对照 **=1**。⇒ 结论：**这次不是"钥匙暴露在别人空间里"**，只是"这台机器跑过 wrangler"。⚠️ 但"日志即密钥库"那条仍然成立（见上文），不要因为这条降级就松手。

**本轮没覆盖到的（⛔ 别当已验）**：闸门 2／3 —— 它**没有任何 Cloudflare 只读凭据**（穷举过环境变量、自己的 mcp.json、连接器清单、~/.wrangler、全空间赋值形态，0 命中），所以判据层它当时只能空着。（⚠️ 09-24 09:0x 更新：这一格**已由第二轮补上一半** —— 我转原始回执、它自己算，见下一节；⛔ 但钥匙层仍然没补。）

**⚠️ 09-24 09:0x 自我更正（对撞时才看出来，功劳记外部复算方）**：本文原有的论证是「etag 与 `sha256(源码)` 不相等」——那是**同长度、不同值**的**经验**证据，必须读一次现值才成立。它这轮给的是更硬的一条：etag 是 **64 hex = 256 bit**，而 git blob SHA-1 是 **40 hex = 160 bit** ⇒ 两者⛔ **量纲不同，结构上就不可能相等**，无需采样、也不会被哪一次巧合推翻。⇒ 今后凡写「etag ⛔ 不能与仓库对撞」，**先给量纲这一条，再谈语义**。（本文此前只说过"它答不了那份东西等不等于仓库"——结论下了，⛔ 最省力的证明漏了。）
我这侧同一时刻的对照读数：serving 仍是 #13 `5e011838…`（deployment `67e626d1` @ 16:53:57Z）、`/secrets` 仍是那四个名字 ⇒ **它就算有钥匙，这两格也不会翻出新的东西**。⇒ 这轮"没做"不改变结论，但⛔ 不改变"只有一只手"这个事实。

**一句话判词**：它这轮是**真复算**（现算、自炸、自修、把不能做的写成"未测"），⛔ 但它复算的面只到仓库侧 —— 派工单要的"两端对撞"里，CF 那两端还欠着。

### 第二轮 · 判据层对撞（同一外部客户端，拿我转的原始 JSON 自己算；测于 09-24 08:4x–09:0x 北京）

我给的是 A–E 五段原始回执（`deployments` / `versions` / `versions/{serving}` / `secrets` / `settings`，采样 `2026-09-24T00:43:48Z`），⛔ 一个结论都没给。他交回：**闸门 2 = 不可判（三条理由）**、**闸门 3 = 成立（限于"存在"这一层）**。我这侧逐条对撞：

| 他算的 | 我现算 | 判 |
|---|---|---|
| A 段 12 条、B 段 13 条、去重仍 13、编号 1..13 无缺号 | 同 | ✅ |
| 部署覆盖 12 个 version_id、**未部署差集恰 1 条 = `#10 a7ba0f39`（source=wrangler）**、反向孤儿 0 | 同 | ✅ |
| serving = `5e011838…` / #13 / `handlers=['fetch']` / `compatibility_date=2026-09-21` | 同 | ✅ |
| etag `b5cc1a50…` 是 64 hex，git blob 是 40 hex ⇒ ⛔ 不可对撞（他没拿去比） | 同 | ✅ 这条比我上一版的表述更干净 |
| C 的 bindings 四个名字与 D/E 全等 ⇒ 把"存在"从设置层下沉到**正在服务的版本层** | 同 ⇒ **这一层我之前没单独取**，是他补的 | ✅ 增量 |
| `deployments[].source` 与 `versions[].source` 不一致的有 **3 条** | **穷举是 6 条**：#13/#9/#7/#3/#2 是 `quick_editor→dash`，另有 #1 `dash_template→dash` | ⚠️ 他**样本没穷举**（结论方向不变，且被加强） |

⭐ **他有一条推论被当场否掉（这是本轮真正的收获）**：他从"两个 `source` 字段不同义"推出"etag 指纹的产物与源码文本之间**没有可验证的恒等关系**"。前件真、后件⛔ 不被支持。我这侧一发只读调用就是反证：
```
versions/f58a17a5…  #11  etag 00f6b1cad98f88db…   @15:27:23Z
versions/085be851…  #12  etag 00f6b1cad98f88db…   @16:14:22Z   ← 同一串
versions/2fc04c35…  #9   etag 5d4e6aada4d5f2b6…                ← 换内容就换串
```
#12 只是把 `SYNC_TOKEN` 从 `plain_text` 改成 `secret_text` 的**配置保存**，脚本没动 ⇒ **同内容 ⇒ 同 etag；换内容 ⇒ 换 etag**。⇒ etag 确实是产物/内容指纹，只是**与 git blob 不同量纲、不能对撞**（他那条②），并且"线上==仓库"的字节等价⛔ 只在"上传即部署那一瞬"可取（本文既有条款）。**他的"不可判"判词成立，但支柱是①（C 不含字节）与②（量纲不同），③得拆掉。** ⇒ 记一条：**从"两个字段语义不同"跳到"指纹与文本无恒等关系"，是共时观察冒充因果**——本文件为这个形状已经付过三次学费，外部客户端第一次来就撞上，说明它确实是个陷阱形状，不是谁笨。

⚠️ **本轮我这侧的事故一枚（贴装，不是数据）**：B 段 `number:8` 那行的 `created_on` 被我贴进聊天时混进了一句中文废话（本地 `receipt_bundle.txt` 干净，`grep -c 请忽略` = 0）。他的处置值得抄进任何复算方：**不静默丢**——把这个字段隔离出时间推理、⛔ 但保留 id（id 合法，集合算术不受影响），另用 A 段独立卡出时间窗证明"是粘贴污染而非数据丢失"，并把它报出来。这正是本文件批评过的"看不见就不是问题"的反面。
　⚠️ 一个小口径纠正：他说 #8 的真值"可回收"并给了 `15:03:55.267235Z` —— 那是 **deployment** 的时刻，version 自己的 `metadata.created_on` 是 `15:03:54.566576Z`。两者对每条都差 **0–1.6 秒**（#13 恰好相同），⛔ 混用会在亚秒级排序上出错。

⚠️ **把他的一条印证降级**：他说 serving 身份获"两条独立渠道"印证（我的 fresh 读数 + 仓库 `drift/known_good.json`）。⛔ 那个文件是**我写的、我推的** ⇒ 独立的是**传输路径**（他自己经 GitHub 只读通道取的），⛔ 不是**作者**。⇒ 准确的账是"**同一只手的两次声明，相隔约 7 小时**"，它买到的是"这 7 小时里没发生部署"，⛔ 买不到"serving 被第二双眼睛看过"。

**独立性账（更新，别记浮）**：
- **仓库面**：两只手（他 `curl` 直取 REST + 我 `gh`），六个 blob 逐字节全等 ⇒ "没人偷偷推 main"这条从此硬了。
- **判据层（闸门 2/3 的算术与判词）**：两只手 ⇒ 他独立求出 serving、差集、"未部署=1"，并**多取了一层我没单独取过的**（C 的版本级 bindings）。
- **钥匙层**：⛔ 仍一只手。**且要写清一条边界：Cloudflare 控制台那个 HTTP 面板不算第二把钥匙** —— 它走的是同一个已登录账号，只是"我不用命令行"的另一副手。⇒ 真要第二把钥匙，只剩"用户在 dashboard 新铸一把只读 token"这一条路（本票已投②：本轮不做）。
- **端点行为（闸门 4/5/6）**：本轮按用户决定不下发凭据 ⇒ 仍是我 + Postman/CF 面板，⛔ 无外部客户端参与。
