# Benchmark harness tài chính Việt Nam — v4.7

Benchmark so sánh ba harness agent trên **cùng một model và cùng một bộ dữ liệu**: **OpenTrading** (harness chuyên tài chính, profile `machine`), **OpenCode** và **DeepSeek Harness (DSH)**. Câu hỏi đặt ra: khi chỉ thay harness, câu trả lời tài chính đúng hơn, nhanh hơn và rẻ hơn đến mức nào.

**Kết quả mới nhất:** [`experiments/finance-v47-study/results/final-300/Results.md`](experiments/finance-v47-study/results/final-300/Results.md)

## Kết quả

300 task tiếng Việt × 3 harness × 1 lượt = 900 trial. Model `deepseek/deepseek-v4.1-flash-1017`, snapshot dữ liệu ngày 01/11/2026.

| | **OpenTrading** | OpenCode | DSH |
|---|---:|---:|---:|
| **Đạt / 300** | **279 (93,0%)** | 245 (81,7%) | 266 (88,7%) |
| Compute (79) | **78** | 75 | 76 |
| Investor (36) | **19** | 16 | 16 |
| Lookup (112) | 110 | 110 | 110 |
| Memory (59) | **58** | 30 | 50 |
| Robustness (14) | 14 | 14 | 14 |
| Chi phí / lần đạt (USD) | **0,0024** | 0,0051 | 0,0045 |
| Thời gian p90 | **95 giây** | 294 giây | 218 giây |
| Từ chối sai / DNF | **0 / 1** | 10 / 6 | 0 / 6 |

- OpenTrading thắng từng cặp trên cùng task: so với OpenCode 40–6 (p ≈ 3·10⁻⁷), so với DSH 19–6 (p ≈ 0,015).
- Khác biệt đến chủ yếu từ **memory**. Ở compute, lookup và robustness, ba harness gần như ngang nhau.
- Không harness nào vượt chiến lược "luôn bán" ở 16 câu khuyến nghị MUA/GIỮ/BÁN.

Cách chấm, toàn bộ metric và phân tích nằm trong `Results.md`.

## Cấu trúc repo

| Đường dẫn | Nội dung |
|---|---|
| `experiments/finance-v47-study/results/final-300/` | **Benchmark cuối:** báo cáo, 300 task, 900 trial kèm câu trả lời đầy đủ, kết quả judge, manifest, script tính lại số liệu |
| `experiments/finance-v47-study/tools/` | Runner, gateway, MCP snapshot, grader, judge, config `bench_config_v47.json` |
| `experiments/finance-v47-study/tasks/` | Cây task gắn seal mà runner và CI dùng (gồm holdout chưa chạy) |
| `experiments/finance-v47-study/README.md` | Dựng toolchain ghim và chạy kiểm tra offline |

Các thư mục còn lại (`experiments/finance-v47-study/tasks-retired/`, `experiments/finance-v46-update-study/`, `audits/`) **không phải benchmark**. Chúng chỉ chứa runtime calculator và fixture mà tool và test của v4.7 cần.

## Phiên bản cũ (lỗi thời)

Các bản v2 đến v4.6u (bộ đề, kết quả, audit, kế hoạch) **đã lỗi thời và đã xoá khỏi repo**. Chúng vẫn còn trong lịch sử git. Đừng dùng số liệu từ các bản đó; chỉ dùng `results/final-300/`.
