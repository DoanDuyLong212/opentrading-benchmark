# Study v4.2 đề xuất sau smoke v4.1: replay interface, per-intent repair và answer contract

Ngày06/11/2026, Asia/Bangkok. **Đăng ký thiết kế trước inference; chưa triển khai, chưa chạy model.** Không sửa source/prompt/grader/results v4.1. Không chạy lại smoke/pilot cũ bằng candidate đã tune rồi thay kết quả. Workspace/code/receipts của phiên bản sau phải có identity riêng và được review trước khi khởi chạy.

## Căn cứ và mục tiêu

Smoke v4.1 kết thúc18trial: official OT1/6, OC2/6, DSH2/6; OT2DNF vì machine contract vẫn sai sau bounded output correction. Tất cả36quote-history calls hợpC1schema nhưng không có recording tương ứng. HPG repair phase có thật nhưng model không gọi corrected request. Năm bank failures song song cùng tool làm state attempts lên5, loại tool khỏi correctionTools trước khi sửa bất kỳ bank intent nào. Một honest-refusal paraphrase bị lexical grader từ chối. Xem [báo cáo v4.1](/home/doanlong/extra/benchmark/audits/financial-prompt-v41/REPORT.md).

Mục tiêu tiếp theo: công bố đúng finite-query interface cho mọi condition, sửa request theo đúng từng intent, và phân biệt complete honest refusal với invalid output. Primary vẫn đòi lấy đúng dữ liệu/tính đúng/cite đúng, không coi schema-valid refusal ở câu answerable là thành công.

## 1. Interface common C2 cho finite-request replay

Chọn rõ track **finite-replay compliance**. C2 dùng cùng17tool, payload/recorded requests/numeric gold và exact matcher; bổ sung machine-readable accepted-request constraints được sinh từ public recorded/default-equivalent contracts. Các tổ hợp `columns/days/interval` chỉ được quảng bá nếu server thật sự hỗ trợ đúng query đó.

- Một common profile cho B0, B1, OC và DSH. Có thể dùng `oneOf`/request variants với required/default rules chính xác; kiểm actual wire/capability mọi SDK trước inference. Không lặng lẽ strip constraints provider không hỗ trợ.
- Chỉ ràng buộc query support; không đưa financial answers, gold, taskID heuristics hoặc phép tính đáp án vào schema. Recorded request catalog vốn đã công khai cho mọi arm; C2 biến phạm vi finite đó thành hợp đồng dễ kiểm chứng.
- Giữ metadata production có nguồn; gắn rõ restriction replay. Không gọi C2 là full production financial API.
- Không bỏ/thay args sau model call, không tự chọn recorded request thay model và không trả payload365ngày cho query1ngày. Không broaden matcher để cứu trial đã chạy.
- Tách type/shape error, production-domain error và unsupported finite-snapshot query. Một request hợpC1 nhưng ngoài C2 phải được nhận diện là giới hạn snapshot; không gắn nhãn thành dữ liệu tài chính không tồn tại hoặc production schema sai.
- Cả402recorded/default-equivalent requests phải qua; mọi query ngoài tập phải fail có code/argument paths/allowed public variants/retryability, không có financial evidence. Đối chiếu589financial files byte-identical nếu corpus không đổi.

Một track production-faithful sau này có thể mở rộng recordings hoặc deterministic projection có semantics/provenance được xác minh. Đó là corpus/version riêng, không trộn với endpoint finite-replay này.

## 2. Native repair state theo tool + intent

**P0:** Chuyển state từ chỉ `def.name` sang canonical tool + các entity/currency, metric/statement, kỳ/scope được mô tả công khai. Không dùng taskID hoặc gold. Chuẩn hóa chỉ để so sánh identity; không sửa actual financial args ngầm.

- Scope guard chỉ áp cho call được nhận diện thuộc failed intent/correction phase. Một failure VCB không được chặn next legitimate BID request trong normal execution. Actual-class repro v4.1 đã xác nhận bug này; xem [policy-counter-repro.json](/home/doanlong/extra/benchmark/audits/financial-prompt-v41/policy-counter-repro.json).
- Phân biệt **initial call failure** với **correction attempt**. Năm bank calls ban đầu là năm intent, không phải năm lần sửa cùng một intent.
- Mỗi eligible failed intent được tối đa một corrected execution trong shared request/token/time/native-step budget. Call đã sửa thành công không được làm mất identity của intent ban đầu để cho phép retry vô hạn.
- Parallel batch có state riêng từng call/intent. Duplicate cùng intent/args không chạmMCP lần hai; một lỗi không tiêu hao budget sửa các intent khác. Partial success giữ nguyên và không replay lại các call đã thành công.
- Không đổi entity/kỳ/metric/scope khi sửa. Invalid enum/type có thể sửa theo public schema; những trường chứa yêu cầu tài chính thật phải giữ nghĩa. Window/projection không mặc nhiên là presentation nếu nó thay đổi câu hỏi tài chính; caller/tool contract phải xác định phạm vi được sửa.
- Auth/no-data/unsupported-operation và side-effect calls không vào parameter repair. Structured error code/retryability là nguồn phân loại chính; không phụ thuộc hoàn toàn regex prose.
- Giữ full declared catalog; native before-execution guard giới hạn actual corrected intents. Ghi `intent_id`, original SDK call ID, correction phase, attempt budget và reason bằng metadata runtime sinh từ actual state. Không tạo financial evidence cho local rejection.
- Action guard, cancel, native upstream recovery và custom correction dùng chung budget/accounting; không nới cap để làm đẹp kết quả.

