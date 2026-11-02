#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_main.py — sinh 250 task (200 main + 50 holdout) từ manifest + recorded + families.

Chạy: python3 build_main.py
Ghi: tasks/main/<id>/ và tasks/holdout/<id>/ (task.toml, instruction.md,
     environment/payloads.json, solution/{oracle.py,gold.json}, tests/grader.py)
Kiểm định: oracle roundtrip (250), grader self-test (correct=mút pass, mutated=fail,
     empty=fail), quét rò rỉ số vàng trong instruction, báo cáo tổng.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
TASKS = os.path.join(ROOT, "tasks")

from build_plan import GROUPS  # noqa: E402
from fam_a import FAMILIES_A  # noqa: E402
from fam_b import FAMILIES_B  # noqa: E402
from _gen_templates import GRADER_TMPL  # noqa: E402

FAMILIES = dict(FAMILIES_A, **FAMILIES_B)

BAND_LIMIT = {"L1": ("<15 phút", 15), "L2": ("<15 phút", 20), "L3": ("15–60 phút", 60),
              "L4": ("15–60 phút", 30), "L5": ("15–60 phút", 60)}
SNAPSHOT = "2026-11-01"

CTRF_APPEND = '''
# --- CTRF (bổ sung chuẩn Harbor) ---
try:
    _g = json.load(open("grade.json", encoding="utf-8"))
    _checks = _g.get("checks", [])
    _ctrf = {"results": {"tool": {"name": "fin-grader"},
                         "summary": {"tests": len(_checks),
                                     "passed": sum(1 for c in _checks if c["pass"]),
                                     "failed": sum(1 for c in _checks if not c["pass"])},
                         "tests": [{"name": c["check"], "status": "passed" if c["pass"] else "failed",
                                    "message": c.get("detail", "")} for c in _checks]}}
    json.dump(_ctrf, open("grade.ctrf.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
except Exception:
    pass
'''

ORACLE_HEAD2 = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Oracle — tái tạo gold từ environment/payloads.json (self-contained)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "environment", "payloads.json"), encoding="utf-8") as _f:
    payloads = json.load(_f)
with open(os.path.join(HERE, "gold.json"), encoding="utf-8") as _f:
    gold = json.load(_f)

problems = []


def check(label, computed, expected):
    def _norm(x):
        if isinstance(x, float):
            return round(x, 6)
        if isinstance(x, list):
            return [_norm(i) for i in x]
        return x
    if _norm(computed) != _norm(expected):
        problems.append("%s: computed=%r expected=%r" % (label, computed, expected))


def env(name):
    t = payloads["tools"][name]
    return t["envelope"] if isinstance(t, dict) and "envelope" in t else t

