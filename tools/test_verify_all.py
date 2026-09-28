"""`tools/verify_all.py` 的自检：**"少跑了必须红"这件事本身也要有反证**。

    py tools/test_verify_all.py

为什么这件要在：聚合器最容易犯的坏是**恒绿**（底线没配、条数取⛔ 到、件根本⛔ 存在却返回 0）。
所以每发都配一个"它必然失败"的对照。除最后一发外都用**合成替身件**跑，⛔ 递归调真套件：
  V1 替身件全达标 ⇒ 0
  V2 底线高于实测条数 ⇒ 1（这一发就是"整组没跑还报绿"的照妖镜）
  V3 件⛔ 存在 ⇒ 2（⛔ 是"跳过"）
  V4 件自己返回 1 ⇒ 1
  V5 件⛔ 暴露 `_results` ⇒ 2（条数⛔ 可观测＝坏量具）
  V6 清单版本戳与聚合器⛔ 配对 ⇒ 2（两文件原子闸）
  V7 真件端到端（排除本件防递归）⇒ 0
"""

import contextlib
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


def req(name, cond, extra=""):
    _results.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'} {name}")
    if not cond and extra:
        print("        " + str(extra).replace("\n", "\n        ")[:700])
    return bool(cond)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


va = load(os.path.join(HERE, "verify_all.py"), "verify_all_under_test")


def stub(tmp, fname, body):
    with open(os.path.join(tmp, fname), "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    return fname


def ck(fname, floor_key):
    return {"id": fname, "path": fname, "entry": "main",
            "count_from": "results_after_main", "floor_key": floor_key}


def capture(root, checks, floors):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code, rows, _b = va.run_all(root=root, checks=checks, floors=floors)
    return code, rows, buf.getvalue()


print("V1 替身件全达标 ⇒ 期望 0")
tmp = tempfile.mkdtemp(prefix="va_")
try:
    stub(tmp, "good.py", "_results = [('a', True), ('b', True), ('c', True)]\ndef main(argv=None):\n    return 0\n")
    code, rows, out = capture(tmp, [ck("good.py", "g")], {"g": 3})
    req("V1 返回码==0", code == 0, out)
    req("V1 条数取到 3", bool(rows) and rows[0][2] == 3, rows)

    print("\nV2 底线高于实测（＝有整组没跑）⇒ 期望 1")
    code, rows, out = capture(tmp, [ck("good.py", "g")], {"g": 4})
    req("V2 返回码==1", code == 1, out)
    req("V2 说了少跑", "少跑" in out, out)

    print("\nV3 件⛔ 存在 ⇒ 期望 2（⛔ 是跳过）")
    code, rows, out = capture(tmp, [ck("nope.py", "g")], {"g": 1})
    req("V3 返回码==2", code == 2, out)
    req("V3 说了件⛔ 存在", "⛔ 存在" in out, out)

    print("\nV4 件自己返回 1 ⇒ 期望 1")
    stub(tmp, "bad.py", "_results = [('a', True)]\ndef main(argv=None):\n    return 1\n")
    code, rows, out = capture(tmp, [ck("bad.py", "b")], {"b": 1})
    req("V4 返回码==1", code == 1, out)

    print("\nV5 件⛔ 暴露 `_results` ⇒ 期望 2")
    stub(tmp, "nores.py", "def main(argv=None):\n    return 0\n")
    code, rows, out = capture(tmp, [ck("nores.py", "n")], {"n": 1})
    req("V5 返回码==2", code == 2, out)
    req("V5 点名了条数⛔ 可观测", "_results" in out, out)

    print("\nV6 清单版本戳⛔ 配对 ⇒ 期望 2")
    tmp2 = tempfile.mkdtemp(prefix="va2_")
    try:
        os.makedirs(os.path.join(tmp2, "drift"), exist_ok=True)
        with open(os.path.join(tmp2, "drift", "verify_manifest.json"), "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"verify_all_min_version": "1970-01-01-wrong", "floors": {}}, ensure_ascii=False))
        old_root = va.ROOT
        va.ROOT = tmp2
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = va.main([])
            req("V6 返回码==2", code == 2, buf.getvalue())
            req("V6 说了版本⛔ 一致", "⛔ 一致" in buf.getvalue(), buf.getvalue())
        finally:
            va.ROOT = old_root
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    print("\nV7 真件端到端（排除本件，防递归）⇒ 期望 0")
    real = [c for c in va.CHECKS if c["floor_key"] != "verify_suite"]
    floors = {}
    try:
        with open(os.path.join(REPO, "drift", "verify_manifest.json"), encoding="utf-8") as f:
            floors = json.loads(f.read())["floors"]
    except (OSError, ValueError) as e:
        req("V7 清单读得到", False, f"{type(e).__name__}")
    if floors:
        code, rows, out = capture(REPO, real, floors)
        req("V7 三件真件返回码==0", code == 0, out)
        req("V7 每件都数到条数", all(r[2] > 0 for r in rows), [(r[0]["id"], r[2]) for r in rows])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

bad = [n for n, v in _results if not v]
print(f"\n合计 {len(_results)} 条，失败 {len(bad)} 条" + ("" if not bad else "：" + ", ".join(bad)))
if bad:
    print("判定：⛔ 绿。聚合器自己就可能恒真 ⇒ 这件⛔ 过，`verify_all.py` 那句「全绿」⛔ 算读数。")
    sys.exit(1)
print("判定：全绿 ⇒ `verify_all.py` 是「少跑了会红」的；它那句「全绿」才算一条读数。")
