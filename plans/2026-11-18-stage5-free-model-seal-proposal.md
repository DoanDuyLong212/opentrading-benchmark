# Đề xuất triển khai Stage 5: Seal v4.7 và Canary với OpenRouter Free Model

**Ngày:** 18/11/2026 · **Trạng thái:** Chờ phê duyệt  
**Định hướng chỉ thị từ người dùng:** Dùng model free từ OpenRouter (`nvidia/nemotron-3-ultra-550b-a55b:free` hoặc tương đương).

---

## 1. Mục tiêu và Phạm vi
- Chuẩn bị cơ chế Seal v4.7 phân phiên bản tách biệt (tránh xung đột với v4.6/v4.5).
- Định cấu hình OpenRouter Free route: không kích hoạt `paid_budget` journal, chi phí USD = 0.00, trần an toàn số lượng request (`max_requests=24`, `max_total_tokens=4.6M`).
- Thực hiện canary test nhỏ (≤ 10 trial cells trên devsmoke) để thẩm định độ trễ và sự ổn định của provider trước khi seal chính thức.

## 2. Tiêu chí kiểm soát kỹ thuật
1. **Model & Route**: `nvidia/nemotron-3-ultra-550b-a55b:free` (1 host Nvidia, max output 65,536 tokens, route `openrouter_free`).
2. **Lịch chạy Main (theo runs_by_stratum)**: 900 cells (100 L × 1 + 40 C × 2 + 30 M × 2 + 30 S × 2 = 300 task-runs × 3 arms).
3. **Phân bổ Holdout**: 240 cells (36 L × 1 + 7 C × 2 + 7 M × 2 + 8 S × 2 = 80 task-runs × 3 arms). Mở duy nhất 1 lần bằng receipt sau khi main hoàn tất.
4. **Không vượt ngân sách**: Tuyệt đối không kích hoạt route trả phí nếu không có chỉ đạo bổ sung.

---