Kiểm offline bắt buộc:5bank fail đồng thời→5intent còn eligible; VCBfail→BIDnewintent tuần tự không bị scope guard; một entityfail và một entityhealthy không lây state; budget từngintent và correctionphase đúng; first correction success; repeated args; mixed success/failure; hai duplicate trong cùng SDKbatch; đổi entity/kỳ; invalid scalar→list khi giữ cùng nghĩa; auth/no-data/write; cancellation; exhausted global budget. Phải chạy qua actual native SDK + actual MCP replay error path và gateway stub, không chỉ synthetic helper.

## 3. Public success/refusal contract và semantic refusal grading

Native caller nhận một public response contract rõ ràng, có success schema và legitimate-refusal branch. Contract công khai cho model/caller; không đọc task gold để suy required fields.

- Với bài tổng hợp, `values` thành công và fallback `value:null,reason,evidence` phải có định nghĩa không mâu thuẫn; evidence luôn là array. Không để rule success-only khiến mọi refusal thành native fatal chỉ vì object shape khác.
- Refusal cho answerable task vẫn trượt primary và tính false refusal. Runtime complete một honest error/refusal không đồng nghĩa tài chính đúng. Failed/cancelled/invalid output tiếp tục DNF theo định nghĩa đã đăng ký.
- Không auto điền evidence/hash/source/value. Chỉ copy immutable actual response receipts khi contract thực sự yêu cầu; rejected query không chứng minh thiếu dữ liệu.
- Grader mới nhận các paraphrase có cùng nghĩa như “không được giải mã thành symbol hợp lệ” khi actual resolver xác nhận empty. Test chống negation kép, contradiction, generic tool-error bị đổi thành not-found, giả JSONnull, missing evidence và fabricated receipts.
- Không chỉ thêm đúng một câu đã thấy để săn điểm. Chuẩn bị tập paraphrase/negative cases độc lập, chốt semantics/rubric trước inference. Nếu dùng semantic adjudication, định danh rubric/judge/version/độ đồng thuận và audit disagreements; không âm thầm thay lexical endpoint lịch sử.
- Chấm mọi answer mới song song frozen-v4.1 và grader mới; báo delta do grader riêng. Official v4.1 vẫn giữ1/6OT dù semantic adjudication chấp nhận trap thành2/6.

## 4. Thiết kế thí nghiệm và gate

Study mới dùng current0.3.1 native base/dependency tree đã pin hoặc một base mới được công bố trước, cùng source cho B0/B1. B0 policyOFF; B1 policyON với các sửa trên và prompt đã chốt. OC/DSH native cùng C2/public contract/grader mới. Không nâng cấp một arm giữa run.

Giữ model nhỏ NVIDIA Bolt E4B, effortnone,temp0,top_p1; provider45s/trial240s;24requests,2048output/request,48000policytokens,retry0,pause2. Native stall theo current base300s và disclose. Không DeepSeek/Go/Google, không main/holdout inference trong track này.

Lịch dự kiến đăng ký trước khi chạy:18smoke=3task×2repeat×3canonicalarms; chỉ sau gate mới176pilot=22eligibletask×2repeat×4condition,44/condition, balanced Latin,seed20261105. Lưu đúng tên version/ngày mới, toàn bộ failures và resume invariants.

Gate kỹ thuật phải gồm actual full-catalog wire, generated-call reconciliation, usage/caps/model identity, partial output/status, source/dependency hashes và tests phù hợp. Thêm numeric retrieval canary rõ ràng cho mỗi arm để smoke toàn trap đúng không che việc không truy xuất được dữ liệu tài chính. Điều kiện canary và acceptance cụ thể phải nằm trong sealed protocol/code trước inference, không sửa sau thấy output. **Không hạ gate v4.1 để dùng kết quả cũ đi tiếp.**

Candidate kết hợp nhiều sửa; concurrent B1−B0 cùngC2 đo gói cải tiến. Delta v4.1→v4.2 chứa commoninterface/grader change, không gọi toàn bộ delta là tác dụng riêng nativeOT. Ablation từng lever, nếu cần, phải là lịch nghiên cứu riêng trong budget đã thống nhất.

## 5. Endpoints, audit và quyết định

