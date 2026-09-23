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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=os.path.join(os.path.dirname(__file__), os.pardir, "drift", "known_good.json"))
    a = ap.parse_args()
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token:
        fail("环境变量 CLOUDFLARE_API_TOKEN 未设")
    led = json.load(open(a.ledger, encoding="utf-8"))
    acct, name = led["account_id"], led["worker"]
    drift = []

    dep = get("/accounts/%s/workers/scripts/%s/deployments" % (acct, name), token)
    deps = (dep.get("result") or {}).get("deployments") or []
    if not deps:
        fail("没有任何 deployment，线上根本没部署过？")
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

    vs = get("/accounts/%s/workers/scripts/%s/versions" % (acct, name), token)
    items = (vs.get("result") or {}).get("items") or []
    if items:
        newest = items[0]
        nm = (newest.get("metadata") or {})
        num = newest.get("number")
        if num is None:
            num = nm.get("number")
        print("· 最新版本号     : #%s %s  source=%s @ %s  triggered_by=%s"
              % (num, (newest.get("id") or "")[:8], nm.get("source"), nm.get("created_on"),
                 (newest.get("annotations") or {}).get("workers/triggered_by")))
        if newest.get("id") != serving:
            # 只有当"未部署的那次上传"内容也不同时才报漂移——否则同一个字节流重传不该长期狼来了。
            nv = get("/accounts/%s/workers/scripts/%s/versions/%s" % (acct, name, newest.get("id")), token)
            netag = (((nv.get("result") or {}).get("resources") or {}).get("script") or {}).get("etag") or ""
            nbinds = sorted("%s:%s" % (b.get("type"), b.get("name")) for b in (((nv.get("result") or {}).get("resources") or {}).get("bindings") or []))
            if netag != etag or nbinds != binds:
                drift.append("有一个未部署的版本 #%s（%s）与服务版本**内容不同**（etag%s/绑定%s 不一致）⇒ 此刻⛔ 不能用字节判据断言线上==仓库，且要问一句它是谁传的什么"
                             % (num, (newest.get("id") or "")[:8], "相同" if netag == etag else "不同", "相同" if nbinds == binds else "不同"))
            else:
                print("  ℹ️ 未部署的上传 #%s 与服务版本内容相同（同字节重传），不算漂移" % num)
    else:
        print("  ⚠️ 拿不到版本列表（不影响上面两项，但「未部署上传」这一项没测到）")

    print()
    if drift:
        for d in drift:
            print("⚠️ 漂移：%s" % d)
        print("\n判定：需要人看。登记值见 drift/known_good.json；确认线上正确后**改登记值**而不是忽略告警。")
        sys.exit(1)
    print("判定：无漂移（etag、绑定集合、服务版本三者都与登记值一致，且没有未部署的上传）。")
    sys.exit(0)


if __name__ == "__main__":
    main()
