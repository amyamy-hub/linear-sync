"""公开面三道机器闸（⛔ 联网、⛔ 要凭据、⛔ 碰线上）。

    py tools/wall_scan.py                 # 跑三道闸；绿=0
    py tools/wall_scan.py --self-test     # 只跑量具自检（每条规则的阳性对照＋一件期望零退出的干净件）
    py tools/wall_scan.py --root <目录>    # 换一棵树跑（反证套件就是这么调它的，⛔ 另开子进程）

为什么这件必须在仓里：横幅第 51 条②登记了三处**我们自己**违反「任何凭据值／前缀／哈希⛔ 进墙」的地方，
第 52 条⑧又登记了同一类错的第二次复发（`ls -l` 打出落盘件字节数）。那些当时靠**人读**才发现
⇒ 现在变成任何人 clone 下来一发就能复算的闸。

三道闸（口径⛔ 一样，别混）：
  闸 A｜明文值形状：整串长得就像一把钥匙（9 条）。**基线＝空**，任何命中都红。
  闸 B｜凭据指纹：⛔ 是整串，但念了「几位」「前缀 xxxx」「xxxx…yyyy」「sha256 前缀 yyyy」，
        再加一条**已烧指纹黑名单**（B5）。只扫给人看的 `*.md`——这类泄漏的载体就是文档。
  闸 C｜落盘指路牌：文档里点到具体文件路径。基线＝内容锚点表。

三条设计约束（都是踩出来的）：
  1. **每条规则先过一发"它必然响"的合成件**，另配一件"期望零退出的干净件"。响⛔ ⇒ 该规则记『没测到』、exit 2。
     （写这件时合成串位数是我手数的，40→38、37→39，那两格的 0 当场⛔ 算结论 ⇒ 位数一律由代码拼。）
  2. **锚点用内容⛔ 用行号**（第 14 条②、第 47 条②(a)：逐条 Ignore 绑行号，代码一插行就漂）。
     锚点读不到 ⇒ exit 2（基线在漂，⛔ 是"变干净了"）。
  3. **基线项自带 `owner` ＋ `review_by`**（第 22 条 b 那套）：过期 ⇒ exit 1，逼下一个人重新看一眼。

退出码：0＝三道闸都过；1＝有新增违规或有登记项过期；2＝量具坏（规则响⛔ 了／锚点漂了／基线件读不到／版本⛔ 一致）。
"""

import datetime
import hashlib
import json
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_REL = os.path.join("drift", "wall_baseline.json")
DOC_EXT = (".md", ".markdown")
TEXT_EXT = (".md", ".markdown", ".py", ".js", ".json", ".toml", ".yml", ".yaml", ".txt")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
MAX_BYTES = 2 * 1024 * 1024
TOOL_REVISION = "2026-09-28-wall-scan-2"

# ---------------- 闸 A｜明文值形状（基线＝空）----------------
SHAPES = [
    ("A1 GitHub PAT", r"\bgh[pousr]_[0-9A-Za-z]{16,}\b"),
    ("A2 Notion 风格令牌", r"\b(?:ntn_[0-9A-Za-z]{6,}|secret_[0-9A-Za-z]{6,}|token_v1_[0-9A-Za-z]{6,})\b"),
    ("A3 JWT", r"\beyJ[0-9A-Za-z_-]{8,}\.[0-9A-Za-z_-]{8,}\.[0-9A-Za-z_-]{6,}\b"),
    ("A4 Bearer 实值", r"(?i)\b(?:bearer|authorization\s*[:=]\s*(?:bearer\s+)?)[ \t]*[0-9A-Za-z_-]{20,}"),
    ("A5 CF 令牌形态", r"\b(?=[0-9A-Za-z_-]{40}\b)(?=[0-9A-Za-z_-]*[-_])[0-9A-Za-z_-]{40}\b"),
    ("A6 base64 带填充", r"\b[0-9A-Za-z+/]{48,}={1,2}(?![0-9A-Za-z+/=])"),
    ("A7 20 位大写加数字", r"\b(?=[0-9A-Z]{20}\b)(?=[0-9A-Z]*[0-9])(?=[0-9A-Z]*[A-Z])[0-9A-Z]{20}\b"),
    ("A8 Linear API 前缀", r"\blin_api_[0-9A-Za-z]{6,}\b"),
    ("A9 37 位十六进制", r"\b[0-9a-f]{37}\b"),
]

