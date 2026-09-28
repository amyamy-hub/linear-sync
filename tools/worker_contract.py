"""第四道闸：把墙上关于 `src/index.js` 的**散文断言**变成离线可复算的判断。

    py tools/worker_contract.py                 # 对着仓里的源码复算契约；绿=0
    py tools/worker_contract.py --root <目录>    # 换一棵树跑（反证套件就这么调它，⛔ 另开子进程）
    py tools/worker_contract.py --only W6        # 只看某一条（调试用）

为什么这件必须在仓里：`src/index.js` 是这个仓里⛔ 任何测试的那件（`GET /git/trees` 现数 15 个 blob，
测试件只覆盖 `tools/`）。而墙上关于它的说法——「`authorized()` 第一行是那句默认放行」「`toProperties()`
交回 9 个键」「`/selftest` 无鉴权且把 `teamKey` 写死成 AMY」「不带 `since` 就是全量覆盖」「命中口径是严格大于」
「dryRun 下 `failed:0` 是结构性常量」——全部是**人读源码抄下来的句子**。抄下来的东西会漂：横幅第 11 条
就是同一句里「9 个键」被写成「10 个字段」（4 处），第 44 条抓到的是另一处抄错的哈希。
⇒ 从此任何人 clone 下来一发就能重算，⛔ 需要相信任何一句话。

三条口径（跟前三道闸同一套，都是踩出来的）：
  1. **登记＝「应当等于什么」，值一律从源码现算**（键名列表、数组项、字节数、比较符、先后次序）。
     期望放在 `drift/worker_contract.json` 里而不是写死在这件代码里，是为了让「契约改了」这件事
     在 diff 里看得见，也让反证套件能**单独改契约**或**单独改源码**来试出两头的牙。
  2. **锚点＝内容⛔ 行号**（第 14 条②、第 47 条②(a)）。行号只在末尾当**读数**打印，供墙上那些
     「第 179 行」「第 149 行」现算复核，⛔ 参与判定。
  3. **契约钉着它是对着哪一份源码定的**（`source.sha256_of_bytes` ＋ `bytes`）：源码一动就对不上 ⇒ exit 2，
     逼下一个人重新看一眼契约，而⛔ 拿旧契约去量新代码。
     ⚠️ 这一钉用 **SHA-256**、⛔ 用 git 的 blob 号：blob 号是 SHA-1，而"再多一处 SHA-1 调用"在门禁上
     ＝新增一批 issue——现有那枚豁免只盖住 `tools/drift_check.py` 里已逐条 Ignore 的那一行（第 47 条：
     豁免绑实例＋行号，新写的行⛔ 在豁免内）。本件要答的是"这份字节变过没"，⛔ 是"它在 git 里叫什么"
     ⇒ 强哈希完全够。契约里仍**展示** `blob_sha1`（登记时从 `GET /git/trees` 现抄的，供与仓库对撞），
     本件⛔ 重算它，也⛔ 联网。

退出码：0＝每条都等；1＝有⛔ 等、或契约过期（`review_by`）；
2＝量具坏（源码/契约读不到、版本⛔ 配对、源码与契约钉的那份⛔ 同、某条要看的锚点⛔ 在、
  规则与期望⛔ 配对、或某条的「它必然响」探针⛔ 响 ⇒ 那条规则是瞎的，它报的 0 一律⛔ 算结论）。
"""

import datetime
import hashlib
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT_REL = os.path.join("drift", "worker_contract.json")
CONTRACT_REVISION = "2026-09-29-worker-contract-1"

