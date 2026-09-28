# -*- coding: utf-8 -*-
"""把 HEAD 上"还活着的凭据指纹"擦掉（历史版本⛔ 能改，那是第 51 条⑥说过的不可撤回）。
   每处替换都断言命中次数，⛔ 一条正则悄悄改掉别处；改完立刻用同一套闸复算。
   原则：⛔ 值、⛔ 长度、⛔ 前缀、⛔ 两头、⛔ 哈希前缀；**指路牌（文件在哪）保留**——
   那是工作必需的指针，删了下一个人就得重新猜。"""
import hashlib
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "HANDOFF.md")
DST = os.path.join(ROOT, "HANDOFF_scrub.md")   # 写完请人复核后再覆盖回 HANDOFF.md
text = io.open(SRC, encoding="utf-8").read()
before = text

EDITS = [
    # 1) 现行 SYNC_TOKEN：长度＋前缀
    (r"新值 48 位 hex、前缀 `[0-9a-fA-F]{2,}`",
     "新值是一把 hex 令牌（长度与前缀⛔ 在这里念，登记在私有侧回执）"),
    # 2) 退役 SYNC_TOKEN：两头＋长度
    (r"旧值 `[0-9a-fA-F]{2,}…[0-9a-fA-F]{2,}`\*\*（36 hex",
     "旧值（两头与长度⛔ 在这里念，登记在私有侧回执；位数这一档也⛔ 复述"),
    # 3) Notion 只读令牌：长度＋两头
    (r"50 字符 `ntn_[0-9A-Za-z]{1,8}…[0-9A-Za-z]{1,8}`",
     "（长度与前两头⛔ 在这里念，登记在私有侧回执）"),
    # 4) 横幅 52③ 我自己新犯的那处：两把令牌的 sha256 前缀
    (r"sha256 前缀 `[0-9a-fA-F]{6,}` → `[0-9a-fA-F]{6,}`（⛔ 反推值，只证\x22⛔ 同一把\x22）",
     "sha256 前缀两把不同（两个前缀本身⛔ 在这里念，登记在私有侧回执）"),
    # 5) 09-24 那两处复述前缀的更正（B2 那把尺⛔ 够得着——它要求同行有"前缀"字样，这两处没有）
    (r"前缀 `[0-9a-fA-F]{4}`、48 位", "前缀与长度（⛔ 在这里念）"),
    (r"前缀 `[0-9a-fA-F]{4}`", "前缀（⛔ 在这里念）"),
    (r"（`[0-9a-fA-F]{4}` 开头）", "（前缀⛔ 在这里念）"),
    (r"之前你让我存了 `[0-9a-fA-F]{4}` 了", "之前你让我存了那把（前缀⛔ 在这里念）"),
    # 6) 那句"教下家怎么念指纹"的防呆——它本身就是这三处泄漏的来源
    (r"要证明它还在，只打印长度与前 4 后 4。",
     "要证明它还在，只报「在 / ⛔ 在」；⛔ 打印长度、前缀、两头、哈希前缀"
     "（这一句原来写的是\x22只打印长度与前 4 后 4\x22——横幅 51② 那三处指纹就是照它念出去的，09-28 改掉）"),
]

counts = []
for pat, rep in EDITS:
    n = len(re.findall(pat, text))
    assert n >= 1, f"这一条⛔ 命中任何地方 ⇒ 要么已被前一条吃掉，要么我记错了形状：{pat[:40]}"
    counts.append((pat[:34], n))
    text = re.sub(pat, rep, text)

assert b"\r" not in text.encode("utf-8")
io.open(DST, "w", encoding="utf-8", newline="\n").write(text)
d = io.open(DST, "rb").read()
print("替换次数登记：")
for p, n in counts:
    print(f"   {n} × {p}…")
print(f"字节 {len(before.encode('utf-8'))} → {len(d)}（{len(d)-len(before.encode('utf-8')):+d}）"
      f"  LF={d.count(b(chr(10))) if False else d.count(b'\n')} CR={d.count(b'\r')}")
print("blob=%s" % hashlib.sha1(b"blob %d\0" % len(d) + d).hexdigest()[:12])
