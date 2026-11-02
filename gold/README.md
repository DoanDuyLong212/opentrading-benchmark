# gold/ — dữ liệu vàng và quy trình tạo gold

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
