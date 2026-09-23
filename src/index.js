/**
 * linear-sync — Linear → Notion 单向同步 Worker
 *
 * 端点
 *   GET  /          服务说明
 *   GET  /health    健康检查（含缺失配置提示）
 *   POST /sync      从 Linear 拉取 issue，upsert 到 Notion 数据库
 *                   body（可选）: { "dryRun": true, "since": "2026-09-01T00:00:00Z", "teamKey": "ENG" }
 *
 * Secrets
 *   LINEAR_API_KEY      Linear personal API key
 *   NOTION_TOKEN        Notion integration token
 *   NOTION_DATABASE_ID  目标 Notion 数据库 ID
 * 可选
 *   LINEAR_TEAM_KEY  仅同步该 team key 前缀的 issue（如 "ENG"）
 *   NOTION_VERSION   Notion API 版本，默认 2022-06-28
 *   SYNC_TOKEN       若设置，POST /sync 需带 Authorization: Bearer <token>
 */

const VERSION = "0.2.0";

const LINEAR_ENDPOINT = "https://api.linear.app/graphql";
const NOTION_ENDPOINT = "https://api.notion.com/v1";
const DEFAULT_NOTION_VERSION = "2022-06-28";

const PAGE_SIZE = 50;
const MAX_ISSUES = 500;
// Notion 单个 text.content 上限 2000 字符；rich_text 数组上限 100 项
const TEXT_LIMIT = 2000;
const TEXT_CHUNKS_LIMIT = 100;

// 去重查询的重试策略，用于等待 Notion 查询索引追平刚写入的页面
const LOOKUP_ATTEMPTS = 3;
const LOOKUP_RETRY_MS = 1500;

const ISSUES_QUERY = `
  query SyncIssues($first: Int!, $after: String) {
    issues(first: $first, after: $after, orderBy: updatedAt) {
      pageInfo { hasNextPage endCursor }
      nodes {
        id
        identifier
        title
        url
        description
        updatedAt
        state { name type }
        assignee { name email }
        labels(first: 10) { nodes { name } }
      }
    }
  }
`;

const REQUIRED_CONFIG = ["LINEAR_API_KEY", "NOTION_TOKEN", "NOTION_DATABASE_ID"];

// ---------- 基础工具 ----------

