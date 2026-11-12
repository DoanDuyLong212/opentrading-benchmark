# PRE-REGISTER — Benchmark harness tài chính v2

**Bản sửa trước main, 04/11/2026 (Asia/Bangkok). Chưa tuyên bố kết quả main.** Audit
lịch sử và các số smoke trước v2 được giữ tại `audits/2026-11-04/`; không gộp vào main.
Bản này thay các định nghĩa/chạy lệnh cũ mâu thuẫn với sửa lỗi v2.

## 1. Câu hỏi và scope

So sánh OpenTrading, OpenCode và DSH trong hỏi đáp tài chính có căn cứ trên MCP
snapshot đóng băng (`snapshot_grounded_financial_qa`). Gold xác định đúng **so với
payload**, không chứng nhận filings gốc hay lợi nhuận giao dịch. L3–L5 là nhóm chiều
sâu; L4 chứa dữ liệu không có/claim cần xác minh, không được đồng nhất mọi câu L4
với refusal. Không cộng success/time/cost thành điểm tổng.

H1: Chênh success của OpenTrading với mỗi đối chứng ở L3–L5. H2: Chênh FP trên task
`scoring=refusal`. H3: Chênh stable-correct 3/3. Đây là giả thuyết nghiên cứu, không
phải các hướng kết quả được đảm bảo. Gap 7 điểm phần trăm là ngưỡng ý nghĩa thực tế
dự kiến; chưa khẳng định power đủ để phát hiện mức đó. Pilot chỉ dùng mô tả/CI và
ước lượng thời gian/discordance, không chọn kết luận có lợi.

## 2. Track kiểm soát và model

Ba arm dùng cùng provider/model/effort, task instruction, snapshot/schema, output
contract, grader, whole-trial deadline và request/token caps. Native system prompt
khác nhau là một phần của harness. Không user skills, external plugins, memory hoặc
web; inventory lưu tool schema thực gửi provider. Gold/payload không được đưa vào
workspace của agent. Cách ly này không là sandbox bảo mật OS hoàn chỉnh.

**Trong giai đoạn phát triển hiện tại chỉ dùng key NVIDIA và model nhỏ.** Config hiện
tại quyết định model; tên/route/hash nằm trong manifest. `effort=none` là cấu hình duy
nhất đã triển khai. OpenCode Go/DeepSeek V4.1 Flash effort medium là **dự định chưa
mua/chưa xác minh**, không là cấu hình đã được đăng ký như đang chạy. Driver từ chối
provider/effort chưa hỗ trợ. Nếu sau này đổi route/effort, phải cập nhật protocol trước
main, xác minh cả ba adapter, canary mới và freeze mới; không gộp model.

Không dùng giá Go cho NVIDIA. Cost mặc định N/A khi không có bảng giá được xác minh
và đóng băng; tách list-price estimate, thực trả, phí thuê bao và allowance. Cache cần
quy ước input bao gồm hay loại cache; không suy missing token thành 0.

## 3. Thiết kế và lịch chạy

- Smoke: 3 câu, không tính điểm; pilot: 24 câu. Main: 200 câu, holdout: 50 câu theo
  bộ hiện có. Main/holdout dự kiến **3 run độc lập/task/arm**.
- CPI chưa xác định rõ chiều chỉ tiêu và rubric narrative chưa kiểm tra đủ dữ kiện
  được hỏi được cách ly bằng metadata, không dựa trên kết quả model. Số câu mặc định
  đủ điều kiện: **178 main, 43 holdout, 22 pilot, 3 smoke**; số câu chỉ dành cho chẩn
  đoán tương ứng là **22, 7, 2, 0**. Manifest/freeze lưu đầy đủ ID và lý do loại; chỉ chẩn đoán
  smoke/pilot được phép `--include-quarantined`, không dùng để cấp certificate.
- Mỗi attempt có workspace/config/session/log riêng; retry không mang lại đáp án hay
  state cũ. Task order seeded; arm order qua các hoán vị cân bằng, lưu cố định trước
  inference trong manifest.
- Timeout cấp task hoặc `--timeout` override, áp dụng chung và gồm retry/backoff.
  Chỉ retry provider transient đã phân loại; auth/format/semantic/effort lỗi không
  tự động được thêm lần thử. Request/token caps trừ cả các attempt trước.
- Resume đúng manifest; row hoàn tất không chạy lại. Attempt hoàn tất nhưng chưa
  append row được finalize từ artifact; crash midstream thành failure interrupted,
  usage chưa biết=N/A. Không cấp lại ngân sách sau crash.
- Chọn subset nếu một tuần không đủ phải làm **trước main**, lưu IDs, phương pháp
  phân tầng, seed và lý do theo pilot runtime. Không bỏ câu sau khi thấy arm nào sai.
- Không chạy model trên holdout để debug. Freeze có offline tests + artifact live
  ba arm được kiểm tra. Holdout mở một lần bằng receipt, sau đó chỉ resume đúng run.

Các replay request pilot/smoke được tái dựng minh bạch trong `request_contracts.json`;
không gọi chúng là bản ghi request lịch sử nguyên gốc. Payload overlap giữa main và
holdout phải được báo: holdout hiện có không chứng minh generalization sang dữ liệu
hoàn toàn mới. Không tinh chỉnh dựa vào kết quả holdout.

## 4. Endpoint và mẫu số