# ---- 源码里的字面锚点。写成常量是为了让「探针钉⛔ 住唯一」这件事可复算 ----
FN_AUTH = "function authorized(request, env) {"
AUTH_DEFAULT_OPEN = FN_AUTH + "\n  if (!env.SYNC_TOKEN) return true;"
AUTH_DEFAULT_CLOSE = FN_AUTH + "\n  if (!env.SYNC_TOKEN) return false;"
FN_TO_PROPS = "function toProperties(issue) {"
FN_RUN_SYNC = "async function runSync(env, options) {"
SELFTEST_OPEN = 'if (pathname === "/selftest") {'
HEALTH_OPEN = 'if (pathname === "/health") {'
SINCE_TERNARY = "options.since ? Date.parse(options.since) : Number.NaN"
SINCE_GUARD = "!Number.isNaN(since) &&"
SINCE_GUARD_FLIP = "Number.isNaN(since) ||"
SINCE_CMP = "Date.parse(issue.updatedAt)"
SINCE_CMP_LE = "Date.parse(issue.updatedAt) <= since"
SINCE_CMP_LT = "Date.parse(issue.updatedAt) < since"
FAILED_BUMP = "summary.failed += 1;"
DRYRUN_OPEN = "if (dryRun) {"
CONTINUE = "continue;"
PREVIEW_PUSH = "      if (preview.length < 5) preview.push({ identifier: issue.identifier, properties });"
PREVIEW_OPEN = "if (preview.length < 5)"
JSON_HELPER = "JSON.stringify(body, null, 2)"
UNAUTH_BODY = '{ error: "unauthorized" }'
UNAUTH_BODY_MUT = '{ error: "unauthorized!!" }'
REQUIRED_OPEN = "REQUIRED_CONFIG = "
REQUIRED_3 = '["LINEAR_API_KEY", "NOTION_TOKEN", "NOTION_DATABASE_ID"]'
REQUIRED_4 = '["LINEAR_API_KEY", "NOTION_TOKEN", "NOTION_DATABASE_ID", "SYNC_TOKEN"]'
URL_LINE = "    URL: { url: issue.url ?? null },\n"
LABELS_SLICE = ".slice(0, 10)"
LABELS_SLICE_MUT = ".slice(0, 8)"
AMY_KEY = 'teamKey: "AMY"'
AMY_KEY_MUT = 'teamKey: "ENG"'
AUTH_CALL = "authorized("
ENDPOINTS_2 = 'endpoints: ["GET /health", "POST /sync"]'
ENDPOINTS_LEAK = 'endpoints: ["GET /health", "GET /selftest", "POST /sync"]'
HEALTH_OK = "      return json({\n        ok: true,"
HEALTH_OK_COMputed = "      return json({\n        ok: !missingConfig(env).length,"
ENDPOINTS_OPEN = "endpoints: ["


def _read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _digest(data):
    """这份字节的 SHA-256 —— 只答"变过没"。git 的 blob 号是 SHA-1：本件⛔ 算它，
       那等于在仓里多开一处弱哈希调用，而现有豁免绑⛔ 到别处（文件头口径 3、第 47 条）。"""
    return hashlib.sha256(data).hexdigest()


def _line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def _scan_string(text, i):
    """i 指向开引号 ⇒ 返回闭引号**之后**的下标；扫⛔ 到 ⇒ -1。模板串里的 `${…}` 整段当字符串吞掉。"""
    quote = text[i]
    i += 1
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == quote:
            return i + 1
        i += 1
    return -1


def _match_pair(text, i, opener, closer):
    """i 指向 opener ⇒ 配对的 closer 下标；⛔ 配 ⇒ -1。字符串／模板串里的括号⛔ 算数。"""
    depth = 0
    while i < len(text):
        c = text[i]
        if c in "\"'`":
            nxt = _scan_string(text, i)
            if nxt < 0:
                return -1
            i = nxt
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _scope(text, opener_literal):
    """取 `…{ … }` 那对花括号的内部文本、内部起点、结尾。锚点⛔ 在／括号⛔ 配 ⇒ (None, -1, -1)。"""
    at = text.find(opener_literal)
    if at < 0:
        return None, -1, -1
    brace = text.find("{", at)
    if brace < 0:
        return None, -1, -1
    end = _match_pair(text, brace, "{", "}")
    if end < 0:
        return None, -1, -1
    return text[brace + 1:end], brace + 1, end


