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
  * ⚠️ 两个列表端点**都只回一页**，默认 10 条封顶 ⇒ 一律带 per_page=100，并在页满时明说"可能还有"。
  * ⭐ 09-24 修掉的盲区：旧版只把**最新版**与服务版本比 ⇒ 一旦再来一次合法部署，
    旧的未部署版本就**从告警里消失**（不是被拆雷，是探测器看不见了）。现在扫**全集**，
    并与所有 deployments 里出现过的 version_id 求差集。豁免走 ledger 的
    `known_undeployed_versions`（按 id 前缀匹配 + kept_intentionally=true），⛔ 不靠"看不见"来消音。
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# 本机是 GBK 控制台，中文/emoji 会直接把 print 炸掉（实测），所以强制 UTF-8 输出。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

API = "https://api.cloudflare.com/client/v4"
PER_PAGE = 100
MAX_DETAIL_GETS = 10   # 未部署版本可能很多，逐个取详情会打爆请求数
# 能力戳：日期前缀 ⇒ 字符串比较即时间序。登记里写 detector_min_version 可以
# 拒掉"拿旧副本跑出一盏假绿灯"（旧版只比最新版，09-24 实测会漏报 #10）。
TOOL_REVISION = "2026-09-24-scan-all-undeployed"


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
    """登记里被明示"有意保留"的未部署版本 id 前缀集合。"""
    out = []
    for e in ledger.get("known_undeployed_versions") or []:
        if e.get("kept_intentionally"):
            p = (e.get("version_id_prefix") or "").strip()
            if p:
                out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=os.path.join(os.path.dirname(__file__), os.pardir, "drift", "known_good.json"))
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

    req = led.get("detector_min_version")
    if req and str(req) > TOOL_REVISION:
        fail("登记要求的检测器能力 %r 比本脚本 %r 新 ⇒ 拒跑。"
             "（这不是摆设：09-24 实测旧版只比『最新版』，会漏掉更早的未部署版本并打印『没有未部署的上传』这种假话。）"
             % (req, TOOL_REVISION))

    dep = get("/accounts/%s/workers/scripts/%s/deployments?per_page=%d" % (acct, name, PER_PAGE), token)
    deps = (dep.get("result") or {}).get("deployments") or []
    if not deps:
        fail("没有任何 deployment，线上根本没部署过？")
    if len(deps) >= PER_PAGE:
        print("  ⚠️ deployments 取满 %d 条 ⇒ 这个数只是**本页**，不是总数（该端点不返回 result_info）" % PER_PAGE)
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
        print("  ⚠️ 拿不到版本列表（不影响上面两项，但「未部署上传」这一项**没测到**）")
    else:
        if len(items) >= PER_PAGE:
            print("  ⚠️ versions 取满 %d 条 ⇒ 未部署扫描可能不全" % PER_PAGE)
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
    print("判定：无漂移（etag / 绑定集合 / 服务版本与登记一致；未部署版本已全部逐个核查并如实归类）。")
    sys.exit(0)


if __name__ == "__main__":
    main()