# ---------------- 闸 B／C 的规则 ----------------
# ⚠️ ⛔ 用切片拼这些串：上一版 `CTX[3:]` 把 `(?i` 切掉、留下一个野括号，三条规则当场⛔ 能编译——
#    而"规则⛔ 能编译"这件事只有跑合成件才会暴露，所以每条都必须有一发必然响的对照。
CTXW = r"token|令牌|密钥|secret|credential|凭据|apikey|api key|口令|钥匙"
FPRS = [
    # B1：凭据**长度**被念出来，且紧挨着一串字面量。⛔ 用"同行有凭据词"的宽版——那会把
    #     描述规则本身的话（"三十七位十六进制"）也量成泄漏（本仓实测误响 8 处）。
    ("B1 长度声明", (
     r"[0-9]{2,3}\s*(?:位|字符|个字符)\s*(?:hex\s*、\s*前缀\s*`(?P<fp>[0-9A-Za-z]{2,12})`"
     r"|[:：]?\s*`(?P<fp2>[0-9A-Za-z]*[0-9][0-9A-Za-z]{2,})`)")),
    # B2：必须同一行 40 字以内出现"凭据词"才算，否则 Linear 附件 id 的"前缀 xxxx"这类普通标识符
    #     会被量成泄漏（本仓现读就有两处）。⛔ 收紧的代价是漏，是**放宽的代价是这台闸被人关掉**。
    ("B2 前缀字面量", (
     rf"(?:{CTXW})[^\n]{{0,40}}(?:前缀|前 [0-9] 位|两头|前后)[^\`\n]{{0,8}}`(?P<fp>[0-9A-Za-z_]{{3,12}})`")),
    ("B3 两头都念", r"`(?P<fp>[0-9A-Za-z_]{2,12})…(?P<fp2>[0-9A-Za-z_]{2,12})`"),
    # B4：截断哈希。⛔ 能反推值，但能让任何一枚候选值被**离线确认** ⇒ 属「值／前缀／哈希⛔ 进墙」那一项。
    #     这条是本件写完当天自己撞出来的：横幅 52③ 念了"新旧两把的 sha256 前缀"。
    ("B4 凭据的哈希指纹", r"(?:sha256|sha1|哈希)[^\`\n]{0,28}`(?P<fp>[0-9a-fA-F]{6,})`"),
]
PATHS = [
    # ⚠️ C1 词首⛔ 能用 `\b`：`cf_deploy_token.txt` 里 `token` 前面是下划线，那是**单词字符**
    #    ⇒ `\b` ⛔ 成立。第一版就是这么静默⛔ 响的（合成件当场把它抓出来）。
    ("C1 落盘件文件名", (
     r"(?i)[^\s`\|()（）\[\]，,、]*(?:token|secret|passwd|password|credential)"
     r"[^\s`\|()（）\[\]，,、]*\.(?:txt|json|env|pem|key|p12)")),
    # C2：只抓"指路句"——动词＋一个**带扩展名的具体文件**（宽版会把 `落在 ~/.bsk` 这类目录叙述也量进来）。
    ("C2 指路句", (
     r"(?:值的存放|值在|落在|钥匙在|存放在|放在|存在)[^\`\n]{0,16}`?"
     r"(?:%LOCALAPPDATA%\\[^\s`]+|~/[^\s`]*/[^\s`]*\.(?:txt|json|env|key|pem))")),
]


def _mk_probes():
    """合成件：位数由代码拼并现算打印，⛔ 手数。"""
    alpha = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    p = {}
    p["A1 GitHub PAT"] = "ghp_" + "A" * 36
    p["A2 Notion 风格令牌"] = "ntn_" + alpha[:14]
    p["A3 JWT"] = ("eyJ" + "hbGciOiJIUzI1NiJ9" + "." + "eyJzdWIi" + "OiIxMjM0NTY3" + "ODkwIn0" + "." + "d" * 43)
    p["A4 Bearer 实值"] = "Authorization: Bearer " + alpha[:28]
    p["A5 CF 令牌形态"] = "vJEr" + "0" * 34 + "-_"
    p["A6 base64 带填充"] = ("U2VjcmV0UGF5bG9hZFRoYXRJc0xvbmdFbm91Z2hUb0ZsYWdBczZiNjRiYXNlNjQ"
                            + "AAAA") + "=="
    p["A7 20 位大写加数字"] = "ABCDEFGHIJ" + "1234567890"
    p["A8 Linear API 前缀"] = "lin_api_" + "Ab3dEfGhIjKl"
    p["A9 37 位十六进制"] = ("ab3f41c09d7e5a2b8c4d1e6f70a3b5c7d9e1f3a5"
                            "b7c9d2e4f6a8b0c1d3e5f7a9")[:37]
    return p


