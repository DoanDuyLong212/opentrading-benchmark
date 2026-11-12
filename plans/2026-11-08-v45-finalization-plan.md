# v4.5 — Hoàn thiện OT trên main mới, rồi đóng băng để so sánh công bằng

Ngày lập: 08/11/2026, Asia/Bangkok. Trạng thái: **kế hoạch triển khai; chưa cấp chứng nhận sẵn sàng main, chưa chạy inference v4.5**. Thay thế hướng nghiên cứu trong bản nháp 07/11, giữ nguyên bản nháp và toàn bộ study v4.4.

## Mục tiêu chính

Người dùng nhận câu trả lời tài chính Việt Nam đúng thực thể, chỉ tiêu, kỳ và đơn vị, có nguồn thật và hoàn tất đáng tin cậy. Đóng băng một bản OT sản phẩm có thể tái tạo cùng môi trường benchmark đã kiểm chứng; chỉ tuyên bố thắng OpenCode/DSH khi kết quả thực nghiệm độc lập đáp ứng tiêu chí đăng ký trước.

“Hoàn thiện 100%” được chuyển thành checklist có bằng chứng cho **phạm vi sản phẩm và benchmark đã định nghĩa**, không phải bảo đảm không còn lỗi hoặc thắng mọi tác vụ tài chính. Tôi hiểu đối thủ trong yêu cầu cuối là OpenCode và DSH; OT baseline vẫn là đối chứng ablation ở dev/pilot.

## Căn cứ và quyết định ngay

- Repo sản phẩm `/home/doanlong/OpenTrading`: trước pull `e5ce4e1a75a6c430ff8464b867032da18814cee3`; remote được fetch là `0a65fa04d0e60ee3d1822de365f2a88dc92eaf2f`. HEAD merge local cuối: `b4b4b848541986239cfd477715b6d3819cbc443c`. Mười hai PR merged mới: #229 memory; #235 yolo; #236 headless; #237 eval memory; #238 dependencies; #222–227 evidence/read_result/units/compute/figures/table-cap; #239 calculate. Merge local giữ `promptDir`, `validatePromptDir`, `clockPolicy` và memory binding/redaction/cards mới. Xem biên bản đồng bộ để biết HEAD merge cuối và kết quả kiểm tra thực tế.
- Sao lưu trước pull gồm 999 file, trong đó 441 file chưa được Git theo dõi. Không đưa research cá nhân, auth, memory.db hay cấu hình người dùng vào snapshot benchmark. Các file chưa commit được giữ nguyên.
- V4.4: hai smoke đủ 24/model, không pilot; B1 primary 2/6 mỗi model. DeepSeek semantic B1 2/6 so với 3/6 của từng đối chứng, DNF 4/6 so với 3/6. Không có bằng chứng OT vượt trội tài chính. Mọi kết quả/graders/auditor/seal cũ giữ nguyên.
- Quan trọng: v4.4 wrapper **loại toàn bộ builtin và không truyền notebook**. Do đó nó không đo memory, `calculate`, `compute`, `read_result` của sản phẩm mới. Không dùng snapshot cũ làm runtime main mới.
- Main sau wave-2: 200 câu danh nghĩa, 183 eligible/17 cách ly; level 34/36/41/49/40. Mười câu mới tự kiểm tra oracle và fixture đúng 10/10, nhưng audit 227 câu exit 1. Task202 sai đề↔oracle, task214 có tie chưa rõ; root grader còn thiếu guard v4.4 và có phản ví dụ refusal chứa số bịa vẫn pass. Đây là blocker **trước khi freeze**, không phải lý do nới tiêu chí sau chạy.
- Model cho mọi study mới: NVIDIA `nvidia/nemotron-3.5-super-vl-120b-a12b` thay Bolt E4B; NVIDIA `deepseek-ai/deepseek-v4.1-flash` giữ làm cohort riêng. Không thay model/config trong run đã đóng băng. Model mới chưa có admission receipt trong gateway hiện tại; đổi chuỗi config đơn thuần không đủ.

## Giai đoạn 0 — Đối chiếu tài liệu, pin base và quyết định hợp đồng

**Phục vụ mục tiêu chính:** bảo đảm đo đúng bản OT có memory/calculate mới và không làm mất safeguard cũ hoặc trộn các môi trường khác nhau.

Thực hiện/đã thực hiện:

