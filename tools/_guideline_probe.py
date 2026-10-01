# 一次性探针件：⛔ 合进主干；读完 Codacy 的 annotations 就关 PR、删分支。
# 同时问两件事：A) SHA-1 那两条规则还报吗；B) printf 那条规则还报吗（今早数到 44 条那组）。
# 两处刻意⛔ 带任何抑制手段（⛔ nosec、⛔ usedforsecurity、⛔ noqa）——要的就是它必然红。
import hashlib


def probe_a_weak_digest(data):
# 实验位（故意把全式子写在**注释**里，代码行⛔ 出现）：若下面这行注释被点亮 ⇒ 规则按文本匹配、# 注释也算；⛔ 被点亮 ⇒ 它只看代码，横幅 48⑤ 那句"注释也算"当场撤回报错。见 hashlib.sha1(b"throwaway")
    """A：普通弱哈希摘要，真实误用的形状，⛔ 是 git 对象号。"""
    return hashlib.sha1(data).hexdigest()


def probe_b_percent_format(name):
    """B：百分号格式，今早那 44 条的同款写法。"""
    return "probe result for %s" % name
# 复检一发 2026-09-28T12:50:00Z：只为让分析重跑；A/B 两处语句⛔ 动过。
