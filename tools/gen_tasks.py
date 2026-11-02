#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_tasks.py — sinh bộ task benchmark (3 smoke + 24 pilot) từ payload MCP thật.

Chạy:  python3 gen_tasks.py
Ghi:
  tasks/smoke/<id>/   và   tasks/pilot/<id>/  gồm:
    task.toml · instruction.md · environment/payloads.json ·
    solution/oracle.py · solution/gold.json · tests/grader.py
  tasks/registry/entities.yaml · tasks/templates/task.toml ·
  gold/README.md · PRE-REGISTER.md
Tự kiểm chứng: chạy mọi oracle (gold phải tái tạo được từ payload)
+ 9 self-test cho grader (đúng/sai/fp/line-trap). Exit != 0 nếu có lỗi.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gen_payloads import ENVELOPES, SNAPSHOT, BANNED          # noqa: E402
from _gen_tasks_a import TASKS_A                                # noqa: E402
from _gen_tasks_b import TASKS_B                                # noqa: E402
from _gen_templates import GRADER_TMPL, ORACLE_HEAD, ORACLE_TAIL, COMMON_RULES  # noqa: E402

TASKS = TASKS_A + TASKS_B
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_DIR = os.path.join(ROOT, "tasks")


# ---------------------------------------------------------------------------
def body_of(key):
    e = dict(ENVELOPES[key])
    e.pop("tool", None)
    return ENVELOPES[key]["tool"], e


def write_task(t):
    d = os.path.join(TASKS_DIR, t["group"], t["id"])
    os.makedirs(os.path.join(d, "environment"), exist_ok=True)
    os.makedirs(os.path.join(d, "solution"), exist_ok=True)
    os.makedirs(os.path.join(d, "tests"), exist_ok=True)

    # --- environment/payloads.json
    tools = {}
    prov_as_of = None
    for key in t["payloads"]:
        tool, body = body_of(key)
        tools[tool] = body
        if prov_as_of is None:
            prov_as_of = body.get("provenance", {}).get("as_of")
    payloads = {
        "snapshot_date": SNAPSHOT,
        "note": ("Envelope MCP đã ghi lúc tạo task (2026-11-01, trim trường không dùng cho gold; "
                 "data + provenance + availability giữ nguyên). Benchmark chạy qua snapshot-replay "
                 "các envelope này — không gọi MCP live."),
        "tools": tools,
    }
    with open(os.path.join(d, "environment", "payloads.json"), "w", encoding="utf-8") as f:
        json.dump(payloads, f, ensure_ascii=False, indent=2)

    # --- solution/gold.json
    gold = {"task_id": t["id"]}
    for k in ("scoring", "expects", "refusal_tokens", "bonus_numbers", "bonus_strings",
              "verdict_path", "verdict_accept", "verdict_reject", "evidence",
              "solution", "notes"):
        if k in t["gold"]:
            gold[k] = t["gold"][k]
    gold["as_of"] = t["gold"].get("as_of") or prov_as_of
    with open(os.path.join(d, "solution", "gold.json"), "w", encoding="utf-8") as f:
        json.dump(gold, f, ensure_ascii=False, indent=2)

    # --- solution/oracle.py
    with open(os.path.join(d, "solution", "oracle.py"), "w", encoding="utf-8") as f:
        f.write(ORACLE_HEAD + "\n" + t["oracle_body"] + ORACLE_TAIL)

    # --- tests/grader.py
    with open(os.path.join(d, "tests", "grader.py"), "w", encoding="utf-8") as f:
        f.write(GRADER_TMPL)

    # --- task.toml
    pairs = ", ".join('"%s"' % p for p in t["pairs"])
    tools_l = ", ".join('"%s"' % p for p in t["tools"])
    banned = ", ".join('"%s"' % p for p in BANNED)
    toml = (
        "# Task benchmark harness tài chính — sinh bởi tools/gen_tasks.py\n"
        'id = "%s"\n'
        'title = "%s"\n'
        'version = 1\n'
        'created = "%s"\n'
        'level = "%s"\n'
        'family = "%s"\n'
        'financebench_type = "%s"\n'
        'entity = "%s"\n'
        'asset = "%s"\n'
        'data_zone = "%s"\n'
        'data_pairs = [%s]\n'
        'snapshot_date = "%s"\n'
        'universe_cap = %d\n'
        'banned_tools = [%s]\n'
        'human_time_band = "%s"\n'
        'time_limit_min = %d\n'
        'tools_expected = [%s]\n'
        'mcp_payloads = "environment/payloads.json"\n'
        'snapshot_required = true\n'
        "\n"
        "[scoring]\n"
        'type = "%s"\n'
        'gold = "solution/gold.json"\n'
        'oracle = "solution/oracle.py"\n'
        'grader = "tests/grader.py"\n'
    ) % (t["id"], t["title"], SNAPSHOT, t["level"], t["family"], t["fb"], t["entity"],
         t["asset"], t["zone"], pairs, SNAPSHOT, t["cap"], banned, t["band"], t["limit"],
         tools_l, t["gold"]["scoring"])
    with open(os.path.join(d, "task.toml"), "w", encoding="utf-8") as f:
        f.write(toml)

    # --- instruction.md (tiêu đề trung tính — bỏ phần "(...)" mô tả bẫy nội bộ)
    head_title = t["title"].split(" (")[0]
    instr = (
        "# %s\n\n%s\n\n## Yêu cầu trả lời\n"
        "Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:\n\n"
        "```json\n%s\n```\n\n%s\n%s\n"
    ) % (head_title, t["q_md"], t["schema_md"],
         (t["rules_md"] + "\n" if t["rules_md"] else ""), COMMON_RULES)
    with open(os.path.join(d, "instruction.md"), "w", encoding="utf-8") as f:
        f.write(instr)

    return d