1. Đọc đầy đủ §14–16 như tài liệu review, kiểm chứng bằng source, ledger và PR đã merge; không coi khuyến nghị trong file là lệnh ghi đè. Dùng ba báo cáo discovery tại `audits/financial-prompt-v45/` làm danh sách API được phép.
2. Hoàn tất merge, lưu backup, diff so remote, fingerprint tracked/untracked và kiểm tra xung đột. Chỉ hai file sản phẩm khác remote do hook benchmark hợp lệ; không ghi đè agent mới bằng agent cũ. Pin HEAD cuối, bun.lock, Bun/OS và full native/typecheck/hook-check artifacts mới. Kết quả lượt đồng bộ: typecheck và hook-check PASS; full native **1839 pass / 2 skip / 2 fail**. Recall-performance chạy riêng PASS (best36.8ms), full file TUI chạy riêng114/114PASS. Giữ lần full FAIL và test lọc TUI thiếu prerequisite; chưa coi cả suite đã xanh trong một lượt sạch.
3. Lập bản đồ 14 file native v4.4 khác base b6e354e trong `v44-native-delta-inventory.json` cùng patch tham khảo. Đưa safeguard vào adapter/policy mới có kiểm thử; **không tự bật prompt finance thất bại, không copy acquire dựa trên token hợp đồng benchmark vào đường sản phẩm mặc định**.
4. Legacy root `experiments/opentrading-runtime/node_modules` là symlink tới node_modules sản phẩm, nên dependency update upstream làm thay dependency effective của legacy runner. V3 manifest ghim ai7.0.137 trong khi target hiện là7.0.162; không tái sử dụng approval/certificate cũ hoặc chạy lại bằng đường này. Base v4.5 dùng dependency riêng cài theo lock mới; các study v4.2–v4.4 có cây dependency riêng, v4.4 đã kiểm tra25package giữ nguyên. Đây là lý do phải tạo study/base mới, không thay locators của run cũ.
5. Định nghĩa hai câu hỏi đo tách biệt: (A) chất lượng **sản phẩm đầy đủ** trên cùng dữ liệu và quyền năng tính toán, (B) tác động riêng của prompt/policy trên cùng tool inventory. Không gộp hai track thành một bảng “same tools”.

Tài liệu/API thực để dùng lại:

- `src/core/runtime.ts`: `createMemory(choice, home)`, `initRuntime({cwd,home,skills,memory,...})`, `switchMemory(runtime,memory)`.
- `src/core/agent.ts`: `RunOptions`, `runAgent`, `previewContext`; `promptDir`, `clockPolicy`, `stallMs` giữ từ local, `memory/constraints/redaction/sessionId/hooks` lấy từ upstream.
- `src/cli/print.ts:runPrint`; `scripts/eval/runner.ts:runEval/ask/prepareHome` cho clean-home, `useResultSession` và raw/visible captures. CLI print hiện chưa thấy gắn persistence như TUI: phải kiểm thử trước khi chọn làm runner.
- `src/core/retry.ts`: `RetryOptions`, `retryMiddleware`, `withRetries`, `classifyFailure`; **chưa có** tham số tắt/maxRetries trong RetryOptions. Không viết API tưởng tượng vào adapter.
- Benchmark frozen v4.4: `tools/runners/ot_headless.ts`, `tools/analytics_compute.py`, `src/core/finance-policy.ts`; chỉ dùng làm tham khảo và regression fixtures.

Kiểm chứng: remote là ancestor của merge; mọi file cá nhân có cùng hash; không conflict marker/unmerged index; source/hooks memory đồng thời hoạt động; compiled/actual CLI không gọi model ngoài lịch; replay một completed run không tạo call. Test hiệu năng thất bại phải báo riêng và điều tra, không hạ ngưỡng để có PASS.

## Giai đoạn 1 — Hoàn thiện đường sản phẩm: nguồn, đơn vị, phép tính và memory

**Phục vụ mục tiêu chính:** kết quả tính đúng phải dùng đúng dữ liệu tài chính đã truy xuất, còn memory hỗ trợ quy trình mà không biến thành nguồn giá hoặc rò đáp án.

Các việc cần triển khai trên base mới, trước product freeze:

1. Dùng `tools/refs.ts:useResultSession/recallResult`, `tools/evidence.ts`, `tools/wrap.ts` làm một đường evidence chung cho TUI, headless và eval. Lưu cả scalar và table; quote `{data:{last:...}}` phải chọn được field có ref mà không đoán. Xác minh failure khi chạm giới hạn lưu không biến thành “không có dữ liệu”. Lưu raw nguồn và visible đã normalize/cap bằng hai hash khác nhau.
2. Dùng `calculateTool`, parser `calculate/expression.ts`, `calculate/units.ts`, `computeTool` thực của upstream. Giữ generic calculator linh hoạt cho sản phẩm, nhưng chế độ financial-grounded phải kiểm tra nguồn: `native ref → native SDK call → biên nhận nguồn thật → lá số/kỳ/thực thể/đơn vị → kết quả suy dẫn`. Literal `ref` hiện chỉ được chép lại, không được coi là chứng minh truy xuất; hằng số như 100/4 là công thức, số liệu tài chính phải có lineage. Không mint seven-field receipt giả cho kết quả native.
3. Chuẩn hóa đơn vị từ **metadata nguồn công khai**, bao gồm VND, nghìn, triệu, tỷ, `VNDbn`; kiểm tra tương thích, đơn vị kết quả, kỳ riêng/lũy kế/TTM, entity và scope hợp nhất. Các phép so hai công ty có thể hợp lệ nếu được khai báo; không áp cấm cùng-entity máy móc. Cross-source cùng kỳ không bị nhầm với growth khác kỳ. Bổ sung chức năng còn thiếu nếu được yêu cầu bởi một họ tác vụ chung, không hardcode câu302 hoặc đáp án mẫu.
4. So kết quả native số học với Decimal độc lập để đặt tolerance theo chỉ tiêu; native dùng JS number/round6 không tự động tương đương Decimal40 của common compute. Scale nghìn đồng↔VND và toán tử abs/relative disagreement phải có fixture đúng. Không bắt prompt gọi một operation backend chưa thực hiện.
5. Tham khảo `FinancePolicyState` v4.4 để port validation trước tool, một correction có hạn theo financial intent, chống replay trùng và lưu original SDK identity. Thêm sửa `invalid_derivation` có cấu trúc; chỉ cho thay selector/representation đã chứng minh tương đương. **Không đánh dấu toàn bộ operands là repairable** rồi vô tình cho đổi call_id/entity/kỳ/chỉ tiêu. Dùng lỗi công khai gợi ý leaf từ nguồn thực đã lấy, không đọc gold hoặc đoán request ưu tiên.
6. Memory giữ chính sách upstream, model chỉ đọc, không tự ghi/activate. Main/stateless: giữ code memory đầy đủ nhưng cấu hình primary **none** đúng mặc định sản phẩm; kiểm chứng `notebook` rỗng độc lập như overhead regression. Mỗi trial/repeat/model/arm dùng home/store/session/refs mới, không profile thật. Muốn tuyên bố lợi thế memory: bộ dev nhiều lượt với cùng thông tin ban đầu cho các đối chứng, có thay đổi/thu hồi luận điểm, compaction/resume/redaction. Không trộn kết quả memory vào grounded-QA một lượt.
7. Finalization/generic public-output contract là lựa chọn caller có phiên bản. Giữ raw final bị từ chối và reason; không thay bằng đáp án tự dựng, không hardwire seven-field benchmark JSON vào mọi câu hỏi sản phẩm. Kết thúc ngay khi yêu cầu đủ nguồn; sửa format có hạn là hành vi native tính request, không gọi là transport retry.

Tài liệu/mẫu: discovery `MEMORY-COMPUTE-DISCOVERY.md`; native `test/{calculate,compute,evidence,print,memory-binding-agent,memory-redaction-agent,compact}.test.ts`; frozen `test/{finance-policy,agent}.test.ts`, `tools/tests/test_v44_compute.py`.

Kiểm chứng: scalar/bảng/array, ref qua restart, scope đúng/sai kỳ, dữ liệu bị sửa, literal không chứng minh nguồn, chain hai bước, percent vs fraction, dimension mismatch, cancel trong repair, hai tool trùng chỉ thực thi một lần; dùng fixture kỹ thuật không thuộc main. Full native/typecheck mới và actual headless/wire fixture phải PASS. Chưa có kết quả các test cho v4.5 ở thời điểm viết kế hoạch.

## Giai đoạn 2 — Chuẩn hóa benchmark, corpus và metrics trước seal

**Phục vụ mục tiêu chính:** một đáp án tài chính sai không được chấm đúng, và thay đổi định dạng không được diễn giải thành tiến bộ tài chính.