Primary đầy đủ trên mọi44trial bắt đầu; semantic/unit/period/grounding riêng. Báo generated type/domain/finite-support validity, same-intent corrected calls, required-data coverage và final-primary recovery riêng; native failed/aborted/unanswered/recovery, false-refusal trên40answerable-started, FP trên4refusal, evidence mismatch/fabrication, usage completeness, request/token/latency và task-pairedCI95/payload-family sensitivity.

Chấm độc lập mọi stored answer với cả hai grader; recheck7field evidence/context và exactledger/capture/model/caps. Giữ mọi timeout/DNF/partialusage, không gán thiếu thành0. Completed resume phải0newcalls/0captures/0duplicates và cácfileđãcó giữbyte-identical.

Guard đề xuất giữ nghiêm: primaryB1>concurrentB0; DNF/false-refusal/FP không regress;0acceptedfabricatedevidence; claimed evidence-mismatch trials không tăng. Chưa có kết quả hoặc dự báo numerator. Study public-development22task×2repeat không chứng minh chiến thắng main+7pp/CI97,5%, stable3/3 hay generalization.

Không tự promote/cài original OT hoặc MCP-server. Mọi rollout sau này cần report cụ thể, review, hashguard/backup và authorization phù hợp. Compute-as-tools/commonunitnormalization là study riêng tiếp theo; không thêm vào giữa thí nghiệm này để săn điểm.

## Artifact phải có trước khởi chạy

- Workspace/source/dependency/config/catalog/protocol/grader/task fingerprints mới; original preservation start/end.
- Offline exactrequest+error+publiccontract adversarial suite; actualSDK/MCP/gateway integrated scripted cases; full relevant suites và independent closure với mọi failure giữ nguyên.
- Sealed smoke/pilot manifests, canary rule, guard/statistics và commands; verifier/resume checklist sẵn sàng.
- Không sửa quality behavior sau inference; blocker hạ tầng thật được version hóa và giữ các run cũ. Không chạymodel trong phạm vi tạo kế hoạch này.

## Implementation registration v4.2 — before first model request

Study root: `experiments/finance-v42-study`; same upstream OT0.3.1 HEAD `b6e354e76894887e31c33b1f13b44eadc02fad7e` and isolated locked dependencies as v4.1. `opentrading_baseline` is current production prompts with finance policy OFF; `opentrading_finance` (canonical `opentrading`) uses same native source with policy ON and finance prompts. Common C2 raw-schema passthrough for marked schemas is plumbing applied equally to B0 and B1; root `anyOf` constraints must survive actual wire for every arm. Gateway rejects changed C2 constraints before provider inference. A provider/adapter incapable of these constraints fails the technical gate; constraints are not silently weakened.

C2 is generated solely from public recorded requests + C1 defaults and keeps the matcher unchanged. It intersects full C1 schema with `anyOf` exact finite variants. Scalar strings retain matcher case/space equivalence where C1 permits it. Array order is ignored with exact length, allowed members and a `contains` assertion for every distinct normalized member; duplicate-valued recorded arrays fail closed pending a reviewed multiset contract. An unsupported finite query returns `unsupported_snapshot_query`, public allowed variants, argument paths, retryability and no financial evidence. This is finite-replay compliance, not proof of production API failure/capability.

All arms receive identical common response contract suffix `PUBLIC_RESPONSE_CONTRACT_V42` from tools/public_response_contract.py. This alternative permits legitimate `value:null,reason,evidence:[]` refusal even where public success example requires `values`. Runtime contract completeness does not confer primary correctness. Existing task instructions, numeric gold, recorded requests and financial payload files are preserved; only new-copy graders change. Semantic refusal grading is a versioned deterministic rule rubric (no additional model judge), with empty-resolver expansions allowed only against the actual frozen empty resolver payload, independent paraphrase/contradiction/double-negation/query-error tests, and actual-session grounding required by primary. Every new stored answer is graded by v4.2, frozen-v4.1 and frozen-v3 graders; deltas are reported separately.

**Sealed smoke gate (no weakening after inference):** exactly 18 scheduled trials, 3 smoke tasks × 2 repeats × canonical OT/OC/DSH; all existing engineering/readiness checks continue to apply. Additionally EACH arm must achieve at least one primary-correct answer on `smoke-quote-01` OR `smoke-agg-01`, grounded in an actual successful `vn_quote_history` execution in that trial's final attempt. Trap-only primary success cannot qualify. Every smoke trial must remain timely/statusOK with complete usage and reconciled generated calls. Poor numerical quality does not permit replacement/resampling. If gate fails, stop before pilot, preserve all failures and report reasons.

Exact run identities: `results/financial-v42-smoke-20261106`, readiness receipt `results/financial-v42-ready-20261106.json`, then only on passing certificate `results/financial-v42-pilot-20261106`. 176 pilot trials, 44 per condition; same seed20261105 and caps as above. Initial manifests freeze code/tasks/protocol/dependency inventories. No main/holdout inference, no model fallback, no tuning after first live request, no production installation. Complete-run resume must preserve all files and emit zero new provider calls/captures/trials. The implementation report records offline checks and exact fingerprints before launch.