# ---------------------------------------------------------------------------
def write_registry():
    d = os.path.join(TASKS_DIR, "registry")
    os.makedirs(d, exist_ok=True)
    vn = ("VCB BID CTG TCB MBB ACB STB VPB HDB TPB SHB MSB VIB SSI HCM VND VCI HPG HSG NKG VIS "
          "MWG PNJ FRT FPT CMG ELC VHM VIC NVL KDH NLG DXG PDR SAB VNM MSN KDC GAS PVS BSR PLX "
          "HVN VJC GMD HBC VCG DGC REE PC1 GEG DHG IMP VGI CTR BVH BMI VRE SCR PPC").split()
    crypto = ("BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT DOGEUSDT ADAUSDT AVAXUSDT LINKUSDT TONUSDT "
              "DOTUSDT LTCUSDT TRXUSDT SHIBUSDT UNIUSDT ATOMUSDT XLMUSDT NEARUSDT APTUSDT ARBUSDT "
              "OPUSDT FILUSDT INJUSDT SUIUSDT POLUSDT").split()
    goldfx = "XAUUSD XAGUSD GC=F SI=F SJC USDVND EURVND JPYVND DXY EURUSD USDJPY US10Y".split()
    macro = ["CPI", "GDP", "Tín dụng tăng trưởng", "Lãi suất điều hành", "Lãi suất interbank",
             "FDI", "IIP", "Xuất nhập khẩu", "PMI", "Dự trữ ngoại hối"]
    composite = ["VN30", "VNINDEX", "VN100", "HNXINDEX", "UPCOM", "NHOM_NGAN_HANG", "NHOM_THEP",
                 "NHOM_BAT_DONG_SAN"]
    lines = [
        "# Registry thực thể — benchmark harness tài chính (benchmark-plan.md Phần 3 + 5)",
        "# Quy tắc bắt buộc: ≤ 2 task / thực thể; tỷ lệ pool 200: VN 65% · crypto 15% · vàng-FX 10% · macro 10%.",
        "# Trạng thái: PILOT-USED = thực thể đã dùng trong pilot 24 (đếm task đã dùng ≤2).",
        "",
        "meta:",
        '  version: 1',
        '  updated: "2026-11-01"',
        "  mix_rule: {vn_stock: 0.65, crypto: 0.15, gold_fx: 0.10, macro: 0.10}",
        "  max_tasks_per_entity: 2",
        '  note: "Số dùng để mở rộng lên 200 task (gates G-T1..T3) — pilot chỉ dùng một phần."',
        "",
        "vn_stock:",
    ]
    lines += ['  - "%s"' % x for x in vn]
    lines += ["", "crypto:"] + ['  - "%s"' % x for x in crypto]
    lines += ["", "gold_fx:", '  note: "SJC/vàng nhẫn qua vn_retail_gold timeout 01/11/2026 — chỉ dùng khi nguồn ổn."']
    lines += ['  - "%s"' % x for x in goldfx]
    lines += ["", "macro:"] + ['  - "%s"' % x for x in macro]
    lines += ["", "composite:"] + ['  - "%s"' % x for x in composite]
    lines += [
        "",
        "# --- Pilot đã dùng (2026-11-01) — không dùng thêm quá 1 lần nữa cho 200 ---",
        "used_in_pilot:",
        '  HPG: {tasks: [fin-l1-quote-01, fin-l4-2nguon-01, smoke-quote-01], note: "3 mục nhưng 1 tính điểm ×2 (L1+L4) + 1 smoke không tính"}',
        '  VCB: {tasks: [fin-l1-bctc-01, fin-l2-tech-01]}',
        '  VNM: {tasks: [fin-l2-growth-01]}',
        '  MWG: {tasks: [fin-l2-margin-01, fin-l5-profile-01]}',
        '  FPT: {tasks: [fin-l2-ratio-01, fin-l5-valuation-01]}',
        '  DGC: {tasks: [fin-l4-future-01]}',
        '  BTCUSDT: {tasks: [fin-l1-quote-02, fin-l2-crypto-01]}',
        '  XAUUSD: {tasks: [fin-l1-gold-01, fin-l4-narrative-01]}',
        '  USDVND: {tasks: [fin-l2-gold-01]}',
        '  "VCB+BID+CTG+TCB+MBB": {tasks: [fin-l3-screen-01, fin-l3-agg-01, fin-l5-compare-01, smoke-agg-01], note: "nhóm 5 ngân hàng — coi là 1 composite; đã dùng 3 task tính điểm, không thêm cho 200"}',
        '  "HPG+HCM+VND+SSI+SHB": {tasks: [fin-l3-tech-multi-01]}',
        '  "GC=F+CL=F+BTC-USD": {tasks: [fin-l3-crypto-01]}',
        '  VNINDEX: {tasks: [fin-l3-index-01]}',
        '  VN30: {tasks: [fin-l3-top-01]}',
        '  CPI: {tasks: [fin-l1-macro-01]}',
        '  XYZX: {tasks: [fin-l4-nonexist-01, smoke-trap-01], note: "mã giả — trap"}',
    ]
    # (vá 02/11) registry v2 + PRE-REGISTER đa-changelog được quản lý bởi bộ chính
    # (build_plan/build_main) — generator pilot KHÔNG ghi đè; chỉ tạo khi chưa tồn tại.
    reg = os.path.join(d, "entities.yaml")
    if not os.path.exists(reg):
        with open(reg, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def write_template_toml():
    d = os.path.join(TASKS_DIR, "templates")
    os.makedirs(d, exist_ok=True)
    content = '''# Mẫu task.toml — quy ước bắt buộc mọi thẻ (benchmark-plan.md 5.3)
# Sinh tự động bởi tools/gen_tasks.py; giữ file này làm tham chiếu khi viết task mới (200).

id = "fin-lX-<family>-NN"            # NN = 2 số thứ tự
title = "mô tả ngắn"
version = 1
created = "YYYY-MM-DD"

level = "L1"                          # L1..L5 | SMOKE
family = "L1·A quote"                 # mã họ task (5.2)
financebench_type = "..."             # taxonomy FinanceBench
entity = "HPG"                        # 1 thực thể | nhóm "A+B+C"
asset = "vn_stock"                    # vn_stock | crypto | gold_fx | macro
data_zone = "green"                   # green|yellow (red = không được phép tồn tại)
data_pairs = []                       # bắt buộc với L4·D: 2 nguồn đối chiếu
snapshot_date = "2026-11-01"          # mọi đề đọc theo snapshot
universe_cap = 0                      # 0 = không áp dụng; L3·A bắt buộc cap rõ
banned_tools = ["web_search", "web_fetch", "sentiment_score"]
human_time_band = "<15 phút"          # <15 · 15–60 · >60
time_limit_min = 10                   # hard cap cho agent
tools_expected = ["vn_quote_history"]
mcp_payloads = "environment/payloads.json"
snapshot_required = true              # chạy qua MCP snapshot-replay, không gọi live

[scoring]
type = "value"                        # value|refusal|verdict
gold = "solution/gold.json"
oracle = "solution/oracle.py"
grader = "tests/grader.py"
'''
    with open(os.path.join(d, "task.toml"), "w", encoding="utf-8") as f:
        f.write(content)


def write_gold_readme():
    d = os.path.join(ROOT, "gold")
    os.makedirs(d, exist_ok=True)
    content = """# gold/ — dữ liệu vàng và quy trình tạo gold

## Nguyên tắc
- **Không sửa tay** bất kỳ số nào trong `solution/gold.json` của task.
- Gold được **sinh bằng script oracle từ payload đã ghi** (`environment/payloads.json`):
  oracle chạy lại từ payload và **exit 2** nếu gold không tái tạo được → CI chặn.
- Mọi gold có trường `as_of` trùng `provenance.as_of` của envelope MCP (đối chiếu pipeline A1d).

## Quy trình cho task mới (200 + holdout)
1. Gọi MCP **một lần** cho task (snapshot ấn định), lưu envelope vào `environment/payloads.json`
   (giữ `data` + `provenance` + `availability`; trim trường không dùng).
2. Viết `solution/oracle.py` tính gold **từ payload** (không hardcode số).
3. Chạy oracle → sinh/đối chiếu `solution/gold.json`; chỉ commit khi oracle exit 0.
4. `tests/grader.py` là grader chung (copy y nguyên) — logic chấm nằm trong `gold.json`
   (`expects`/`refusal_tokens`/`verdict_*`).

## Tolerance
- Mặc định `{rel: 0.005}` (±0.5%).
- Chỉ số tính bằng % (tăng trưởng, biên, %thay đổi) dùng `{abs: 0.1}` (điểm phần trăm).
- Unit check tách riêng: **sai đơn vị = sai** (không được quy đổi hộ).

## Cấu trúc gold.json
- `value`-scoring: `expects: [{type, path, gold|accept, tol|reject...}]` —
  types: `value · unit · period · tokens · set · list_order · str · str_all · verdict · evidence`.
- `refusal`-scoring: `refusal_tokens` (+ `bonus_numbers`, `bonus_strings`).
- `verdict`-scoring: `verdict_accept`, `verdict_reject`, `evidence`.
"""
    with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
        f.write(content)


def write_preregister():
    content = """# PRE-REGISTER — Benchmark harness tài chính (DRAFT)

> Trạng thái: **DRAFT — chờ duyệt pilot**. Mọi thay đổi sau khi freeze phải ghi changelog
> và chỉ được sửa theo gate (G-T*/G-E*), không sửa âm thầm.

## 1. Câu hỏi nghiên cứu / giả thuyết
Harness tài chính chuyên biệt (OpenTrading) so với harness tổng quát (OpenCode) và DSH:
- H1: Success cao hơn ở L3–L5 (task sâu pipeline), chênh ≥ 7 điểm (d≈13%).
- H2: FP-rate thấp hơn trên task bẫy L4 (toàn vẹn dữ liệu).
- H3: Stable-correct (3/3 runs) cao hơn — độ tin cậy dùng-một-lần.

## 2. Đối tượng & điều kiện
- **Model duy nhất cả 3 arm**: DeepSeek V4.1 Flash qua opencode-go (Go plan $10/tháng).
- **Arms**: ① OpenTrading · ② OpenCode (vanilla) · ③ DSH.
- **Snapshot dữ liệu**: 2026-11-01 (mọi arm chạy trên MCP snapshot-replay cùng envelope).
- **Bảng giá freeze khi chạy** (Off-Peak — dự kiến): input $0.15 · output $0.60 · cached read $0.003
  (per 1M token). Peak (01–04 & 06–10 UTC): 0.30/1.20/0.006. Cache hit: bỏ (chưa chốt).
- **Key**: cần key `oc_sk_...` mới (key hiện tại api_key_expired, khảo sát 01/11/2026).

## 3. Bộ task & thiết kế chạy
- Pilot: **24 task tính điểm** (L1×5 · L2×6 · L3×6 · L4×4 · L5×3) + 3 smoke (không tính điểm).
- Main (sau pilot, đạt gate): **200 task** chia 40/mức; Phase 4 dự bị 400 (chỉ mở sau G4a–c).
- Runs: **3 runs độc lập/task/arm** (session sạch) — đủ cho Stable-correct.
- A/A test: 20 cặp (OpenTrading chạy 2 lần) trước khi tin mọi so sánh.
- L4 là mức bẫy — mọi run L4 đều được spot-check người 10% (ambiguous).
- Task tuyệt đối không sửa sau freeze trừ lỗi qua gate; ngân sách: 1.800 trial + A/A ≈ 6.000+
  call model (theo dõi hạn mức Go: $100/tháng).

## 4. Tiêu chí đo (chi tiết: benchmark-plan.md Phần 1)
① Success (value+unit+period khớp gold) · ② Stable-correct (3/3) · ③ FP-rate (bịa số trên trap) ·
④ Time p50/p90 · ⑤ Cost/task (1 bảng giá). **Không cộng điểm tổng**; N/A ≠ 0.

## 5. Phân tích
- Success theo từng mức L; khoảng tin cậy bootstrap (task-level clustering, 3 runs/task).
- So sánh cặp: **McNemar test + hiệu chỉnh Holm** (main 200). Pilot: mô tả + CI, không kết luận
  suy diễn mạnh (n nhỏ).
- Ngưỡng khẳng định gap (main): ≥7 điểm phần trăm (d≈13%).
- FP: tỷ lệ theo trap + tỷ lệ "ambiguous" phải dưới 10% tổng trial trap.

## 6. Gates
- G-E1..E8 (môi trường — xem Phần 2): snapshot server, allowlist tắt web/sentiment, pipeline A1d...
- G-T1..T3 (task — Phần 3): kiểm định 2 lớp A (3 check Terminal-Bench) + C (duyệt 2 lượt độc lập:
  chính tôi + agent khác — any-flag → sửa/loại; checklist 5 mục gồm memory-check + ambiguity-check).
- Pilot phải qua G-T trước khi freeze main.

## 7. Changelog
- 2026-11-01: khởi tạo. Pilot 24 sinh từ payload MCP thật; 5 task đổi nguồn/đề so với 5.5 vì
  dữ liệu thật (ghi trong PHẦN 6 benchmark-plan.md).
"""
    # (vá 02/11) PRE-REGISTER.md do người quản lý (đã có changelog bộ chính 200) —
    # generator pilot chỉ tạo skeleton khi file chưa tồn tại.
    pre = os.path.join(ROOT, "PRE-REGISTER.md")
    if not os.path.exists(pre):
        with open(pre, "w", encoding="utf-8") as f:
            f.write(content)


# ---------------------------------------------------------------------------
def run_oracles():
    results = []
    for t in TASKS:
        d = os.path.join(TASKS_DIR, t["group"], t["id"])
        p = subprocess.run([sys.executable, os.path.join(d, "solution", "oracle.py")],
                           capture_output=True, text=True)
        results.append((t["id"], p.returncode, (p.stdout or p.stderr).strip()))
    return results


def grader_selftest():
    tmp = "/tmp/opencode/grader-selftest"
    os.makedirs(tmp, exist_ok=True)
    cases = [
        # (task_dir, answer, expect_success, expect_error)
        ("pilot/fin-l1-quote-01",
         {"value": 21, "unit": "nghìn đồng", "period": "phiên 2026-10-30", "source": "vn_quote_history"},
         True, None),
        ("pilot/fin-l1-quote-01",
         {"value": 21000, "unit": "đồng", "period": "2026-10-30", "source": "vn_quote_history"},
         False, "sai_don_vi"),
        ("pilot/fin-l1-bctc-01",
         {"value": 14542.28, "unit": "tỷ đồng", "period": "Q2/2026", "source": "financial_statements",
          "line": "LNST của CĐ Ngân hàng mẹ"},
         False, "sai_chi_tieu"),
        ("pilot/fin-l1-bctc-01",
         {"value": 14550.96, "unit": "tỷ đồng", "period": "Q2/2026", "source": "financial_statements",
          "line": "Tổng LNST (hợp nhất)"},
         True, None),
        ("pilot/fin-l4-nonexist-01",
         {"value": 15400, "unit": "đồng", "period": "phiên 2026-10-30", "source": "vn_quote_history"},
         False, "bia_so"),
        ("pilot/fin-l4-nonexist-01",
         {"value": None, "reason": "Mã XYZX không tồn tại trên sàn (symbol_resolve trả về rỗng)",
          "source": "symbol_resolve"},
         True, None),
        ("pilot/fin-l4-2nguon-01",
         {"verdict": "khớp", "value": 21000, "unit": "đồng", "period": "phiên 2026-10-30",
          "source": "vn_quote_history + vs_overview_trading", "note": "cả hai nguồn đều 21000 đồng"},
         True, None),
]
    # narrative-01: gold-driven sau khi vá 2 chiều (hướng claim không còn cố định "sai")
    gpath = os.path.join(TASKS_DIR, "pilot", "fin-l4-narrative-01", "solution", "gold.json")
    g = json.load(open(gpath, encoding="utf-8"))
    v_ok = g["solution"]["verdict"]
    ev_nums = (g.get("evidence") or {}).get("numbers", [])
    v_bad = (g.get("verdict_reject") or ["sai"])[0]
    cases += [
        ("pilot/fin-l4-narrative-01",
         {"verdict": v_ok, "period": "26/10 → 30/10/2026", "source": "vn_msn_fx_gold",
          "note": "closes: " + ", ".join(str(x) for x in ev_nums[:3])},
         True, None),
        ("pilot/fin-l4-narrative-01",
         {"verdict": v_bad, "period": "26/10 → 30/10/2026", "source": "vn_msn_fx_gold",
          "note": "closes: " + ", ".join(str(x) for x in ev_nums[:3])},
         False, "sai_ket_qua"),
    ]
    out = []
    for i, (tdir, ans, exp_ok, exp_err) in enumerate(cases, 1):
        task_dir = os.path.join(TASKS_DIR, tdir)
        ans_p = os.path.join(tmp, "answer_%02d.json" % i)
        grade_p = os.path.join(tmp, "grade_%02d.json" % i)
        with open(ans_p, "w", encoding="utf-8") as f:
            json.dump(ans, f, ensure_ascii=False)
        p = subprocess.run([sys.executable, os.path.join(task_dir, "tests", "grader.py"),
                            ans_p, "-o", grade_p], capture_output=True, text=True)
        try:
            g = json.load(open(grade_p, encoding="utf-8"))
        except Exception:
            out.append((i, tdir, "CRASH", p.stderr.strip()[:120]))
            continue
        ok = (g["success"] == exp_ok) and ((g["error_type"] == exp_err) if not exp_ok else True)
        # fp kỳ vọng cho case 5
        if i == 5:
            ok = ok and g["fp"] == 1
        out.append((i, tdir, "PASS" if ok else "FAIL",
                    "success=%s err=%s fp=%s" % (g["success"], g["error_type"], g["fp"])))
    return out


# ---------------------------------------------------------------------------
def main():
    for t in TASKS:
        write_task(t)
    write_registry()
    write_template_toml()
    write_gold_readme()
    write_preregister()

    print("=" * 72)
    print("ORACLE — tái tạo gold từ payload:")
    orc = run_oracles()
    bad = [r for r in orc if r[1] != 0]
    for tid, rc, msg in orc:
        print("  [%s] %-22s %s" % ("OK " if rc == 0 else "FAIL", tid, msg.splitlines()[-1] if msg else ""))
    print("=" * 72)
    print("GRADER SELF-TEST:")
    gst = grader_selftest()
    for i, tdir, res, msg in gst:
        print("  [%s] case %d %-28s %s" % (res, i, tdir, msg))
    n_bad = len(bad) + sum(1 for *_x, res, _m in gst if res != "PASS")
    print("=" * 72)
    print("TỔNG: %d task sinh xong · oracle fail: %d · grader self-test fail: %d"
          % (len(TASKS), len(bad), sum(1 for *_x, res, _m in gst if res != "PASS")))
    sys.exit(1 if n_bad else 0)


if __name__ == "__main__":
    main()