1. Tạo study mới từ **corpus root cập nhật** và base sản phẩm mới, không copy tasks/main cũ trong study v4.4. Giữ hashes, MIGRATION và archived −10. Cập nhật README/PRE-REGISTER theo inventory thực.
2. Dùng grader v4.4 làm baseline sửa chung ở phiên bản mới: resolver predicate, period negation có scope, conflicting-success/refusal. Thêm assertion-level test về entity/kỳ/unit/source ngay trong refusal, câu có nhiều giá trị/bonus, scope hợp nhất và tolerance. Fixture giả phải dán nhãn; end-to-end test vẫn đối soát ledger thật. **Không sửa grader trong kết quả v4.4**.
3. Sửa/quarantine202 (đề decliners nhưng oracle volume_leaders) và214 (tie/tolerance/tiebreak). Sửa ví dụ `value:null` ở307/308 thành hợp đồng không lộ branch đúng; lịch giao dịch phải có căn cứ công khai/captured calendar. Các cảnh báo ngày đã công khai ở301/303 cần phân loại đúng là consistency-template, không gọi đó là secret numeric leak; giải quyết invariant chung, không tắt leak scanner chỉ cho bốn task.
4. Kiểm tra mỗi field người dùng yêu cầu đều có check tương ứng (305/306 kỳ,306 pct/note,307/308 bonus). Bonus là secondary và phải ràng buộc field/kỳ/nguồn, không cứu primary. Hai resolver near-miss là fixture tổng hợp, phải ghi provenance fixture rõ; không gắn nhãn đã capture live.
5. Có metadata năng lực/họ tác vụ đã review; không dùng substring ID để gọi chain là retrieval đơn giản. Báo per-level/per-family, source/split overlap và tương quan theo payload. Không bổ sung 17 task stage2 hoặc50 “OT-strength” có lợi cho OT vào main hiện tại mà không migration và đánh giá construct chung riêng.
6. Metrics song song: **strict grounded success** (giữ hợp đồng raw), **grounded financial correctness** (nội dung tài chính + nguồn đúng, parser phân tích được đăng ký trước; không thưởng dữ liệu bịa), raw-format validity, completion/DNF, FR trên tất cả câu answerable đã lên lịch, FP trên traps, required-data coverage, compute attempt/success/uptake, repairattempt/execution, source+derived lineage, usage và latency mọi attempt. Semantic-only/frozen score là phân tích độ nhạy, không tự nâng thành finance-primary khi thiếu kiểm tra nguồn/kỳ.
7. Giữ mọi timeout/DNF trong mẫu số; numeric canary không có numeric win phải ghi “không đánh giá được năng lực số”, không PASS rỗng. Sửa auditor dispatch cho mọi schema profile, đối soát mỗi generated call = executed MCP/native hoặc local rejection có proof; không biến local rejection thành nguồn đã chạy.
8. Holdout hiện27/50 chia sẻ payload,11/50 trùng instruction+payload với main. Không dùng làm chứng nhận unseen. Giữ nguyên holdout cũ; nếu muốn đánh giá tổng quát hóa cần một bộ external/unseen mới được bên độc lập seal. Main đã được review nội dung là controlled comparison, không tuyên bố chưa từng thấy trong phát triển.

Tài liệu/mẫu: `CORPUS-DISCOVERY.md`, `corpus-offline-checks/grader-probes.json`, `corpus-offline-audit/audit-evidence.json`, migration wave2; frozen `tools/public_response_contract.py`, `tools/tests/test_public_contract.py`, grader fixes và auditor failures v4.4. Root `tools/metrics.py:build_summary`, `tools/audit_benchmark.py`, `tools/task_quality_report.py` là điểm tích hợp thật.

Kiểm chứng: audit offline tất cả eligible tasks exit0, đúng→pass và từng mutation value/unit/entity/period/scope/refusal/evidence→fail; oracle pass **không thay** expert content review. Header/hash mọi grader và corpus thống nhất; không inference main/holdout trong phát triển. N eligible cuối được chốt sau sửa, không mặc nhiên tiếp tục dùng183 nếu quarantine thay đổi.

## Giai đoạn 3 — Admission model, retry hạ tầng và canary schema

**Phục vụ mục tiêu chính:** giảm câu rỗng do lỗi tạm thời mà không che thất bại, chọn đáp án sau chấm hoặc chi tiêu không kiểm soát.

### Model và tham số

