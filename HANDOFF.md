# 接手须知（HANDOFF）

> 这个仓、这条链路（Linear ↔ GitHub ↔ Notion ↔ Cloudflare）**以后不止一个 agent 在跑**。
> 本文件是给下一个会话的入口。⛔ 动手前先读完。改于 2026-09-22 23:4x（北京）。
> 另两处交接面：Linear 项目 **P-AMY-1** 顶部横幅、工单 **AMY-6 / AMY-7** 文末记录。

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
3. **“GitHub↔Linear↔Notion 三向循环”这个担心已被实测否定。** Worker 全文 `mutation` 命中 0 次；Two-way 开启到 23:0x 两侧新增镜像对象 0 条。⛔ 别再为此写“护栏”代码——真该补的是**部署自动化**（见下）。

## 钥匙能力表（省你三小时）

| 通道 | 能做什么 | ⛔ 不能做什么 |
|---|---|---|
| github 连接器 | 读、写、合并 PR、建/删文件（均实测成功） | —— ⛔ 别引用“token 只读、写会 403”那句旧话，已被当场证伪 |
| cloudflare MCP | 读配置、读 secret **名字**、拉线上源码、改配置 | ⛔ 写 secret（10405，凭据是受限钥匙）；⛔ 读遥测（`analytics_engine/sql` 403）；⛔ fetch 自家 workers.dev（出口策略 403） |
| linear 连接器 | 读写 issue/project；`patch` 可局部改正文 | ⛔ 改附件标题（无接口）；`links` 回执成功但 **0/1 生效** ⇒ 写后必回读 |
| qca 云沙箱 | 跑 shell、有外网（api.github.com=200） | ⛔ 到 workers.dev（`allowed_hosts: []` 且不可改 ⇒ DNS 黑洞） |
| 用户本机 | 校园网 | ⛔ 到 workers.dev（**SNI 重置**）；⛔ 开不了 VPN |
| **用户手机 + VPN** | ✅ 目前**唯一**能打到这个端点的设备 | 浏览器发不出 `Authorization` 头 ⇒ 只能测“不带密码”那一半 |

## 真存在的风险（当前未处置）

**仓库与线上之间没有任何自动链路。** 8 次部署的 source 只有 `dash_template` / `quick_editor` / `dash`，`wrangler` 一次都没跑过，secrets 也是手贴的。⇒ 今天“线上==main”是**手抄对上了**，不是机制保证的。要治漂移，下一步是接上 `wrangler deploy`（或 Workers Builds 跟 Git 绑），⛔ 不是给 `/health` 加个 commit 字段（那只能让漂移可见）。

## 变更约定

- 登记按“原文不改、文末追加”——但⛔ 只读前 20 行一定读到过期快照，所以**更正必须同时放顶部横幅**。
- 每条结论都要写“**怎么测的 + 测于哪一刻**”，⛔ 不要只写“现行值”。
- 写操作回执成功不算落盘，**必回读**。
