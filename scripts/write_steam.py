# -*- coding: utf-8 -*-
"""步骤4: 把收藏集写入 Steam 云存储。守卫(Steam 运行检测) + 双备份 + 原子写入。

用法: python write_steam.py [--dry-run] [--force]
前置: step4/steam_collections.json 已生成; 用户已在写前确认清单上同意; Steam 已完全退出。
"""
import json, os, sys, time, shutil, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
NEW = os.path.join(os.path.dirname(BASE), "step4", "steam_collections.json")
BACKUP_DIR = os.path.join(os.path.dirname(BASE), "step4", "backup")

def load_cfg():
    c = {"steamid32": "", "steamid64": "", "steam_root": ""}
    f = os.path.join(BASE, "local_config.json")
    if os.path.exists(f):
        try: c.update({k: v for k, v in json.load(open(f, encoding="utf-8")).items() if k in c})
        except Exception: pass
    for k, e in (("steamid32", "STEAM_ID32"), ("steamid64", "STEAM_ID64"), ("steam_root", "STEAM_ROOT")):
        if os.environ.get(e): c[k] = os.environ[e]
    return c

def target_path(c):
    root = c["steam_root"]
    if not root:
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
            root = winreg.QueryValueEx(k, "SteamPath")[0]
        except Exception: pass
    # userdata 目录名是 SteamID32；缺 steamid32 时由 steamid64 换算
    if c.get("steamid32"):
        sid = str(c["steamid32"])
    else:
        sid = str(int(c["steamid64"]) - 76561197960265728)
    assert root and sid, "缺少 steam_root 与 steamid32/steamid64 配置"
    return os.path.join(root, "userdata", sid, "config", "cloudstorage",
                        "cloud-storage-namespace-1.json")

def steam_running():
    """True=运行中 False=未运行 None=无法判定 (三重交叉检测)。"""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            "(Get-Process -Name steam,steamwebhelper,steamservice -ErrorAction SilentlyContinue | Measure-Object).Count"],
            capture_output=True, text=True, timeout=25)
        out = (r.stdout or "").strip().splitlines()
        if out and out[-1].strip().isdigit(): return int(out[-1].strip()) > 0
    except Exception: pass
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
            "(Get-ItemProperty -Path 'HKCU:\\Software\\Valve\\Steam\\ActiveProcess' -ErrorAction SilentlyContinue).ActiveUser"],
            capture_output=True, text=True, timeout=25)
        t = (r.stdout or "").strip()
        if t: return t not in ("0", "")
    except Exception: pass
    try:
        out = subprocess.check_output(["tasklist"], text=True, errors="ignore")
        return "steam.exe" in out.lower()
    except Exception: pass
    return None

def main():
    dry = "--dry-run" in sys.argv
    tgt = target_path(load_cfg())
    run = steam_running()
    if run is not False:
        print("REFUSE: %s。请完全退出 Steam (含托盘 steamwebhelper/steamservice) 后重试; 确认已退出可 --force。"
              % ("Steam 正在运行" if run else "无法确认 Steam 是否已退出"))
        if "--force" not in sys.argv: sys.exit(2)
    if not os.path.exists(tgt):
        print("REFUSE: 找不到目标文件:", tgt); sys.exit(3)
    orig = json.load(open(tgt, encoding="utf-8"))
    if not isinstance(orig, list):
        print("REFUSE: 目标文件结构不是数组"); sys.exit(4)
    new = json.load(open(NEW, encoding="utf-8"))
    # 保护 Steam 内置收藏集（收藏夹/已隐藏），其余 user-collections.* 才移除
    protect = {"user-collections.favorite", "user-collections.hidden"}

    def is_removable(e):
        return (isinstance(e, list) and e and str(e[0]).startswith("user-collections")
                and str(e[0]) not in protect)

    removed = [str(e[0]) for e in orig if is_removable(e)]
    keep = [e for e in orig if not is_removable(e)]
    merged = keep + new
    keys = [e[0] for e in merged if isinstance(e, list) and e]
    assert len(keys) == len(set(keys)), "存在重复 key, 中止"
    blob = json.dumps(merged, ensure_ascii=False, separators=(",", ":"))
    json.loads(blob)
    print("原有 %d 条, 移除旧收藏集 %d 个, 保留系统收藏集, 新增 %d 个, 合并后 %d 条"
          % (len(orig), len(removed), len(new), len(merged)))
    if removed:
        print("将移除:", removed)
    if dry: print("DRY-RUN: 未写入。"); return
    ts = time.strftime("%Y%m%d_%H%M%S")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    b1 = os.path.join(BACKUP_DIR, "backup_cloud-storage-namespace-1_%s.json" % ts)
    b2 = tgt.replace(".json", "_backup_%s.json" % ts)
    shutil.copy2(tgt, b1); shutil.copy2(tgt, b2)
    print("备份:", b1); print("备份:", b2)
    tmp = tgt + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: f.write(blob)
    json.load(open(tmp, encoding="utf-8"))
    os.replace(tmp, tgt)
    print("已原子写入:", tgt)
    print("请启动 Steam 查看收藏集; 回滚 = 用备份 JSON 覆盖回目标文件 (需先退出 Steam)。")

if __name__ == "__main__":
    main()
