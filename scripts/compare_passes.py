# -*- coding: utf-8 -*-
"""两遍独立复核结果比对：逐款找出判定不一致，供人工/第三遍裁决。

适用任意"每行首列=键、末列=依据、中间为判定列"的结果格式（步骤3 的 7 列、
厂商国别的 3 列等都行）。

用法:
  python scripts/compare_passes.py --a step3/results --b step3/results2
  python scripts/compare_passes.py --a A --b B --table step2/preclassification.csv --out step3
输出:
  <out>/disagreements.csv  <out>/compare_report.md
"""
import argparse, csv, glob, os


def load(d):
    out = {}
    for fp in sorted(glob.glob(os.path.join(d, "batch_*.csv"))):
        for line in open(fp, encoding="utf-8-sig").read().splitlines():
            line = line.strip()
            if not line:
                continue
            p = [x.strip() for x in next(csv.reader([line]))]
            if len(p) < 2 or not p[0]:
                continue
            out[p[0]] = (tuple(p[1:-1]), p[-1])   # (判定列, 依据)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--table", default="")
    ap.add_argument("--out", default=".")
    a = ap.parse_args()

    A, B = load(a.a), load(a.b)
    names = {}
    if a.table and os.path.exists(a.table):
        names = {r.get("appid"): r.get("name") for r in csv.DictReader(open(a.table, encoding="utf-8-sig"))}
    common = sorted(set(A) & set(B))
    diff = [k for k in common if A[k][0] != B[k][0]]
    only_a = sorted(set(A) - set(B)); only_b = sorted(set(B) - set(A))
    os.makedirs(a.out, exist_ok=True)

    with open(os.path.join(a.out, "disagreements.csv"), "w", encoding="utf-8-sig", newline="") as fp:
        w = csv.writer(fp); w.writerow(["key", "name", "passA", "passB", "reasonA", "reasonB"])
        for k in diff:
            w.writerow([k, names.get(k, ""), ";".join(A[k][0]), ";".join(B[k][0]), A[k][1], B[k][1]])

    L = ["# 两遍复核比对", "",
         "A: %s（%d） | B: %s（%d） | 共同：%d" % (a.a, len(A), a.b, len(B), len(common)),
         "**不一致（需定夺）：%d**" % len(diff), ""]
    if only_a or only_b:
        L += ["- 仅 A 有：%s" % (",".join(only_a) or "-"), "- 仅 B 有：%s" % (",".join(only_b) or "-"), ""]
    L += ["| key | 名称 | 一遍 | 二遍 |", "|---|---|---|---|"]
    for k in diff:
        L.append("| %s | %s | %s | %s |" % (k, (names.get(k, "") or "")[:26], ";".join(A[k][0]), ";".join(B[k][0])))
    open(os.path.join(a.out, "compare_report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("A=%d B=%d common=%d 不一致=%d -> %s/disagreements.csv" % (len(A), len(B), len(common), len(diff), a.out))


if __name__ == "__main__":
    main()