'''


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


FAM_UTIL_SRC = read(os.path.join(HERE, "fam_util.py"))


# ---------------------------------------------------------------------------
def resolve_payloads(t, rec):
    keys = []
    for k in t["payloads"]:
        if k.startswith("techgrp:"):
            g = k.split(":")[1]
            keys += ["tech:" + s for s in GROUPS[g]]
        else:
            keys.append(k)
    env = {}
    for k in keys:
        if k not in rec:
            raise KeyError("task %s thiếu payload %s" % (t["id"], k))
        env[k] = rec[k]["body"]
    return keys, env


def build_task(t, rec, out_root):
    fam = FAMILIES[t["family"]]
    keys, env = resolve_payloads(t, rec)
    spec = fam(t, env)
    d = os.path.join(out_root, t["id"])
    os.makedirs(os.path.join(d, "environment"), exist_ok=True)
    os.makedirs(os.path.join(d, "solution"), exist_ok=True)
    os.makedirs(os.path.join(d, "tests"), exist_ok=True)

    # payloads.json
    tools = {}
    as_ofs = []
    for k in keys:
        item = rec[k]
        tools[k] = {"tool": item["tool"], "params": item.get("params", {}), "envelope": item["body"]}
        prov = item["body"].get("provenance", {})
        if prov.get("as_of"):
            as_ofs.append(prov["as_of"])
    payloads = {"snapshot_date": SNAPSHOT,
                "note": "Envelope MCP ghi lúc tạo task. Key = mã payload nội bộ; envelope giữ nguyên data+provenance+availability.",
                "tools": tools}
    with open(os.path.join(d, "environment", "payloads.json"), "w", encoding="utf-8") as f:
        json.dump(payloads, f, ensure_ascii=False, indent=1)

    # gold.json
    gold = {"task_id": t["id"], "scoring": spec["scoring"], "solution": spec["solution"],
            "as_of": max(as_ofs) if as_ofs else SNAPSHOT, "split": t["split"]}
    for k in ("expects", "refusal_tokens", "bonus_numbers", "bonus_strings", "verdict_accept",
              "verdict_reject", "evidence"):
        if k in spec:
            gold[k] = spec[k]
    with open(os.path.join(d, "solution", "gold.json"), "w", encoding="utf-8") as f:
        json.dump(gold, f, ensure_ascii=False, indent=1)

    # oracle.py
    orc = ORACLE_HEAD2 + "\n# === fam_util (inline) ===\n" + FAM_UTIL_SRC + "\n\n# === thân oracle ===\n" + spec["oracle"] + (
        '\nif problems:\n    print("ORACLE MISMATCH:")\n    [print(" -", p) for p in problems]\n    sys.exit(2)\n'
        'print("ORACLE OK — %s" % gold["task_id"])\n')
    with open(os.path.join(d, "solution", "oracle.py"), "w", encoding="utf-8") as f:
        f.write(orc)

    # grader.py (+CTRF)
    with open(os.path.join(d, "tests", "grader.py"), "w", encoding="utf-8") as f:
        f.write(GRADER_TMPL + CTRF_APPEND)

    # instruction.md (tiêu đề trung tính)
    head = spec["title"].split(" (")[0]
    instr = ("# %s\n\n%s\n\n## Yêu cầu trả lời\nGhi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:\n\n```json\n%s\n```\n\n%s%s\n"
             % (head, spec["q"], spec["schema"],
                (spec.get("rules", "") + "\n" if spec.get("rules") else ""),
                COMMON_RULES_TXT))
    with open(os.path.join(d, "instruction.md"), "w", encoding="utf-8") as f:
        f.write(instr)

    # task.toml
    band, limit = BAND_LIMIT[t["level"]]
    tools_seen = []
    for k in keys:
        tn = rec[k]["tool"]
        if tn not in tools_seen:
            tools_seen.append(tn)
    pairs = keys if t["family"] == "l4-2src" else []
    cap = 0
    if t["family"] in ("l3-agg", "l3-screen", "l3-tech-multi", "l5-compare"):
        cap = 5
    toml = (
        "# Task benchmark harness tài chính (bộ 200+50) — sinh bởi tools/build_main.py\n"
        'id = "%s"\ntitle = "%s"\nversion = 1\ncreated = "2026-11-01"\n'
        'level = "%s"\nfamily = "%s"\nfinancebench_type = "%s"\nentity = "%s"\nasset = "%s"\n'
        'data_zone = "green"\ndata_pairs = [%s]\nsnapshot_date = "%s"\nuniverse_cap = %d\n'
        'banned_tools = ["web_search", "web_fetch", "sentiment_score"]\n'
        'human_time_band = "%s"\ntime_limit_min = %d\ntools_expected = [%s]\n'
        'mcp_payloads = "environment/payloads.json"\nsnapshot_required = true\n'
        'split = "%s"\n\n[scoring]\ntype = "%s"\ngold = "solution/gold.json"\noracle = "solution/oracle.py"\ngrader = "tests/grader.py"\n'
    ) % (t["id"], spec["title"], t["level"], spec["family_code"], spec["fb"], t["entity"], t["subject"],
         ", ".join('"%s"' % p for p in pairs), SNAPSHOT, cap, band, limit,
         ", ".join('"%s"' % x for x in tools_seen), t["split"], spec["scoring"])
    with open(os.path.join(d, "task.toml"), "w", encoding="utf-8") as f:
        f.write(toml)
    return {"id": t["id"], "split": t["split"], "level": t["level"], "family": t["family"],
            "scoring": spec["scoring"], "gold": gold, "spec": spec, "dir": d}


COMMON_RULES_TXT = """
## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.
"""


# ---------------------------------------------------------------------------
def synthesize(gold, mutate=False):
    """Sinh answer 'đúng' từ gold (để self-test grader), hoặc lệch (mutate)."""
    sc = gold["scoring"]
    if sc == "refusal":
        if mutate:
            return {"value": 12345, "unit": "đồng", "source": "x"}
        return {"value": None, "reason": gold.get("refusal_tokens", ["chưa công bố"])[0], "source": "x"}
    if sc == "verdict":
        ans = {"verdict": gold.get("verdict_accept", ["sai"])[0], "source": "x"}
        ev = gold.get("evidence", {})
        nums = ev.get("numbers") or [0]
        ans["note"] = str(nums[0])
        for s in (ev.get("strings") or []):
            ans["note"] += " " + s
        if mutate:
            ans["verdict"] = gold.get("verdict_reject", ["đúng"])[0]
        return ans
    ans = {}

    def setv(path, val):
        cur = ans
        parts = path.split(".")
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = val

    for exp in gold.get("expects", []):
        t, path = exp["type"], exp.get("path", "value")
        if t == "value":
            v = exp["gold"]
            if mutate:
                v = v * 2 if abs(v) > 1e-9 else 999
            setv(path, v)
        elif t == "unit":
            setv(path, exp["accept"][0])
        elif t == "period":
            setv(path, exp["accept"][0])
        elif t == "tokens":
            setv(path, exp["accept"][0])
        elif t == "set":
            setv(path, list(exp["gold"]))
        elif t == "list_order":
            setv(path, list(exp["gold"]))
        elif t == "str":
            setv(path, exp["accept"][0])
        elif t == "str_all":
            setv(path, " + ".join(exp["accept"]))
        elif t == "verdict":
            setv(path, gold.get("verdict_reject", ["sai"])[0] if mutate else exp["accept"][0])
        elif t == "evidence":
            setv(path, " ".join(str(x) for x in (exp.get("numbers") or [])[:2] + list(exp.get("strings") or [])[:2]))
    ans.setdefault("source", "x")
    if mutate:
        kinds = [e["type"] for e in gold.get("expects", [])]
        if "value" not in kinds:
            # mutate kiểu set/list_order/str/verdict/tokens
            for e in gold.get("expects", []):
                p = e.get("path", "value")
                if e["type"] in ("set", "list_order"):
                    cur = ans
                    parts = p.split(".")
                    for part in parts[:-1]:
                        cur = cur.setdefault(part, {})
                    cur[parts[-1]] = ["KHONG-CO"]
                    break
                if e["type"] in ("str", "verdict", "tokens"):
                    cur = ans
                    parts = p.split(".")
                    for part in parts[:-1]:
                        cur = cur.setdefault(part, {})
                    cur[parts[-1]] = "SAI-BET"
                    break
    return ans


def run_checks(built):
    rep = {"oracle_fail": [], "selftest_fail": [], "mutate_fail": [], "empty_fail": [], "leak_fail": [], "ctrf_missing": []}
    tmp = "/tmp/opencode/main-selftest"
    os.makedirs(tmp, exist_ok=True)
    for i, b in enumerate(built):
        d = b["dir"]
        # oracle
        p = subprocess.run([sys.executable, os.path.join(d, "solution", "oracle.py")], capture_output=True, text=True)
        if p.returncode != 0:
            rep["oracle_fail"].append((b["id"], (p.stdout + p.stderr).strip().splitlines()[-1] if (p.stdout + p.stderr).strip() else "?"))
        # grader self-tests
        for tag, ans, want_success, store in (
                ("ok", synthesize(b["gold"]), True, "selftest_fail"),
                ("mut", synthesize(b["gold"], mutate=True), False, "mutate_fail"),
                ("empty", {}, False, "empty_fail")):
            ap = os.path.join(tmp, "a_%s_%d.json" % (tag, i)); gp = os.path.join(tmp, "g_%s_%d.json" % (tag, i))
            with open(ap, "w", encoding="utf-8") as f:
                json.dump(ans, f, ensure_ascii=False)
            subprocess.run([sys.executable, os.path.join(d, "tests", "grader.py"), ap, "-o", gp],
                           capture_output=True, text=True)
            try:
                g = json.load(open(gp, encoding="utf-8"))
            except Exception:
                rep[store].append((b["id"], tag + ": no grade.json")); continue
            if g["success"] != want_success:
                rep[store].append((b["id"], "%s: success=%s (want %s) err=%s" % (tag, g["success"], want_success, g["error_type"])))
            if tag == "mut" and b["scoring"] == "refusal" and g.get("fp") != 1:
                rep["mutate_fail"].append((b["id"], "refusal mutate: fp != 1"))
        # leak scan (dùng chung check_leaks — 6 lớp: fence_null, fence_period, value_leak,
        # evidence_leak, bonus_leak, narrative_leak)
        from check_leaks import scan_task
        for cls, detail in scan_task(d):
            rep["leak_fail"].append((b["id"], "%s: %s" % (cls, detail)))
        # ctrf check (chạy lại grader trên answer đúng)
        ap = os.path.join(tmp, "ctrf_%d.json" % i)
        with open(ap, "w", encoding="utf-8") as f:
            json.dump(synthesize(b["gold"]), f, ensure_ascii=False)
        subprocess.run([sys.executable, os.path.join(d, "tests", "grader.py"), ap, "-o", os.path.join(d, "grade.json")],
                       capture_output=True, text=True, cwd=d)
        if not os.path.exists(os.path.join(d, "grade.ctrf.json")):
            rep["ctrf_missing"].append(b["id"])
        for fn in ("grade.json", "grade.ctrf.json"):
            fp = os.path.join(d, fn)
            if os.path.exists(fp):
                os.remove(fp)
    return rep


def main():
    manifest = json.load(open(os.path.join(HERE, "manifest.json"), encoding="utf-8"))
    rec = {}
    rdir = os.path.join(HERE, "recorded")
    for fn in sorted(os.listdir(rdir)):
        if fn.endswith(".json"):
            rec.update(json.load(open(os.path.join(rdir, fn), encoding="utf-8"))["items"])
    built = []
    errors = []
    for t in manifest["main"] + manifest["holdout"]:
        try:
            out_root = os.path.join(TASKS, "main" if t["split"] == "main" else "holdout")
            os.makedirs(out_root, exist_ok=True)
            built.append(build_task(t, rec, out_root))
        except Exception as e:
            errors.append((t["id"], "%s: %s" % (type(e).__name__, str(e)[:160])))
    print("built:", len(built), "| errors:", len(errors))
    for e in errors[:30]:
        print("  ERR", e)
    if errors:
        print("DỪNG — sửa lỗi build trước khi kiểm định.")
        sys.exit(1)
    rep = run_checks(built)
    print("=" * 72)
    for k, v in rep.items():
        print("%-14s fail: %d" % (k, len(v)))
        for item in v[:10]:
            print("   ", item)
    n_fail = sum(len(v) for v in rep.values())
    print("TỔNG:", len(built), "task | lỗi kiểm định:", n_fail)
    if n_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
