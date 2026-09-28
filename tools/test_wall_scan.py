#!/usr/bin/env python3
"""`tools/wall_scan.py` 的故障注入 ＋ 期望零退出的对照组（⛔ 联网、⛔ 要凭据、⛔ 碰线上）。

    py tools/test_wall_scan.py

为什么这件必须在仓里（第 47 条④、第 51 条同一个道理）：闸的价值⛔ 来自"它今天绿"，
来自"**它要是坏了、这里当场红**"。没有这件，`wall_scan.py` 绿一次没人知道它是真在跑还是恒真。

六组各抓一种坏法：
  G0 绿对照     ：真仓原样跑 ⇒ 必须 0（⛔ 这条 可省——少了它，"红"可能只是环境坏）
  G1 新增指纹   ：墙上加一行"新值 48 位 hex、前缀 abcd" ⇒ 必须 1
  G2 新增明文值 ：README 里塞一把合成 40 位令牌 ⇒ 必须 1（闸 A 扫全部文本件，⛔ 止于 .md）
  G3 基线在漂   ：把某条 anchor 那行整行删掉 ⇒ 必须 2（⛔ 能"条目没了对着空气放行"）
  G4 登记过期   ：把一条 review_by 改到过去 ⇒ 必须 1（到期要重新看一眼，⛔ 自动续期）
  G5 量具坏     ：把 B3 的正则换成永远⛔ 匹配的一条 ⇒ 必须 2（合成件当场响⛔ 了）
"""

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join("tools", "wall_scan.py")
BASELINE = os.path.join("drift", "wall_baseline.json")
_results = []

# 合成"泄漏"样本：值全是编的，只为让闸响；⛔ 任何真凭据形状的真值
PLANT_FPR = "> 注入对照：`SYNC_TOKEN` 新值 48 位 hex、前缀 `abcd`，令牌 `ntn_1…9zZ`。"
PLANT_VALUE = "配置示例：`vJEr" + "0" * 34 + "-_`"


def req(name, cond, extra=""):
    _results.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'} {name}")
    if not cond and extra:
        print("        " + str(extra).replace("\n", "\n        ")[:900])
    return bool(cond)


def fresh_tree():
    tmp = tempfile.mkdtemp(prefix="wallscan_")
    for sub in ("tools", "drift"):
        os.makedirs(os.path.join(tmp, sub), exist_ok=True)
    shutil.copy2(os.path.join(REPO, TOOL), os.path.join(tmp, TOOL))
    shutil.copy2(os.path.join(REPO, BASELINE), os.path.join(tmp, BASELINE))
    for fn in ("HANDOFF.md", "README.md"):
        src = os.path.join(REPO, fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(tmp, fn))
    return tmp


