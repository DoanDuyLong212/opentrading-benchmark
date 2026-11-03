# Benchmark Harness Tài chính — README

> Đánh giá **harness agent tài chính** (OpenTrading) so với harness tổng quát (OpenCode, DSH)
> trên bộ task dữ liệu chứng khoán Việt Nam/crypto/vàng-FX/macro, snapshot đóng băng
> **2026-11-01**. Thiết kế đầy đủ: [`benchmark-plan.md`](benchmark-plan.md) · Khung đo đã
> đăng ký trước: [`PRE-REGISTER.md`](PRE-REGISTER.md).

---

## 1. Đo cái gì

Dashboard 5 cột — **không cộng điểm tổng**:

| # | Tiêu chí | Cơ chế |
|---|---|---|
| ① | **Success** (đúng số + đơn vị + kỳ + nguồn) | Grader code đối chiếu `answer.json` × gold (oracle sinh từ payload) |
| ② | **Stable-correct** (đúng cả 3 runs) | Tận dụng 3 runs/task — đo độ tin cậy "dùng một lần" |
| ③ | **FP-rate** (chống bịa) | Task bẫy (kỳ chưa công bố / mã không tồn tại) — bịa số = FP=1 |
| ④ | **Time p50/p90** | wall_ms từ driver, tách theo mức L |
| ⑤ | **Cost/task** | tokens × bảng giá freeze (N/A nếu harness không xuất usage) |

Bộ task: **200 main + 50 holdout + 24 pilot + 3 smoke** — 5 mức L1→L5 (extraction →
computation → multi-entity → trap/verification → multi-part report); mỗi thẻ có
`task.toml / instruction.md / payloads.json / oracle.py + gold.json / grader.py`.
Giả thuyết H1–H3 và ngưỡng khẳng định: xem PRE-REGISTER.

---

## 2. Nguyên lí hoạt động

```
run_benchmark.py (driver — 1 lệnh)
│  chọn task → tạo workspace CHỈ có instruction.md → gọi runner của arm
│  → timeout = time_limit_min → chấm bằng tests/grader.py → trials.jsonl
│
├── arm OpenCode    : opencode run --format json (XDG cách ly + PWD=ws + permissions deny)
├── arm DSH         : dsh --profile headless --json --patch <per-trial patch>
└── arm OpenTrading : bun wrapper → core harness headless (OPENTRADING_HOME riêng)
         │
         ▼
   MCP snapshot server (stdio, KHÔNG mạng) — phục vụ đúng envelope đã ghi
         │
         ▼
   agent → answer.json trong workspace → grader.py (gold ngoài workspace)
```

### 2.1. Tám trục điều kiện chung (3 arm chạy như nhau)

| Trục | Cơ chế |
|---|---|
| **Dữ liệu** | MCP snapshot replay `tools/mcp_snapshot_server.py` — mọi arm nhận đúng cùng envelope `{data, provenance, availability}`; không gọi mạng |
| **Workspace** | Mỗi trial 1 workspace mới **chỉ chứa `instruction.md`**; gold/payloads nằm ngoài |
| **Cách ly** | Opencode: `XDG_*` riêng + `PWD`=ws + `permissions` deny external_directory/shell/web · DSH: profile patch + sandbox `workspace-write` · OpenTrading: `OPENTRADING_HOME` riêng (không có tool ghi file → runner trích answer từ output) |
| **Model/API** | Cùng model + key NVIDIA NIM (`tools/bench_config.json`) |
| **Chấm** | Cùng `tests/grader.py`, chấm ngoài workspace; tolerance `±0.5%` (giá) / `±0.1` điểm % (chỉ số); **sai đơn vị = sai** |
| **Ngân sách** | Timeout = `time_limit_min` của task; quá hạn → kill process group, tính là timeout |
| **Lịch chạy** | Tuần tự (tránh rate-limit); round-robin arm trong từng task |
| **Sạch** | Session mới mỗi trial; retry tự động khi lỗi hạ tầng (429/timeout mạng) |

### 2.2. Chống rò rỉ / bypass

- **Gold ngoài workspace**: agent không đọc được `solution/` (workspace chỉ có đề).
- **Snapshot replay**: agent buộc dùng MCP tool — server từ chối tool ngoài snapshot,
  không có `web_search/web_fetch/sentiment_score`.
- **Telemetry tuân thủ**: mỗi trial ghi `mcp_calls` (số lời gọi tool MCP trong log) +
  `answer_source` (`file`/`extracted`/`extracted_input`/`missing`) — phát hiện trial
  "trả lời mà không dùng MCP".
- Hạn chế đã biết: agent có shell vẫn có thể `cat` được đường dẫn nếu đoán ra (đã chặn
  các đường rò chính; mức chặn tuyệt đối cần container — việc chuẩn bị pilot).

---

## 3. Xây dựng môi trường (đã cài đặt gì)

| Thành phần | Vị trí / Cấu hình |
|---|---|
| **Driver + infra** | `tools/run_benchmark.py`, `tools/mcp_snapshot_server.py`, `tools/runners/…`, `tools/ready_check.py` — 24 test hạ tầng (`python3 -m pytest tools/tests/`) |
| **OpenCode** v2.1.2 | `~/.opencode/bin/opencode`; trial dùng config V2 (`mcp.servers`, `permissions` array, `codemode:false`) trong XDG riêng |
| **DSH** 0.2.1-rc.2 | `~/.local/bin/dsh`, profile `headless`; đã cài plugin `@deepseek-ai/dsh-mcp-client@0.2.1-rc.2` vào profile; patch per-trial dùng cú pháp `- insert:` |
| **OpenTrading** | repo `~/OpenTrading` (pin commit ghi trong log); wrapper headless `tools/runners/ot_headless.ts` (bun) |
| **NVIDIA NIM** | key `NVIDIA_API_KEY` + `~/.local/share/opencode/auth.json` (nvidia) + `~/.opentrading/auth.json` (nvidia). ⚠️ Rate-limit **theo từng model** — danh sách model khả dụng thực tế hẹp (xem `bench_config.json`) |
| **MCP snapshot** | Chạy hoàn toàn offline từ `environment/payloads.json` (hỗ trợ cả 2 format main/pilot); tool khai báo `readOnlyHint:true` (bắt buộc cho OpenTrading headless auto-allow) |

