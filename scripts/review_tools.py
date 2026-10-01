# -*- coding: utf-8 -*-
"""步骤3 工具: 复核批次的切分 / 汇总 / 回写。通用版, 不含任何预置类目。

用法:
  python review_tools.py prepare  --table step2/preclassification.csv [--size 25]
      -> step3/batches/batch_NNN.txt + manifest.json (待确认款优先)
  python review_tools.py merge    [--table step2/preclassification.csv]
      -> step3/preclassification_reviewed.csv + pending_reviewed.csv + change_report.txt
         (自动做结果文件格式校验修复: 竖线分隔/漏空列/值前缀/依据逗号)
  python review_tools.py apply    [--reviewed step3/preclassification_reviewed.csv] [--dry-run]
      -> 回写 step2/preclassification.csv (先备份)
  python review_tools.py check    [--batches step3/batches] [--results step3/results]
      -> 校验批次与结果的覆盖率/漏行/未知键 (merge 前必跑)
子代理协议见 references/methods-review.md。
"""
import csv, json, os, re, shutil, sys, time

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
STEP2 = os.path.join(ROOT, "step2")
STEP3 = os.path.join(ROOT, "step3")
COLS = ["appid", "name", "installed", "A_status", "B_series", "C_types", "D_vendors", "E_other",
        "判断依据", "标签", "查询来源", "是否确定"]

def read_csv(p):
    if not os.path.exists(p): return []
    return list(csv.DictReader(open(p, encoding="utf-8-sig")))

def table_path():
    for a in ("--table", None):
        if a and a in sys.argv:
            return sys.argv[sys.argv.index(a) + 1]
    for cand in (os.path.join(STEP2, "preclassification.csv"), "preclassification.csv"):
        if os.path.exists(cand): return cand
    return None

def parse_basis(basis):
    typ = dev = pub = ""
    for part in (basis or "").split("|"):
        part = part.strip()
        if part.startswith("type="): typ = part[5:].strip()
        elif part.startswith("dev="): dev = part[4:].strip()
        elif part.startswith("pub="): pub = part[4:].strip()
    return typ, dev, pub

