"""一条命令跑完这条线上**所有离线反证**，并且拒绝"少跑了还报绿"。

    py tools/verify_all.py                # 跑清单里全部件；全绿=0
    py tools/verify_all.py --show         # 只看清单与底线，⛔ 跑
    py tools/verify_all.py --raise-floors # 把底线抬到本次实测条数（加了断言之后跑这一发）

为什么要这件：仓里现在有四件离线反证（漂移检测器套件、公开面三道闸、闸的反证、本件的自检），
但"谁跑了、跑了几条"⛔ 有任何东西在管。而这条线反复栽的那一类坏是**静默跳过**：
子进程零输出＝根本没跑（第 9 条①）、断言没执行＝假绿（第 47 条）、少跑一组照发"全绿"。
⇒ 本件的判据⛔ 只是"退出码 0"，是**每条件的断言条数⛔ 低于登记的底线**：
  条数只⛔ 降（有人删了用例、或某组用例整组没跑）⇒ 当场红；涨了只报⛔ 红（那是好事，但要你确认）。

三条口径（都是踩出来的）：
  1. **条数从模块自己的记录里取**（`_results` 长度、规则表长度），⛔ 去正则解析 stdout——
     打印格式一改判据就静默失效（与"逐条 Ignore 绑行号"同一类错，第 47 条②(a)）。
  2. **件与件之间同进程跑**（`importlib` 载入），⛔ 子进程：快、⛔ 招 `S603`/`S607`，
     而且"子进程零输出＝根本没跑"那一格从结构上⛔ 存在了。
  3. **清单与聚合器版本配成一对**（同 `drift_check.py` 的 `TOOL_REVISION` ↔ `known_good.json` 那把两文件原子闸）：
     两侧必须同改，⛔ 一致 ⇒ exit 2。

退出码：0＝全部达标；1＝有件⛔ 过、有件失败、或有件条数低于底线；2＝量具坏（件读⛔ 到、版本⛔ 配对、条数⛔ 可观测）。
"""

import contextlib
import importlib.util
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_REL = os.path.join("drift", "verify_manifest.json")
VERIFY_REVISION = "2026-09-28-verify-all-2"

# 每件的"条数从哪来"写死在这里，⛔ 靠猜：
#   rule_tables        ＝ 三张规则表长度之和（闸那件⛔ 有 `_results`）
#   results_after_main ＝ 调 main() 后读 `_results`
#   results_top        ＝ 载入即跑（脚本型套件），再读 `_results`
CHECKS = [
    {"id": "公开面三道闸", "path": "tools/wall_scan.py", "entry": "main",
     "count_from": "rule_tables", "floor_key": "wall_gate_rules"},
    {"id": "闸的反证（注入）", "path": "tools/test_wall_scan.py", "entry": "top",
     "count_from": "results_top", "floor_key": "wall_suite"},
    {"id": "漂移检测器反证", "path": "tools/test_drift_check.py", "entry": "main",
     "count_from": "results_after_main", "floor_key": "drift_suite"},
    {"id": "本件的自检（少跑必须红）", "path": "tools/test_verify_all.py", "entry": "top",
     "count_from": "results_top", "floor_key": "verify_suite"},
]


class Capture(io.StringIO):
    """被聚合的套件开头都有 `sys.stdout.reconfigure(encoding=...)`（Windows GBK 那坑）。
       `redirect_stdout` 换成裸 StringIO 后那个方法⛔ 存在 ⇒ 整件会崩在 import。
       所以给捕获流补一个⛔ 做事的 reconfigure，⛔ 为此去改那三件套件的开头。"""

    def reconfigure(self, **_kwargs):
        return None


def call_main(mod):
    """`test_drift_check.main()` ⛔ 收参数、`wall_scan.main(argv)` 收 ⇒ 两种签名都要能跑。"""
    try:
        return mod.main([])
    except TypeError:
        return mod.main()


def run_one(root, ck):
    """跑一件 ⇒ (退出码, 条数, 失败条数, 秒, 备注)。⛔ 子进程、⛔ 解析 stdout 计数。"""
    path = os.path.join(root, ck["path"].replace("/", os.sep))
    if not os.path.exists(path):
        return 2, 0, 0, 0.0, "件⛔ 存在"
    name = "va_" + os.path.basename(ck["path"]).replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, path)
    # 先建模块对象**再**执行：脚本型套件末尾会 `sys.exit(1)`；要是"执行并返回"，
    # 崩在半路时拿到的就是 None ⇒ 条数读⛔ 到、备注还会指错方向（本件实测踩过）。
    mod = importlib.util.module_from_spec(spec)
    code, failed = None, 0
    t0 = time.time()
    try:
        with contextlib.redirect_stdout(Capture()):
            spec.loader.exec_module(mod)
            code = call_main(mod) if ck["entry"] == "main" else 0
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except (OSError, ValueError, TypeError, AttributeError, ImportError) as e:
        # ⛔ 用裸 `except Exception`（那正是 BLE001 要拦的）：这四类就是"件读⛔ 到／签名对⛔ 上／
        # 模块自己引用了⛔ 存在的名字"三种崩法的并集，兜住它们并记成**坏量具**（exit 2），
        # 而⛔ 顺手把别的东西也咽下去。
        return 2, 0, 0, time.time() - t0, f"载入/运行崩了：{type(e).__name__}: {str(e)[:70]}"
    dt = time.time() - t0

    if ck["count_from"] == "rule_tables":
        n = len(mod.SHAPES) + len(mod.FPRS) + len(mod.PATHS)
    else:
        res = getattr(mod, "_results", None)
        if res is None:
            return 2, 0, 0, dt, "模块里找不到 `_results` ⇒ 条数⛔ 可观测，判坏量具"
        n = len(res)
        failed = len([1 for _name, v in res if not v])
    return (code if code is not None else 0), n, failed, dt, ""