- Chỉ hai model NVIDIA đã yêu cầu: wire `nvidia/nemotron-3.5-super-vl-120b-a12b` và `deepseek-ai/deepseek-v4.1-flash`. Theo convention gateway hiện tại, benchmark key Super là `nvidia/nvidia/nemotron-3.5-super-vl-120b-a12b`; phải kiểm tra catalog và không strip nhầm namespace.
- [NVIDIA Super model card](https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b/modelcard) xác nhận120B tổng/12B active, NVFP4, text+vision. Khả năng model không chứng minh hosted endpoint nhận mọi knob. Model card khuyến nghị text temperature1/top_p.95, thinking qua chat template. Cohort mới sẽ dùng cấu hình endpoint đã canary, cùng effective setting cho mọi arm trong mỗi model; không mặc định ép0/1 như v4.4 rồi gọi đó là cấu hình tối ưu của Super. Reasoning/default/effort phải lưu wire và usage; `effort=none` không chứng minh thinking off.
- Đầu vào benchmark text-only; không dùng khả năng vision như một lợi thế chưa được đo. Bolt cũ chỉ tồn tại trong báo cáo lịch sử.
- `normalize_model`, `verify_nvidia.py`, model metadata/manifest/provider identity validators cần thêm admission riêng cho Super sau catalog+actual tool-call+tool-result continuation. Không mở allowlist tùy tiện chỉ vì model card tồn tại.

### Retry chung, phân loại lỗi và ngân sách

Chọn **một owner ở common gateway**, áp dụng cùng chính sách cho mọi arm của từng model. Driver whole-trial retry=0. Tắt/prove native provider retries ở OT/OC/DSH bằng seam thật; production default giữ nguyên. OT upstream có custom retry4/2 dù SDKmaxRetries0; `OPENTRADING_RETRY_SCALE=0` chỉ bỏ thời gian chờ, không tắt retry.

Policy dự kiến để seal sau canary kỹ thuật:

- Mỗi logical request tối đa initial+2 transport retry, waits4s/8s; honor Retry-After đến60s và trong remaining trial deadline.
- Chỉ retry lỗi upstream tạm thời trước khi có output/toolcall được đưa cho agent: per-minute429, connectreset/timeout và500/502/503/504. Không retry dailyquota, auth401/403, badrequest, actualmodelmismatch, schema/tool/format/semantic/refusal, localbudgetdeny hoặc usageunknowncontinuationdeny. Servererrorcode và origin phải tách; không map tất cả ValueError thành403.
- Cùng payload native/effective/context hash; không replay tool đã chạy; không thêm gold/qualityfeedback; lấy response transport-success đầu tiên. Giữ raw response an toàn, finish_reason, request IDs, bytes received, model metadata, ledger từng attempt. Missing metadata không được lấp model name giả; partial response là protocol fail, không mặc nhiên retry.
- Usage thiếu giữ partial. Khi không có bound đáng tin cho chi phí request lỗi thì fail closed; chỉ retry được nếu đã đăng ký conservative upper reservation theo actual request+output cap. Không reset token/request cap hoặc tính lỗi tốn0.
- Dự thảo resource profile: request timeout240s, trial deadline900s,24 **upstream attempts tổng**/trial gồm retry; max_output và token cap phải dimension bằng canary mới trên hai model/assembled prompt mới rồi chốt **trước smoke**. Không bê48000/2048 mặc định cũ hoặc coi bytes/4 là bound cứng. Khi chưa có cap có căn cứ thì launch blocked.
- Báo first-attempt completion, recovered by transport retry, exhausted/partial separately; primary vẫn tính mọi trial. Retry giúp availability, không bảo đảm mọi câu có đáp án đúng/parseable hoặc100%khôngDNF.

### Canary trước tài chính

1. Fixtures không gọi provider:503→success,429RetryAfter, dailyquota/auth/localbudget không retry, partial output/usageunknown, deadline/cancel, double-layer retry, captures native/effective, exact completed resume0call.
2. Model admission canary tổng hợp nhỏ: catalog, actual function call, continuation, metadata identity và reasoning/options/usage; không chứa dữ liệu/gold main. Chốt số request/cap trước khi gọi.
3. Schema canary đã đăng ký: so prefix pattern cũ, pattern neo toàn bộ cho hậu tố và khôngpattern trên cùng synthetic numeric object, hai repeat/mỗi treatment/model; template/payload cố định, báo cả bác bỏ giả thuyết. Không suy backendXGrammar từ chữ ký17/17. Nếu native source-ref mới thay JSONpointer, vẫn giữ canary để kiểm chứng nguyên nhân cũ, không tune schema theo từng output.

