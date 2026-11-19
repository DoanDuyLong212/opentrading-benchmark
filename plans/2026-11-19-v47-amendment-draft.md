# Amendment v4.7 — DỰ THẢO, CHƯA ĐƯỢC DUYỆT

Trạng thái: **draft**. Không có hiệu lực, không mở main/holdout, không thay cho quyết định
của FinDaHuman tại #10/#13/#15/#16/#21/#22. Bản này ghi đúng những gì code và corpus
đang có, và đánh dấu rõ chỗ còn thiếu quyết định.

## 1. Danh tính study và phạm vi

- Study: `v4.7`, protocol `financial_product_v45`, config `experiments/finance-v47-study/tools/bench_config_v47.json`.
- Seal: chưa có. `v47_gate.validate_seal` từ chối mọi seal không phải `study_version == "v4.7"`;
  seal v4.6u không authorize được v4.7.
- Phạm vi bằng chứng xác nhận: main + một cohort holdout. Pilot/devsmoke/smoke chỉ để
  kiểm vận hành, không dùng tuyên bố thắng.
- Runtime OT: commit ghim trong `experiments/opentrading-runtime.SHA`; hash cây file ở
  `tools/bootstrap/runtime-source.json`. Prompt baseline: `tools/prompt_variants/baseline/baseline.SHA256SUMS`.

## 2. Task, hash và PRUNE/exposure

- Inventory hiện tại (verifier `verify_offline.py`):
  - main **200** (lookup 100, compute 40, memory 30, safety 30)
  - holdout **58** (lookup 36, compute 7, memory 7, safety 8)
  - pilot 39, devsmoke 15, smoke 3, memorydev 2; tổng 317 task.
- Receipt kiểm corpus gần nhất: `pass=true`, 317 task, 1.660 mutation, 0 external call.
  Hash exposure holdout: `1931280fbe3fd6d7083fa92192266226aef8d490d4d113d310ca53809e37560d`
  (`holdout_exposure_status: unknown`).
- **Exposure:** repo công khai; task/gold holdout nằm trong repo. Không được gọi holdout là
  "unseen" khi chưa xác minh lịch sử exposure. Main đã được dùng trong các study trước.
- **PRUNE:** danh sách task bị loại và lý do phải đóng băng trong seal receipt
  (`quarantined_tasks` trong manifest). Draft này không thêm/bớt task nào so với corpus
  đang có.
- Hash từng task: lấy từ `run_manifest.task_fingerprint` khi tạo seal; amendment không
  chép tay hash để tránh lệch.

## 3. Metric và cách phân tầng

- Primary: **LCM** (grounded answer đúng theo grader hiện hành) cho từng arm, báo paired
  theo task. Không gộp S vào endpoint chính.
- **S (safety)** báo riêng: tỷ lệ từ chối/không bịa, không dùng để xếp hạng tổng.
- Memory: so OT machine và DSH khi cả hai có memory tool; OpenCode báo "không có năng lực"
  thay vì chấm 0 như cùng năng lực.
- **S3 clock:** native cross-arm clock parity chưa được chứng minh. S3 là diagnostic, loại
  khỏi so sánh chéo harness cho tới khi audit `clock_policy.audit_clock_observations` có
  quan sát thật từ cả 3 arm. Không sửa timeout/đồng hồ để tạo parity giả.

## 4. Model, route, host

- Model: `nvidia/nemotron-3-ultra-550b-a55b:free` (context 1M, output tối đa 65.536).
- Route: `openrouter_free`; không fallback model/host. Host thực phải khớp response
  (`returned_model`), lệch là fail preflight.
- Credential: `OPENROUTER_KEY` hoặc `OPENROUTER_API_KEY`. **Không fallback sang NVIDIA key**
  (đã sửa lỗi này; test `test_openrouter_route_never_falls_back_to_nvidia_credential`).
- Canary Stage 5: tối đa **10 trial devsmoke**, free route, chỉ kiểm vận hành/latency/resume.
  Hiện **chưa chạy được**: cả 3 credential OpenRouter có trên máy trả HTTP 401 tại
  `GET /api/v1/key`; cần key hợp lệ trước khi canary.

## 5. Lịch chạy theo tầng (runs-by-stratum)

Policy `stratum_policy.DEFAULT_RUNS_BY_STRATUM`: lookup 1, compute 2, memory 2, safety 2.

| Split | Task | Trial-cell (task×runs) | ×3 arm |
|---|---:|---:|---:|
| main | 200 | 300 | **900** |
| holdout | 58 | 80 | **240** |
| devsmoke | 15 | 17 | 51 |
| pilot | 39 | 53 | 159 |

## 6. Caps, retry, exclusion

- 24 request/trial (memory 48), 4,6M token/trial, output không ép; trần output thực tế theo
  model 65.536.
- Timeout: 600 s/request, 1.800 s/trial, interval 2 s.
- Transport retry 3 lần/request; **whole-trial retry = 0**. Lỗi hạ tầng có receipt; không
  chạy lại vì đáp án sai.
- Failed/DNF giữ trong mẫu số; không xoá trial, không mở cohort mới để "chạy lại cho đẹp".

## 7. Chi phí và allocation — CHỖ CẦN QUYẾT ĐỊNH

- Free route: $0 nhưng hạn mức key là **1.000 request/ngày**; budget code hiện chặn cứng
  **1.900 request** cho smoke+pilot. Main 900 cell × tối thiểu ~4 request/cell ≈ **3.600
  request**, đã vượt cả budget lẫn hạn mức ngày. **Không thể chạy main trên free route với
  allocation hiện tại.**
- Paid route (nếu được duyệt riêng): DeepSeek v4.1 flash, giá trong config
  (`prompt_usd 0.006`, `completion_usd 0.5` mỗi 1M token). Ước tính từ smoke OT
  (~447k input + 15k output/trial) ≈ **$0,010/trial**; 900 cell ≈ **$9** chỉ cho OT, các arm
  khác cần đo lại. Đây là ước tính, không phải cam kết; phải dùng measured usage.
- Allocation draft (điền sau khi chọn route):
  - main: ____ request / ____ USD
  - holdout: ____ request / ____ USD (chỉ mở sau khi main được review)
  - reserve: ____ request / ____ USD (chỉ lỗi hạ tầng có evidence)

## 8. Thời điểm suy luận và thống kê

- Main chỉ chạy sau khi: #9–#15 đóng theo quyết định, checkpoint 16A đạt, infra PR xanh,
  seal v4.7 được duyệt và `v47_gate.authorize_run` chấp nhận đúng run đã đăng ký.
- Holdout mở đúng một cohort bằng `v47_gate.write_holdout_receipt`; resume chỉ cohort đó.
  Receipt bind `seal_sha256`, `approval_sha256`, `decision_id`, `cohort_id`.
- Thống kê: paired theo task, báo CI; không đổi metric/split sau khi xem kết quả. S báo
  riêng; S3 diagnostic.

## 9. Việc phải làm trước khi seal

1. Trả lời #10/#13/#15 và ghi quyết định vào amendment này (bỏ nhãn draft).
2. Có credential OpenRouter hợp lệ; chạy canary ≤10 trial; lưu receipt.
3. Chọn route/host cho main và điền allocation thực.
4. Tạo seal receipt bằng code (không viết tay), gồm protected files, runs, settings, tasks,
   state hash, approval reference.
5. Chạy `v47_gate.validate_seal` + `authorize_run` trên run đã đăng ký trước khi gửi request.
