# Finance v4.7 study

Kết quả cuối (300 task, judge Claude Haiku 5.5): [`final-20261126/Results.md`](final-20261126/Results.md). Config chạy: `tools/bench_config_v47.json`. Thiết kế và các quyết định: `plans/2026-11-15-v47-study-design.md`.

- Runtime OpenTrading: `experiments/opentrading-runtime/`, commit ở `experiments/opentrading-runtime.SHA` (dependency cài tại chỗ, không symlink).
- Prompt OT: `tools/prompt_variants/baseline/` là bản chép nguyên văn `prompts/` của runtime; hash nằm trong `baseline.SHA256SUMS`.
- Shell dùng chung: `tools/runners/mathshell/`. Mỗi trial ghi `runner/shell.jsonl`, mỗi dòng là một lệnh của model kèm verdict `run` hoặc `refused`.

| Tool model thấy | OT | OpenCode | DSH |
|---|---|---|---|
| MCP snapshot | có | có | có |
| Shell (qua bộ lọc chỉ-toán) | `shell` | `shell` | `bash` |
| Khác | `read_result` | không | không |

| Giới hạn | Giá trị | Ở đâu |
|---|---|---|
| Request mỗi trial | 24 | gateway, chung cho mọi arm |
| Tổng token mỗi trial | 4,6M | gateway, chung |
| Output mỗi request | không giới hạn; harness tự xin (đo smoke: OpenCode 256 000, DSH 32 768, OT không đặt) | gateway chuyển nguyên |
| Bước trong harness | mặc định của từng harness (OT/OpenCode không giới hạn, DSH không có tuỳ chọn) | |
| Chống lặp | OT loop guard (tự duyệt), OpenCode `doom_loop` allow, DSH `repeat-tool-reminder` bật | |

## Tái lập offline từ clone mới (không cần credential model)

Hỗ trợ Linux/WSL x86_64, glibc ≥ 2.34, Python 3.12.3. Docker chỉ cần cho shell
sandbox và job container; các bước dưới đây không gọi provider.

```sh
# 1. Toolchain ghim (Bun/OpenCode/Node/DSH) + Python lock đầy đủ hash
python3.12 experiments/finance-v47-study/tools/bootstrap_offline.py \
  --prefix .toolchains --cache .bootstrap-cache
python3.12 experiments/finance-v47-study/tools/bootstrap_offline.py \
  --prefix .toolchains --cache .bootstrap-cache --verify-only

# 2. Dependency Python (bắt buộc --require-hashes, chỉ wheel)
python3.12 -m pip install --require-hashes --only-binary=:all: \
  -r experiments/finance-v47-study/tools/bootstrap/requirements-offline.lock

# 3. Active suite + kiểm corpus/oracle/grader local
python3.12 -m pytest -q experiments/finance-v47-study/tools/tests
python3.12 experiments/finance-v47-study/tools/verify_offline.py \
  --study-root experiments/finance-v47-study --out /tmp/offline-verification.json
```

`bootstrap_offline.py` chỉ tải artifact đúng URL/hash trong
`tools/bootstrap/toolchain-receipts.json` và `python-artifacts.json`; không cần
`HOME` của tác giả. Các runner và `run_manifest` dùng chung bộ locator
`tools/trusted_toolchain.py`, nên manifest chỉ ghi nhận đúng bytes sẽ thực thi.
`BENCH_BUN_BIN` chỉ đổi vị trí, không đổi hash tin cậy.

## Kiểm lịch sử v4.6u (job riêng)

```sh
cd experiments/finance-v46-update-study/experiments/opentrading-runtime
$OLDPWD/.toolchains/bun/bin/bun install --frozen-lockfile   # dùng Bun đã ghim
cd -
BENCH_BUN_BIN=$PWD/.toolchains/bun/bin/bun python3.12 -m pytest -q \
  experiments/finance-v46-update-study/tools/tests/test_v45_calculate.py \
  experiments/finance-v46-update-study/tools/tests/test_v45_math_audit.py
```

Test lịch sử whole-study (`tools/tests/legacy`) cần snapshot v4.2/v4.3/v4.4
không phân phối trong repo; không skip/xfail — chạy riêng và báo thiếu
prerequisite trung thực (`tools/tests/legacy/README.md`).

## CI offline

`.github/workflows/offline.yml` chạy 4 job không secret: active suite + verifier,
legacy v4.6u, bootstrap toolchain + verify receipt, và build/smoke shell sandbox
no-network. Không job nào gửi gold holdout tới provider.

## Cổng chạy và ngân sách

- `BENCH_V47_DEV=1` chỉ cho phép split **devsmoke**; main/holdout bị chặn trước
  mọi request cho tới khi có seal hợp lệ.
- Route trả phí cần `--budget-usd` và paid-budget journal; thiếu cấu hình thì
  gateway từ chối trước provider (không có request nào được gửi).
- Route OpenRouter cần credential riêng `OPENROUTER_KEY` (hoặc
  `OPENROUTER_API_KEY`); không fallback sang NVIDIA key.
- Canary Stage 5 dùng model free, trần ≤10 trial devsmoke, chỉ để kiểm vận hành
  — không dùng để chọn đề hay tuyên bố thắng.