| Endpoint | Định nghĩa đóng băng |
|---|---|
| Primary success | Mọi check schema/nội dung/provenance đúng; evidence `call_id/tool/source/as_of/payload_sha256/matched_entry_id/response_sha256` khớp call thành công của attempt hiện tại, đúng entry và response; status ok, trong budget. Mẫu số started. |
| Semantic secondary | Check nội dung tài chính tách khỏi schema/provenance; có thể đúng dù primary fail do adapter. |
| Stable-correct | Đúng cả ba run. Chỉ task đủ run IDs 1/2/3 thuộc mẫu complete; báo đồng thời all-scheduled với incomplete riêng. Không dùng pass@3 hoặc 1/1 thay 3/3. |
| FP | Task gold refusal; báo FP/started, FP/answered, DNF. Không dùng mọi L4 làm mẫu số. |
| False refusal | Trường yêu cầu thực sự có đáp án bị null/từ chối. Missing key là format error; set/ranking có dữ liệu không bị suy ra refusal vì thiếu scalar. Partial đánh giá theo trường gold. |
| DNF/answered | Answered có JSON trả lời và status ok trong thời hạn. Success/answered chỉ lấy tử số của chính tập answered. |
| Latency | Tổng end-to-end gồm retries/backoff, p50/p90 và valid-answer latency/timeout. |
| Usage/cost | Mọi attempt/request, coverage riêng input/output/reasoning/cache. Incomplete cost coverage: tổng quan sát báo riêng; cost/success toàn run=N/A. Model và giá lấy manifest của run. |

Diagnostics: per-check breakdown, execution/format/semantic error, số call thật từ
ledger, retry, bonus thay thế khi refusal, MAD/abs(median) per-task trên pass-only.
Các chỉ số phụ không thay primary hoặc được chọn lại sau khi xem kết quả.

## 5. Phân tích và công bố

Unit phân tích là **task**, ba lần cùng task là cụm. Paired bootstrap 2.000 draws,
seed 20261104 trên chênh trung bình success per-task; CI 95%. Thêm bootstrap theo
nhóm payload hash trùng như sensitivity của tương quan dữ liệu. So sánh ba cặp arm
được lưu; exact McNemar áp dụng endpoint **stable-correct nhị phân đủ 3 run**; Holm
cho họ ba phép so sánh này. Smoke một run không tạo p-value stable 3/3.

Báo paired complete-task count, incomplete/dropped pairs, tổng task/trial theo mức,
coverage, model/config/manifest hashes và mọi thay đổi protocol. CI/mức ý nghĩa không
thay thế ngưỡng ý nghĩa thực tế. Không coi ba lần cùng task là ba quan sát độc lập.
Mixed-model result directory bị từ chối; dữ liệu lịch sử chưa freeze chỉ dùng chẩn đoán.

L3–L5 và FP là các phân tích nhóm đã định trước; nếu thực hiện thêm subgroup test phải
gắn nhãn exploratory hoặc đăng ký họ kiểm định riêng, không nhận p-value toàn main
làm bằng chứng trực tiếp cho subgroup. Kết luận chênh hiệu quả phải đi cùng thời gian,
cost coverage, refusal/DNF và giới hạn đại diện bộ đề.

## 6. Gates và thay đổi protocol

1. Regression/adversarial pass: request sai không replay, schema/kỳ/nguồn/null sai fail,
   grounded ledger join không bị tự khai nguồn vượt qua; metrics/retry/recovery/resume
   có counterexample tests. Không kiểm tra model trên holdout trong phát triển.
2. Live smoke 3 câu × 3 arm × ít nhất 2 run đúng model/config/code/harness; tool-call/schema/provenance và
   inventory được kiểm tra từ artifact; offline check xanh đơn lẻ không đủ.
   Sửa đổi protocol vận hành `operational_parity_v3` ngày 04/11/2026, trước lần smoke
   xác nhận mới: mọi trial phải hoàn tất trong budget, usage đầy đủ, đúng model/catalog
   và ledger khớp replay. Request bị snapshot từ chối rõ ràng do chọn sai tham số là
   lỗi chất lượng model, vẫn giữ FAIL trong điểm số. Model không gọi tool được phép
   không có ledger chỉ khi telemetry provider chứng minh đúng 0 tool call và catalog
   đầy đủ. Tool call provider đã phát phải có ledger tương ứng; ledger hỏng/thiếu,
   lỗi server/protocol, fallback, timeout hoặc usage không rõ đều chặn certificate.
   Mỗi arm vẫn cần ít nhất một canary thực gọi tool thành công, tiếp tục trả đáp án
   primary đúng và evidence khớp ledger; kiểm tra lại bằng grader đóng băng. Certificate
   xác nhận vận hành, không chứng nhận độ chính xác của model nhỏ. Artifact smoke cũ
   giữ nguyên và không được cấp lại certificate theo sửa đổi này; phải chạy mới.
3. `ready_check --certificate` tạo bằng chứng được `run_manifest.py` kiểm tra trước
   freeze; main/holdout từ chối khi state đổi. Source scope được ghi rõ.
4. Sau freeze, thay gold/task/runner/metric/config/harness phải ghi lỗi và lập nghiên
   cứu mới; không âm thầm sửa rồi resume cùng manifest. Holdout chỉ xác nhận.

Changelog 04/11/2026: sửa matcher/grader và provenance; chuẩn hóa output, isolation,
budget/telemetry; manifest/schedule/resume/freeze/holdout receipt; bổ sung metrics/
thống kê và sửa định nghĩa stable-correct. Mọi smoke trước thay đổi không là baseline
xếp hạng chính thức. Số liệu xác minh mới được ghi trong báo cáo validation riêng sau
khi hoàn tất integration, không ghi đè audit lịch sử.