def _top_split(text):
    """按**深度 0** 的逗号切；括号嵌套、字符串、模板串都整段吞进去。"""
    parts, buf, depth, i = [], [], 0, 0
    while i < len(text):
        c = text[i]
        if c in "\"'`":
            start = i
            nxt = _scan_string(text, i)
            if nxt < 0:
                return parts
            buf.append(text[start:nxt])
            i = nxt
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    parts.append("".join(buf))
    return [p for p in parts if p.strip()]


def _bare_key(raw):
    key = raw.strip()
    if len(key) >= 2 and key[0] in "\"'" and key[-1] == key[0]:
        return key[1:-1]
    return key


def _obj_pairs(lit):
    """`{ a: 1, "b c": {…}, d, }` ⇒ [("a","1"),("b c","{…}"),("d",None)]；切不出来 ⇒ None。
       ⚠️ 键要**括号配对**着数：上一版按逗号硬切，把 `{ title: richText(x) }` 里的逗号也算成顶层
       ⇒ 键数虚高（这条是「审计别的 agent」时抓过的同款坏量具，先给自己跑对照）。"""
    if not lit.startswith("{"):
        return None
    end = _match_pair(lit, 0, "{", "}")
    if end < 0:
        return None
    out = []
    for part in _top_split(lit[1:end]):
        body = part.strip()
        depth, colon, i = 0, -1, 0
        while i < len(body):
            c = body[i]
            if c in "\"'`":
                nxt = _scan_string(body, i)
                if nxt < 0:
                    return None
                i = nxt
                continue
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif c == ":" and depth == 0:
                colon = i
                break
            i += 1
        if colon < 0:
            out.append((body.rstrip(), None))
        else:
            out.append((_bare_key(body[:colon]), body[colon + 1:].strip()))
    return out


def _array_items(lit):
    """`["a", "b"]` ⇒ ["a","b"]（每项去引号）；切不出来 ⇒ None。"""
    at = lit.find("[")
    if at < 0:
        return None
    end = _match_pair(lit, at, "[", "]")
    if end < 0:
        return None
    return [_bare_key(p) for p in _top_split(lit[at + 1:end])]


def _str_value(value):
    """值必须是**纯字符串字面量**才谈得上数字节；否则 None（⇒ 这条判『⛔ 可判』而⛔ 是「等」）。"""
    if value is None:
        return None
    body = value.strip()
    if len(body) >= 2 and body[0] in "\"'" and body[-1] == body[0]:
        return body[1:-1]
    return None


def _stringify_len(pairs):
    """照 `JSON.stringify(x, null, 2)` 的形状排出来再数 **UTF-8 字节**。只覆盖平坦对象。"""
    lines = ["{"]
    for i, (key, val) in enumerate(pairs):
        tail = "," if i + 1 < len(pairs) else ""
        lines.append(f'  "{key}": "{val}"{tail}')
    lines.append("}")
    return len("\n".join(lines).encode())


def _first_stmt(body):
    for raw in body.split("\n"):
        line = raw.strip()
        if not line or line.startswith(("//", "/*")):
            continue
        return line
    return ""


def _returned_object(body):
    """函数体里 `return { … };` 那个对象字面量的原文；取不到 ⇒ (None, 理由)。"""
    at = body.find("return")
    if at < 0:
        return None, "函数体里找⛔ 到 return"
    brace = body.find("{", at)
    if brace < 0:
        return None, "return 后面找⛔ 到 {"
    end = _match_pair(body, brace, "{", "}")
    if end < 0:
        return None, "那个返回对象的括号⛔ 配"
    return body[brace:end + 1], ""


