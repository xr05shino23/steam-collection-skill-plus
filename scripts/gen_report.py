# -*- coding: utf-8 -*-
import csv, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "step2")
rows = list(csv.DictReader(open(os.path.join(S, "preclassification.csv"), encoding="utf-8-sig")))
defs = json.load(open(os.path.join(S, "categories.json"), encoding="utf-8"))
FIELD = {"A": "A_status", "B": "B_series", "C": "C_types", "D": "D_vendors", "E": "E_other", "F": "F_tags"}
byname = {r["appid"]: r for r in rows}

lines = ["# Steam 收藏集分类总表", "",
         "共 %d 款游戏，%d 个收藏集。每款游戏的完整归属见文末。  " % (len(rows), len(defs)),
         "（B/C/D 可多选，A 互斥）", ""]

for g, gt in [("A", "A 状态"), ("B", "B 系列"), ("C", "C 类型"), ("D", "D 厂商"), ("E", "E 其他"), ("F", "F 特性")]:
    gl = [d for d in defs if d["group"] == g]
    if not gl:
        continue
    lines.append("## %s" % gt)
    lines.append("")
    for d in gl:
        mem = [r for r in rows if d["code"] in (r.get(FIELD[g]) or "").split(";")]
        if not mem:
            continue
        lines.append("### %s（%d）" % (d["name"], len(mem)))
        for r in sorted(mem, key=lambda x: x["name"].lower()):
            src = "共享" if r.get("source") == "shared" else "自有"
            lines.append("- %s 〔%s〕" % (r["name"], src))
        lines.append("")

lines.append("## 逐款总表（%d 款）" % len(rows))
lines.append("")
lines.append("| appid | 游戏 | 来源 | A | B | C | D | F |")
lines.append("|---|---|---|---|---|---|---|---|")
name_of = {d["code"]: d["name"].split("-", 1)[-1] for d in defs}
for r in sorted(rows, key=lambda x: x["name"].lower()):
    def cn(s):
        return "、".join(name_of.get(c, c) for c in (s or "").split(";") if c)
    lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
        r["appid"], r["name"], "共享" if r.get("source") == "shared" else "自有",
        cn(r["A_status"]), cn(r["B_series"]), cn(r["C_types"]), cn(r["D_vendors"]), cn(r["F_tags"])))

out = os.path.join(ROOT, "step4", "分类总表.md")
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8").write("\n".join(lines))
print("saved ->", out, "| lines:", len(lines))