PROBES_A = _mk_probes()
PROBES_B = {
    "B1 长度声明": "新值 48 位 hex、前缀 `aaaa1111`",
    "B2 前缀字面量": "令牌前缀 `deadbeef`",
    "B3 两头都念": "令牌 `ntn_A…zz9`",
    "B4 凭据的哈希指纹": "两把的 sha256 前缀 `deadbeefcafe` 不同",
}
PROBES_C = {
    # ⚠️ 必须 raw 串：`\notion` 里的 `\n` 在普通串里会被吃成换行 ⇒ 合成件⛔ 再是路径（上一版就这么假失败过）。
    "C1 落盘件文件名": r"本机 `%LOCALAPPDATA%\cf_deploy_token.txt`",
    "C2 指路句": r"值的存放：本机 `%LOCALAPPDATA%\notion_read_key.txt`",
}
CLEAN_TEXT = ("这一行只有普通叙述：blob 915d1f64277a 与 5b2ef41e5af7 两个短号、"
              "30 条断言、L72 那行、2026-09-28 这个日期。\n")


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def load_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            try:
                if os.path.getsize(p) > MAX_BYTES:
                    continue
                data = read_bytes(p)
            except OSError:
                continue
            out.append((os.path.relpath(p, root).replace("\\", "/"), data))
    return out


def hits_for(rules, text):
    """返回 [(规则名, 行号, 该行)]。只报行号与整行，⛔ 把匹配段原样打出去（那可能就是钥匙）。"""
    lines = text.split("\n")
    out = []
    for name, pat in rules:
        rx = re.compile(pat)
        for i, ln in enumerate(lines):
            if rx.search(ln):
                out.append((name, i + 1, ln))
    return out


def forbidden_scan(files, forbidden):
    """B5：已烧指纹黑名单。⛔ 能靠正则解决——"4 位十六进制"与 git 短号在文本上⛔ 可分，
       所以只能拿"我们已知道⛔ 该再出现在 HEAD 上"的具体串去撞。表里存 sha256：
       ⛔ 等于藏住（4 位十六进制可穷举），登记它是为了让"别再出现在 HEAD"这件事可复算。"""
    if not forbidden:
        return []
    want = set(forbidden)
    out = []
    rx = re.compile(r"[0-9A-Za-z_]{3,}")
    for fname, data in files:
        text = data.decode("utf-8", "replace")
        for i, line in enumerate(text.split("\n")):
            for tok in rx.findall(line):
                if hashlib.sha256(tok.encode("utf-8")).hexdigest() in want:
                    out.append(("B5 已烧指纹", fname, i + 1))
                    break
    return out


