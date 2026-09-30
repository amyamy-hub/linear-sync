"""`tools/wall_scan.py` 的故障注入 ＋ 期望零退出的对照组（⛔ 联网、⛔ 要凭据、⛔ 碰线上）。

    py tools/test_wall_scan.py

为什么这件必须在仓里（第 47 条④、第 51 条同一个道理）：闸的价值⛔ 来自"它今天绿"，
来自"**它要是坏了、这里当场红**"。没有这件，`wall_scan.py` 绿一次没人知道它是真在跑还是恒真。

十组各抓一种坏法（全部**在同一个进程里**调 `wall_scan.main(["--root", 临时树])`，⛔ 开子进程）：
  G0 绿对照     ：真仓原样跑 ⇒ 必须 0（少了它，"红"可能只是环境坏）
  G1 新增指纹   ：墙上加一行合成指纹 ⇒ 必须 1
  G2 新增明文值 ：README 塞一把合成令牌 ⇒ 必须 1（闸 A 扫全部文本件，⛔ 止于 .md）
  G3 基线在漂   ：把某条 anchor 那行整行删掉 ⇒ 必须 2（⛔ 能"条目没了对着空气放行"）
  G4 登记过期   ：把一条 review_by 改到过去 ⇒ 必须 1
  G5 量具坏     ：把 B3 的正则换成永远⛔ 匹配的一条 ⇒ 必须 2（合成件当场响⛔ 了）
  G6 黑名单回流 ：塞一枚登记在案的已烧指纹（合成串） ⇒ 必须 1（B5 抓的是正则够⛔ 着的写法）
  G7 扫描面缺件 ：把带锚点的 HANDOFF.md 造成"读⛔ 到" ⇒ 必须 2，且**⛔ 能归因成「锚点漂了」**
  G8 超尺寸件   ：塞一把比 `MAX_BYTES` 还大的 `.json` ⇒ 必须 2，且跳过计数**从 0 跳到 1**（两发配对，⛔ 单发）
  G9 版本半改   ：只改基线那侧的 `wall_scan_min_version` ⇒ 必须 2（两文件原子闸；上一版这件**根本没人测**，
                  `fresh_tree()` 两侧同取 ⇒ 那道闸在测试里恒真——与 `test_drift_check` 第 264 行记的同一类洞）
  末条 命名互斥 ：没有任何一条断言名是另一条的子串（09-30 我两条都叫 `C13a…`，正则分辨⛔ 出炸的是哪条）
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
_results = []

# 合成"泄漏"样本：值全是编的，只为让闸响；⛔ 任何真凭据
PLANT_FPR = "> 注入对照：`SYNC_TOKEN` 新值 48 位 hex、前缀 `abcd`，令牌 `ntn_A…zz9`。"
PLANT_VALUE = "配置示例：`vJEr" + "0" * 34 + "-_`"
PLANT_B5 = "cafe9999deadbeef"


def req(name, cond, extra=""):
    _results.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'} {name}")
    if not cond and extra:
        print("        " + str(extra).replace("\n", "\n        ")[:900])
    return bool(cond)


def load_ws(path):
    spec = importlib.util.spec_from_file_location("wall_scan_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_text(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write_text(p, s, newline="\n"):
    with open(p, "w", encoding="utf-8", newline=newline) as f:
        f.write(s)


def fresh_tree(tool="wall_scan.py"):
    tmp = tempfile.mkdtemp(prefix="wallscan_")
    for sub in ("tools", "drift"):
        os.makedirs(os.path.join(tmp, sub), exist_ok=True)
    shutil.copy2(os.path.join(REPO, "tools", tool), os.path.join(tmp, "tools", tool))
    shutil.copy2(os.path.join(REPO, "drift", "wall_baseline.json"), os.path.join(tmp, "drift", "wall_baseline.json"))
    for fn in ("HANDOFF.md", "README.md"):
        src = os.path.join(REPO, fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(tmp, fn))
    return tmp


def run_gate(tmp, tool="wall_scan.py"):
    """在进程内调 main()，抓 stdout 与返回码（⛔ 子进程 ⇒ ⛔ 那类 subprocess 告警，也快一个量级）。"""
    ws = load_ws(os.path.join(tmp, "tools", tool))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = ws.main(["--root", tmp])
    return code, buf.getvalue()


print("G0 绿对照：真仓原样跑 ⇒ 期望 0")
t = fresh_tree()
try:
    code, out = run_gate(t)
    req("G0 返回码==0", code == 0, out[-800:])
    req("G0 真在扫（报出了基线登记数）", "基线登记" in out, out[-800:])
    # ⚠️ 这里⛔ 把那枚已烧指纹原样写进本件——写了就会被 B5 自己抓到（实测撞上过一次，
    #    抓的是本件第 93 行）。拼出来即可，判据⛔ 变。
    req("G0 输出⛔ 回显被检内容", ("ntn_" + "1" not in out) and ("vJEr" not in out), out[-400:])
    req("G0 对账行报出「跳过 0 件」（计数器真接着线，⛔ 是恒真的句子）",
        "跳过 0 件（超尺寸 0／读不到 0）" in out, out[-800:])
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG1 新增凭据指纹：墙上加一行合成指纹 ⇒ 期望 1")
t = fresh_tree()
try:
    hp = os.path.join(t, "HANDOFF.md")
    write_text(hp, read_text(hp).replace("# 接手须知（HANDOFF）",
                                         "# 接手须知（HANDOFF）\n\n" + PLANT_FPR, 1))
    code, out = run_gate(t)
    req("G1 返回码==1", code == 1, out[-800:])
    req("G1 点名了 B1/B2/B3 之一", any(k in out for k in ("B1 长度声明", "B2 前缀字面量", "B3 两头都念")), out[-800:])
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG2 新增明文值：README 塞一把合成 40 位令牌 ⇒ 期望 1")
t = fresh_tree()
try:
    rp = os.path.join(t, "README.md")
    write_text(rp, read_text(rp).replace("\n", "\n" + PLANT_VALUE + "\n", 1))
    code, out = run_gate(t)
    req("G2 返回码==1", code == 1, out[-800:])
    req("G2 是闸 A 报的（⛔ 只报 B/C）", "A5 CF 令牌形态" in out, out[-800:])
    req("G2 输出⛔ 回显那把合成值", "vJEr" not in out, out[-400:])
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG3 基线在漂：把第一条 anchor 所在行整行删掉 ⇒ 期望 2")
t = fresh_tree()
try:
    b = json.loads(read_text(os.path.join(t, "drift", "wall_baseline.json")))
    anchor = b["entries"][0]["anchor"]
    hp = os.path.join(t, "HANDOFF.md")
    lines = read_text(hp).split("\n")
    keep = [l for l in lines if anchor not in l]
    ok = req("G3 注入点存在（那一行删得掉）", len(keep) < len(lines), "anchor 一行都没命中")
    if ok:
        write_text(hp, "\n".join(keep))
        code, out = run_gate(t)
        req("G3 返回码==2（⛔ 是「没命中就算绿」）", code == 2, out[-800:])
        req("G3 说了锚点读不到", "锚点" in out, out[-800:])
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG4 登记过期：把一条 review_by 改到过去 ⇒ 期望 1")
t = fresh_tree()
try:
    bp = os.path.join(t, "drift", "wall_baseline.json")
    b = json.loads(read_text(bp))
    b["entries"][0]["review_by"] = "2020-01-01"
    write_text(bp, json.dumps(b, ensure_ascii=False, indent=2) + "\n", newline="\r\n")
    code, out = run_gate(t)
    req("G4 返回码==1", code == 1, out[-800:])
    req("G4 说了到期", "过期" in out, out[-800:])
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG5 量具坏：把 B3 的正则换成永远⛔ 匹配的一条 ⇒ 期望 2（自检先把坏尺拦下）")
t = fresh_tree()
try:
    src = read_text(os.path.join(REPO, "tools", "wall_scan.py"))
    old = '("B3 两头都念", r"`(?P<fp>[0-9A-Za-z_]{2,12})…(?P<fp2>[0-9A-Za-z_]{2,12})`")'
    if req("G5 变异点唯一命中（变异锚没漂）", src.count(old) == 1, f"count={src.count(old)}"):
        write_text(os.path.join(t, "tools", "wall_scan_broken.py"),
                   src.replace(old, '("B3 两头都念", r"(?P<fp>NEVER_MATCH_XYZZY{2,12})")'))
        code, out = run_gate(t, tool="wall_scan_broken.py")
        req("G5 返回码==2", code == 2, out[-800:])
        req("G5 点名了 B3", "B3 两头都念" in out, out[-800:])
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG6 黑名单回流：塞一枚登记在案的已烧指纹（合成串） ⇒ 期望 1")
t = fresh_tree()
try:
    bp = os.path.join(t, "drift", "wall_baseline.json")
    b = json.loads(read_text(bp))
    b["forbidden_literals_sha256"] = [hashlib.sha256(PLANT_B5.encode("utf-8")).hexdigest()]
    write_text(bp, json.dumps(b, ensure_ascii=False, indent=2) + "\n", newline="\r\n")
    hp = os.path.join(t, "HANDOFF.md")
    write_text(hp, read_text(hp).replace("# 接手须知（HANDOFF）",
                                         "# 接手须知（HANDOFF）\n\n> 注入对照：环境里就是当前那把（`"
                                         + PLANT_B5 + "` 开头）。\n", 1))
    code, out = run_gate(t)
    req("G6 返回码==1（B5 拦得住正则够⛔ 着的写法）", code == 1, out[-800:])
    req("G6 点名了 B5", "B5" in out, out[-800:])
    req("G6 输出⛔ 回显那枚合成串", PLANT_B5 not in out, out[-400:])
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG7 扫描面缺件：把带锚点的 HANDOFF.md 造成读不到 ⇒ 期望 2，且⛔ 算「锚点漂了」")
t = fresh_tree()
try:
    ws = load_ws(os.path.join(t, "tools", "wall_scan.py"))
    real_read = ws.read_bytes

    def broken_read(path):
        if os.path.basename(path) == "HANDOFF.md":
            raise OSError("注入：这件读不到")
        return real_read(path)

    ws.read_bytes = broken_read
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = ws.main(["--root", t])
    out = buf.getvalue()
    req("G7 返回码==2（缺件＝量具⛔ 全，既⛔ 算绿也⛔ 算违规）", code == 2, out[-800:])
    req("G7 点名 HANDOFF.md 且报读不到", ("HANDOFF.md" in out) and ("读不到 1）" in out), out[-800:])
    req("G7 没掉进旧归因「基线锚点漂了」", "基线锚点漂了" not in out, out[-800:])
    req("G7 先拦在自检之前（⛔ 让坏尺把缺件说成 B3/C1 响⛔ 了）", "量具自检" not in out, out[-800:])
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG8 超尺寸件：塞一把比 MAX_BYTES 还大的 .json ⇒ 两发配对，跳过数必须从 0 变 1")
t = fresh_tree()
try:
    ws0 = load_ws(os.path.join(REPO, "tools", "wall_scan.py"))
    limit = int(ws0.MAX_BYTES)
    code0, out0 = run_gate(t)
    req("G8 空场对照＝0 且报「跳过 0 件」（同树同闸，只差那一件）",
        code0 == 0 and "跳过 0 件（超尺寸 0" in out0, f"code={code0}")
    big = os.path.join(t, "drift", "oversize_fixture.json")
    write_text(big, '{"pad":"' + "x" * (limit + 7) + '"}')
    code, out = run_gate(t)
    req("G8 返回码==2（扫描面缺件＝判⛔ 了分，⛔ 是「它没命中所以绿」）", code == 2, out[-800:])
    req("G8 跳过计数真的从 0 跳到 1（会变的那一维）", "跳过 1 件（超尺寸 1／读不到 0）" in out, out[-800:])
    req("G8 点名被跳的是哪一件", "oversize_fixture.json" in out, out[-800:])
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG9 版本半改：只改基线那侧 ⇒ 期望 2（两文件原子闸这一轮才第一次被反证）")
t = fresh_tree()
try:
    bp = os.path.join(t, "drift", "wall_baseline.json")
    b = json.loads(read_text(bp))
    b["wall_scan_min_version"] = str(b.get("wall_scan_min_version")) + "-solo"
    write_text(bp, json.dumps(b, ensure_ascii=False, indent=2) + "\n", newline="\r\n")
    code, out = run_gate(t)
    req("G9 只改基线一侧 ⇒ 返回码==2", code == 2, out[-800:])
    req("G9 说了「两侧必须同改」", "两侧必须同改" in out, out[-800:])

    t2 = fresh_tree()
    try:
        src = read_text(os.path.join(t2, "tools", "wall_scan.py"))
        rev = str(load_ws(os.path.join(REPO, "tools", "wall_scan.py")).TOOL_REVISION)
        old = 'TOOL_REVISION = "' + rev + '"'
        if req("G9 反向变异点唯一命中", src.count(old) == 1, f"count={src.count(old)}"):
            write_text(os.path.join(t2, "tools", "wall_scan_solo.py"),
                       src.replace(old, 'TOOL_REVISION = "' + rev + '-solo"', 1))
            code2, out2 = run_gate(t2, tool="wall_scan_solo.py")
            req("G9 只改检测器一侧 ⇒ 同样==2（两个方向都得拦）", code2 == 2, out2[-800:])
    finally:
        shutil.rmtree(t2, ignore_errors=True)
finally:
    shutil.rmtree(t, ignore_errors=True)

_names = [n for n, _v in _results]
_coll = [a + " 是 " + b + " 的子串" for a in _names for b in _names if a != b and a in b]
req("末条 断言命名互斥（没有一条是另一条的子串 ⇒ 正则能分辨炸的是哪条）", not _coll, ", ".join(_coll[:6]))

bad = [n for n, v in _results if not v]
print(f"\n合计 {len(_results)} 条，失败 {len(bad)} 条" + ("" if not bad else "：" + ", ".join(bad)))
if bad:
    print("判定：⛔ 绿。有断言没通过 ⇒ 那三道闸⛔ 能签「公开面已减密」。")
    sys.exit(1)
print("判定：全绿 ⇒ `wall_scan.py` 那三道闸是**真会红**的；它绿一次，才算一条读数。")
