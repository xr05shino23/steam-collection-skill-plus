# -*- coding: utf-8 -*-
"""类目体检：计算同一维度内两两类目的重叠（Jaccard），并对高重叠告警。

用法:
  python scripts/overlap_check.py                 # 打印 C 维度体检
  python scripts/overlap_check.py --group D       # 指定维度
  python scripts/overlap_check.py --write         # 写 step2/overlap_matrix.md
  python scripts/overlap_check.py --threshold 0.25
"""
import argparse, csv, itertools, os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
FIELD = {"A": "A_status", "B": "B_series", "C": "C_types", "D": "D_vendors", "E": "E_other", "F": "F_tags"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default=os.path.join(ROOT, "step2", "preclassification.csv"))
    ap.add_argument("--defs", default=os.path.join(ROOT, "step2", "categories.json"))
    ap.add_argument("--group", default="C")
    ap.add_argument("--threshold", type=float, default=0.25)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    g = a.group.upper()
    col = FIELD.get(g, "C_types")
    rows = list(csv.DictReader(open(a.table, encoding="utf-8-sig")))
    mem = {}
    for r in rows:
        for c in (r.get(col) or "").split(";"):
            c = c.strip()
            if c:
                mem.setdefault(c, set()).add(r["appid"])
    codes = sorted(mem)
    pairs = []
    for x, y in itertools.combinations(codes, 2):
        A, B = mem[x], mem[y]
        if not (A | B):
            continue
        pairs.append((len(A & B) / len(A | B), x, y, len(A & B)))
    pairs.sort(reverse=True)

    from collections import Counter
    dist = Counter(sum(1 for c in (r.get(col) or "").split(";") if c.strip()) for r in rows)
    avg = sum(sum(1 for c in (r.get(col) or "").split(";") if c.strip()) for r in rows) / max(1, len(rows))
    warn = [p for p in pairs if p[0] > a.threshold]

    L = ["# %s 维度类目体检" % g, "",
         "游戏 %d 款 | 类目 %d 个 | 每款平均 %.2f 个 | 类数分布 %s" % (
             len(rows), len(codes), avg, dict(sorted(dist.items()))), "",
         "## 重叠告警（Jaccard > %.2f）：%d 对" % (a.threshold, len(warn)), "",
         "| A | B | Jaccard | 同时属于 | |A| | |B| |", "|---|---|---|---|---|---|"]
    for j, x, y, ab in warn:
        L.append("| %s | %s | %.3f | %d | %d | %d |" % (x, y, j, ab, len(mem[x]), len(mem[y])))
    L += ["", "## 全部重叠 TOP20", "", "| A | B | Jaccard | 同时属于 |", "|---|---|---|---|"]
    for j, x, y, ab in pairs[:20]:
        L.append("| %s | %s | %.3f | %d |" % (x, y, j, ab))
    L += ["", "## 各类目成员数", ""] + ["- %s：%d" % (c, len(mem[c])) for c in codes]
    text = "\n".join(L) + "\n"

    if a.write:
        out = os.path.join(ROOT, "step2", "overlap_matrix.md")
        open(out, "w", encoding="utf-8").write(text)
        print("已写入", out)
    print("维度 %s | 类目 %d | 平均每款 %.2f 个 | 高重叠告警 %d 对 (>%.2f)" % (g, len(codes), avg, len(warn), a.threshold))
    for j, x, y, ab in warn[:10]:
        print("   %s + %s : %.3f (both=%d)" % (x, y, j, ab))


if __name__ == "__main__":
    main()