def _all_endpoints(text):
    """文件里每一处 `endpoints: [ … ]` 的项目列表 ⇒ (列表们, 是否全部切得出来)。"""
    out, at = [], text.find(ENDPOINTS_OPEN)
    while at >= 0:
        bracket = text.find("[", at)
        end = _match_pair(text, bracket, "[", "]")
        if end < 0:
            return out, False
        items = _array_items(text[at:end + 1])
        if items is None:
            return out, False
        out.append(items)
        at = text.find(ENDPOINTS_OPEN, end + 1)
    return out, True


def _forty_one_body(src):
    """从源码里找出那发 401 的对象字面量：顺着 `401` 这个状态实参回溯到 `return json(`。
       ⛔ 是去匹配整行——那样改一个字节就变成「找⛔ 到」，探针会打在空气上（这条踩过）。"""
    idx = src.find("401")
    while idx >= 0:
        head = src.rfind("return json(", 0, idx)
        if head >= 0:
            brace = src.find("{", head)
            if 0 <= brace < idx:
                end = _match_pair(src, brace, "{", "}")
                if end > 0 and end < idx:
                    return src[brace:end + 1], ""
        idx = src.find("401", idx + 1)
    return None, "源码里找⛔ 到那发 401"


# ---------------- 每条一个 checker：签名 (src, exp) -> (True/False/None, 现算读数) ----------------

def w1(src, exp):
    body, _s, _e = _scope(src, FN_AUTH)
    if body is None:
        return None, "找⛔ 到 authorized()"
    got = _first_stmt(body)
    return got == exp["first_stmt"], f"首行={got}"


def w2(src, exp):
    n = src.count(JSON_HELPER)
    return n == exp["count"], f"json() 里 null,2 缩进出现 {n} 次"


def w3(src, exp):
    lit, why = _forty_one_body(src)
    if lit is None:
        return None, why
    pairs = _obj_pairs(lit)
    if pairs is None:
        return None, "401 的对象字面量切不出来"
    vals = [_str_value(v) for _k, v in pairs]
    if any(v is None for v in vals):
        return None, "401 的键值里有很⛔ 是字符串字面量的东西 ⇒ 数⛔ 了长度"
    n = _stringify_len([(k, v) for (k, _o), v in zip(pairs, vals)])
    return n == exp["body_bytes"], f"正文={n} B（键 {len(pairs)} 个，indent=2）"


def w4(src, exp):
    body, _s, _e = _scope(src, SELFTEST_OPEN)
    if body is None:
        return None, "找⛔ 到 /selftest 分支"
    n = body.count(exp["must_absent"])
    return n == 0, f"/selftest 分支里 {exp['must_absent']!s} 出现 {n} 次"


def w5(src, exp):
    body, _s, _e = _scope(src, SELFTEST_OPEN)
    if body is None:
        return None, "找⛔ 到 /selftest 分支"
    n = src.count(AMY_KEY)
    in_scope = AMY_KEY in body
    ok = n == exp["file_count"] and in_scope is exp["in_selftest"]
    return ok, f"写死的 {AMY_KEY!s} 全仓 {n} 处，落在 /selftest 分支里={in_scope}"


def w6(src, exp):
    body, _s, _e = _scope(src, FN_TO_PROPS)
    if body is None:
        return None, "找⛔ 到 toProperties()"
    lit, why = _returned_object(body)
    if lit is None:
        return None, why
    pairs = _obj_pairs(lit)
    if pairs is None:
        return None, "toProperties 的键切不出来"
    got = [k for k, _v in pairs]
    return got == exp["keys"], f"{len(got)} 个键={got}"


def w7(src, exp):
    body, _s, _e = _scope(src, FN_TO_PROPS)
    if body is None:
        return None, "找⛔ 到 toProperties()"
    lit, why = _returned_object(body)
    if lit is None:
        return None, why
    pairs = _obj_pairs(lit)
    if pairs is None:
        return None, "键切不出来"
    labels = dict(pairs).get(exp["key"])
    if labels is None:
        return None, f"找⛔ 到 {exp['key']!s} 这个键"
    needle = f".slice(0, {exp['cap']})"
    n_keys = len(pairs)
    hit = needle in labels
    return hit and n_keys == exp["key_count"], f"{exp['key']} 含 {needle}={hit}，键数={n_keys}"