Tham khảo API/fixture thật trong `OPENCODE-SECTIONS14-16-FACTCHECK.md` mục3/6; `tools/runners/provider.py:ProviderGateway`, `aggregate_usage`; `tools/run_benchmark.py:transient_failure/execute_trial`; frozen `tools/tests/test_current_wire_gateway.py`. Không chạy canary trong lượt chỉ lập kế hoạch này.

## Giai đoạn 4 — Prompt và thí nghiệm dev trên base mới

**Phục vụ mục tiêu chính:** chọn một prompt giúp lấy đủ dữ liệu và dùng compute đúng, sau khi đã loại lỗi hợp đồng mà prompt không thể sửa.

- Không chép nguyên P-EN-bal §15.3: refusal evidence[] cứng có thể bỏ biên nhận bắt buộc, ví dụ pointer cố định không phù hợp native ref, “mọi field có receipt” chưa bảo đảm kỳ/scope. Nội dung nên ngắn, ưu tiên public task/output contract, đọc metadata nguồn, không coi rejection là no-data, một bounded repair, không tự tính khi tool hỗ trợ, phân biệt nguồn/suy dẫn và dừng khi đủ.
- Một candidate English có cùng nội dung với candidate Vietnamese, notices đồng ngôn ngữ; task vẫn tiếng Việt chung. Đo token bằng usage/request thực, không hứa tiết kiệm20–25% từ bytecount. Model card Bolt không đủ chứng minh ngôn ngữ là nguyên nhân và còn mâu thuẫn primary; không áp kết luận English-only lên Super.
- Screen dev riêng trên8 tình huống kỹ thuật/tài chính không thuộc main:2 language candidates ×8cases ×1repeat ×2models=32candidate trials tối đa. Cố định selection rule trước chạy: chọn English khi grounded success không kém VN trên từng model, contract/completion không regress; nếu không thì giữ VN. Không thử prompt thứ ba sau xem điểm trong cùng study. Đây là selection/dev, không phải xác nhận vượt đối chứng. Có thể bỏ screen và dùng baseline nếu ngân sách tuần không đủ; quyết định trước inference.
- Sau selection, seal một candidate duy nhất. Chốt danh sách smoke **9 câu answerable + 3 trap** trước inference. Smoke xác nhận bằng12 task dev mới ×2repeat ×4arm =96trial/model, hai model riêng. Các họ: quote/resolve, BCTCscope, growth, margin, ratio/scale, aggregate, cross-source cùng kỳ, chain, và ba trường hợp không trả lời được. Không dùng câu301–310 làm prompt tutorial hoặc smoke rồi coi main là untouched.
- B0 là upstream mới+hook với cùng inventory/memory policy và common infrastructure; B1 thêm prompt/policy đã pin. OC/DSH cùng model/data/cap/retry và quyền năng tính toán. Track sản phẩm giữ native compute/calculate/read_result; đối chứng được cấp common read-only utility tương đương. Không giới thiệu track này là identicaltool-schema. Track controlled hạn chế tool là ablation riêng nếu cần, không thay thế câu hỏi sản phẩm.
- Smoke gate dự kiến trên24trial/B1/model: grounded financial success≥20/24, trong đó **answerable grounded≥14/18** và **trap grounded-success6/6**; rawcontract≥23/24, DNF≤1/24, FR≤2/18answerable, FP0/6traps, zeroacceptedfabrication và mỗi họ tính toán có numeric grounded win. B1 không thấp hơn B0 trên strict/grounded và không regress DNF/FR/evidence. Instrumentation/independent audit toàn4arm PASS. Đây là ngưỡng kỹ thuật/chất lượng phải đăng ký **trước seal**; số ngưỡng không phải dự báo điểm.
- Chỉ sau cả hai smoke được audit, từng model đủ gate mới có pilot riêng:22eligible pilot ×2repeat ×4arm=176trial/model, mẫu số44/arm (inventory phải xác nhận lại). Pilot có40answerable+4trap/arm. Gate pilot trước productfreeze/main: B1 strict≥33/44, groundedfinancial≥35/44 (answerablegrounded≥31/40), trapgroundedsuccess4/4, FR≤2/40, FP0/4, DNF≤1/44 và không nhiều hơn bất kỳ đối chứng; strict và grounded B1 cao hơn B0/OC/DSH từng đối thủ ít nhất3/44, evidence không regress, zeroacceptedfabrication, instrumentation và manualfinancialaudit PASS. Đây là tiêu chí sàng lọc, không phải chứng minh thống kê thắng rộng. Nếu không đạt, dừng và báo nguyên nhân, không retry chất lượng, tune hoặc nâng cap trong cohort.

