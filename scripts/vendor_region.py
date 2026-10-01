# -*- coding: utf-8 -*-
"""厂商兜底类细化工具：国别判定 + 名厂独立成类。

子命令:
  prepare   从兜底类抽取去重工作室，切批次供子代理联网判国别
  merge     汇总国别结果 -> studio_region.json，并把中国厂商并入目标类
  classify  直接按 studio_region.json 把已知厂商并入目标类（增量/离线，无需联网）
  split     给定厂商清单(JSON)，逐个新增 D 类并迁移对应游戏

通用参数:
  --table   分类表路径 (默认 step2/preclassification.csv)
  --meta    元数据 CSV (默认 step2/parsed_meta.csv，列含 developer/publisher)
  --fallback 兜底类编码 (默认 D99)
  --work    工作目录 (默认 step3/vendors)
  --apply   真正写文件；缺省只做预览

详见 references/vendor-region.md。
"""
import argparse, csv, glob, json, os, re, shutil, sys, time

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
NON_STUDIO = {"", "-", "?", "N/A", "Unknown", "本游戏已经下架退市"}
REGIONS = ("CN", "JP", "KR", "EUUS", "OTHER")


def paths(a):
    table = a.table or os.path.join(ROOT, "step2", "preclassification.csv")
    meta = a.meta or os.path.join(ROOT, "step2", "parsed_meta.csv")
    work = a.work or os.path.join(ROOT, "step3", "vendors")
    return table, meta, work


def read_csv(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig")))


def backup(p):
    bak = os.path.join(os.path.dirname(p), "backup")
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p, os.path.join(bak, "%s_%s" % (os.path.basename(p), time.strftime("%Y%m%d_%H%M%S"))))


