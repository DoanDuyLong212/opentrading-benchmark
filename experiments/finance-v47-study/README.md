# Finance v4.7 study

**Chưa seal.** Chỉ dùng cho dev smoke: `BENCH_V47_DEV=1 python3 tools/run_benchmark.py --config tools/bench_config_v47.json ...`. Thiết kế và các quyết định: `plans/2026-11-15-v47-study-design.md`.

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
