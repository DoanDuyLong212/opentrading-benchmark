# Amendment (i), 2026-11-11: xác nhận verdict của judge theo lô. Thêm sau khi đã thấy kết quả; user duyệt

## Vấn đề
- or16r chấm theo lô 5 mục: `fin-l4-nonexist-236` và `fin-l4-nonexist-238` (OT) bị chấm *incorrect*.
- Cả hai là câu bẫy hỏi mã XYZA. OT trả `value: null` kèm lý do "không có dữ liệu", strict grader cho đạt.
- Nhưng lý do judge ghi lại nói về **QWER9**, tức là của một mục khác trong cùng lô: verdict bị gán nhầm id.

## Luật mới, áp như nhau cho mọi arm và mọi run (main, or16r, holdout)
1. **Chấm lại riêng lẻ:**
   - Mọi verdict theo lô khác `correct` được chấm lại riêng lẻ, cùng model, prompt một mục, temp 0.
   - Verdict riêng lẻ là verdict cuối cùng. Verdict theo lô vẫn được giữ trong `batch_verdict` / `batch_reason` để audit.
2. **Khi chấm lại cũng rỗng:** nếu lần chấm riêng lẻ không ra verdict hợp lệ sau 12 lần thử, verdict theo lô được giữ
   nguyên (`confirm_failed`).
3. **Vì sao chỉ chấm lại verdict khác `correct`:** verdict `correct` vẫn qua chốt chặn số deterministic và luật FP/FR,
   nên một verdict `correct` bị gán nhầm không thể vượt qua giá trị sai.
   - Hệ quả có chủ ý: luật này chỉ có thể làm tăng số verdict judge `correct`, đối xứng giữa các arm. Báo cáo sẽ nêu
     kèm số verdict bị đổi theo từng arm.
4. **Ghi đè thủ công:** user xác nhận hai trial trên là đúng (`analysis/labels/or16-manual-overrides.json`). Kết quả
   chấm lại theo luật 1 cũng cho `correct`, nên ghi đè trùng với kết quả của luật.

## Cài đặt
- **Code:**
  - `analysis/grade_run_llm_nvidia.py` (`judge_batch_confirmed`): luật áp ngay khi chấm cho các trial mới.
  - `--confirm-existing GRADED`: rà lại các file đã chấm, ghi ra `*-confirm.jsonl`.
  - `tools/` không sửa vì đang bị seal or16 khoá.
- **Holdout:** dùng cùng luật, qua route OpenRouter trả phí với data_collection=deny:
  `analysis/grade_run_llm_nvidia.py RUN --route openrouter-deny --batch 5`. Wrapper từ chối holdout với mọi route khác.
- **Judge route** (user 2026-11-11):
  - Nemotron Ultra qua NVIDIA NIM, vì route free trên OpenRouter trả rỗng khoảng 50% số lần.
  - Ở cả hai route, verdict rỗng được thử lại tối đa 12 lần, timeout mỗi lần 120 s.