def cmd_prepare(a):
    table, meta, work = paths(a)
    rows = read_csv(table)
    m = {r["appid"]: r for r in read_csv(meta)}
    sel = [r for r in rows if a.fallback in (r.get("D_vendors") or "").split(";")]
    studios = {}
    for r in sel:
        d = m.get(r["appid"], {})
        for key in ("developer", "publisher"):
            nm = (d.get(key) or "").strip()
            if not nm:
                continue
            e = studios.setdefault(nm, [])
            if r["name"] not in e:
                e.append(r["name"])
    items = sorted(studios.items(), key=lambda kv: -len(kv[1]))
    os.makedirs(work, exist_ok=True)
    bd = os.path.join(work, "batches")
    os.makedirs(bd, exist_ok=True)
    with open(os.path.join(work, "studios.csv"), "w", encoding="utf-8-sig", newline="") as fp:
        w = csv.writer(fp); w.writerow(["name", "game_count", "sample"])
        for nm, games in items:
            w.writerow([nm, len(games), ";".join(games[:3])])
    manifest = []
    for idx, i in enumerate(range(0, len(items), a.size), 1):
        name = "batch_%03d" % idx
        lines = ["%d | %s | 关联游戏数=%d | 示例=%s" % (i + j + 1, nm, len(g), ";".join(g[:3]))
                 for j, (nm, g) in enumerate(items[i:i + a.size])]
        open(os.path.join(bd, name + ".txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
        manifest.append({"batch": name, "count": len(lines)})
    json.dump({"total_studios": len(items), "batch_size": a.size, "batches": manifest},
              open(os.path.join(bd, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[%s] 游戏 %d | 去重工作室 %d | 批次 %d | 输出 %s" % (
        a.fallback, len(sel), len(items), len(manifest), work))


def load_studio_region(work, fallback):
    """从 results/*.csv(序号,地区,依据) 与 studios.csv 重建 工作室->{region,reason}。"""
    names = [r["name"] for r in read_csv(os.path.join(work, "studios.csv"))]
    idx2name = {i + 1: n for i, n in enumerate(names)}
    out = {}
    for fp in sorted(glob.glob(os.path.join(work, "results", "batch_*.csv"))):
        for line in open(fp, encoding="utf-8-sig").read().splitlines():
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            p = [x.strip() for x in next(csv.reader([line]))]
            if len(p) >= 2 and p[1] in REGIONS and int(p[0]) in idx2name:
                out[idx2name[int(p[0])]] = {"region": p[1], "reason": ",".join(p[2:])}
    return out


def apply_move(a, pairs, label):
    """pairs: {appid: set(codes)} 目标 D 编码集合（替换兜底类）。"""
    table, meta, work = paths(a)
    rows = read_csv(table)
    m = {r["appid"]: r for r in read_csv(meta)}
    changes = []
    for r in rows:
        codes = [x for x in (r.get("D_vendors") or "").split(";") if x]
        if a.fallback not in codes:
            continue
        d = m.get(r["appid"], {})
        hit = pairs.get(r["appid"])
        if not hit:
            continue
        new = [c for c in codes if c != a.fallback] + sorted(hit)
        changes.append((r["appid"], r["name"], ";".join(new), ";".join(sorted(hit)), d.get("developer", ""), d.get("publisher", "")))
    print("[%s] 命中 %d 款游戏" % (label, len(changes)))
    for c in changes[:15]:
        print("   ", c[0], c[1][:26], "->", c[2], "|", c[3])
    if not a.apply:
        print("  [预览] 未改文件。加 --apply 生效。")
        return
    backup(table)
    gmap = {c[0]: c[2] for c in changes}
    for r in rows:
        if r["appid"] in gmap:
            r["D_vendors"] = gmap[r["appid"]]
    with open(table, "w", encoding="utf-8-sig", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=list(rows[0].keys())); w.writeheader()
        for r in rows: w.writerow(r)
    print("  已回写", table)


def cmd_merge(a):
    table, meta, work = paths(a)
    region = load_studio_region(work, a.fallback)
    json.dump(region, open(os.path.join(work, "studio_region.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    cn = {n for n, v in region.items() if v["region"] == "CN" and n not in NON_STUDIO}
    print("国别覆盖 %d | CN=%d | 目标类=%s" % (len(region), len(cn), a.target))
    rows = read_csv(table); m = {r["appid"]: r for r in read_csv(meta)}
    pairs = {}
    for r in rows:
        if a.fallback not in (r.get("D_vendors") or "").split(";"):
            continue
        d = m.get(r["appid"], {})
        if {s for s in ((d.get("developer") or "").strip(), (d.get("publisher") or "").strip()) if s} & cn:
            pairs[r["appid"]] = {a.target}
    apply_move(a, pairs, "国别合并")


def cmd_classify(a):
    """按已有 studio_region.json 离线回填（增量用）。"""
    table, meta, work = paths(a)
    region = json.load(open(os.path.join(work, "studio_region.json"), encoding="utf-8"))
    known = {n for n, v in region.items() if v.get("region") == "CN" and n not in NON_STUDIO}
    rows = read_csv(table); m = {r["appid"]: r for r in read_csv(meta)}
    pairs = {}
    for r in rows:
        if a.fallback not in (r.get("D_vendors") or "").split(";"):
            continue
        d = m.get(r["appid"], {})
        if {s for s in ((d.get("developer") or "").strip(), (d.get("publisher") or "").strip()) if s} & known:
            pairs[r["appid"]] = {a.target}
    apply_move(a, pairs, "离线回填")


def cmd_split(a):
    table, meta, work = paths(a)
    vendors = json.load(open(a.list, encoding="utf-8-sig"))
    rows = read_csv(table); m = {r["appid"]: r for r in read_csv(meta)}
    per = {v["code"]: 0 for v in vendors}
    pairs = {}
    for r in rows:
        if a.fallback not in (r.get("D_vendors") or "").split(";"):
            continue
        d = m.get(r["appid"], {})
        text = (d.get("developer") or "") + " || " + (d.get("publisher") or "")
        hit = [v["code"] for v in vendors if re.search(v["pattern"], text, re.I)]
        if hit:
            pairs[r["appid"]] = set(hit)
            for c in hit:
                per[c] += 1
    print("[split] 新增 D 类 %d 个 | 命中 %d 款" % (len(vendors), len(pairs)))
    for c, n in per.items():
        if n:
            print("   %s : %d" % (c, n))
    if not a.apply:
        print("  [预览] 未改文件。加 --apply 生效（会同步 categories.json/.md/rules）。")
        return
    # 更新类目定义
    pj = os.path.join(ROOT, "step2", "categories.json")
    if os.path.exists(pj):
        defs = json.load(open(pj, encoding="utf-8"))
        idx = next((i for i, d in enumerate(defs) if d["code"] == a.fallback), len(defs))
        have = {d["code"] for d in defs}
        add = [{"code": v["code"], "name": "%s %s" % (v["code"], v["name"]), "group": v["code"][0],
                "installedOnly": False, "exclusive": False} for v in vendors if v["code"] not in have]
        json.dump(defs[:idx] + add + defs[idx:], open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pr = os.path.join(ROOT, "step2", "categories_rules.json")
    if os.path.exists(pr):
        rules = json.load(open(pr, encoding="utf-8"))
        for v in vendors:
            rules.setdefault("D", {})[v["code"]] = v["pattern"]
        json.dump(rules, open(pr, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    pm = os.path.join(ROOT, "step2", "categories.md")
    if os.path.exists(pm):
        lines = open(pm, encoding="utf-8").read().splitlines(); out = []
        for ln in lines:
            if ln.startswith("- %s " % a.fallback):
                for v in vendors:
                    out.append("- %s %s  匹配: %s" % (v["code"], v["name"], v["pattern"]))
            out.append(ln)
        open(pm, "w", encoding="utf-8").write("\n".join(out) + "\n")
    apply_move(a, pairs, "名厂独立")


def main():
    p = argparse.ArgumentParser(description="厂商兜底类细化工具")
    p.add_argument("cmd", choices=["prepare", "merge", "classify", "split"])
    p.add_argument("--table"); p.add_argument("--meta"); p.add_argument("--work")
    p.add_argument("--fallback", default="D99"); p.add_argument("--target", default="D21")
    p.add_argument("--size", type=int, default=45); p.add_argument("--list")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    {"prepare": cmd_prepare, "merge": cmd_merge, "classify": cmd_classify, "split": cmd_split}[a.cmd](a)


if __name__ == "__main__":
    main()