def w8(src, exp):
    needles = (SINCE_TERNARY, SINCE_GUARD)
    n = len([s for s in needles if s in src])
    return n == exp["count"] == len(needles), f"地雷两处锚点在场 {n}/{len(needles)}"


def w9(src, exp):
    at = src.find(SINCE_CMP)
    if at < 0:
        return None, "找⛔ 到那句时间戳比较"
    tail = src[at + len(SINCE_CMP):at + len(SINCE_CMP) + 24].lstrip()
    op = ""
    for c in tail:
        if c in "<=>!":
            op += c
        else:
            break
    return op == exp["operator"], f"比较符={op or '(读不到)'}"


def w10(src, exp):
    items, why = _required_config(src)
    if items is None:
        return None, why
    return items == exp["names"], f"{len(items)} 项={items}"


def w11(src, exp):
    items, why = _required_config(src)
    if items is None:
        return None, why
    hit = exp["absent_item"] in items
    return hit is False, f"{exp['absent_item']!s} 在 REQUIRED_CONFIG 里={hit}"


def _required_config(src):
    at = src.find(REQUIRED_OPEN)
    if at < 0:
        return None, "找⛔ 到 REQUIRED_CONFIG"
    semi = src.find(";", at)
    if semi < 0:
        return None, "REQUIRED_CONFIG 那行读⛔ 到结尾"
    return _array_items(src[at:semi]), ""


def w12(src, exp):
    run_body, run_start, _run_end = _scope(src, FN_RUN_SYNC)
    if run_body is None:
        return None, "找⛔ 到 runSync()"
    inner, dry_start, _dry_end = _scope(run_body, DRYRUN_OPEN)
    if inner is None:
        return None, "找⛔ 到 dryRun 分支"
    bump = run_body.find(FAILED_BUMP)
    if bump < 0:
        return None, "找⛔ 到 failed 计数那行"
    has_cont = CONTINUE in inner
    order = dry_start < bump
    ok = has_cont and order is exp["dryrun_before_counter"]
    a = _line_of(src, run_start + dry_start)
    b = _line_of(src, run_start + bump)
    return ok, f"dryRun 短路 continue={has_cont}，短路在计数之前={order}（读数 L{a} 早于 L{b}）"


def w13(src, exp):
    caps = (f"if (preview.length < {exp['cap']})", f"if (summary.errors.length < {exp['cap']})")
    n = len([s for s in caps if s in src])
    return n == len(caps), f"两处封顶 <{exp['cap']} 都在场 {n}/{len(caps)}"


def w14(src, exp):
    lists, parsed = _all_endpoints(src)
    if not parsed:
        return None, "endpoints 数组切不出来"
    if len(lists) != exp["count"]:
        return False, f"门牌数组读到 {len(lists)} 处，登记 {exp['count']} 处"
    leaked = [i for i, items in enumerate(lists) if any(exp["absent"] in s for s in items)]
    return not leaked, f"{len(lists)} 处门牌={lists}，点了 {exp['absent']!s} 的处={leaked}"


def w15(src, exp):
    body, _s, _e = _scope(src, HEALTH_OPEN)
    if body is None:
        return None, "找⛔ 到 /health 分支"
    n = body.count(exp["literal"])
    return n == exp["count"], f"/health 分支里 {exp['literal']!s} 出现 {n} 次"


