# ⏰ REMINDER: R4 Context reduction — BẬT LÚC NÀO?

**Đặt lúc**: 09/11/2026 (theo chỉ định user: "R4 thì tạm thời để sau và đặt remind")
**Bật khi**: v4.7 R1 (reference bridge) + R2 (typed claims) + R3 (claim serializer) đã smoke PASS
**Vì sao để sau**: R4 cắt context TRƯỚC khi R1-R3 đổi nguồn/serializer = phải làm hai lần; và cắt context trên prompt chưa ổn (v4.4 bài học: cắt sai gây misread)

## Việc khi bật R4
1. Đo lại tool-inventory bytes (B1 14.369 ký tự/6 tool vs OC/DSH ~7.930/3 — số liệu R3 09/11)
2. B1 107 requests vs B0/DSH 78/OC 72 — xác định nguyên nhân (schema verbosity vs loop) trước khi cắt
3. Chỉ bỏ lặp + schema verbosity; KHÔNG cắt provenance/failed-calls/period/user-memory conflicts
4. So inventory động vs đầy đủ; kiểm không tool mất khả dụng
5. A/B: R4-on vs R0 trên devsmoke 96; gate nguyên trạng

## Ngữ cảnh
- v4.7 proposal: plans/2026-11-09-v47-proposal-pending-approval.md (mục 4 — Context gọn theo trạng thái)
- Số liệu nền: audits/financial-v46-update/ + §18 opencode-review.md
