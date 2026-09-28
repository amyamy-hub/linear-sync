# 一次性探针件：⛔ 合进主干；读完 Codacy 的 annotations 就关 PR、删分支。
# 同时问两件事：A) SHA-1 那两条规则还报吗；B) printf 那条规则还报吗（今早数到 44 条那组）。
# 两处刻意⛔ 带任何抑制手段（⛔ nosec、⛔ usedforsecurity、⛔ noqa）——要的就是它必然红。
import hashlib


def probe_a_weak_digest(data):
    """A：普通弱哈希摘要，真实误用的形状，⛔ 是 git 对象号。"""
    return hashlib.sha1(data).hexdigest()


def probe_b_percent_format(name):
    """B：百分号格式，今早那 44 条的同款写法。"""
    return "probe result for %s" % name