# (规则号, 墙上那句, checker, 探针(锚点 ⇒ 改成什么；锚点必须全文件唯一))
# 期望值⛔ 写在这里——它们住在 drift/worker_contract.json，配对由 pairing() 管。
RULES = [
    ("W1", "横幅第 6 条①：`authorized()` 第一行是「没配 SYNC_TOKEN 就放行」⇒ 哪天这把锁被删，`/sync` 静默从 401 变全开放",
     w1, (AUTH_DEFAULT_OPEN, AUTH_DEFAULT_CLOSE)),
    ("W2", "401 正文那个字节数由 `json()` 里的 `null, 2` 决定；缩进一改，墙上那个数当场作废",
     w2, (JSON_HELPER, "JSON.stringify(body, null, 1)")),
    ("W3", "横幅第 6 条②：401 正文＝29 B（旧值 26 已更正，那句给的是算式而⛔ 读数）",
     w3, (UNAUTH_BODY, UNAUTH_BODY_MUT)),
    ("W4", "横幅第 7 条：`/selftest` 绕开 `authorized()` ⇒ 用它永远验不到「带密码放得进」",
     w4, (SELFTEST_OPEN, SELFTEST_OPEN + "\n      if (!authorized(request, env)) return json({ error: \"nope\" }, 401);")),
    ("W5", "横幅第 7 条后半：`teamKey` 是写死的 AMY ⇒ `/selftest` 只自证一支，⛔ 当任意 teamKey 的同步能力证明",
     w5, (AMY_KEY, AMY_KEY_MUT)),
    ("W6", "横幅第 11 条：`toProperties()` 交回 9 个键（本文曾有 4 处写「10 个字段」）",
     w6, (URL_LINE, "")),
    ("W7", "横幅第 11 条那句「起因推断」：`Labels` 的 `.slice(0, 10)` 是每条最多 10 个标签、⛔ 是字段数 ⇒ 9 与 10 同时钉住才钉得住那句",
     w7, (LABELS_SLICE, LABELS_SLICE_MUT)),
    ("W8", "「不带 `since` 就是全量覆盖」那枚地雷：取不到值时给 NaN，守卫用 `!Number.isNaN` 把过滤整条短路",
     w8, (SINCE_GUARD, SINCE_GUARD_FLIP)),
    ("W9", "格 I② 定稿：命中口径是**严格大于**（`<=` 即跳过）⇒ 恰好等于 `since` 的那一行被挡在门外",
     w9, (SINCE_CMP_LE, SINCE_CMP_LT)),
    ("W10", "闸门 3「配置在场」看的就是 `REQUIRED_CONFIG` 这份名单",
     w10, (REQUIRED_3, REQUIRED_4)),
    ("W11", "承上：`SYNC_TOKEN` ⛔ 在这份名单里 ⇒ 锁被删时 `/health` 照样报 `missingConfig: []`",
     w11, (REQUIRED_3, REQUIRED_4)),
    ("W12", "「dryRun 下 `errors:[]` 与 `failed:0` 是结构性常量」：dryRun 分支在 try/计数**之前**就 continue",
     w12, (PREVIEW_PUSH + "\n      continue;", PREVIEW_PUSH)),
    ("W13", "`preview` 与 `errors` 各自封顶 5 ⇒ 墙上那发 `fetched:7 / previewCount:5` 里的 5 是上限⛔ 是总数",
     w13, (PREVIEW_OPEN, "if (preview.length < 6)")),
    ("W14", "`/selftest` ⛔ 在门牌上：`/` 与 404 两处 `endpoints` 都⛔ 列它（列了就是把无鉴权触发器指给扫描器）",
     w14, (ENDPOINTS_2, ENDPOINTS_LEAK)),
    ("W15", "`/health` 的 `ok` 是写死的 true ⇒「health 一切正常」⛔ 能证明配置在场，得看 `missingConfig` 那个数组",
     w15, (HEALTH_OK, HEALTH_OK_COMputed)),
]

READINGS = [
    ("toProperties() 起于", FN_TO_PROPS),
    ("since 守卫在", SINCE_CMP),
    ("authorized() 起于", FN_AUTH),
    ("默认放行那行在", "if (!env.SYNC_TOKEN) return true;"),
    ("/selftest 分支在", SELFTEST_OPEN),
    ("REQUIRED_CONFIG 在", REQUIRED_OPEN),
]