def self_test(files):
    print("=== 量具自检（先跑；它⛔ 绿，下面所有 0 一律记『没测到』）===")
    bad = []
    for rules, probes in ((SHAPES, PROBES_A), (FPRS, PROBES_B), (PATHS, PROBES_C)):
        for name, pat in rules:
            probe = probes.get(name)
            if probe is None:
                print(f"  FAIL {name} 配了规则却没配合成件")
                bad.append(name)
                continue
            fired = bool(re.search(pat, probe))
            print(f"  {'PASS' if fired else 'FAIL'} {name} 合成件命中={fired}")
            if not fired:
                bad.append(name)
    false_pos = [name for rules in (SHAPES, FPRS, PATHS) for name, pat in rules if re.search(pat, CLEAN_TEXT)]
    print(f"  干净件（期望零退出）被误判的规则={false_pos if false_pos else '无'}")
    bad += false_pos
    real = dict(files).get("HANDOFF.md", b"").decode("utf-8", "replace")
    caught = Counter()
    for name, _lineno, _line in hits_for(FPRS + PATHS, real):
        caught[name] += 1
    need = ("C1 落盘件文件名",)
    miss = [n for n in need if caught[n] == 0]
    print("  真件对照：把墙上现存的指路牌喂给同一套规则 ⇒ " + "、".join(f"{n}={caught[n]}" for n in need))
    if miss:
        print(f"  FAIL 这几条规则在真件上⛔ 响：{miss} ⇒ 它抓不住自己该抓的那一类")
        bad += miss
    return bad


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = DEFAULT_ROOT
    if "--root" in argv:
        root = os.path.abspath(argv[argv.index("--root") + 1])
    files = load_files(root)
    print(f"根={root} 件数={len(files)} 检测器版本戳={TOOL_REVISION}")

    bad = self_test(files)
    if bad:
        print(f"\n判定：⛔ 绿。量具坏 {len(set(bad))} 条 ⇒ 下面所有 0 都⛔ 算结论。")
        return 2
    if "--self-test" in argv:
        print("\n判定：量具自检全绿（--self-test 到此为止）。")
        return 0

    try:
        base = json.loads(read_bytes(os.path.join(root, BASELINE_REL)).decode("utf-8"))
    except (OSError, ValueError) as e:
        print(f"\n判定：⛔ 基线件读不到（{type(e).__name__}）⇒ 三道闸⛔ 能开，exit 2")
        return 2
    if base.get("wall_scan_min_version") != TOOL_REVISION:
        print("\n判定：⛔ 基线件与检测器版本⛔ 一致 ⇒ 两侧必须同改（原子闸），exit 2")
        return 2
    entries = base.get("entries", [])
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()

    print("\n=== 闸 A｜明文值形状（基线＝空，任何命中都红）===")
    a_hits = [(fn, name, ln) for fn, data in files
              for name, ln, _ in hits_for(SHAPES, data.decode("utf-8", "replace"))]
    for fn, name, ln in a_hits[:20]:
        print(f"  🔴 {fn} L{ln} {name}")
    print(f"  命中 {len(a_hits)} 处 ⇒ {'⛔ 红' if a_hits else '绿'}")

    print("\n=== 闸 B／C｜指纹与指路牌（内容锚点基线，⛔ 行号）===")
    docs = [(fn, data.decode("utf-8", "replace")) for fn, data in files if fn.lower().endswith(DOC_EXT)]
    doc_text = "\n".join(t for _, t in docs)
    print(f"  扫描面＝给人看的文本 {len(docs)} 件：{', '.join(sorted(fn for fn, _ in docs))}")
    print("  逐件命中：" + ("、".join(f"{fn}={len(hits_for(FPRS + PATHS, t))}" for fn, t in sorted(docs)) or "无"))
    print("  ⚠️ 逐件那行是给人看的：仓里要是多出一面墙的**副本**，每个数都会翻倍（本件实测栽过一次）。")

    total_new, drift, expired, per_rule = [], [], [], Counter()
    for name, pat in FPRS + PATHS:
        found = hits_for([(name, pat)], doc_text)
        per_rule[name] = len(found)
        ents = [e for e in entries if e["rule"] == name]
        unreg = 0
        for _, _, ln in found:
            if not any(e["anchor"] in ln for e in ents):
                unreg += 1
                total_new.append((name, ln.strip()[:70]))
        for e in ents:
            if e["anchor"] not in doc_text:
                drift.append(f"{name} 的锚点「{e['anchor'][:34]}…」在文档里读不到了")
            elif e.get("review_by") and e["review_by"] < today:
                expired.append(f"{name} 的登记项 review_by={e['review_by']} 已过期（owner={e.get('owner')}）")
        print(f"  {name}: 现读 {len(found)} 处，基线登记 {sum(e.get('count', 1) for e in ents)} 处，未登记 {unreg} 处")

    fb = forbidden_scan(files, base.get("forbidden_literals_sha256", []))
    print(f"\n=== 闸 B5｜已烧指纹黑名单（哈希比对）=== 黑名单 {len(base.get('forbidden_literals_sha256', []))} 条，"
          f"命中 {len(fb)} 处 ⇒ {'⛔ 红' if fb else '绿'}")
    for _n, fn, ln in fb[:12]:
        print(f"  🔴 {fn} L{ln} 出现一枚登记在案的已烧指纹（值⛔ 回显）")

    print("\n=== 判定 ===")
    if drift:
        print("  ⛔ 基线锚点漂了（被改过⛔ 被登记，或闸在量一个不存在的东西）：")
        for d in drift:
            print("     " + d)
        return 2
    if a_hits or fb:
        print(f"  🔴 闸 A {len(a_hits)} 处明文值形状；闸 B5 {len(fb)} 处已烧指纹 ⇒ 当场红")
        return 1
    if total_new:
        print(f"  🔴 新增违规 {len(total_new)} 处：")
        for name, frag in total_new[:12]:
            print(f"     {name} :: {frag}")
        return 1
    if expired:
        print("  🔴 基线登记项到期，需重新看一眼（改期或删掉那条登记都算答复）：")
        for e in expired:
            print("     " + e)
        return 1
    print(f"  绿：闸 A 0 命中；B／C 现读 {sum(per_rule.values())} 处全落在已登记锚点上；"
          f"黑名单 0 回流；⛔ 过期项。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
