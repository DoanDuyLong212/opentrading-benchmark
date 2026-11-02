# Hướng dẫn chạy benchmark (1 lệnh)

> Setup ngày 02/11/2026 — 3 harness: **OpenTrading** (bun wrapper headless) · **OpenCode** v2.1.2
> (`opencode run`) · **DSH** 0.2.1-rc.2 (`dsh --profile headless`). Model chạy qua NVIDIA NIM
> (key `NVIDIA_API_KEY`; model đặt trong `tools/bench_config.json`).

## Chạy

```bash
cd ~/extra/benchmark

# ① Kiểm tra môi trường (tuỳ chọn, ~30s): 8 hạng mục PASS = sẵn sàng
python3 tools/ready_check.py

# ② SMOKE 5 câu (xác nhận pipeline): 3 arm × 5 task × 1 run
python3 tools/run_benchmark.py --split pilot --sample 5 --seed 20261102 --runs 1

# ③ PILOT đầy đủ (3 arm × 24 task × 3 runs theo pre-register)
python3 tools/run_benchmark.py --split pilot --runs 3 --arms opencode,dsh,opentrading

# ④ MAIN 200 (sau freeze)
python3 tools/run_benchmark.py --split main --runs 3

# ⑤ HOLDOUT — có GUARD, chỉ mở sau freeze theo quy chế 7.4
python3 tools/run_benchmark.py --split holdout --confirm-holdout
```

Tùy chọn thêm: `--tasks id1,id2` (chạy đúng task chỉ định) · `--arms opencode` (một arm) ·
`--model nvidia/<model>` · `--retry N --pause S` (mặc định 2/5s — thử lại khi NIM 429/timeout) ·
`--out <dir>` · `--list-only`.

**Lưu ý vận hành:** NIM rate-limit theo từng model và có lúc chập chờn — chạy **tuần tự**
(driver tự giãn cách); đừng chạy song song nhiều lệnh. glm-5.3-flash bị session điều khiển
đốt cạn → config đang dùng `deepseek-ai/deepseek-v4.1-flash` (model chính thức của benchmark).

## Kết quả ở đâu

- `results/<ts>_<split>/trials.jsonl` — 1 dòng/trial: task, arm, run, status, success, fp,
  error_type, wall_ms, tokens, mcp_calls, answer_source, attempt, session_id.
- `results/<ts>_<split>/trials/<task>__<arm>__r<run>/` — `ws/` (workspace agent: instruction.md +
  answer.json), `runner/` (config cách ly), `run.log` (log thô), `grade.json` (chấm chi tiết).

## Cơ chế bảo đảm điều kiện chung (3 arm)

| Trục | Cơ chế |
|---|---|
| Dữ liệu | MCP snapshot replay (`tools/mcp_snapshot_server.py`) phục vụ đúng envelope `environment/payloads.json`; không gọi mạng ngoài |
| Workspace | Mỗi trial 1 workspace mới chỉ có `instruction.md`; gold/payloads nằm ngoài |
| Cách ly | OpenCode: XDG riêng + `permissions` deny external_directory/shell/web; DSH: profile patch + sandbox `workspace-write`; OpenTrading: `OPENTRADING_HOME` riêng |
| Model/API | Cùng model/key/baseURL NVIDIA cho cả 3 arm |
| Chấm | Cùng `tests/grader.py` của task, chấm ngoài workspace |
| Ngân sách | Timeout = `time_limit_min` của task (vượt → kill process group) |
| Skills | Smoke: không skills trên cả 3 arm (điều kiện ngang nhau). Pilot: wire skills-pack chung trước khi chạy |
| Holdout | Guard `--confirm-holdout` (quy chế 7.4: chưa freeze thì từ chối) |

## Kiến trúc thư mục

```
tools/
├── run_benchmark.py        # driver 1 lệnh
├── ready_check.py          # preflight 8 hạng mục
├── mcp_snapshot_server.py  # MCP stdio replay (hỗ trợ 2 format payloads main/pilot)
├── bench_config.json       # model + ghi chú môi trường
├── tests/                  # 21 test hạ tầng (pytest)
└── runners/
    ├── run_opencode.py     # XDG-isolate + V2 permissions deny
    ├── run_dsh.py          # per-trial patch (insert mcp-opentrading)
    ├── run_opentrading.py  # bun wrapper → core harness, OPENTRADING_HOME riêng
    └── ot_headless.ts      # wrapper headless OpenTrading (copy pattern chat.ts)
```
