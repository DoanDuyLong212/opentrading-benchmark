# DRAFT — OT-strength stratum (50 task, 5 họ) — CHỜ v4.7 xong mới bật

Đăng ký hoãn có kiểm soát (user 09/11: "4 xử lí"). Nguyên tắc: stratum riêng có nhãn, môi trường
chung 4 arm, preregister trước inference, KHÔNG trộn điểm với pilot/main/holdout, thiết kế = giả thuyết.

## Điều kiện bật
1. v4.7 R1-R3 đã smoke PASS + contract/serializer ổn định (tránh regenerate 50 task hai lần)
2. Frozen study mới (v4.7-final) đã seal
3. Ngân sách: 50×2×4=400 trial hoặc sample 25 task

## 5 họ (thiết kế đầy đủ tại opencode-review.md §13.5)
A. Resolver-first ×12 — tên VN/ticker mơ hồ → symbol_resolve trước
B. Bẫy kỳ/thời gian + refusal chính xác ×12 — HDB trễ kỳ, future-period, non-trading-day, unpublished-macro
C. Hợp đồng chặt + đa nguồn ×10 — l4-2src mở rộng (bẫy đơn vị đồng↔nghìn), stock_overview dossier ≥6 trường
D. Chuỗi dài song song ×8 — agg 10 mã, compare 8 mã, screen 2 điều kiện, top-5 VN30 + volume
E. Chuỗi phụ thuộc 2 bước ×8 — vốn hóa=giá×SLCP, khối lượng top-3, RSI 1W top-2, chain ngược

## Fair-play constraints
- Môi trường chung: cùng tool/instruction/contract mọi arm
- Không gold-leak/task-ID-routing; ≤2 cá thể/entity/split; không trùng entity×kỳ×family với main/holdout
- Họ E: workflow analyst thật, cấm cưỡng bức tham số sai C2
- Per-family scoring: OT vs OC vs DSH trong từng họ — họ nào OT thắng = bằng chứng; họ nào không = điều chỉnh giả thuyết

## Generator spec
- tools/_gen_tasks_a.py + _gen_templates.py + registry entities.yaml
- Ràng buộc data: LTG/VIS stale loại; SBT chỉ l2-tech/narrative; POM partial; HDB trễ kỳ = bẫy; movers vn30-only
- Cấu trúc mỗi task: instruction.md + environment/{payloads,request_contracts}.json + solution/gold.json + tests/grader.py
