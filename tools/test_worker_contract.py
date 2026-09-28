"""第四道闸的反证：`tools/worker_contract.py` 那 15 条**必须是有牙的**。

    py tools/test_worker_contract.py

为什么这件必须在仓里：第四道闸判的是「源码现算 == 契约登记」。两件里任意一件坏掉都会伪装成结论——
checker 数错键、锚点漂了还照样报绿、契约被改成一枚恒真的期望、或者整件因为路径没配好而⛔ 真判分。
所以这里⛔ 只问「红没红」，每一发都问**红的恰好是哪几条**（第 47 条：同批发一发⛔ 受覆盖的必然红对照件）。

口径：
  1. **同进程**调 `wc.main(["--root", 临时树])`，⛔ 开子进程（快，且「子进程零输出＝根本没跑」那格⛔ 存在）。
  2. **红在哪几条＝直接跑 checker 现数**，⛔ 去正则解析它打印的东西（打印格式一改判据就静默失效）。
  3. 每发只改**一处**：改源码／改契约／改版本戳……一次改两处就归⛔ 到是谁救的场。
  4. 另有一组**期望零退出**的干净对照（G0）——它是整件的地基：它要是不绿，后面所有「转红」都⛔ 算证据。

判据分三档，与闸本体一致：0＝全等；1＝有⛔ 等／契约过期；2＝量具坏。
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
SRC_REL = os.path.join("src", "index.js")
CON_REL = os.path.join("drift", "worker_contract.json")
_results = []


def req(name, cond, extra=""):
    _results.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'} {name}")
    if not cond and extra:
        print("        " + str(extra).replace("\n", "\n        ")[:900])
    return bool(cond)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


wc = load(os.path.join(HERE, "worker_contract.py"), "worker_contract_under_test")


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


PRISTINE_SRC = read_text(os.path.join(REPO, SRC_REL))
PRISTINE_CON = json.loads(read_text(os.path.join(REPO, CON_REL)))


def fresh_tree(src=None, contract=None):
    """临时树：⛔ 动仓里的实物。src/contract 给 None 就用原件。"""
    tmp = tempfile.mkdtemp(prefix="wc_")
    os.makedirs(os.path.join(tmp, "src"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "drift"), exist_ok=True)
    with open(os.path.join(tmp, SRC_REL), "w", encoding="utf-8", newline="\n") as f:
        f.write(PRISTINE_SRC if src is None else src)
    con = PRISTINE_CON if contract is None else contract
    with open(os.path.join(tmp, CON_REL), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(json.dumps(con, ensure_ascii=False, indent=2))
    return tmp


def repined(src):
    """改过源码的那一发要把契约里钉的那份 blob 一起换掉——
       这模拟的是**真实场景**：有人改了 index.js、重跑了登记，但某条语义断言塌了。
       ⛔ 钉的更新 = 「契约作废」那一档，另有 G8 专测它。"""
    data = src.encode("utf-8")
    con = json.loads(json.dumps(PRISTINE_CON))
    con["source"]["blob_sha1"] = wc._blob_sha1(data)
    con["source"]["bytes"] = len(data)
    return con


def run(tmp):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = wc.main(["--root", tmp])
    return code, buf.getvalue()


def red_set(src, contract):
    expect = contract.get("expect", {})
    out = []
    for rid, _claim, fn, _probe in wc.RULES:
        ok, _obs = fn(src, expect.get(rid, {}))
        if ok is False:
            out.append(rid)
    return sorted(out)


def mutate(text, needle, replacement):
    if text.count(needle) != 1:
        return None
    return text.replace(needle, replacement, 1)


def bump_source(needle, replacement):
    """改源码那一发 ⇒ (临时树, 新源码, 重新钉过 blob 的契约)。锚点⛔ 唯一 ⇒ (None,)*3。"""
    src = mutate(PRISTINE_SRC, needle, replacement)
    if src is None:
        return None, None, None
    con = repined(src)
    return fresh_tree(src=src, contract=con), src, con


def code_of(tmp):
    return run(tmp)[0]


def cleanup(tmp):
    shutil.rmtree(tmp, ignore_errors=True)


print("G0 干净对照（原件原契约 ⇒ 期望零退出）。它⛔ 绿，后面每一发的「转红」都⛔ 算证据。")
tmp0 = fresh_tree()
code0, out0 = run(tmp0)
req("G0 返回码==0", code0 == 0, out0[-400:])
req("G0 红的规则集合为空", red_set(PRISTINE_SRC, PRISTINE_CON) == [], red_set(PRISTINE_SRC, PRISTINE_CON))
req("G0 自检探针条数==规则条数", wc.RULES and out0.count("注入后转红=True") == len(wc.RULES),
    f"探针 PASS 数={out0.count('注入后转红=True')} 规则数={len(wc.RULES)}")
cleanup(tmp0)

print("\nG1–G5 改源码那一族（契约里的 blob 已跟着重新钉过）")
print("   为什么这一族大多拿 2 而⛔ 是 1：动的是某条规则的**校准锚点**（needle 在这份代码里已经⛔ 存在）")
print("   ⇒ 自检当场报「这条尺瞎掉」，于是整件⛔ 敢报任何结论——这是设计要的（⛔ 用没校准的尺说「红了一条」）。")
print("   只有 G5 那种「锚点还在、往里加一句」才拿得到 1。塌了哪几条一律由 red_set 直接跑 checker 现数。")
CASES = [
    ("G1 默认放行改成 return false", wc.AUTH_DEFAULT_OPEN, wc.AUTH_DEFAULT_CLOSE, ["W1"], 2, "瞎掉"),
    ("G2 删掉 toProperties 的 URL 那一行", wc.URL_LINE, "", ["W6", "W7"], 2, "瞎掉"),
    ("G3 比较符 <= 改成 <（命中口径变了）", wc.SINCE_CMP_LE, wc.SINCE_CMP_LT, ["W9"], 2, "瞎掉"),
    ("G4 REQUIRED_CONFIG 塞进 SYNC_TOKEN", wc.REQUIRED_3, wc.REQUIRED_4, ["W10", "W11"], 2, "瞎掉"),
    ("G5 给 /selftest 补上鉴权", wc.SELFTEST_OPEN,
     wc.SELFTEST_OPEN + "\n      if (!authorized(request, env)) return json({ error: \"nope\" }, 403);", ["W4"], 1, "⛔ 等"),
]
for label, needle, replacement, want, want_code, want_phrase in CASES:
    print(f"\n  {label} ⇒ 期望 {want_code}，塌的恰好是 {want}，话里要带「{want_phrase}」")
    tmp, src, con = bump_source(needle, replacement)
    if src is None:
        req(f"{label} 锚点唯一可注入", False, f"锚点在原件里出现 {PRISTINE_SRC.count(needle)} 次")
        continue
    code, out = run(tmp)
    req(f"{label} 返回码=={want_code}", code == want_code, out[-260:])
    req(f"{label} 说了「{want_phrase}」", want_phrase in out, out[-320:])
    req(f"{label} 塌的恰好是 {want}", red_set(src, con) == want, red_set(src, con))
    cleanup(tmp)

print("\nG6 ⛔ 动源码、只把契约里 W3 的字节数改成 30 ⇒ 期望 1，红的恰好只有 W3（登记侧也⛔ 能顺手改）")
con6 = json.loads(json.dumps(PRISTINE_CON))
con6["expect"]["W3"]["body_bytes"] = 30
tmp6 = fresh_tree(contract=con6)
code, out = run(tmp6)
req("G6 返回码==1", code == 1, out[-300:])
req("G6 红的恰好是 W3", red_set(PRISTINE_SRC, con6) == ["W3"], red_set(PRISTINE_SRC, con6))
cleanup(tmp6)

print("\nG7 契约版本戳改坏 ⇒ 期望 2（两文件原子闸）")
con7 = json.loads(json.dumps(PRISTINE_CON))
con7["worker_contract_min_version"] = "1970-01-01-wrong"
tmp7 = fresh_tree(contract=con7)
code, out = run(tmp7)
req("G7 返回码==2", code == 2, out[-300:])
req("G7 说了版本⛔ 配对（两文件原子闸）", "两文件原子闸" in out, out[:300])

print("\nG8 源码尾部加一个空行（字节一改就对不上钉的那份）⇒ 期望 2")
tmp8 = fresh_tree(src=PRISTINE_SRC + "\n")
code, out = run(tmp8)
req("G8 返回码==2", code == 2, out[-300:])
req("G8 说了源码与契约⛔ 同", "⛔ 同" in out, out[:300])
cleanup(tmp7)
cleanup(tmp8)

print("\nG9 契约过期 ⇒ 期望 1（过期是「该重新看一眼」，⛔ 是量具坏）")
con9 = json.loads(json.dumps(PRISTINE_CON))
con9["review_by"] = "2020-01-01"
tmp9 = fresh_tree(contract=con9)
code, out = run(tmp9)
req("G9 返回码==1", code == 1, out[-300:])
req("G9 说了过期", "过期" in out, out[-400:])
cleanup(tmp9)

print("\nG10 契约里删掉 W6 的期望 ⇒ 期望 2（规则与期望⛔ 配对；⛔ 能拿空 dict 蒙）")
con10 = json.loads(json.dumps(PRISTINE_CON))
del con10["expect"]["W6"]
tmp10 = fresh_tree(contract=con10)
code, out = run(tmp10)
req("G10 返回码==2", code == 2, out[-300:])
req("G10 点名了 W6", "W6" in out, out[:400])
req("G10 配对函数自己也报", bool(wc.pairing(wc.RULES, con10["expect"])), wc.pairing(wc.RULES, con10["expect"]))
cleanup(tmp10)

print("\nG11 契约里多留一条没有对应规则的期望 ⇒ 期望 2（「有件断言被摘走」那一洞）")
con11 = json.loads(json.dumps(PRISTINE_CON))
con11["expect"]["W99"] = {"keys": []}
tmp11 = fresh_tree(contract=con11)
code, out = run(tmp11)
req("G11 返回码==2", code == 2, out[-300:])
req("G11 说了被摘走", "被摘走" in out, out[:400])
cleanup(tmp11)

print("\nG12 把锚点复制一份（`.slice(0, 10)` 出现两次）⇒ 期望 2：探针钉⛔ 住唯一，那条判『瞎』")
dup = PRISTINE_SRC.replace(wc.LABELS_SLICE, wc.LABELS_SLICE + " // " + wc.LABELS_SLICE, 1)
tmp12 = fresh_tree(src=dup, contract=repined(dup))
code, out = run(tmp12)
req("G12 返回码==2", code == 2, out[-500:])
req("G12 点名了 W7", "W7" in out, out[:400])
cleanup(tmp12)

print("\nG13 源码整件不见了 ⇒ 期望 2（⛔ 是「跳过」）")
tmp13 = fresh_tree()
os.remove(os.path.join(tmp13, SRC_REL))
code, out = run(tmp13)
req("G13 返回码==2", code == 2, out[-300:])
cleanup(tmp13)

print("\nG14 假装的瞎规则（一条恒报绿的 checker）必须被自检抓出来")
print("   ⚠️ 下面两行 FAIL 是**故意打出来的**：它们喂给自检的是「永远报绿的假规则」和「锚点出现两次的假规则」，")
print("      被抓出来才算这条守卫有牙。真正的失败判据是紧跟其后的两条 PASS。")
blind = wc.self_test(PRISTINE_SRC, {"X1": {}}, [("X1", "假规则", lambda _s, _e: (True, "永远绿"), (wc.LABELS_SLICE, wc.LABELS_SLICE_MUT))])
req("G14 抓到了 X1", blind == ["X1"], blind)
req("G14 锚点⛔ 唯一的规则也被抓到",
    wc.self_test(PRISTINE_SRC, {"X2": {}}, [("X2", "假规则", lambda _s, _e: (False, "x"), ("return true", "return false"))]) == ["X2"],
    "return true 在源码里止一次")

print("\nG15 覆盖面边界（⛔ 是它坏了，是它⛔ 管这件事）：把 MAX_ISSUES 从 500 改成 50 并重新钉 blob")
print("   ⇒ 闸报 0。这一发是**故意让它绿**的：契约里⛔ 登记过「一次最多同步 500 条」，所以这道闸管⛔ 住它。")
print("   写在这里是为了让下一个人⛔ 把这闸当「源码怎么改都会响」。")
tmp15, src15, con15 = bump_source("const MAX_ISSUES = 500;", "const MAX_ISSUES = 50;")
code, out = run(tmp15)
req("G15 返回码==0（边界外，闸⛔ 装坏）", code == 0, out[-260:])
req("G15 一条都⛔ 塌", red_set(src15, con15) == [], red_set(src15, con15))
cleanup(tmp15)

bad = [name for name, v in _results if not v]
print(f"\n合计 {len(_results)} 条，失败 {len(bad)} 条" + ("" if not bad else "：" + ", ".join(bad)))
if bad:
    print("判定：⛔ 绿。第四道闸自己有⛔ 牙的那几条就在上面 ⇒ 它报的「全等」⛔ 算结论。")
    sys.exit(1)
print(f"判定：全绿 ⇒ 15 条断言每条都有「它必然响」的对照，配对／版本戳／过期／瞎规则四样坏也都拦得住。")