function json(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function clip(value) {
  if (value === null || value === undefined) return "";
  return String(value).slice(0, TEXT_LIMIT);
}

function richText(content) {
  const value = clip(content);
  return value ? [{ type: "text", text: { content: value } }] : [];
}

// 长文本按 2000 字符切片放进多个 rich_text 项，避免截断丢内容
function richTextChunks(content) {
  const value = content === null || content === undefined ? "" : String(content);
  if (!value) return [];

  const chunks = [];
  for (let i = 0; i < value.length && chunks.length < TEXT_CHUNKS_LIMIT; i += TEXT_LIMIT) {
    chunks.push({ type: "text", text: { content: value.slice(i, i + TEXT_LIMIT) } });
  }
  return chunks;
}

function missingConfig(env) {
  return REQUIRED_CONFIG.filter((key) => !env[key]);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ---------- Linear ----------

async function linear(env, query, variables) {
  const res = await fetch(LINEAR_ENDPOINT, {
    method: "POST",
    headers: {
      Authorization: env.LINEAR_API_KEY,
      "content-type": "application/json",
    },
    body: JSON.stringify({ query, variables }),
  });
  const payload = await res.json().catch(() => ({}));

  if (!res.ok) {
    const error = new Error(payload?.errors?.[0]?.message || `Linear API ${res.status}`);
    error.status = res.status;
    error.detail = payload;
    throw error;
  }
  if (payload?.errors?.length) {
    const error = new Error(payload.errors[0].message || "Linear GraphQL 返回错误");
    error.status = 502;
    error.detail = payload;
    throw error;
  }
  return payload.data ?? {};
}

async function fetchIssues(env, options) {
  const collected = [];
  let after = null;
  let hasNext = true;

  while (hasNext && collected.length < MAX_ISSUES) {
    const data = await linear(env, ISSUES_QUERY, { first: PAGE_SIZE, after });
    const connection = data.issues;
    if (!connection) throw new Error("Linear 响应缺少 issues 字段");

    for (const node of connection.nodes ?? []) {
      collected.push(node);
      if (collected.length >= MAX_ISSUES) break;
    }
    hasNext = Boolean(connection.pageInfo?.hasNextPage);
    after = connection.pageInfo?.endCursor ?? null;
  }

  const teamKey = clip(options.teamKey || env.LINEAR_TEAM_KEY || "").trim().toUpperCase();
  const since = options.since ? Date.parse(options.since) : Number.NaN;

  return collected.filter((issue) => {
    if (teamKey && !String(issue.identifier ?? "").toUpperCase().startsWith(`${teamKey}-`)) {
      return false;
    }
    if (!Number.isNaN(since) && Date.parse(issue.updatedAt) <= since) {
      return false;
    }
    return true;
  });
}

// ---------- Notion ----------

async function notion(env, path, init = {}) {
  const res = await fetch(`${NOTION_ENDPOINT}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${env.NOTION_TOKEN}`,
      "Notion-Version": env.NOTION_VERSION || DEFAULT_NOTION_VERSION,
      "content-type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  const payload = await res.json().catch(() => ({}));

  if (!res.ok) {
    const error = new Error(payload?.message || `Notion API ${res.status}`);
    error.status = res.status;
    error.detail = payload;
    throw error;
  }
  return payload;
}

function toProperties(issue) {
  return {
    Name: { title: richText(issue.title) },
    "Linear ID": { rich_text: richText(issue.id) },
    Identifier: { rich_text: richText(issue.identifier) },
    Status: { select: issue.state?.name ? { name: clip(issue.state.name) } : null },
    Assignee: { rich_text: richText(issue.assignee?.name) },
    Labels: {
      multi_select: (issue.labels?.nodes ?? [])
        .filter((label) => label?.name)
        .slice(0, 10)
        .map((label) => ({ name: clip(label.name) })),
    },
    URL: { url: issue.url ?? null },
    "Updated At": { date: issue.updatedAt ? { start: issue.updatedAt } : null },
    Description: { rich_text: richTextChunks(issue.description) },
  };
}

async function findByLinearId(env, linearId) {
  // Notion 的查询索引对刚写入的页面有约 1 秒的可见延迟（实测 1.14s）。
  // 查不到时不能立刻当作"不存在"，否则连续多次同步会重复建页。这里重试等待索引追平。
  for (let attempt = 1; attempt <= LOOKUP_ATTEMPTS; attempt += 1) {
    const data = await notion(env, `/databases/${env.NOTION_DATABASE_ID}/query`, {
      method: "POST",
      body: JSON.stringify({
        filter: { property: "Linear ID", rich_text: { equals: linearId } },
        page_size: 1,
      }),
    });
    const page = data.results?.[0];
    if (page) return page;
    if (attempt < LOOKUP_ATTEMPTS) await sleep(LOOKUP_RETRY_MS);
  }
  return null;
}

// ---------- 同步主流程 ----------

async function runSync(env, options) {
  const dryRun = Boolean(options.dryRun);
  const issues = await fetchIssues(env, options);

  const summary = {
    dryRun,
    fetched: issues.length,
    created: 0,
    updated: 0,
    failed: 0,
    errors: [],
  };
  const preview = [];

  for (const issue of issues) {
    const properties = toProperties(issue);

    if (dryRun) {
      if (preview.length < 5) preview.push({ identifier: issue.identifier, properties });
      continue;
    }

    try {
      const existing = await findByLinearId(env, issue.id);
      if (existing) {
        await notion(env, `/pages/${existing.id}`, {
          method: "PATCH",
          body: JSON.stringify({ properties }),
        });
        summary.updated += 1;
      } else {
        await notion(env, "/pages", {
          method: "POST",
          body: JSON.stringify({
            parent: { database_id: env.NOTION_DATABASE_ID },
            properties,
          }),
        });
        summary.created += 1;
      }
    } catch (error) {
      summary.failed += 1;
      if (summary.errors.length < 5) {
        summary.errors.push({ identifier: issue.identifier, message: error.message });
      }
    }
  }

  if (dryRun) summary.preview = preview;
  return summary;
}

// ---------- 路由 ----------

function authorized(request, env) {
  if (!env.SYNC_TOKEN) return true;
  return (request.headers.get("authorization") ?? "") === `Bearer ${env.SYNC_TOKEN}`;
}

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);

    if (pathname === "/health") {
      return json({
        ok: true,
        service: "linear-sync",
        version: VERSION,
        missingConfig: missingConfig(env),
      });
    }

    if (pathname === "/" && request.method === "GET") {
      return json({
        service: "linear-sync",
        version: VERSION,
        description: "Linear → Notion 单向同步 Worker",
        endpoints: ["GET /health", "POST /sync"],
        syncOptions: { dryRun: "boolean", since: "ISO8601", teamKey: "string" },
      });
    }

    // 只读自检：在 Cloudflare 内部直接跑一次 dryRun，不写 Notion、不经鉴权分支
    if (pathname === "/selftest") {
      const missing = missingConfig(env);
      if (missing.length) {
        return json({ ok: false, error: "missing_config", missing }, 500);
      }
      const startedAt = Date.now();
      try {
        const summary = await runSync(env, { dryRun: true, teamKey: "AMY" });
        return json({
          ok: true,
          selftest: true,
          durationMs: Date.now() - startedAt,
          fetched: summary.fetched,
          previewCount: (summary.preview || []).length,
          errors: summary.errors,
          syncAuthEnabled: Boolean(env.SYNC_TOKEN),
        });
      } catch (error) {
        return json({ ok: false, selftest: true, error: "selftest_failed", message: error.message }, 502);
      }
    }

    if (pathname === "/sync") {
      if (request.method !== "POST") {
        return json({ error: "method_not_allowed", hint: "POST /sync" }, 405);
      }
      if (!authorized(request, env)) {
        return json({ error: "unauthorized" }, 401);
      }

      const missing = missingConfig(env);
      if (missing.length) {
        return json({ error: "missing_config", missing }, 500);
      }

      let options = {};
      try {
        options = await request.json();
      } catch {
        options = {};
      }

      const startedAt = Date.now();
      try {
        const summary = await runSync(env, options ?? {});
        return json({
          ok: true,
          service: "linear-sync",
          durationMs: Date.now() - startedAt,
          ...summary,
        });
      } catch (error) {
        return json(
          { ok: false, error: "sync_failed", message: error.message, detail: error.detail ?? null },
          502,
        );
      }
    }

    return json(
      { error: "not_found", endpoints: ["GET /", "GET /health", "POST /sync"] },
      404,
    );
  },
};