Tài liệu/mẫu: frozen `tools/run_manifest.py`, `tools/v44_supervisor.py`, `tools/v44_gate.py`, actualCLI first-trial interceptor fixtures và post-completion audit. Copy cơ chế immutability/resume; sửa lỗi auditor trong phiên bản mới trước seal, không sửa báo cáo cũ. **Certificate plumbing phải có phiên bản mới**: `tools/ready_check.py:validate_live_run` legacy hiện hardcode3smoketask/3arm/sampling0/1/effortnone/statusOK/usagecomplete; không dùng chứng nhận đó để phê duyệt96smoke/nativeutility/retry mới. Viết validator/certificate theo protocol v4.5, có fixture failclosed cho thiếu cell, wrongmodel/settings/partialusage không được khai báo; không giả vờ API mới đã tồn tại.

Kiểm chứng: actual system/tool/context captures cho mọi arm/model, native/effective equality của tham số bị kiểm soát, cleanmemory+profile proof, pilot raw + financial + lineage độc lập, usage complete/partial, mọi attempt/timeouts giữ nguyên. Pilot chỉ cho tín hiệu chọn bản release, không chứng nhận thắng rộng từ22task phát triển.

## Giai đoạn 5 — Product freeze, quyết định mở main và kiểm chứng cuối

**Phục vụ mục tiêu chính:** có một kết quả so sánh có thể tin và tái lập, không phải một bản OT tiếp tục thay đổi trong lúc đo.

Trước main phải đồng thời có:

1. Pin product commit cuối sau các sửa giai đoạn1; upstream merge và v4.4 preservation mapping rõ. Full native/typecheck/CLI/build self-check, benchmark suites, offline content/grader audit PASS; không còn failure chưa giải thích hoặc caveat làm vô hiệu chất lượng.
2. Hai model admitted; wire/retry/usage/metadata/caps và canary thực PASS, không đơn giản “chạy được stub”. Candidate smoke/pilot audit PASS theo lịch; numeric source/entity/kỳ/unit/scope/maths kiểm độc lập, không acceptedfabrication.
3. Main/corpus/grader/protocol/harnessversions pinhash; task defects và answerability leaks giải quyết chung; Neligible/mẫu số/exclusions/familyweights cố định trước kết quả. Thời điểm hiện tại **CHƯA đạt**.
4. Sau freeze không đổi prompt/source/tool/schema/memory/policy để “optimize benchmark”. Chỉ vận hành đúng protocol và phân tích offline; mọi code ảnh hưởng kết quả làm mất hiệu lực seal, phải versioned study mới. Không sửa giữa main hoặc chọn run tốt nhất.

Thiết kế main dự kiến:

- Một OT v4.5 cuối cùng vs OpenCode vs DSH, không cần B0 ở main sau pilot ablation. Cùng recordeddata, thông tin ban đầu, quyền tính toán, budgets trong từng model; thứ tự arm được randomize/interleave theo task/repeat/seed để giảm bias outages/cache. Báo snapshot chronology, cache chỉ observed không bảo đảm công bằng cachehit.
-2repeat/task/model **là amendment mới so PRE-REGISTER hiện quy định3**, chọn vì ngân sách tuần và đủ ghép cặp theo task; phải ghi rõ trước seal và báo stable2/2, không stable3/3. Không thay metadata run cũ. Nếu vẫn183eligible:366trial/arm/model;3arm×2model=**2.196trial**,17quarantine không tự chạy để làm đẹp danh nghĩa200. Nếu corpus đổi N thì cập nhật con số trước seal. Phân tích từng model riêng, không pooling Super/Flash hoặc thay mẫu số bằng trials đã hoàn tất.
- Co-primary: strict grounded success và grounded financial correctness; phụ: DNF/FR/FP/evidence/latency/observedtokenspergroundedsuccess, không tối ưu token trên trap-only win. Ghép cặp theo task, giữ repeats trong cluster; báo paired differences và CI95% theo task, sensitivity theo nhóm payload/source. Không coi hai repeat là hai câu độc lập. Multiplicity Holm cho hai metrics×hai đối thủ; nếu tuyên bố thắng ở cả hai model thì family tám comparisons đăng ký trước.
- Chỉ dùng chữ **vượt trội trên benchmark đã định nghĩa** khi OT có cải thiện có ý nghĩa thực tế (mục tiêu≥5điểm phần trăm trên hai co-primary so từng đối thủ), CI/kiểm định đã điều chỉnh hỗ trợ, và DNF/FR/FP/evidence không regress theo margin đã đăng ký, zeroacceptedfabrication. Không đủ lực thống kê thì kết luận chưa xác định; không đổi threshold sau nhìn điểm.
- Không gọi main/holdout trong lượt lập kế hoạch. Holdout bị overlap chỉ dùng robustness với nhãn đúng, không làm bằng chứng unseen. Phạm vi hiện tại vẫn grounded financial data reliability; chưa đủ nói vượt trội portfolio/đầu tư mọi mặt hoặc memory dài hạn nếu thiếu stratum riêng.

