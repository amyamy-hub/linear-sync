#!/usr/bin/env python3
"""linear-sync 漂移检测：**全程只读**，不部署、不写任何远端资源。

用法（需要一把能读 Workers 的凭据，⛔ 不要写进文件）：
    export CLOUDFLARE_API_TOKEN=...      # 建议：作用域限到本 Worker 的 Editor/Metadata Read-Only
    python3 tools/drift_check.py [--ledger drift/known_good.json]

退出码：0 = 无漂移；1 = 发现漂移或未登记变更；2 = 检测器自身跑不动（凭据/网络/字段）。
设计要点（都是踩出来的）：
  * ⛔ 不要用 GET /workers/scripts/{name} 判"线上是什么"——它返回**最后一次上传**的产物，
    不是**正在服务**的那一份。必须先取 deployments[0].versions[0].version_id，再读那个版本。
  * etag 在 versions/{id} 的 resources.script.etag；绑定在 resources.bindings。
  * 有"上传了但没部署"的版本时，字节级判据不可用 ⇒ 本脚本会单独报这一条，而不是误报"线上≠仓库"。
  * ⭐ 09-28 现读：CF 的 `/download` 回 **multipart 打包件** ⇒ 整包 etag / 整包字节永⛔ 能证「线上==仓库」，必须解包取源块算 git blob SHA-1（闸门 2c）。
  * ⚠️ 两个列表端点**都只回一页**，默认 10 条封顶 ⇒ 一律带 per_page=100，并在页满时明说"可能还有"。
  * ⭐ 09-24 修掉的盲区：旧版只把**最新版**与服务版本比 ⇒ 一旦再来一次合法部署，
    旧的未部署版本就**从告警里消失**（不是被拆雷，是探测器看不见了）。现在扫**全集**，
    并与所有 deployments 里出现过的 version_id 求差集。豁免走 ledger 的
    `known_undeployed_versions`（按 id 前缀匹配 + kept_intentionally=true），⛔ 不靠"看不见"来消音。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date

# 本机是 GBK 控制台，中文/emoji 会直接把 print 炸掉（实测），所以强制 UTF-8 输出。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

API = "https://api.cloudflare.com/client/v4"
PER_PAGE = 100
MAX_DETAIL_GETS = 10   # 未部署版本可能很多，逐个取详情会打爆请求数
# 能力戳：09-26 起改成**同版才算数**。旧写法 `req > TOOL_REVISION` 在 req == TOOL_REVISION 时
# 恒不触发——现读实测今天就是恒不响（登记的 min_version 与脚本 revision 逐字符相等）。
# ⚠️ 串比较⛔ 等于日历序：非零填充（2026-9-26）跨月那侧会把"更新的要求"判成"不更新"⇒ 静默放行。
# ⇒ 先校验格式，再要求两侧完全相等，任一方向不一致都拒跑。
TOOL_REVISION = "2026-09-28-multipart-source-blob"
REV_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def get_raw(path, token):
    """只读取裸字节（/download 用）。返回 (bytes 或 None, 错误说明)。
    ⚠️ 取不到产物字节属于"没测到"，⛔ 走 fail()——那会把"我这侧没读到"上报成"检测器跑不动"。"""
    req = urllib.request.Request(API + path, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read(), None
    except urllib.error.HTTPError as e:
        return None, "HTTP %s" % e.code
    except (urllib.error.URLError, OSError) as e:
        return None, "%s: %s" % (type(e).__name__, str(e)[:100])


def _git_blob_sha1(data):
    """git 的对象号**就是** SHA-1 内容寻址（⛔ 安全用途），照 git 的定义算：sha1("blob "+字节数+"\0"+字节)。
    ⚠️ 这一行上**两套规则都在跑**（09-28 在同文件另放一处⛔ 受豁免的 SHA-1 现证）：**Opengrep**（Semgrep 分支）
       按两个 pattern 各报一条（…insecure-hash-algorithm-sha1 与 Semgrep_python_crypto_rule-hash-sha1），它们⛔ 认
       `# nosec`、也⛔ 被 `usedforsecurity=False` 挡；**bandit 的 B324** 也在场，本行是被那两个一起压住的。
       ⇒ 门禁"新增 issue = 0"在这行⛔ 有绕的写法：那两条已逐条 Ignore＋写理由（登记＝横幅 44、执行＝46），而该豁免
       绑在实例上、⛔ durable（第 47 条五发读数）。反证⛔ 一起被豁免：这行算错，24 条故障注入＋变异用例当场就红。
    ⚠️ 手工算时 `blob %d\0` 那三个字节⛔ 能省：省了就⛔ 是 git 的对象号（同一份 10,860 B 源码，正确包裹＝`3a698aff59f5…`）。"""
    payload = b"blob %d\0" % len(data) + data
    return hashlib.sha1(payload, usedforsecurity=False).hexdigest(), None  # nosec B324  # 内容寻址，非安全用途


def source_blob_from_multipart(data):
    """CF 的 /download 回的是 **multipart 打包件**（09-28 现读：整包 11,043 B，内含 name="index.js" 那块 10,860 B）。
    ⇒ 整包 etag / 整包字节都⛔ 能代表源文件，"拿整份 /download 字节算 blob"这种写法结构上永⛔ 成立。
    这里取入口脚本那一块，算它的 **git blob SHA-1**。返回 (sha1 或 None, 这块的来历描述)。"""
    if not data or not data.startswith(b"--"):
        return None, "返回体⛔ 是 multipart 形态（前 2 字节=%r）⇒ 取法要改，这一项记「没测到」" % (data[:2] if data else b"")
    try:
        boundary = data[2:data.index(b"\r\n")].decode("utf-8", "replace")
    except ValueError:
        return None, "multipart 头部读不出边界 ⇒ 记「没测到」"
    cand = []
    for part in data.split(b"--" + boundary.encode()):
        if part.startswith(b"--"):
            continue
        if part.startswith(b"\r\n"):
            part = part[2:]
        if part.endswith(b"\r\n"):
            part = part[:-2]
        if not part:
            continue
        idx = part.find(b"\r\n\r\n")
        if idx < 0:
            continue
        head = part[:idx].decode("utf-8", "replace")
        body = part[idx + 4:]
        m = re.search(r'name="([^"]+)"', head)
        nm = m.group(1) if m else "?"
        is_js = (nm.endswith(".js") or "javascript" in head.lower())
        sh, sherr = _git_blob_sha1(body)
        if sherr:
            return None, sherr
        cand.append((nm, len(body), sh, is_js))
    if not cand:
        return None, "multipart 里解不出任何块 ⇒ 记「没测到」（⛔ 当成「线上没有源文件」）"
    chosen = [c for c in cand if c[3]] or cand
    chosen.sort(key=lambda c: -c[1])
    best = chosen[0]
    return best[2], "块 name=%s %d B（共 %d 块：%s）" % (
        best[0], best[1], len(cand), ", ".join("%s/%dB" % (c[0], c[1]) for c in cand))


def fail(msg):
    print("❌ 检测器跑不动：%s" % msg)
    sys.exit(2)


def get(path, token):
    req = urllib.request.Request(API + path, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            d = json.loads(body)
        except Exception:
            fail("HTTP %s 非 JSON：%s" % (e.code, body[:120]))
        if e.code in (401, 403):
            fail("凭据不足（HTTP %s）：%s" % (e.code, json.dumps(d.get("errors"), ensure_ascii=False)[:160]))
        fail("HTTP %s：%s" % (e.code, json.dumps(d.get("errors"), ensure_ascii=False)[:160]))
    except Exception as e:
        fail("请求失败 %s: %s" % (type(e).__name__, str(e)[:140]))


def listed_prefixes(ledger):
    """豁免必须**可到期、有 owner**：缺失／格式非法／已过期 ⇒ 拒跑，⛔ 降级成告警。
    09-26 起因：现读登记里那条 #10 的豁免只有 kept_intentionally 一个布尔，无 expires、无 owner，
    而本函数当年是 `if e.get("kept_intentionally")` ⇒ 永久且无主的豁免＝把「灯灭」制度化。"""
    out = []
    today = date.today().isoformat()
    for e in ledger.get("known_undeployed_versions") or []:
        if not e.get("kept_intentionally"):
            continue
        vid = (e.get("version_id_prefix") or "").strip()
        owner = (e.get("owner") or "").strip()
        rb = (e.get("review_by") or "").strip()
        if not vid:
            fail("豁免条目缺 version_id_prefix ⇒ ⛔ 知道它挡的是哪一条，等于没挡")
        if not owner:
            fail("豁免 %s 无 owner ⇒ 永久且无主的豁免就是把「灯灭」常态化，拒跑" % vid)
        if not DATE_RE.match(rb):
            fail("豁免 %s 的 review_by=%r 不是 YYYY-MM-DD ⇒ 拒跑（⛔ 静默当成永不过期）" % (vid, rb))
        if rb < today:
            fail("豁免 %s 已于 %s 到期（owner=%s）⇒ 拒跑。要么重新复核后推 review_by，要么撤掉豁免让告警亮" % (vid, rb, owner))
        out.append(vid)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=os.path.join(os.path.dirname(__file__), os.pardir, "drift", "known_good.json"))
    ap.add_argument("--expect-blob", default="",
                    help="仓库里那份源码的 git blob SHA-1（由调用方用 gh api / git hash-object --no-filters 现取）。⛔ 传 ⇒ 闸门 2c 只算源块、⛔ 对撞，并记「没测到」")
    a = ap.parse_args()
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token:
        fail("环境变量 CLOUDFLARE_API_TOKEN 未设")
    try:
        led = json.load(open(a.ledger, encoding="utf-8"))
    except Exception as e:
        fail("读不了登记文件 %s：%s" % (a.ledger, e))
    acct, name = led["account_id"], led["worker"]
    drift = []
    unverified = []   # ⭐ 09-28 起：“没测到”必须单独记一条，终判语必须引用它，⛔ 让它混进“无漂移”

    req = led.get("detector_min_version")
    if req is None:
        fail("登记里没有 detector_min_version ⇒ 无法确认这份登记是为哪一版检测器写的，拒跑")
    if not REV_RE.match(str(req)):
        fail("登记的 detector_min_version=%r 格式非法（要 YYYY-MM-DD-…）⇒ ⛔ 按字符串比会静默放行" % (req,))
    if not REV_RE.match(TOOL_REVISION):
        fail("本脚本 TOOL_REVISION=%r 自己就不合规 ⇒ 比较无意义" % (TOOL_REVISION,))
    if str(req) != TOOL_REVISION:
        fail("登记要求 %r，本脚本是 %r ⇒ 任一方向不一致都拒跑。"
             "改检测器与改登记是**两文件原子动作**，漏一个就是自锁死或假绿灯。"
             % (req, TOOL_REVISION))

    dep = get("/accounts/%s/workers/scripts/%s/deployments?per_page=%d" % (acct, name, PER_PAGE), token)
    deps = (dep.get("result") or {}).get("deployments") or []
    if not deps:
        fail("没有任何 deployment，线上根本没部署过？")
    ri = dep.get("result_info") or {}
    if ri.get("total_count") is None:
        unverified.append("deployments 信封缺 total_count（本页 %d，per_page=%d）⇒ “这就是全部 deployment”没测到（09-28 现读：该端点正常是**带** result_info 的，缺 ⇒ 形态变了，⛔ 静默当成完整）" % (len(deps), PER_PAGE))
    ri = dep.get("result_info") or {}
    if ri.get("total_count") is not None and ri["total_count"] != len(deps):
        drift.append("deployments 没拉全：本页 %d，信封 total_count=%s ⇒ 未部署扫描可能不全" % (len(deps), ri["total_count"]))
    if len(deps) >= PER_PAGE:
        print("  ⚠️ deployments 取满 %d 条 ⇒ 必须翻页。顶层 result_info.total_count=%s"
              "（09-26 现读更正：该字段在**信封顶层**，⛔ 在 result 里——旧注释说它不存在是错的）"
              % (PER_PAGE, ri.get("total_count")))
    d0 = deps[0]
    versions = d0.get("versions") or []
    if not versions:
        fail("deployments[0] 里没有 versions 字段，取法要改")
    serving = versions[0]["version_id"]
    percent = versions[0].get("percent", versions[0].get("percentage"))
    print("· 正在服务的版本 : %s (%s%%)  来自 deployment %s @ %s  source=%s"
          % (serving, percent if percent is not None else "?", (d0.get("id") or "")[:8], d0.get("created_on"), d0.get("source")))
    if len(versions) > 1:
        print("  ⚠️ 这次部署是**分流**的，共 %d 个版本，逐条比对本脚本未覆盖，请人工看" % len(versions))

    # 所有 deployments 里出现过的版本 = 曾经被切过流量的那些（⛔ 只看 deployments[0]）
    deployed = set()
    for d in deps:
        for v in (d.get("versions") or []):
            if v.get("version_id"):
                deployed.add(v["version_id"])
    print("· deployment 条数 : %d（覆盖版本 %d 个）" % (len(deps), len(deployed)))

    ver = get("/accounts/%s/workers/scripts/%s/versions/%s" % (acct, name, serving), token)
    res = (ver.get("result") or {}).get("resources") or {}
    etag = ((res.get("script") or {}).get("etag")) or ""
    binds = sorted("%s:%s" % (b.get("type"), b.get("name")) for b in (res.get("bindings") or []))
    print("· 产物 etag      : %s…" % etag[:16])
    print("· 绑定           : %s" % (", ".join(binds) or "(无)"))
    # 闸门 2b：/download 给的是【脚本槽位当前内容】，不是【服务版本】的内容。
    # 只有槽位 etag == 服务版本 etag 时，那份字节才代表线上。09-24 的 #10 是反例：
    # 上传未部署却占住槽位、被之后每次 dashboard 保存继承，线上跑了 1.5 小时打包件。
    slot_ok = False
    slot = get("/accounts/%s/workers/scripts" % (acct,), token)
    slot_rows = slot.get("result") or []
    if isinstance(slot_rows, dict):
        slot_rows = slot_rows.get("scripts") or []
    slot_row = next((s for s in slot_rows if s.get("id") == name), None)
    if slot_row is None:
        drift.append("scripts 列表里找不到该 Worker 槽位 => 槽位 etag 没测到（⛔ 当成「没有」）")
    else:
        slot_etag = slot_row.get("etag") or ""
        print("· 槽位 etag      : %s…" % slot_etag[:16])
        if not slot_etag:
            drift.append("槽位记录里没有 etag 字段 => 字节判据此刻不可用；没测到 ≠ 没有")
        elif slot_etag == etag:
            slot_ok = True
        elif slot_etag != etag:
            drift.append("槽位 etag(%s…) ≠ 服务版本 etag(%s…) => /download 回的是最后一次上传，"
                         "⛔ 用它下「线上==仓库」的判；本轮那条字节比对结论作废"
                         % (slot_etag[:8], etag[:8]))

    # ⭐ 闸门 2c（09-28 新增）：etag 相等只证「槽位 == 服务版本」，⛔ 证「线上 == 仓库」。
    # 要证后者必须把 /download 的**打包件拆开**、取入口脚本那块、算 git blob SHA-1，再与仓库那份对撞。
    # 现读实物：整包 11,043 B、内含 name="index.js" 那块 10,860 B，那块逐字节等于主干 src/index.js（blob 3a698aff…）。
    if slot_ok:
        dl, derr = get_raw("/accounts/%s/workers/scripts/%s/download?version_id=%s" % (acct, name, serving), token)
        if derr:
            unverified.append("产物字节取不到（%s）⇒「线上==仓库」这格记**没测到**" % derr)
        else:
            got, desc = source_blob_from_multipart(dl)
            if not got:
                unverified.append("源块解不出来：%s ⇒「线上==仓库」记**没测到**" % desc)
            else:
                print("\u00b7 源块 blob      : %s  <- %s" % (got[:16], desc))
                want = (a.expect_blob or "").strip().lower()
                if not want:
                    unverified.append("⛔ 传 --expect-blob ⇒ 源块只算出来、⛔ 对撞（有读数 ≠ 已验证）")
                elif got != want:
                    drift.append("线上服务版本的源块 blob=%s ≠ 仓库传入 blob=%s ⇒ **线上⛔ 等于仓库**"
                                 % (got[:16], want[:16]))
                else:
                    print("  ✅ 源块 blob == 仓库那份 ⇒ 线上 == 仓库（现证，⛔ 靠登记值）")
    else:
        unverified.append("闸门 2b 未放行（槽位 etag 取不到，或与版本 etag 不等）⇒ 2c 跳过，字节判据此刻不可用；"
                          "具体原因见上面那条漂移，⛔ 把这次读成「已核对」")

    if etag != led["artifact_etag"]:
        drift.append("etag 与登记值不同 ⇒ 线上产物不是登记过的那一份")
    if binds != sorted(led["expected_bindings"]):
        add = [b for b in binds if b not in led["expected_bindings"]]
        rem = [b for b in led["expected_bindings"] if b not in binds]
        drift.append("绑定集合与登记值不同：多=%s 缺=%s" % (add or "无", rem or "无"))
    if serving != led["serving_version_id"]:
        print("  ℹ️ 版本 id 与登记值不同（正常轮换会这样），以 etag 为准判内容是否一致")

    vs = get("/accounts/%s/workers/scripts/%s/versions?per_page=%d" % (acct, name, PER_PAGE), token)
    items = (vs.get("result") or {}).get("items") or []
    if not items:
        drift.append("拿不到 versions 列表 ⇒「未部署上传」这一项根本没测到，⛔ 允许它混进一次\"无漂移\"")
    else:
        ri2 = vs.get("result_info") or {}
        if ri2.get("total_count") is None:
            unverified.append("versions 信封缺 total_count（本页 %d，per_page=%d）⇒ 无法证明这一页就是全部版本；「未部署扫描完整」这一项记**没测到**（minimax 第 1 段挑出：原先这里与下面“取满”两道闸会同时静默）"  % (len(items), PER_PAGE))
        ri2 = vs.get("result_info") or {}
        if ri2.get("total_count") is not None and ri2["total_count"] != len(items):
            drift.append("versions 没拉全：本页 %d，信封 total_count=%s ⇒ 未部署扫描不完整，⛔ 报无漂移"
                         "（09-26 补：这里原先只 print 一行警告就走，与 deployments 那侧不对称——由 codacy Bot 在 PR #5 挑出）"
                         % (len(items), ri2["total_count"]))
        if len(items) >= PER_PAGE:
            drift.append("versions 取满 %d 条 ⇒ 必须翻页，未部署扫描可能漏掉更早的版本" % PER_PAGE)
        newest = items[0]
        nm = (newest.get("metadata") or {})
        newest_num = newest.get("number") or nm.get("number")
        print("· 最新版本号     : #%s %s  source=%s @ %s  triggered_by=%s"
              % (newest_num, (newest.get("id") or "")[:8], nm.get("source"), nm.get("created_on"),
                 (newest.get("annotations") or {}).get("workers/triggered_by")))

        waived = listed_prefixes(led)
        undeployed = [it for it in items if it.get("id") not in deployed]
        print("· 版本总数 %d，其中**从未进过任何 deployment** 的：%d" % (len(items), len(undeployed)))
        for it in undeployed[:MAX_DETAIL_GETS]:
            vid = it.get("id") or ""
            num = it.get("number") or (it.get("metadata") or {}).get("number")
            src = (it.get("metadata") or {}).get("source")
            if any(vid.startswith(p) for p in waived):
                print("  ℹ️ 未部署版本 #%s %s（source=%s）已在登记里明示「有意保留」⇒ 不报漂移，⛔ 不是没看见"
                      % (num, vid[:8], src))
                continue
            nv = get("/accounts/%s/workers/scripts/%s/versions/%s" % (acct, name, vid), token)
            nres = (nv.get("result") or {}).get("resources") or {}
            netag = ((nres.get("script") or {}).get("etag")) or ""
            nbinds = sorted("%s:%s" % (b.get("type"), b.get("name")) for b in (nres.get("bindings") or []))
            if netag == etag and nbinds == binds:
                print("  ℹ️ 未部署的 #%s %s 与服务版本内容相同（同字节重传），不算漂移" % (num, vid[:8]))
                continue
            drift.append("有一个**未部署且未登记豁免**的版本 #%s（%s，source=%s）与服务版本内容不同（etag%s/绑定%s）"
                         "⇒ 此刻⛔ 不能用字节判据断言线上==仓库；且 ⭐ 它会**占住脚本槽位**，被之后每次 dashboard 保存继承"
                         "（09-24 实测：#10 就是这么让线上跑了 1.5 小时的打包件）。要么盖掉它，要么把它写进 known_undeployed_versions"
                         % (num, vid[:8], src, "相同" if netag == etag else "不同", "相同" if nbinds == binds else "不同"))
        if len(undeployed) > MAX_DETAIL_GETS:
            drift.append("未部署版本 %d 个，超过本脚本逐个核查上限 %d ⇒ 只查了前 %d 个，剩下的没测到"
                         % (len(undeployed), MAX_DETAIL_GETS, MAX_DETAIL_GETS))

    print()
    if drift:
        for d in drift:
            print("⚠️ 漂移：%s" % d)
        print("\n判定：需要人看。登记值见 drift/known_good.json；确认线上正确后**改登记值**而不是忽略告警。")
        sys.exit(1)
    if unverified:
        print("判定：本轮未报漂移，但有 %d 项**没测到**（≠ 已验证）：" % len(unverified))
        for u in unverified:
            print("  · 没测到：%s" % u)
        print("  ⇒ 这些格子⛔ 算通过。要补齐：deployments/versions 信封形态、或带 --expect-blob 现读仓库 blob 再跑。")
    else:
        print("判定：未报漂移，且本轮列出的判据**都取到了读数**（etag / 槽位 etag / 源块 blob 对撞 / 绑定集合 / 未部署版本）。")
    sys.exit(0)


if __name__ == "__main__":
    main()
