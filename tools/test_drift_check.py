"""漂移检测器的故障注入 + 变异自检（⛔ 联网、⛔ 要凭据、⛔ 碰线上）。

    py tools/test_drift_check.py            # 跑 10 组用例 / 27 条断言
    py tools/test_drift_check.py -v         # 失败时多打一段输出

为什么这件**必须在仓里**（横幅第 47 条④）：`tools/drift_check.py` 里算 git 对象号那一处弱哈希调用是 Codacy 的误报，
我们据此登记了一条有据的豁免（第 44 条）并逐条 Ignore（第 46 条）。
那条豁免的底气⛔ 来自「扫描器闭嘴」，来自「**那行要是算错，本文件会当场红**」。此前那 24 条断言只活在
审计位客户端的一个临时目录里，意思是：目录一清，反证就没了，而墙上还写着「本仓那套」。
⇒ 现在它在仓里了（10 组 / 27 条），任何人 clone 下来一发就能复算，⛔ 依赖任何一个 agent 的硬盘。

四条设计约束（都是踩出来的，改这个文件前先读）：
  1. **期望值是离线钉死的字面量**，⛔ 在这里现算。两个号各由两把独立工具对撞过：`git hash-object --stdin`
     （输入 5 字节 `abcde`）与按定义手算 `sha1("blob 5" + NUL + bytes)` 给出同一个号
     `6a8165460570531a1247bd99a73b53a5a6e500d5`；6 字节那份（`abcde` 再加一个换行）＝ `00dedf6bd5f3e493ce8b03c889912f47b01297d4`。
     拿被测对象自己算一遍再和它对撞＝自证，⛔ 是验收（横幅第 9 条①那个老坑）。
  2. **⛔ 用裸 `assert`**：`python -O` 会把它们整片静默删掉，测试全绿而一条没跑（假绿最贵的一种）。⇒ 一律走 `req()`。
  3. 本文件里⛔ 出现那处弱哈希的调用式——**连注释里都⛔ 写全**：规则按文本匹配，豁免只钉在 `drift_check.py`
     那一行上，这里再写一次全式子就是一发新的、⛔ 被豁免覆盖的告警（横幅 47 第 3 发现测：同文件另一处被点了 4 条）。
  4. 字符串一律 f-string，⛔ 百分号格式：这条不是洁癖——本件第一版用 `%` 写了 17 处，Codacy 当场记 17 条新增
     （UP031），把门禁点亮成「23 new issues」。**新件⛔ 给门禁添活**，尤其⛔ 添那种「豁免只管那一行」管不到的活。
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL_PATH = os.path.join(HERE, "drift_check.py")
VERBOSE = "-v" in sys.argv[1:]

BLOB_5 = "6a8165460570531a1247bd99a73b53a5a6e500d5"     # git hash-object over b"abcde"
BLOB_6 = "00dedf6bd5f3e493ce8b03c889912f47b01297d4"     # 同上，内容是 b"abcde" 加一个换行
ETAG = "b5cc1a50" * 8
OTHER_ETAG = "5d4e6aad" * 8
SRC5 = b"abcde"
SRC6 = b"abcde\n"

# 一个两块的 multipart：入口脚本那块 5 字节，另一块是 JSON 元数据（09-28 现读线上就是这两块）
PART5 = (b"--BND\r\nContent-Disposition: form-data; name=\"index.js\"\r\nContent-Type: application/javascript"
         b"; charset=utf-8\r\n\r\n" + SRC5 + b"\r\n--BND\r\nContent-Disposition: form-data; name=\"metadata\"\r\n"
         b"Content-Type: application/json\r\n\r\n{\"a\":1}\r\n--BND--\r\n")
# 那块内容自带一个结尾换行：专抓「边界 CRLF 被一起 strip 掉」那种过剥（6 字节⛔ 是 5）
PART6 = (b"--BND\r\nContent-Disposition: form-data; name=\"index.js\"\r\nContent-Type: application/javascript"
         b"\r\n\r\n" + SRC6 + b"\r\n--BND--\r\n")

LEDGER_BASE = {"account_id": "acctX", "worker": "linear-sync", "artifact_etag": ETAG,
               "expected_bindings": [], "serving_version_id": "v-uuid-1",
               "known_undeployed_versions": []}

FAKE_ENV_NAME = "CLOUDFLARE_API_TOKEN"
FAKE_ENV_VALUE = "synthetic" + "-" + "not-a-real-credential" + "-" + str(os.getpid())

_results = []


def req(name, cond, detail=""):
    """⛔ 用裸 assert（见文件头约束 2）：这里把每条都记下来，最后一起判。"""
    _results.append((name, bool(cond)))
    if cond:
        print(f"  PASS {name}")
    else:
        print(f"  FAIL {name}" + (f"\n       {detail}" if detail else ""))
    return bool(cond)


def load_tool(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_case(mod, slot_etag=ETAG, ver_etag=ETAG, versions_total=1, items=None,
             download=(None, "未调用"), expect_blob="", min_version=None):
    """把检测器的两只取数手换成合成的，跑它一遍 main()，拿回 (退出码, 输出, 调用序列)。
       ⛔ 联网：任何没预料到的只读路径都当场抛，⛔ 静默放过。"""
    if items is None:
        items = [{"id": "v-uuid-1", "number": 13, "metadata": {"source": "quick_editor"}}]
    calls = []

    def get(path, token):
        calls.append(path)
        if "/deployments" in path:
            return {"success": True, "errors": [],
                    "result": {"deployments": [{"id": "d1", "created_on": "t", "source": "web",
                                                "versions": [{"version_id": "v-uuid-1", "percent": 100}]}]},
                    "result_info": {"total_count": 1}}
        if path.endswith("/workers/scripts") or "scripts?per_page" in path:
            return {"success": True, "errors": [], "result": [{"id": "linear-sync", "etag": slot_etag}]}
        if "/versions?per_page" in path:
            ri = {"total_count": versions_total} if versions_total is not None else {}
            return {"success": True, "errors": [], "result": {"items": items}, "result_info": ri}
        if "/versions/" in path:
            return {"success": True, "errors": [],
                    "result": {"resources": {"script": {"etag": ver_etag}, "bindings": []}}}
        raise AssertionError(f"没预料到的只读路径（harness 覆盖⛔ 全）: {path}")

    def get_raw(path, token):
        calls.append("RAW" + path)
        return download

    mod.get, mod.get_raw = get, get_raw
    os.environ[FAKE_ENV_NAME] = FAKE_ENV_VALUE
    ledger = dict(LEDGER_BASE)
    ledger["detector_min_version"] = min_version if min_version is not None else mod.TOOL_REVISION
    fd, ledpath = tempfile.mkstemp(suffix=".json", prefix="drift_ledger_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(ledger))
    argv = ["drift_check.py", "--ledger", ledpath] + (["--expect-blob", expect_blob] if expect_blob else [])
    import io as _io
    buf = _io.StringIO()
    old_out = mod.sys.stdout
    mod.sys.argv = argv
    mod.sys.stdout = buf
    code = None
    try:
        try:
            mod.main()
        except SystemExit as e:
            code = e.code
    finally:
        mod.sys.stdout = old_out
        os.remove(ledpath)
        os.environ.pop(FAKE_ENV_NAME, None)
    return code, buf.getvalue(), calls


def main():
    if not os.path.isfile(TOOL_PATH):
        print(f"❌ 找不到被测文件：{TOOL_PATH}（这件必须和 drift_check.py 放在同一个目录）")
        return 2
    mod = load_tool(TOOL_PATH, "drift_check_under_test")
    print(f"被测：{os.path.basename(TOOL_PATH)}（TOOL_REVISION={mod.TOOL_REVISION}）")

    def tail(o):
        return o[-900:] if VERBOSE else ""

    print("\n用例 1｜全等＋--expect-blob 命中 ⇒ exit 0，且字节结论是现证不是登记")
    code, out, calls = run_case(mod, download=(PART5, None), expect_blob=BLOB_5)
    req("C1 退出码==0（对照组，⛔ 省）", code == 0, f"code={code}\n{tail(out)}")
    req("C1 打出了源块 blob", "源块 blob" in out and BLOB_5[:16] in out, tail(out))
    req("C1 判据写的是现证", "现证" in out, tail(out))
    req("C1 终判语⛔ 无「已全部逐个核查」", "已全部逐个核查" not in out, tail(out))
    req("C1 终判语＝都取到了读数", "都取到了读数" in out, tail(out))

    print("\n用例 2｜反向对照（必然变红）：源块与传入的仓库 blob 不等 ⇒ exit 1")
    code, out, calls = run_case(mod, download=(PART5, None), expect_blob="0" * 40)
    req("C2 退出码==1", code == 1, f"code={code}\n{tail(out)}")
    req("C2 报了「线上⛔ 等于仓库」", "线上⛔ 等于仓库" in out, tail(out))

    print("\n用例 3｜静默路径：versions 信封缺 total_count ⇒ 进「没测到」，⛔ 谎称全查")
    code, out, calls = run_case(mod, download=(PART5, None), expect_blob=BLOB_5, versions_total=None)
    req("C3 退出码==0（缺 total_count⛔ 是漂移，是没验）", code == 0, f"code={code}\n{tail(out)}")
    req("C3 记进了没测到", "versions 信封缺 total_count" in out, tail(out))
    req("C3 ⛔ 说「都取到了读数」", "都取到了读数" not in out, tail(out))

    print("\n用例 4｜⛔ 传 --expect-blob ⇒ 只算读数、⛔ 下结论（有读数≠已验证）")
    code, out, calls = run_case(mod, download=(PART5, None))
    req("C4 退出码==0", code == 0, f"code={code}\n{tail(out)}")
    req("C4 有源块读数", "源块 blob" in out, tail(out))
    req("C4 记没测到", ("只算出来" in out) or ("没测到" in out), tail(out))

    print("\n用例 5｜闸门 2b 该拦的：槽位 etag ≠ 服务版本 etag ⇒ exit 1，且 2c ⛔ 跑")
    code, out, calls = run_case(mod, slot_etag=OTHER_ETAG, download=(PART5, None), expect_blob=BLOB_5)
    req("C5 退出码==1", code == 1, f"code={code}\n{tail(out)}")
    req("C5 说了字节判据作废", "用它下「线上==仓库」的判" in out, tail(out))
    req("C5 2c 被跳过（没打 /download）", not any(p.startswith("RAW") for p in calls), str(calls))

    print("\n用例 6｜/download 取不到（404）⇒ 记没测到，⛔ 判「线上没有源文件」")
    code, out, calls = run_case(mod, download=(None, "HTTP 404"), expect_blob=BLOB_5)
    req("C6 退出码==0", code == 0, f"code={code}\n{tail(out)}")
    req("C6 产物字节取不到进了没测到", "产物字节取不到" in out, tail(out))
    req("C6 ⛔ 说「都取到了读数」", "都取到了读数" not in out, tail(out))

    print("\n用例 7｜返回体⛔ 是 multipart 形态 ⇒ 取法要改，进没测到")
    code, out, calls = run_case(mod, download=(b'{"result":"not a boundary"}', None), expect_blob=BLOB_5)
    req("C7 退出码==0", code == 0, f"code={code}\n{tail(out)}")
    req("C7 源块解不出来进了没测到", "源块解不出来" in out, tail(out))

    print("\n用例 8｜阳性对照（证 harness 真在跑真文件）：登记的能力戳与脚本不同串 ⇒ 必须拒跑 exit 2")
    code, out, calls = run_case(mod, download=(PART5, None), expect_blob=BLOB_5, min_version="2020-01-01-tampered")
    req("C8 退出码==2（两文件原子闸还活着）", code == 2, f"code={code}\n{tail(out)}")

    print("\n用例 9｜专抓过剥换行：源块以换行结尾 ⇒ 那 6 字节⛔ 能缩成 5")
    code, out, calls = run_case(mod, download=(PART6, None), expect_blob=BLOB_6)
    req("C9 退出码==0（换行没被吃掉 ⇒ blob 与期望字面量相等）", code == 0, f"code={code}\n{tail(out)}")
    req("C9 报的块大小是 6 B（⛔ 5）", "index.js/6B" in out, tail(out))

    print("\n用例 10｜变异自检：把剥边界改回过剥那一版，用例 9 那条判据必须转红（否则是量具假绿）")
    with open(TOOL_PATH, encoding="utf-8") as f:
        src = f.read()
    good_block = ('        if part.startswith(b"\\r\\n"):\n'
                  '            part = part[2:]\n'
                  '        if part.endswith(b"\\r\\n"):\n'
                  '            part = part[:-2]')
    mut_block = '        part = part.strip(b"\\r\\n")'
    if not req("C10a 被测文件里那段精确剥边界的代码在场（变异锚点没漂）", src.count(good_block) == 1,
               f"count={src.count(good_block)}"):
        print("  SKIP C10b/C10c（变异锚点找不到 ⇒ 变异注入无从做起，这件本身就该红）")
    else:
        fd, mutpath = tempfile.mkstemp(suffix=".py", prefix="drift_mutated_")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(src.replace(good_block, mut_block, 1))
        try:
            bad = load_tool(mutpath, "drift_check_mutated")
            g, gd = mod.source_blob_from_multipart(PART6)
            b, bd = bad.source_blob_from_multipart(PART6)
            req("C10b 真代码算出期望号（该绿）", g == BLOB_6, f"真代码给的是 {g}（{gd}）")
            req("C10c 变异代码算不出期望号（该红）", b != BLOB_6,
                f"变异活了下来 ⇒ 用例 9 是假绿，这条验收⛔ 算做过（它给的是 {b}，{bd}）")
        finally:
            os.remove(mutpath)

    bad_count = len([1 for _, v in _results if not v])
    names = ", ".join(n for n, v in _results if not v)
    print(f"\n合计 {len(_results)} 条，失败 {bad_count} 条" + ("" if not bad_count else f"：{names}"))
    if bad_count:
        print("判定：⛔ 绿。有断言没通过（或变异锚点漂了）——本文件就是那条豁免的反证，它红着就说明⛔ 能签。")
        return 1
    print("判定：全绿 ⇒ `drift_check.py` 里那行 SHA-1 若算错，这里当场红（横幅 44/46 那条豁免的反证在场且可复算）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
