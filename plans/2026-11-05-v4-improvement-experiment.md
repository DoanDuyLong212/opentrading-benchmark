# Protocol thực nghiệm prototype OT/MCP v4

Đăng ký05/11/2026 trước khi triển khai candidate và trước inference mới. Trạng thái: engineering/development exploratory; không confirmatory, không chứng nhận thắng toàn lĩnh vực.

## Primary goal

Kiểm tra một phiên bản OT sửa được lỗi request và giữ hợp đồng đáp án có tăng tỷ lệ trả lời đúng trên dữ liệu development, so với native OT baseline, OpenCode và DSH trên cùng interface MCP mới, model nhỏ và ngân sách.

## Phạm vi và identity

- Workspace mới `experiments/finance-v4-study/`; copy source/tools/tasks cần thiết theo whitelist, không copy credentials/.env/results/node_modules thành file dữ liệu agent. Dependency native được reuse read-only và hash đúng version; không npm install vào symlink node_modules của dự án gốc.
- V3 source/runtime/prompt/results/certificate giữ nguyên. Không reset ba thay đổi diagnostic bên ngoài. Code v4 có config/protocol/runtime/toolcatalog/task/grader manifests mới.
- Chỉ NVIDIA `nvidia/nemotron-3.5-bolt-e4b`, effortnone,temp0,top_p1. Không gọi DeepSeek/Go/Google/model khác. Chỉ smoke/pilot; không inference main/holdout.

## Một candidate cố định trước inference

Native loop OT giữ nguyên; bổ sung policy opt-in, OFF cho baseline và ON cho candidate:

1. Local input validation theo raw MCP JSONschema bằng validator thực; no coercion/default mutation. Model-visible schema không mất ràng buộc quan trọng.
2. Bounded tool-error correction cho lỗi parse/schema/invalid_argument/not_recorded của thao tác read-only; tối đa một correction attempt cho cùng intent, không lặp args, không retry auth/no-data/side effect. Feedback dựa actualtoolresults/catalog công khai, không chọn request theo hidden gold/taskID. Không giả recovery nếu chỉ tool khác thành công.
3. Public machine-response policy: JSON object nếu người dùng yêu cầu, kiểm required evidence khi contract yêu cầu, canonical mapping source/tool từ actual registry, immutable provenance từ actual successful results. Sai contract được một model correction trong cùng budget, không sửa số tài chính theo oracle. Không tự thêm evidence của tool chưa gọi/thất bại hoặc làm scalar→list tự động.
4. Prompt machine-output gọn, giải quyết conflict JSON/style/unit, giữ safety/data integrity. Đây là combined candidate; không quy delta cho riêng shortening/validator.

Các API mới là native product options/capabilities, không benchmark-only answer rescue trong adapter. Không thêm calculator riêng cho OT trong track này. Phép tính/kỳ/đơn vị còn do model và tools hiện có; nếu vẫn sai phải báo, không auto chữa theo gold.

## MCP chung và grader

- Cùng contract-v4metadata cho mọi condition: giữ mô tả tool gốc, bổ sung field semantics/allowed domain values đã xác minh, actual outputSchema/annotations/meta và replay restriction riêng.
- Authoritative input validation của server dùng chính schema C1 đã quảng bá cho mọi condition, gồm enum/bounds mới; không chỉ đổi description rồi vẫn validate schema cũ. Các default/type/recorded requests được giữ, thuật toán matching không đổi. V4 phân loại riêng lỗi type/shape theo schema frozen-v3 và domain constraints bổ sung; input bị OT chặn trước MCP phải có native call-ID/error/wire proof riêng, không bị bỏ khỏi mẫu số generated calls.
- Giữ nguyên recorded requests, matching, payload bytes và numeric gold; không nới matcher/bỏ args/trả payload không đúng query. Profile contract và schema được hash; valid recorded requests phải qua offline gate.
- Các sửa production MCP sâu trong standardization plan chưa được gọi đã triển khai chỉ nhờ metadata experiment. Prototype contract guards có thể kiểm offline bằng source-local handler/stub, không fetch dữ liệu thật.
- Fix `period_hit` broad-negation bug trong task/grader copies v4, dùng chung mọi arm; giữ wrongyear/quarter/date và temporalnegation adversarial guards. Không sửa task/grader v3 tại chỗ. Đáp án mới chấm song song frozen grader cho sensitivity để tách tác động grader khỏi chất lượng.

## Lịch chạy cố định

1. Relevant native/MCP/benchmark offline tests, actual wire capture mocks và nguồn dependencies đủ pin trước inference.
2. Smoke18lượt:3task×2run×3canonicalarms, canonicalOT chọn candidate. Operational gate yêu cầu native loop/model/schema/usage/ledger đúng; quality failures giữ nguyên; mỗi nativearm có tool-grounded canary primary đúng. Không retry để làm đẹp smoke.
3. Khi gate pass, pilot176lượt:22eligiblepilot×2run×4condition `opentrading_baseline`, `opentrading_finance` (v4candidate), `opencode`, `dsh`. Balanced cyclicLatin order,seed20261105;44task/runblocks,11lần/position/condition.
4. Timeout240s/trial, provider_timeout45s,24request,2048output/request,48000total-policytoken,retry0,pause2s; stall policy giữ120s và disclosebuffering (model nhỏ expected<45s/request); không tăng cap riêngOT. Usage thiếu giữN/A. Nếu outage kéo dài thì stop/resume đúngmanifest, không thay trial lỗi.
5. Sau launch để process chạy, không AI polling liên tục. Review một lượt khi hoàn tất; heartbeat nhẹ nếu cần, không gửi tiến độ không thay đổi. Resume completed phải0newrequests/0duplicates.

## Endpoint và phân tích

- Primary: full success trên started44/condition, với grader v4 và actual ledger, schema/timely/status. Báo frozen-grader sensitivity cùng numerator/denominator.
- Secondary: semantic numeric/period/unit, requested-source/provenance, wrongschema calls, schema-validreplay mismatch, required-data coverage, same-intentcorrection success, corrected-call withoutfinalprimary, DNF/false-refusal/FP, latency/tokenusagecoverage.
- Difference candidate−OTbaseline vàcandidate−mỗi comparator theo22task; exploratory task-paired CI95, payload-family sensitivity. Không gọi2run làstable3/3; không claim +7pp/97,5%maincriterion.
- Public task set đã được xem/tối ưu: kết quả chỉ là development diagnostic, không generalization proof. MCP/interface/grader đều đổi nên delta v3→v4 không là hiệu ứng riêng OT; concurrent candidate−baseline cùngv4 mới đánh giá combinednativechange.
- Không retune candidate sau smoke/pilot để săn kết quả. Smoke chỉ sửa blocker hạ tầng thật; bất kỳ sửa quality behavior sau inference tạo experiment version mới và giữ mọi kết quả cũ.

## Rollout guard trước khi xem kết quả

Default không tự promote trong lượt này. Chỉ đề xuất promote nếu primary candidate>baseline, DNF/false-refusal/FP không regress, không có fabricated evidence accepted và không tăng số trial claimed evidence mismatch; báo wrongperiod/unit và semantic riêng. Thua hoặc bằng primary → giữ candidate thử nghiệm. Guard là engineering gate, không thay xác nhận trên dữ liệu mới.

Original `/home/doanlong/OpenTrading` và `/home/doanlong/MCP-server` không bị ghi đè trong prototype. Chỉ xem xét cài/deploy sau review cụ thể và hash-guard/backup; không muaGo. Khi xong báo cả improvements lẫn failures, không chỉ chọn task thắng.
