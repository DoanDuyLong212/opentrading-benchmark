# Amendment (j) 2026-11-11 — auditor: toán hạng `calculate` có cả tham chiếu nguồn lẫn giá trị gõ

**Người duyệt:** user, 2026-11-11, chọn "Amendment auditor" sau khi xem kết quả audit main gộp or16.
**Công khai:** luật này được thêm **sau khi đã thấy kết quả** (outcome-aware). Nó chỉ ảnh hưởng 2 trial OpenTrading
r2 (`fin-l2-gf-compare-174`, `fin-l4-2src-258`), cả hai đều strict-correct. Mọi trial bị nới đều được liệt kê
trong `audit-v45.json` → `amendment_j_relaxed_bindings`.

## Hiện tượng
Model gửi một toán hạng của `calculate` có cả `from_call/field/path/...` và `value` gõ tay. Runtime OpenTrading chỉ
giữ `{value, unit}` và gắn nhãn kết quả `lineage: unverified`. Auditor so khớp nguyên văn tham số giữa lệnh model sinh
ra và bản runtime lưu, nên báo `native_execution_sdk_binding` và `generated_call_reconciliation`. Fix #10 chỉ xử lý
trường hợp tương tự khi status=error.

## Luật (j)
Áp dụng khi phép khớp nguyên văn thất bại với một lệnh `calculate` native. Lệnh được gắn với occurrence mà model đã sinh
ra nếu thoả cả ba điều kiện:
1. Cùng SDK id, tool, lượt provider (và scope). Occurrence đó là duy nhất, và lịch sử hội thoại phát lại cũng trỏ đúng
   occurrence ấy.
2. Bỏ các khoá tham chiếu khỏi những toán hạng có `value` dạng số thì tham số model sinh ra trùng khít với tham số
   runtime đã lưu.
3. Mỗi `value` gõ tay phải **bằng chính xác** một con số mà trial đó đã có trước đó từ một lần chạy native thành công:
   giá trị input đã gắn nguồn, hoặc kết quả của phép tính trước. Không truy được thì trial bị audit báo lỗi
   `amendment_j_typed_value_provenance`.

## Không đổi
- Grader strict, judge, FP/FR, chốt chặn số và mọi kiểm tra khác của `tools/audit_v45_run.py` giữ nguyên.
- `tools/` không bị sửa vì freeze state của seal or16 vẫn dùng cho holdout. Luật được áp từ bên ngoài bằng
  `analysis/audit_v45_amended.py` (monkeypatch `CallBindings.claim`).
- Holdout cũng audit bằng wrapper này để dùng cùng một luật.