Kiểm chứng cuối: regrade độc lập rawfinal+ledger+visiblecontext+derivedmath; usage partial không bù0; giữ mọiDNF/timeouts; completed resume0modelcall với byte/hash/mtime trial/capture không đổi; release manifest/checksum/backup+rollback. Báo cả first-attempt và recovered completion; không tự promote một candidate dựa vào rawformat hay engineeringtest.

## Dự tính kết quả và thời gian — giả thuyết, không cam kết điểm

| Thay đổi | Kỳ vọng hợp lý | Chưa thể kết luận |
|---|---|---|
| Super thay Bolt | Tăng khả năng đọc/tool orchestration so E4B là giả thuyết có lý do; cần đo mới | Không suy OT sẽ hưởng lợi hơn OC/DSH hoặc giữ thứ hạng cũ |
| Sửa sourceleaf/ref/unit/compute | Cho phép arithmetic chạy thật, tách lỗi nguồn với sai tính | Mọi đối chứng cũng có thể tăng; không hứa +6–12/44 riêng OT |
| Transport retry+capture+caps | Giảm DNF do lỗi tạm thời; phân loại được nguyên nhân | Không chữa localschema/budget/format; không đảm bảo100%answers |
| Memory mới | Thực hiện đúng isolation/read/redaction/compaction | Empty notebook không tạo lợi thế một lượt; cần multiturn để nói lợi ích |
| Prompt EN/VN | Có thể giảm hiểu nhầm và overhead nếu actual measurement support | Không có forecast20–26/44 hoặc xác suất thắng có căn cứ hiện nay |

Ưu tiên một tuần: ngày1 base+kiểm chứng (lượt này); ngày2 đường nguồn/tính toán/memory và grader/corpus; ngày3 actualwire/retry/model/schema canary; ngày4 prompt screen+smoke; ngày5 pilot nếu gate; ngày6 audit+productfreeze; ngày7 bắt đầu main nếu đủ mọi điều kiện. Đây là thứ tự dự kiến, không deadline ép mở main khi fail. Full2400/2196trial có thể vượt tuần tùy quota/latency; đo throughput sau admission và tính `trials × mean_latency / concurrency + retry_wait`, không lấy p50 của Bolt dự báo Super/Flash. Hardbudget modelcalls/tokens/wallclock và điều kiện abort phải ký trước chạy; không chạy đến khi thắng. Ban đầu concurrency1/model; chỉ tăng sau rate-limit canary và giữ interleaving chung. Không tự tạo heartbeat mới trong lượt này.

**Phán định hiện tại:** base upstream mới là nền phù hợp hơn v4.4 và đã được đồng bộ có bảo toàn, nhưng chưa xứng đáng mang nhãn “bản cuối sẵn sàng main”. Chỉ sau khi hoàn tất các gate và thực nghiệm trên chính base này mới có thể kết luận; không có bằng chứng hiện tại bảo đảm đánh bại OpenCode/DSH.

## Liên kết bằng chứng

- [Biên bản merge và bảo toàn](/home/doanlong/extra/benchmark/audits/financial-prompt-v45/BASE-SYNC-REPORT.md).
- [Factcheck §14–16](/home/doanlong/extra/benchmark/audits/financial-prompt-v45/OPENCODE-SECTIONS14-16-FACTCHECK.md).
- [Memory/compute/headless APIs](/home/doanlong/extra/benchmark/audits/financial-prompt-v45/MEMORY-COMPUTE-DISCOVERY.md).
- [Corpus main cập nhật và phản ví dụ grader](/home/doanlong/extra/benchmark/audits/financial-prompt-v45/CORPUS-DISCOVERY.md).
- [Kết quả v4.4 nguyên bản](/home/doanlong/extra/benchmark/audits/financial-prompt-v44/REPORT.md).
