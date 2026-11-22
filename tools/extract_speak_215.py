#!/usr/bin/env python3
"""从《2024新版PET口语215话题（附参考答案）》文本层提取结构化数据。

输出（data-src/speak/）：
  part1_85.json     — 归类话题85题（问题 en + 题目译文 cn + 参考答案）
  part1_130.json    — 口语表达130题范文（问题 + 完整范文段落）

红线：只做解析与切分，内容零改写；OCR/文本读不通的条目原样跳过并在报告中列出。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_work/speak_textbooks/_extract_215topics.txt"
OUT = ROOT / "data-src/speak"

pages: dict[int, str] = {}
cur = 0
for line in SRC.read_text(encoding="utf-8").splitlines():
    m = re.match(r"===== PAGE (\d+) =====", line)
    if m:
        cur = int(m.group(1))
        pages[cur] = []
    elif cur:
        pages[cur].append(line)
pages = {k: "\n".join(v) for k, v in pages.items()}

# ---------- 第一部分：归类话题85题（p2-p10 题目列表；p11-p43 参考答案） ----------
# 题目列表：形如 "12.What subject do you like best? / Do you like maths?"
# 存在两种坑：① 粘连行 "...house?59. Which of..."；② 跨行续行（无题号开头）
q_map: dict[int, str] = {}
for p in range(2, 12):
    body = pages.get(p, "")
    for line in body.splitlines():
        line = line.strip()
        if not line or "题目译文" in line or "参考答案" in line or "Part 1" in line:
            continue
        # 拆粘连：?59. / !61. 等（英文标点后紧跟题号）
        for seg in re.split(r"(?<=[?!.])\s*(?=\d{1,3}\.\s*[A-Z\u4e00-\u9fff])", line):
            m = re.match(r"^(\d{1,3})\.(.+)$", seg)
            if m:
                n = int(m.group(1))
                q_map[n] = (q_map.get(n, "") + " " + m.group(2).strip()).strip()
            elif q_map:
                # 续行：并入最近的题（可能题号更大，视为下一题的续行也并入其前驱）
                last = max(q_map)
                q_map[last] = (q_map[last] + " " + seg).strip()

qa_raw: dict[int, dict] = {}
for p in range(11, 44):
    body = pages.get(p, "")
    # 形如 "12.题目译文:..." 与 "参考答案:..."
    for m in re.finditer(r"(\d+)\.\s*题目译文[:：]\s*(.+)", body):
        n = int(m.group(1))
        qa_raw.setdefault(n, {})["cn"] = m.group(2).strip()
    for m in re.finditer(r"参考答案[:：]\s*(.+?)(?=(?:\d+\.\s*题目译文)|$)", body, re.S):
        n = int(qa_raw and 0)  # placeholder, 顺序无法对齐，改用逐题切分
        break
    break

# 更稳的逐题切分：PDF 文本层会把多位数题号拆开（"12." → "1"+"2."），
# 因此用 finditer 找 "题目译文"，回溯收集其前面可能跨行的题号数字
body_all = "\n".join(pages.get(p, "") for p in range(11, 44))
body_all = re.sub(r"===== PAGE \d+ =====", "", body_all)
num_pat = re.compile(r"((?:\d\s*){1,3})\.\s*题\s*目\s*译\s*文")
marks = [(int(m.group(1).replace("\n", "").replace(" ", "")), m.start()) for m in num_pat.finditer(body_all)]
chunks = []
for idx, (n, pos) in enumerate(marks):
    end = marks[idx + 1][1] if idx + 1 < len(marks) else len(body_all)
    chunks.append((n, body_all[pos:end]))
skipped_85 = []
part1_85 = []
for n, ch in chunks:
    m = re.match(r"\s*\d+\s*\.\s*题\s*目\s*译\s*文\s*[:：]\s*(.*?)\s*参考答案[:：]\s*(.*)", ch, re.S)
    if not m:
        continue
    cn = re.sub(r"\s+", " ", m.group(1)).strip()
    ans = re.sub(r"[ \t]+", " ", m.group(2)).strip()
    ans = re.sub(r"\n{2,}", "\n", ans)
    ans = re.sub(r"\n?(?:@?Daniel 老师|版权登记| KP 成长营).*$", "", ans)
    if n <= 85 and ans:
        part1_85.append({"no": n, "q": q_map.get(n, ""), "cn": cn, "ans": ans})
    elif n <= 85:
        skipped_85.append(n)

part1_85.sort(key=lambda x: x["no"])

missing_q = [x["no"] for x in part1_85 if not x["q"]]
print(f"题干列表解析到 {len(q_map)} 条；缺题干的答案条目: {missing_q}")
dup = [n for n in {x['no'] for x in part1_85} if [y['no'] for y in part1_85].count(n) > 1]
print(f"重复题号: {dup}")

# 分类标签：p2-10 中形如 "问候(Greetings)" 的行，按最大题号划段
categories: list[dict] = []
for p in range(2, 12):
    body = pages.get(p, "")
    for line in body.splitlines():
        m = re.match(r"^([\u4e00-\u9fff]{2,8})\(([^)]+)\)\s*$", line.strip())
        if m:
            categories.append({"cn": m.group(1), "en": m.group(2), "max_no": None})
# 分类后遇到的最大题号即该类上界
nums = sorted(q_map)
cat_ranges = []
ci = 0
for n in nums:
    pass  # 分类行不与题号同页对齐，改用题号分段（见下）
# 直接按分类出现顺序 × 题号分段：第 i 类覆盖到下一个分类首页号-1；
# 由于跨页无法精确对齐，用启发式：分类总数 17，题号 1-85 均分不成立，
# 改为按 q_map 行序：分类行出现在题号 N 之前，则该类从 N 开始。
# 重新按页序扫描，同时记录行内题号：
cat2: list[dict] = []
for p in range(2, 12):
    body = pages.get(p, "")
    for line in body.splitlines():
        line = line.strip()
        mc = re.match(r"^([\u4e00-\u9fff]{2,8})\(([^)]+)\)\s*$", line)
        if mc:
            cat2.append({"cn": mc.group(1), "en": mc.group(2), "from": None, "to": None})
            continue
        mq = re.match(r"^(\d{1,3})[.．](.+)$", line)
        if mq and cat2 and cat2[-1]["from"] is None:
            cat2[-1]["from"] = int(mq.group(1))
for i, c in enumerate(cat2):
    c["to"] = cat2[i + 1]["from"] - 1 if i + 1 < len(cat2) else 85
categories = [c for c in cat2 if c["from"]]
print(f"分类: {len(categories)} 组 -> " + ", ".join(f"{c['cn']}{c['from']}-{c['to']}" for c in categories))

# ---------- 第二部分：口语表达130题范文（p44-p69） ----------
body130 = "\n".join(pages.get(p, "") for p in range(44, 70))
# 形如 "1. Do you like sports?..."（注意部分题号用全角句号 "58．"）到下一题
chunks = re.split(r"\n\s*(\d{1,3})\s*[.．]\s*", body130)
part1_130 = []
skipped_130 = []
i = 1
while i < len(chunks) - 1:
    n = int(chunks[i])
    rest = chunks[i + 1]
    lines = rest.strip().splitlines()
    if lines:
        q = re.sub(r"\s+", " ", lines[0]).strip()
        ans = "\n".join(l.strip() for l in lines[1:] if l.strip())
        if q and ans:
            part1_130.append({"no": n, "q": q, "ans": ans})
        else:
            skipped_130.append(n)
    i += 2
part1_130.sort(key=lambda x: x["no"])
# 原书编号笔误：51 出现两次（两条内容均真实），第二条编号记为 51b
seen: set[int] = set()
for it in part1_130:
    if it["no"] in seen:
        it["no_orig"] = it["no"]
        it["no"] = f"{it['no']}b"
    seen.add(it["no"] if isinstance(it["no"], int) else 0)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "part1_85.json").write_text(
    json.dumps({"source": "2024新版PET口语215话题（附参考答案）p2-43", "categories": categories, "items": part1_85}, ensure_ascii=False, indent=1),
    encoding="utf-8")
(OUT / "part1_130.json").write_text(
    json.dumps({"source": "2024新版PET口语215话题（附参考答案）p44-69", "items": part1_130}, ensure_ascii=False, indent=1),
    encoding="utf-8")

print(f"85题: {len(part1_85)} 条（跳过 {sorted(set(range(1,86)) - {x['no'] for x in part1_85})}）")
print(f"130范文: {len(part1_130)} 条（跳过 {skipped_130}）")
for j in part1_85[:2] + part1_130[:2]:
    print(json.dumps(j, ensure_ascii=False)[:200])