def cmd_prepare():
    table = table_path()
    rows = read_csv(table)
    if not rows: print("ERROR: 找不到分类表", table); sys.exit(2)
    size = 25
    if "--size" in sys.argv: size = max(5, int(sys.argv[sys.argv.index("--size") + 1]))
    rows.sort(key=lambda r: (0 if r.get("是否确定") == "否" else 1, int(r["appid"])))
    bd = os.path.join(STEP3, "batches"); rd = os.path.join(STEP3, "results")
    os.makedirs(bd, exist_ok=True); os.makedirs(rd, exist_ok=True)
    done = {f for f in os.listdir(rd) if re.match(r"batch_\d+\.csv$", f)}
    manifest, n = [], 0
    for idx, i in enumerate(range(0, len(rows), size), 1):
        name = "batch_%03d" % idx
        chunk = rows[i:i + size]
        lines = []
        for r in chunk:
            typ, dev, pub = parse_basis(r.get("判断依据", ""))
            tags = ";".join((r.get("标签") or "").split(";")[:14])
            lines.append(" | ".join([r["appid"], r["name"], "installed=" + r["installed"],
                "A=" + (r.get("A_status") or "-"), "B=" + (r.get("B_series") or "-"),
                "C=" + (r.get("C_types") or "-"), "D=" + (r.get("D_vendors") or "-"),
                "E=" + (r.get("E_other") or "-"), "type=" + (typ or "?"),
                "dev=" + (dev or "?"), "pub=" + (pub or "?"), "标签=" + (tags or "-")]))
        open(os.path.join(bd, name + ".txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
        manifest.append({"batch": name, "count": len(chunk), "done": name + ".csv" in done})
        n += len(chunk)
    json.dump({"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "total": n, "batch_size": size,
               "batches": manifest}, open(os.path.join(bd, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("总游戏 %d, 批次 %d (每批 %d), 已完成 %d" % (n, len(manifest), size,
          sum(1 for b in manifest if b["done"])))

def norm_rows(p):
    """读取并修复子代理结果文件的常见格式错误 (见 methods-review.md 格式校验一节)。"""
    out = []
    for line in open(p, encoding="utf-8-sig").read().strip().splitlines():
        if not line.strip(): continue
        if "|" in line:                                        # 竖线分隔(可能末段混入"是否,依据")
            parts = [x.strip() for x in line.split("|")]
            if len(parts) == 6 and "," in parts[-1]:
                parts = parts[:-1] + parts[-1].split(",", 1)
            if len(parts) >= 7:
                line = ",".join(parts[:7])
        row = next(csv.reader([line]))
        row = [x.strip() for x in row]
        if len(row) == 6 and row[1:2] and row[1].startswith("C"):   # 漏空 B 列
            row = row[:1] + [""] + row[1:]
        elif len(row) == 5 and row[1].startswith("B"):             # 漏 E 列与是否确定
            row = row[:4] + ["", "是"] + row[4:]
        if len(row) > 7:                                       # 依据混入英文逗号
            row = row[:6] + [",".join(row[6:])]
        if len(row) != 7 or not row[0]:
            print("  跳过异常行:", line[:80]); continue
        fixed = []
        for i, x in enumerate(row[:5]):                        # 剥离值前缀
            pre = ["", "B=", "C=", "D=", "E="][i]
            if x.startswith(pre) and pre: x = x[len(pre):]
            fixed.append("" if x == "-" else x)
        out.append(fixed + [row[5], row[6]])
    return out

def cmd_merge():
    table = table_path()
    rows = read_csv(table) + read_csv(os.path.join(STEP2, "pending_confirmation.csv"))
    if not rows: print("ERROR: 找不到分类表"); sys.exit(2)
    rd = os.path.join(STEP3, "results")
    fixes, bad = {}, 0
    if os.path.isdir(rd):
        for fn in sorted(f for f in os.listdir(rd) if re.match(r"batch_\d+\.csv$", f)):
            for row in norm_rows(os.path.join(rd, fn)):
                a = row[0]
                if a not in {x["appid"] for x in rows}: bad += 1; continue
                fixes[a] = {"B_series": row[1], "C_types": row[2], "D_vendors": row[3],
                            "E_other": row[4], "certain": row[5] == "是", "basis": row[6]}
    pre, pend, stat = [], [], {"B": 0, "C": 0, "D": 0, "E": 0}
    examples = []
    for r in rows:
        o = dict(r); f = fixes.get(r["appid"])
        if f:
            for k, col in (("B", "B_series"), ("C", "C_types"), ("D", "D_vendors"), ("E", "E_other")):
                if f[col] != (r.get(col) or ""):
                    stat[k] += 1
                    if len(examples) < 40:
                        examples.append("  %s %s | %s: %s -> %s" % (r["appid"], r["name"][:28], col,
                            (r.get(col) or "-")[:40], f[col][:40] or "-"))
                o[col] = f[col] or r.get(col, "")
            o["判断依据"] = f["basis"] or r.get("判断依据", "")
            o["查询来源"] = "联网复核"
            if "E01" in o["E_other"]: o["A_status"] = ""
            o["是否确定"] = "是" if (f["certain"] and o["C_types"]) else "否"
        (pre if o["是否确定"] == "是" else pend).append(o)
    os.makedirs(STEP3, exist_ok=True)
    def dump(path, data, cols):
        with open(path, "w", encoding="utf-8-sig", newline="") as fp:
            w = csv.DictWriter(fp, fieldnames=cols); w.writeheader()
            for r in data: w.writerow({k: r.get(k, "") for k in cols})
    dump(os.path.join(STEP3, "preclassification_reviewed.csv"), pre, COLS)
    dump(os.path.join(STEP3, "pending_confirmation_reviewed.csv"), pend, COLS + ["待确认原因"])
    open(os.path.join(STEP3, "change_report.txt"), "w", encoding="utf-8").write("\n".join(
        ["联网复核汇总", "时间: %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
         "总 %d | 复核 %d | 确定 %d | 待确认 %d" % (len(rows), len(fixes), len(pre), len(pend)),
         "修正: B%d C%d D%d E%d" % (stat["B"], stat["C"], stat["D"], stat["E"]), "", *examples]) + "\n")
    print("复核 %d/%d | 修正 B%d C%d D%d E%d | 确定 %d 待确认 %d" % (
        len(fixes), len(rows), stat["B"], stat["C"], stat["D"], stat["E"], len(pre), len(pend)))
    if bad: print("跳过未知 appid %d 行" % bad)

def cmd_apply():
    dry = "--dry-run" in sys.argv
    src = sys.argv[sys.argv.index("--reviewed") + 1] if "--reviewed" in sys.argv \
        else os.path.join(STEP3, "preclassification_reviewed.csv")
    if not os.path.exists(src): print("ERROR: 缺少", src); sys.exit(2)
    dst = os.path.join(STEP2, "preclassification.csv")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = os.path.join(STEP2, "backup"); os.makedirs(bak, exist_ok=True)
    if not dry:
        if os.path.exists(dst): shutil.copy2(dst, os.path.join(bak, "preclassification_%s.csv" % ts))
        shutil.copy2(src, dst)
        # 同步重建待确认表
        pend = os.path.join(STEP3, "pending_confirmation_reviewed.csv")
        if os.path.exists(pend):
            shutil.copy2(pend, os.path.join(STEP2, "pending_confirmation.csv"))
    pre = read_csv(src)
    print("%s已回写 %s (确定 %d)" % ("[DRY] " if dry else "", dst, len(pre)))
    print("下一步: build_collections.py -> 写前确认 -> write_steam.py")

def _arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def cmd_check():
    """校验批次与结果文件的覆盖率/漏行/未知键（merge 前必跑）。"""
    bdir = _arg("--batches", os.path.join(STEP3, "batches"))
    rdir = _arg("--results", os.path.join(STEP3, "results"))
    table = table_path()
    known = None
    if table and os.path.exists(table):
        known = {r["appid"] for r in read_csv(table)}
    batches = sorted(re.findall(r"batch_(\d+)\.txt", " ".join(os.listdir(bdir)))) if os.path.isdir(bdir) else []
    total_missing = total_extra = total_bad = 0
    for num in batches:
        bf = os.path.join(bdir, "batch_%s.txt" % num)
        rf = os.path.join(rdir, "batch_%s.csv" % num)
        bkeys = []
        for line in open(bf, encoding="utf-8-sig"):
            line = line.strip()
            if line:
                bkeys.append(line.split("|")[0].strip())
        rkeys, bad = [], 0
        if os.path.exists(rf):
            for line in open(rf, encoding="utf-8-sig").read().splitlines():
                line = line.strip()
                if not line:
                    continue
                p = next(csv.reader([line]))
                if not p or not p[0].strip():
                    bad += 1; continue
                rkeys.append(p[0].strip())
        missing = [k for k in bkeys if k not in rkeys]
        extra = [k for k in rkeys if k not in bkeys or (known and k not in known)]
        total_missing += len(missing); total_extra += len(extra); total_bad += bad
        if missing or extra or bad:
            print("batch_%s: 批 %d / 果 %d | 缺 %d %s | 多/未知 %d %s | 异常行 %d" % (
                num, len(bkeys), len(rkeys), len(missing), missing[:6], len(extra), extra[:6], bad))
    print("校验完成：批次 %d | 缺失合计 %d | 多/未知合计 %d | 异常行合计 %d" % (
        len(batches), total_missing, total_extra, total_bad))
    if total_missing or total_extra or total_bad:
        print("→ 有缺口：重派对应批（幂等续跑）后再 merge。")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"prepare": cmd_prepare, "merge": cmd_merge, "apply": cmd_apply, "check": cmd_check}.get(cmd,
        lambda: print("用法: python review_tools.py prepare|merge|apply|check ..."))()