def verdict(bad, rows, bumped, raise_floors):
    """退出码分三档，⛔ 把两种坏混成一档：
       2＝有件**根本判⛔ 了分**（件缺、载入即崩、条数⛔ 可观测）＝量具坏；
       1＝件都跑成了、但有件**真失败**或条数低于底线；0＝全达标。
       （上一版把 2 折进 1，被自己的 V3/V5 抓出来：聚合器把"没法判"说成"判红了"，
         下一个人就会去查用例，⛔ 去查那件压根没跑起来的工具。）"""
    if not bad:
        if raise_floors:
            print("  抬底线：" + ("、".join(f"{k}: {a}→{b}" for k, a, b in bumped) if bumped else "无一变化"))
            return 0, rows, bumped
        tot = sum(r[2] for r in rows)
        print(f"  绿：{len(rows)} 件全过，可观测判据合计 {tot} 条，且每件条数都⋝ 登记的底线。")
        return 0, rows, bumped
    broken = [r for r in rows if r[1] == 2]
    print(f"  ⛔ 绿。{len(bad)} 件达⛔ 标" + ("（抬底线模式，但抬⛔ 平坏件）" if raise_floors else "") + "：")
    for b in bad:
        print("     " + b)
    if broken:
        print(f"  ⇒ 其中 {len(broken)} 件是**判⛔ 了分**（件缺／崩／条数⛔ 可观测）＝量具坏 ⇒ exit 2。")
        return 2, rows, bumped
    print("  ⇒ 条数低于底线＝**有用例没跑**，那⛔ 叫「全绿」。")
    return 1, rows, bumped


def pairing_problems(checks, floors):
    """两件必须一一对上：`CHECKS` 里每件都要有底线，清单里每条底线都要有对应件。
       为什么单独查：上一版只查"件⛔ 过"，于是**有人把一件反证从 CHECKS 里摘掉**（或清单里漏一条），
       聚合器就照着剩下几件报"全绿"——实测：摘掉漂移套件后总数从 77 掉到 47，返回码仍是 0。
       这正是本件存在的理由，所以它⛔ 算"红"，算**量具坏**（exit 2）。"""
    want = {ck["floor_key"] for ck in checks}
    have = set(floors or {})
    out = []
    for k in sorted(want - have):
        out.append(f"件「{k}」在清单里⛔ 底线 ⇒ 它会拿 0 当底线混过去")
    for k in sorted(have - want):
        out.append(f"清单里留着底线「{k}」，但 CHECKS 里⛔ 这一件 ⇒ **有件反证被摘走了**")
    return out


def run_all(root=ROOT, checks=None, floors=None, revision=VERIFY_REVISION, raise_floors=False):
    checks = CHECKS if checks is None else checks
    floors = {} if floors is None else floors
    print(f"聚合器版本戳={revision}  件数={len(checks)}  根={root}")
    probs = pairing_problems(checks, floors)
    if probs:
        print("  ⛔ 清单与件表⛔ 配对（量具坏，先修这个再谈绿）：")
        for q in probs:
            print("     " + q)
        return 2, [], []
    print(f"{'件':<26} {'退出':<5} {'条数':<6} {'底线':<6} {'失败':<5} 秒   备注")
    bad, rows, bumped = [], [], []
    for ck in checks:
        code, n, failed, dt, note = run_one(root, ck)
        floor = floors.get(ck["floor_key"])
        ok = (code == 0) and (failed == 0) and (floor is not None) and (n >= floor)
        rows.append((ck, code, n, floor, failed, dt, note, ok))
        print(f"{ck['id']:<26} {code:<5} {n:<6} {floor!s:<6} {failed:<5} {dt:.1f}   {note}")
        if not ok:
            if code != 0 or failed:
                bad.append(f"{ck['id']}：退出码={code} 失败={failed}")
            elif floor is None:
                bad.append(f"{ck['id']}：清单里⛔ 这条底线 ⇒ 静默放行")
            else:
                bad.append(f"{ck['id']}：条数 {n} < 底线 {floor} ⇒ **有件少跑了或整组没跑**")
        if raise_floors and n > (floor or 0):
            bumped.append((ck["floor_key"], floor, n))
            floors[ck["floor_key"]] = n

    print("\n=== 判定 ===")
    return verdict(bad, rows, bumped, raise_floors)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    man_path = os.path.join(ROOT, MANIFEST_REL)
    try:
        with open(man_path, encoding="utf-8") as f:
            man = json.loads(f.read())
    except (OSError, ValueError) as e:
        print(f"⛔ 清单读不到（{type(e).__name__}）⇒ 无从判分，exit 2")
        return 2
    if man.get("verify_all_min_version") != VERIFY_REVISION:
        print("⛔ 清单与聚合器版本⛔ 一致 ⇒ 两侧必须同改（两文件原子闸），exit 2")
        return 2
    floors = man.get("floors", {})

    if "--show" in argv:
        print(f"聚合器版本戳={VERIFY_REVISION}  清单里 {len(CHECKS)} 件：")
        for ck in CHECKS:
            print(f"   {ck['id']:<26} {ck['path']:<28} 底线={floors.get(ck['floor_key'])}")
        return 0

    code, _rows, bumped = run_all(floors=floors, raise_floors=("--raise-floors" in argv))
    if "--raise-floors" in argv and bumped:
        with open(man_path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(json.dumps(man, ensure_ascii=False, indent=2) + "\n")
        print("  ⇒ 已写回清单；请把这条改动与新增断言放进**同一个 commit**")
    return code


if __name__ == "__main__":
    sys.exit(main())