---

## 4. Hướng dẫn chạy

### 4.0. Điều kiện tiên quyết
- `NVIDIA_API_KEY` set trong môi trường; 3 harness cài đúng chỗ như bảng trên.

### 4.1. Lệnh chính (1 lệnh là chạy)

```bash
cd ~/extra/benchmark

# ① Preflight (~30s) — 8 hạng mục PASS = sẵn sàng
python3 tools/ready_check.py

# ② SMOKE 3 câu (xác nhận pipeline, 9 trials ~1–1.5h)
#    L1-macro (trap chuỗi CPI) · L3-crypto-multi · L4-future (trap FP)
python3 tools/run_benchmark.py --split pilot --sample 3 --seed 20261102 --runs 1 --retry 3 --pause 15

# ③ PILOT đầy đủ (3 arm × 24 task × 3 runs theo pre-register — chạy dài)
python3 tools/run_benchmark.py --split pilot --runs 3 --retry 3 --pause 15

# ④ MAIN 200 (sau freeze)
python3 tools/run_benchmark.py --split main --runs 3 --retry 3 --pause 15

# ⑤ HOLDOUT — niêm phong, có GUARD (quy chế 7.4): chỉ chạy sau freeze
python3 tools/run_benchmark.py --split holdout --confirm-holdout
```

Tùy chọn: `--tasks id1,id2` · `--arms opencode,dsh,opentrading` · `--model nvidia/<model>` ·
`--out <dir>` (mặc định `results/<ts>_<split>`) · `--retry N --pause S` · `--list-only`.

> ⚠️ **Vận hành:** chạy **tuần tự** — NIM rate-limit theo model, chạy song song sẽ 429.
> Driver tự nghỉ giữa trial và tự retry khi lỗi hạ tầng. Không Ctrl-C giữa chừng;
> muốn chạy tiếp task khác thì chạy lệnh mới với `--tasks`.

### 4.2. Đọc kết quả

```
results/<ts>_<split>/
├── trials.jsonl                  # 1 dòng/trial
└── trials/<task>__<arm>__r<run>/
    ├── ws/instruction.md         # đề agent nhận
    ├── ws/answer.json            # câu trả lời (nếu có)
    ├── runner/                   # config cách ly của từng harness
    ├── run.log                   # log thô (events + output)
    └── grade.json                # chấm từng check + error_type + fp
```

Mỗi dòng `trials.jsonl`: `task, arm, run, status, success, fp, error_type, wall_ms,
tokens, mcp_calls, answer_source, attempt, session_id, snapshot_date`.

Xem nhanh tổng hợp:

```bash
python3 - <<'EOF'
import json, collections
rows = [json.loads(l) for l in open("results/<run-id>/trials.jsonl")]
by = collections.defaultdict(lambda: {"n": 0, "ok": 0, "fp": 0})
for r in rows:
    s = by[r["arm"]]; s["n"] += 1; s["ok"] += r["success"]; s["fp"] += r["fp"]
for a, s in by.items():
    print(f"{a:11s} n={s['n']} success={s['ok']} fp={s['fp']}")
EOF
```

---

## 5. Cấu trúc thư mục

```
benchmark/
├── README.md · benchmark-plan.md · PRE-REGISTER.md     # tài liệu
├── tasks/  main/ · holdout/ · pilot/ · smoke/ · registry/ · templates/
├── tools/  run_benchmark.py · ready_check.py · mcp_snapshot_server.py
│           bench_config.json · tests/ · runners/{opencode,dsh,opentrading}
├── results/  (gitignore) — kết quả từng đợt chạy
└── gold/README.md — quy trình vàng
```

## 6. Trạng thái & việc tiếp theo

- ✅ **SMOKE 3 câu ĐẠT (03/11/2026)** — 9/9 trials success, model đồng nhất
  `deepseek-v4.1-flash`: L1-macro 3/3 · L3-crypto-multi 3/3 · L4-future trap 3/3
  (fp=0 — cả 3 arm từ chối đúng + nêu kỳ thay thế Q3/2026). Kết quả:
  `results/smoke3_20261103/trials.jsonl`. Median wall: dsh 161s · opencode 169s ·
  opentrading 168s. `mcp_calls` > 0 toàn bộ (1–5), `answer_source`: opencode/dsh=file,
  opentrading=extracted (thiết kế R14).
- 📌 Model: `deepseek-v4.1-flash` (pre-register) — NVIDIA đã hồi phục. Google path
  `gemini-3.5-flash-lite` (key từ opentrading, đã nạp opencode/dsh/OT) chạy tốt trên
  opencode+OT nhưng **dsh blocker** (Gemini 3.x thought_signature) → giữ fallback,
  xem `tools/bench_config.json`.
- ⏳ Trước PILOT thật: wire **skills-pack chung 3 arm**; freeze + hash 250 thẻ;
  duyệt người mẫu thẻ (memory/ambiguity check); (tùy chọn) container hóa chống đọc chéo.
- 🔒 HOLDOUT chỉ mở 1 lần sau freeze (`--confirm-holdout`).
- Chi tiết bug-fix hạ tầng & rulings: ledger nội bộ phiên setup (ngoài repo).