def load_contract(root):
    path = os.path.join(root, CONTRACT_REL)
    try:
        text = _read_text(path)
    except OSError as e:
        return None, f"契约件读不到（{type(e).__name__}: {path}）"
    try:
        return json.loads(text), None
    except ValueError as e:
        return None, f"契约件⛔ 是合法 JSON（{type(e).__name__}）"


def load_source(root, contract):
    rel = (contract or {}).get("source", {}).get("path", "src/index.js")
    path = os.path.join(root, rel.replace("/", os.sep))
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        return None, None, rel, f"源码读不到（{type(e).__name__}: {path}）"
    return data.decode("utf-8", "replace"), data, rel, None


def pairing(rules, expect):
    """规则表与契约里的期望必须一一对上——同 `verify_all.py` 那条底线配对的道理：
       有规则没配期望 ⇒ 它拿空 dict 去比，永远「⛔ 等」或永远蒙混；有期望没配规则 ⇒ 那条断言被摘走了。"""
    want = [rid for rid, _c, _f, _p in rules]
    have = list(expect or {})
    out = []
    for rid in want:
        if rid not in have:
            out.append(f"{rid} 在规则表里，契约里却⛔ 它的期望 ⇒ 这条没法判")
    for rid in have:
        if rid not in want:
            out.append(f"契约里留着 {rid} 的期望，规则表里⛔ 这一条 ⇒ 有断言被摘走了")
    return out


def self_test(src, expect, rules):
    """每条一发「它必然响」：把锚点改掉再跑同一条 checker，仍报绿 ⇒ 这条是瞎的。
       顺带查锚点唯一性：needle 出现⛔ 止一次 ⇒ 那发红⛔ 能归到这条头上（第 47 条的绑行号同款坑）。"""
    print("=== 量具自检（它⛔ 绿 ⇒ 下面所有读数一律记『没测到』）===")
    bad = []
    for rid, _claim, fn, (needle, replacement) in rules:
        n = src.count(needle)
        if n != 1:
            print(f"  FAIL {rid} 探针锚点出现 {n} 次（⛔ 止一次）⇒ 注入的那发红⛔ 能归给它")
            bad.append(rid)
            continue
        ok, obs = fn(src.replace(needle, replacement, 1), expect.get(rid, {}))
        fired = ok is False
        print(f"  {'PASS' if fired else 'FAIL'} {rid} 注入后转红={fired}（现算={obs[:110]}）")
        if not fired:
            bad.append(rid)
    return bad