def run_in(tmp):
    p = subprocess.run([sys.executable, TOOL], cwd=tmp, capture_output=True,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    return p.returncode, out


def tail(text, n=800):
    return text[-n:]


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


print("G0 绿对照：真仓原样跑 ⇒ 期望 exit 0")
t = fresh_tree()
try:
    code, out = run_in(t)
    req("G0 退出码==0", code == 0, tail(out))
    req("G0 真在扫（报出了基线登记数）", "基线登记" in out, tail(out))
    req("G0 输出里⛔ 回显任何被检内容片段", "ntn_1" not in out and "vJEr" not in out, tail(out))
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG1 新增凭据指纹：墙上加一行合成指纹 ⇒ 期望 exit 1")
t = fresh_tree()
try:
    hp = os.path.join(t, "HANDOFF.md")
    write(hp, read(hp).replace("# 接手须知（HANDOFF）", "# 接手须知（HANDOFF）\n\n" + PLANT_FPR, 1))
    code, out = run_in(t)
    req("G1 退出码==1", code == 1, tail(out))
    req("G1 点名了 B1 或 B2 或 B3", ("B1 长度声明" in out) or ("B2 前缀字面量" in out) or ("B3 两头都念" in out), tail(out))
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG2 新增明文值：README 塞一把合成 40 位令牌 ⇒ 期望 exit 1")
t = fresh_tree()
try:
    rp = os.path.join(t, "README.md")
    write(rp, read(rp).replace("\n", "\n" + PLANT_VALUE + "\n", 1))
    code, out = run_in(t)
    req("G2 退出码==1", code == 1, tail(out))
    req("G2 是闸 A 报的（⛔ 只报 B/C）", "A5 CF 令牌形态" in out, tail(out))
    req("G2 输出⛔ 回显那把合成值", "vJEr" not in out, tail(out))
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG3 基线在漂：把第一条 anchor 所在行整行删掉 ⇒ 期望 exit 2")
t = fresh_tree()
try:
    b = json.loads(read(os.path.join(t, BASELINE)))
    anchor = b["entries"][0]["anchor"]
    hp = os.path.join(t, "HANDOFF.md")
    lines = read(hp).split("\n")
    keep = [l for l in lines if anchor not in l]
    if not req("G3 注入点存在（那一行删得掉）", len(keep) < len(lines), f"anchor={anchor} 一行都没命中"):
        raise SystemExit(1)
    write(hp, "\n".join(keep))
    code, out = run_in(t)
    req("G3 退出码==2（⛔ 是「没命中就算绿」）", code == 2, tail(out))
    req("G3 说了锚点读不到", "锚点" in out, tail(out))
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG4 登记过期：把一条 review_by 改到过去 ⇒ 期望 exit 1")
t = fresh_tree()
try:
    bp = os.path.join(t, BASELINE)
    b = json.loads(read(bp))
    b["entries"][0]["review_by"] = "2020-01-01"
    io.open(bp, "w", encoding="utf-8", newline="\r\n").write(json.dumps(b, ensure_ascii=False, indent=2) + "\n")
    code, out = run_in(t)
    req("G4 退出码==1", code == 1, tail(out))
    req("G4 说了到期", "过期" in out, tail(out))
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG5 量具坏：把 B3 的正则换成永远⛔ 匹配的一条 ⇒ 期望 exit 2")
t = fresh_tree()
try:
    tp = os.path.join(t, TOOL)
    s = read(tp)
    old = '"B3 两头都念", r"`(?P<fp>[0-9A-Za-z_]{2,12})…(?P<fp2>[0-9A-Za-z_]{2,12})`"'
    if not req("G5 变异点唯一命中（变异锚没漂）", s.count(old) == 1, f"count={s.count(old)}"):
        raise SystemExit(1)
    write(tp, s.replace(old, '"B3 两头都念", r"NEVER_MATCH_THIS_PATTERN_XYZZY"'))
    code, out = run_in(t)
    req("G5 退出码==2（自检先把坏尺拦下）", code == 2, tail(out))
    req("G5 点名了 B3", "B3 两头都念" in out, tail(out))
finally:
    shutil.rmtree(t, ignore_errors=True)

print("\nG6 已烧指纹回流：往墙上塞一枚黑名单里的字面量（用基线哈希反查不到值，所以这里塞的是" +
      "本件自己造的合成串） ⇒ 期望 exit 1")
t = fresh_tree()
try:
    bp = os.path.join(t, BASELINE)
    b = json.loads(read(bp))
    synth = "cafe9999dead"  # 合成串，⛔ 任何真凭据
    b["forbidden_literals_sha256"] = [hashlib.sha256(synth.encode("utf-8")).hexdigest()]
    io.open(bp, "w", encoding="utf-8", newline="\r\n").write(json.dumps(b, ensure_ascii=False, indent=2) + "\n")
    hp = os.path.join(t, "HANDOFF.md")
    write(hp, read(hp).replace("# 接手须知（HANDOFF）", "# 接手须知（HANDOFF）\n\n> 注入对照：环境里就是当前那把（`" + synth + "` 开头）。\n", 1))
    code, out = run_in(t)
    req("G6 退出码==1（B5 拦得住正则够⛔ 着的写法）", code == 1, tail(out))
    req("G6 点名了 B5", "B5" in out, tail(out))
    req("G6 输出⛔ 回显那枚合成串", synth not in out, tail(out))
finally:
    shutil.rmtree(t, ignore_errors=True)

bad = [n for n, v in _results if not v]
print(f"\n合计 {len(_results)} 条，失败 {len(bad)} 条" + ("" if not bad else "：" + ", ".join(bad)))
if bad:
    print("判定：⛔ 绿。有断言没通过 ⇒ 那三道闸⛔ 能签「公开面已减密」。")
    sys.exit(1)
print("判定：全绿 ⇒ `wall_scan.py` 那三道闸是**真会红**的；它绿一次，才算一条读数。")