def evaluate(src, expect, rules, only=None, show_readings=True):
    """跑自检＋全部规则 ⇒ (退出码, 红的编号, 判不了的编号)。⛔ 管契约作废那件事（在 main 里）。"""
    blind = self_test(src, expect, rules)
    if blind:
        print(f"  ⚪ 量具自检：{len(blind)} 条瞎掉，或探针锚点⛔ 唯一 ⇒ 那几条报的数一律⛔ 算结论")
        return 2, [], blind
    print(f"\n=== 现算（共 {len(rules)} 条；登记＝应当等于什么）===")
    bad, cant = [], []
    for rid, claim, fn, _probe in rules:
        if only and rid != only:
            continue
        ok, obs = fn(src, expect[rid])
        tag = "🟢" if ok is True else ("🔴" if ok is False else "⚪")
        if ok is None:
            cant.append(rid)
        elif ok is False:
            bad.append(rid)
        print(f"  {tag} {rid} 现算={obs[:160]}")
        print(f"       登记={json.dumps(expect[rid], ensure_ascii=False)[:160]}")
        if only:
            print(f"       墙上那句={claim}")
    if show_readings and not only:
        print("\n=== 行号读数（⛔ 参与判定；墙面上那些「第 N 行」拿这一段现算复核，第 14 条②）===")
        for label, needle in READINGS:
            at = src.find(needle)
            print(f"  {label} L{_line_of(src, at) if at >= 0 else '(读不到)'}")
    if cant:
        print(f"  ⚪ 有 {len(cant)} 条要看的锚点根本⛔ 在（{', '.join(cant)}）⇒ 量具对不上代码")
        return 2, bad, cant
    if bad:
        print(f"  🔴 有 {len(bad)} 条⛔ 等（{', '.join(bad)}）")
        return 1, bad, cant
    return 0, bad, cant


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = DEFAULT_ROOT
    if "--root" in argv:
        root = os.path.abspath(argv[argv.index("--root") + 1])
    only = argv[argv.index("--only") + 1] if "--only" in argv else None

    contract, err = load_contract(root)
    if err:
        print(f"{err} ⇒ 第四道闸⛔ 能开，exit 2")
        return 2
    if contract.get("worker_contract_min_version") != CONTRACT_REVISION:
        print(f"契约登记的检测器版本={contract.get('worker_contract_min_version')!s}，本件={CONTRACT_REVISION}"
              " ⇒ 两侧必须同改（两文件原子闸），exit 2")
        return 2
    expect = contract.get("expect", {})
    probs = pairing(RULES, expect)
    if probs:
        print("⛔ 规则表与契约⛔ 配对（量具坏，先修这个再谈绿）：")
        for p in probs:
            print("   " + p)
        return 2

    src, data, rel, err = load_source(root, contract)
    if err:
        print(f"{err} ⇒ exit 2")
        return 2
    digest = _digest(data)
    source = contract.get("source", {})
    pin = f"{source.get('sha256_of_bytes')!s}"
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    print(f"根={root} 源码={rel} 字节={len(data)}")
    print(f"这份字节现算 sha256={digest[:16]}… ／契约钉的={pin[:16]}…")
    print(f"登记的 git 对象号（**展示用**，本件⛔ 重算 SHA-1、⛔ 联网）={source.get('blob_sha1')!s}")
    print(f"契约 owner={contract.get('owner')!s} review_by={contract.get('review_by')!s} 今日={today}")

    # 契约作废先判：源码一动就对不上钉的那份 ⇒ 下面这批 checker 的"我有没有瞎"是对着**旧代码**校准的，
    # 它报什么都不算结论。所以这一档拿 exit 2，规则读数只当**顺带诊断**打出来给人看是哪几条塌了。
    if digest != pin or len(data) != source.get("bytes"):
        print("⚠️ 源码与契约钉的那份⛔ 同 ⇒ 契约作废：重新看一眼，⛔ 改契约里的登记、或⛔ 改回代码。")
        print("\n=== 顺带诊断（⛔ 作数，量具是对着另一份代码校准的）===")
        evaluate(src, expect, RULES, only)
        print("\n=== 判定 ===\n  ⛔ 绿：契约作废（源码动过）⇒ exit 2")
        return 2

    code, bad, _cant = evaluate(src, expect, RULES, only)
    if code == 2:
        print("\n=== 判定 ===\n  ⛔ 绿：量具坏（自检或锚点）⇒ 它报的 0 一律⛔ 算结论，exit 2")
        return 2
    if bad:
        print(f"\n=== 判定 ===\n  🔴 有 {len(bad)} 条⛔ 等 ⇒ 登记与代码对不上（改代码必须重新登记，"
              "而重新登记＝一次看得见的动作：本仓⛔ 带自动重算登记的工具）⇒ exit 1")
        return 1
    if contract.get("review_by") and contract["review_by"] < today:
        print(f"\n=== 判定 ===\n  🔴 契约 review_by={contract['review_by']} 已过期（owner={contract.get('owner')!s}）"
              "⇒ 重新看一眼，改期或删契约都算答复，exit 1")
        return 1
    print(f"\n=== 判定 ===\n  绿：{len(RULES)} 条全等，且这份源码与契约钉的那份逐字节相同（sha256 {digest[:12]}…）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
