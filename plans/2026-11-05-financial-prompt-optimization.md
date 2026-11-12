# Kế hoạch tối ưu prompt OpenTrading cho tài chính Việt Nam

Ngày lập: 05/11/2026. Trạng thái: **plan và bản nháp prompt, chưa triển khai/chưa chứng minh thắng**.
Baseline, source OpenTrading và certificate hiện tại không bị sửa trong bước lập plan.

## Primary goal

Người dùng nhận câu trả lời tài chính đúng kỳ, đúng đơn vị, có bằng chứng và ít từ chối
oan hơn khi dùng OpenTrading. Mục tiêu nghiên cứu là OpenTrading vượt cả OpenCode và
DeepSeek Harness trên cùng model, dữ liệu và ngân sách; kết quả phải được xác nhận
trên tập chưa dùng để chỉnh prompt, không chỉ thắng ba câu smoke.

“Thắng” ở đây là chất lượng financial QA theo snapshot, không phải lợi nhuận đầu tư,
dự báo giá hay mọi nghiệp vụ tài chính. Một system prompt là ứng viên cần kiểm chứng;
không có lời hứa rằng chỉ viết prompt sẽ bảo đảm vượt hai harness.

## Tiêu chí thắng đề xuất — đăng ký trước main

Giữ câu hỏi chính L3–L5 của PRE-REGISTER hiện tại. Với từng task, lấy trung bình
primary success của ba run; so OpenTrading với **từng** đối chứng theo cùng task.

| Hạng mục | Quy tắc trước khi xem main |
|---|---|
| Chất lượng chính | Chênh primary success L3–L5 ít nhất **+7 điểm phần trăm** với cả hai đối chứng. Đây là mục tiêu thực tế, không phải mức tăng được dự báo. |
| Bằng chứng thống kê | Cận dưới khoảng tin cậy task-paired bootstrap **97,5% cho mỗi một trong hai so sánh** lớn hơn 0; dùng mức này như điều chỉnh Bonferroni để nhắm coverage đồng thời 95%. Bootstrap là xấp xỉ, không bảo đảm power. |
| Tính ổn định | Báo stable-correct 3/3; dùng exact McNemar + Holm như endpoint phụ đã có. Không gọi 2/2 là 3/3 hoặc lấy pass@3 thay stable-correct. |
| Chống bịa | Không có evidence giả được chấp nhận; báo FP trên task refusal. Không chọn prompt bằng cách tăng từ chối ở mọi câu. |
| Từ chối và format | Candidate không làm xấu false refusal/DNF so baseline OT trong bộ regression; báo riêng outcome và nguyên nhân từ ledger. |
| Hiệu quả | Caps giống nhau; báo latency câu đúng, token, số call và coverage. Không cộng accuracy/time/token thành một điểm tổng; nếu chất lượng tăng nhưng chậm hơn phải nói rõ trade-off. |
| Tổng thể | Báo toàn main và mọi subgroup đã đăng ký, kể cả khi không có lợi. Không đổi từ L3–L5 sang overall sau khi xem kết quả. |

Hiện `metrics._bootstrap` chỉ xuất CI95 với 2.000 draws. CI97,5 và phân tích primary
L3–L5 cần được bổ sung minh bạch trước main, kiểm thử riêng và ghi vào protocol mới;
không phải khả năng đã triển khai. Dự kiến 10.000 draws, seed cố định cho bản mới.
Không đạt ngưỡng hoặc CI còn bao trùm 0 → báo “chưa đủ bằng chứng thắng”. Không tăng
sample hoặc thử prompt tiếp sau khi mở holdout để tìm kết quả có lợi.

Pilot chỉ có hai câu refusal; số nhỏ không đủ chứng minh an toàn/không thua về bịa
trên nghiệp vụ rộng. Luôn báo tử số, mẫu số và bất định; không dùng “0 lỗi” thay
cho chứng nhận tổng quát.

## Phase 0 — Documentation Discovery và chốt phạm vi

**How this serves the primary goal:** Chỉ tối ưu các hành vi và API thực có, với tiêu
chí thành công đo được; tránh viết prompt đẹp nhưng không thể tích hợp hoặc so công bằng.

### Phát hiện đã xác minh

- [Review hiện tại](/home/doanlong/extra/benchmark/audits/2026-11-05/opentrading-review/REVIEW.md):
  toàn bộ gap smoke hiện tại là hai lần HPG. Tám probe trước chưa chứng minh prompt
  ngắn hơn tốt hơn. Không dùng các probe đó chọn candidate thắng.
- Eligible: **22 pilot, 178 main, 43 holdout, 3 smoke**; 31 câu diagnostic vẫn loại.
  Pilot có 18 payload hash, main 109; không trùng nguyên file giữa eligible pilot/main,
  nhưng điều đó không chứng minh độc lập ngữ nghĩa. Holdout vẫn có overlap đã công bố.
- Pilot theo capability: retrieval 8, compute 4, aggregation 5, evidence check 3,
  synthesis 2. Nhãn là heuristic, không phải chứng nhận chuyên gia. Các giá trị P/E,
  RSI có thể là trích xuất; không tự gọi đó là định giá hoặc tính chỉ báo độc lập.

### Allowed APIs / patterns đã đọc

| API/pattern thực có | Cách dùng đúng | Nguồn |
|---|---|---|
| `runAgent(opts: RunOptions): AsyncGenerator<AgentEvent>` | Giữ native main agent loop, registry và history/session riêng. | [agent.ts](/home/doanlong/OpenTrading/src/core/agent.ts:103) |
| `RunOptions.now?: Date` | Pin thời gian OT từ policy/manifest, không hardcode ngày của câu HPG. | [agent.ts:599](/home/doanlong/OpenTrading/src/core/agent.ts:599) |
| `assemble(input, promptsDir = PROMPTS_DIR)` | Dùng thư mục prompt tạm trong unit test. Chưa có đường `promptsDir` từ RunOptions. | [assemble.ts](/home/doanlong/OpenTrading/src/core/prompt/assemble.ts:135) |
| `Assembled.system/context/reminders/report` | Capture đủ request thực, không chỉ file identity. | [assemble.ts](/home/doanlong/OpenTrading/src/core/prompt/assemble.ts:76) |
| `promptVersion(dir)` | Hash ngắn hiện có hỗ trợ truy vết, không thay SHA256 đầy đủ của prompt/calendar/request. | [assemble.ts](/home/doanlong/OpenTrading/src/core/prompt/assemble.ts:98) |
| `resultToOutput` và `isError` | OT đã chuyển `isError:true` thành tool-error. | [convert.ts:49](/home/doanlong/OpenTrading/src/core/mcp/convert.ts:49) |
| Python `Server.call_tool(validate_input=False)` | Callback SDK đang cài chấp nhận `types.CallToolResult`; dùng error state đúng cho execution error, vẫn giữ ledger. | [snapshot server](/home/doanlong/extra/benchmark/tools/mcp_snapshot_server.py:187), SDK introspection ngày lập plan |
| `types.CallToolResult(content=..., structuredContent=..., isError=False)` | `isError=True` cho lỗi thực thi/input có feedback; không đánh đồng với JSON-RPC protocol error. | [MCP tools spec](https://modelcontextprotocol.io/specification/2025-11-25/server/tools#error-handling) |
| `--arms/--tasks/--runs/--seed/--resume` | Có thật; `--sample` là random, chưa phân tầng. Seed lịch không làm model deterministic. | [driver CLI](/home/doanlong/extra/benchmark/tools/run_benchmark.py:424) |

**Chưa có:** native `outputMode`, `outputSchema`, `promptDir` trong RunOptions;
`--prompt-variant` hoặc `--common-system` trong benchmark CLI. Không dùng `role:subagent`
để lách override system, vì nó đổi identity và trạng thái. `previewContext` chỉ trả
report, không phải raw effective system. Không hứa `response_format` hay structured
output của SDK trước khi đọc capability/version và kiểm tra route thực.

### Bài học từ nguồn ngoài, áp dụng có giới hạn

- FinanceBench lưu gold, justification và evidence gắn tài liệu/trang: dùng để thiết kế
  hợp đồng bằng chứng thay vì tự khai tên nguồn. Không bê số liệu Mỹ làm gold Việt Nam.
  [Repo tác giả](https://github.com/patronus-ai/financebench).
- FinQA tách retrieval và numerical execution; dự án từng sửa lỗi formatting gây
  leakage. Vì vậy phải phân biệt lấy dữ liệu, tính đúng và format đúng; không đọc gold
  vào prompt. [Repo tác giả](https://github.com/czyssrs/FinQA).
- Evals agent cần trace và outcome, chạy lặp, kiểm cả capability lẫn regression;
  lời nói đã làm không thay bằng chứng tool thực. [Anthropic](https://www.anthropic.com/research/demystifying-evals-for-ai-agents).

**Verification:** đối chiếu đủ source/API ở bảng; lưu model/provider/effort dự kiến,
scope, endpoints và số variant. **Guard:** không mua/gọi Go khi chưa xác minh route;
không dùng NVIDIA để suy ra prompt chắc chắn chuyển tốt sang model khác.

## Phase 1 — Sửa nền tảng so sánh, trước khi sửa prompt

**How this serves the primary goal:** Model được phép sửa lỗi request và mọi so sánh
đều tái lập; prompt không phải bù cho một protocol đang báo lỗi thành thành công.

**What to implement**

1. Copy pattern `CallToolResult(isError=True)` đã được SDK hỗ trợ cho replay rejection;
   phân biệt `invalid_request`, `not_recorded`, `unavailable` và protocol/server failure.
   Cung cấp feedback có thể sửa và request mẫu, không cấp financial evidence cho lỗi.
   Giữ tất cả ledger record và không nới điều kiện replay để model dễ pass.
2. Hash `prompts/*.md`, `market/calendar.json`, runtime source và request hiệu lực
   (system + context + reminders + tools). Lưu raw hash cùng canonical hash, ghi rõ
   dynamic IDs/path; không xóa khác biệt ảnh hưởng hành vi để tuyên bố parity.
3. Clock policy: as-of dữ liệu là mốc trả lời “gần nhất”; wall-clock chỉ là thời gian
   thực thi. Pin `now` ở OT qua API thực có. Việc tắt reminder phiên hoặc điều khiển
   ngày native của OC/DSH cần implementation/capability discovery; nếu chưa pin được,
   ghi nhận effective context và giới hạn, không ghi “clock đồng bộ” khi chưa đúng.
4. Thêm variant metadata và đường nạp prompt được kiểm soát. Đề xuất mới: một hook
   `promptDir` được validate từ cấu hình thí nghiệm rồi forward vào `assemble`; không
   coi hook này đã tồn tại. Hoặc dùng checkout thí nghiệm riêng với cùng runtime và
   bộ prompt được hash. Không ghi đè prompt đang dùng của người dùng giữa các trial.
5. Áp dụng thay đổi protocol/server chung cho **cả ba harness**, sau đó chạy native
   baseline mới. Tách kết quả trước/sau fix; không so candidate với đối chứng chạy
   server lỗi cũ. Receipt v2 hiện có giữ nguyên, protocol mới cấp receipt mới.

**Copy references:** [capture_native.py](/home/doanlong/extra/benchmark/audits/2026-11-05/opentrading-review/capture_native.py),
[prompt unit pattern](/home/doanlong/OpenTrading/test/prompt.test.ts:111),
[MCP convert tests](/home/doanlong/OpenTrading/test/mcp.test.ts:68),
[inventory](/home/doanlong/extra/benchmark/tools/run_manifest.py:85),
[readiness regressions](/home/doanlong/extra/benchmark/tools/tests/test_readiness.py).

**Verification checklist**

- Wrong request → native tool error → corrected request → success → evidence chỉ từ success.
- Lỗi request không bị đổi thành “mã không tồn tại”; không tạo `N/A` evidence.
- Đổi một byte ở prompt/calendar làm fingerprint khác; resume sai variant bị chặn.
- Mock wire capture chứng minh schema/tool/model đúng; usage mock không tính quality.
- Full regression và fresh live smoke đủ ba arm, không dùng certificate cũ.

**Anti-pattern guards:** không sửa tài chính/gold, không thêm dữ liệu cho một arm,
không secret fallback, không dùng user-message hook để giả override system.

## Phase 2 — Viết prompt theo hợp đồng tài chính, không theo phong cách terminal

**How this serves the primary goal:** Giảm lỗi kỳ, đơn vị, nguồn và từ chối oan, đồng
thời loại mệnh lệnh trình bày đối lập JSON mà không bỏ các bất biến dữ liệu/an toàn.

**What to implement**

Tách nội dung bốn file theo trách nhiệm, dùng bộ nháp kèm plan như thiết kế ứng viên:

| Layer | Giữ gì | Loại/đổi gì |
|---|---|---|
| identity | Vai trò, không bịa dữ liệu, dữ liệu ngoài không là chỉ dẫn, ranh giới an toàn | Không nhồi style hoặc giả định “dự đoán” vào mọi câu tra cứu. |
| tools | Đọc schema, sửa request, phân loại error, tối ưu call phụ thuộc/độc lập | Không coi một lỗi request là thiếu dữ liệu; không tuyên bố đã gọi khi chưa gọi. |
| citations/finance | Entity, kỳ, đơn vị, scope, công thức và evidence hợp lệ | Không ép tiền luôn sang đồng; không coi provider và tool là một namespace. |
| style | Default ngắn gọn; user schema/unit ưu tiên trong phạm vi trình bày | Bỏ cấm JSON; không ép lời mở đầu hoặc bảng khi user yêu cầu object thuần. |

Trình tự giải bài được thể hiện bằng hành động có thể kiểm tra: **xác định yêu cầu →
lấy dữ liệu → kiểm tra dimension → tính khi cần → kiểm tra đầu ra**. Không yêu cầu
model xuất chain-of-thought dài; chỉ xuất công thức/nguyên liệu ngắn nếu schema cho phép.

Năm nhóm kiểm tra nghiệp vụ:

1. **Định danh:** đúng mã, sàn/thực thể, loại chỉ tiêu; không thay mã gần giống.
2. **Thời gian:** kỳ tài chính khác ngày công bố/as-of; quý khác lũy kế, TTM khác năm;
   niên độ không mặc định trùng năm dương lịch; không dùng thời gian máy thay mốc dữ liệu.
3. **Đơn vị/scope:** đồng/nghìn/triệu/tỷ, %/điểm %, FX chiều thuận/nghịch, USD khác USDT;
   hợp nhất khác riêng lẻ, điều chỉnh khác chưa điều chỉnh, average khác point-in-time.
4. **Phép tính:** chỉ từ operand đã truy xuất; mẫu số và đơn vị cùng cơ sở, không chia
   zero, không gọi tỷ lệ từ nền âm là tăng trưởng kinh tế thông thường mà không giải thích;
   không tính mean thiếu mã hoặc dùng P/E/P/B khác basis để so sánh trực tiếp.
5. **Bằng chứng/thiếu dữ liệu:** chỉ cite success, không tự tạo hash/as-of; thiếu một
   trường không làm cả task thành refusal; không thay “không lấy được” thành “không có”.

Không buộc model làm đủ checklist không liên quan. Những điều corpus hiện chưa đo
(restatement lineage, corporate actions, hợp nhất/riêng lẻ, fair-value modelling) là
quy tắc thiết kế và ca regression tương lai, **không là năng lực đã được chứng minh**.

Độ dài là budget, không phải mục tiêu thắng: đo token hiệu lực trên model thật;
đề xuất core khoảng 700–1.200 token làm mốc thử, không dùng chars/4 để chứng nhận.
Rút câu trùng/không liên quan trước khi thêm module. Module chọn theo intent công khai
hoặc nội dung user, không theo task ID/gold; không yêu cầu `load_skill` khi tool bị tắt.
Tuần đầu dùng một candidate core + finance fragment tĩnh ngắn; routing module động chỉ
thêm nếu pilot chứng minh cần, tránh mở rộng runtime làm nhiễu phép thử prompt.

**Verification:** copy assembly test vào prompt temp dir; kiểm core contract không
bị cắt ở tier C; JSON không có prose, VND và nghìn VND đều đúng theo user, không
vẽ bảng trong JSON mode; kiểm invalid/missing/successful data qua native scripted mock.
Sau đó mới dùng model nhỏ để kiểm hành vi. Test string/LLM mock không chứng minh quality.

**Guards:** không ghi mã HPG, ngày snapshot hay đáp án vào system; không đưa schema
field cụ thể từ hidden gold vào runtime; không nhét few-shot số thị trường thật dễ bị
sao chép; không xóa chính sách không bịa số để tăng completion.

**Documentation references:** [identity](/home/doanlong/OpenTrading/prompts/identity.md),
[tools](/home/doanlong/OpenTrading/prompts/tools.md),
[citations](/home/doanlong/OpenTrading/prompts/citations.md),
[style](/home/doanlong/OpenTrading/prompts/style.md),
[assembly test pattern](/home/doanlong/OpenTrading/test/prompt.test.ts:111).

## Phase 3 — Ablation hữu hạn trên pilot

**How this serves the primary goal:** Chọn cải thiện có khả năng lặp lại trên nhiều
loại câu tài chính, đồng thời biết thay đổi nào giúp hay làm hại.

Đăng ký **tối đa bốn condition OT**, cùng native loop và nền tảng Phase 1:

| ID | Nội dung thay đổi |
|---|---|
| B0 | Native prompt hiện tại trên protocol chung đã sửa. |
| P1 | Chỉ ngoại lệ presentation/JSON/unit/source contract, giữ phần còn lại. |
| P2 | Chỉ request selection/error recovery, giữ presentation cũ. |
| P3 | Candidate kết hợp và finance checklist gọn từ Phase 2. |

P3 có nhiều yếu tố nên không dùng nó để quy riêng tác dụng cho một câu luật. Nếu cần
tách hiệu ứng finance checklist, đó là nghiên cứu tiếp theo; không tăng số variant
không giới hạn trong tuần này sau khi thấy pilot.

- OT: 22 task × 2 run × 4 condition = **176 trial**.
- OpenCode + DSH baseline: 22 × 2 × 2 = **88 trial**.
- Tổng tối đa **264 trial pilot**, chưa tính smoke/canary. Nếu budget hạn chế, đăng ký
  chế độ gọn B0/P3 ngay từ đầu: 88 OT + 88 đối chứng = **176 trial**; không chạy bốn
  rồi giấu hai variant thua. Số điều kiện phải đóng băng trước inference.
- Mỗi variant có manifest riêng, source/prompt hash, output dir và nhận diện rõ; mới
  cần bổ sung support variant/lịch interleave. CLI hiện **chưa** có flag chọn variant.
- Counterbalance variant và arm order để tránh B0 chạy lúc ít quota, P3 lúc provider
  chậm; same task/run pairs, mọi attempt và chi phí đều được ghi.
- Phân loại lỗi ledger: invalid request → dừng; success → đọc/tính sai; content đúng
  → schema/evidence sai; valid unavailable → refusal hợp lý. Đây là diagnostic bổ
  sung, không đổi primary success hoặc bỏ failed trial khỏi mẫu số.
- Candidate selection: ưu tiên primary success pilot sau guard chống bịa/evidence;
  tie → false refusal thấp hơn, rồi token/call thấp hơn. Chỉ chọn một candidate.
  Pilot là dữ liệu phát triển, không dùng p-value của nó để tuyên bố chiến thắng.

**References:** [task-quality report](/home/doanlong/extra/benchmark/audits/contract-v2/task-quality.json),
[metrics](/home/doanlong/extra/benchmark/tools/metrics.py:209),
[schedule pattern](/home/doanlong/extra/benchmark/tools/run_manifest.py:118),
[CLI](/home/doanlong/extra/benchmark/tools/run_benchmark.py:424).

**Verification:** đủ 22 task đã định, không lẫn model/variant, lịch cân bằng và counts
đúng; đọc cả trace pass và fail. So candidate với B0 mới, không với smoke cũ.
**Guards:** không bỏ task mà OC/DSH mạnh, không đưa 31 diagnostic vào điểm chính,
không lấy kết quả gọi đầu tiên thay native end-to-end, không coi model seed là cố định.

## Phase 4 — Chốt model và một candidate, cấp receipt mới

**How this serves the primary goal:** Prompt thắng trên đúng model dùng thực tế, không
chọn bằng một model nhỏ rồi gán chiến thắng cho model khác.

**What to implement / execute sau khi được yêu cầu triển khai**

1. NVIDIA model nhỏ dùng để smoke/debug trước. Main chỉ so các arm trên cùng route,
   model ID và effort **đã xác minh**. Hiện runtime chỉ hỗ trợ Bolt + effort none.
2. Nếu chọn Go/DeepSeek sau này: đây là dependency riêng cần adapter và xác minh native
   ba arm; không chỉ sửa chuỗi model. Verify model trả về, tool loop, usage, effort
   thực và entitlement/quota. Chưa xác minh thì không gọi medium và không claim đã hỗ trợ.
3. Khi target model khác model tuning, chạy lại ít nhất B0/P3 và hai đối chứng trên
   pilot: **176 trial** theo chế độ gọn; không tự cộng thẳng kết quả khác model. Ngân
   sách/quota phải đủ trước khi đặt lịch một tuần trên target mới.
4. Chọn candidate, khóa prompt/module, source, calendar, clock policy, model, schema,
   caps, grader, task IDs, seeds và endpoints. Fresh smoke 3×3×2 ít nhất 18 trial;
   readiness/full tests/certificate/freeze mới, không ghi đè receipt v2.

**Verification:** exact wire model/effort/tools; primary canary thật mỗi arm; error
rejection được đo là quality failure nhưng server/protocol/usage lỗi phải chặn readiness.
**Guards:** không mua dịch vụ/đổi key trong bước lập plan; không chọn lại prompt sau main.

**Documentation references:** [provider route/effort gates](/home/doanlong/extra/benchmark/tools/runners/provider.py),
[readiness](/home/doanlong/extra/benchmark/tools/ready_check.py),
[freeze](/home/doanlong/extra/benchmark/tools/run_manifest.py),
[NVIDIA verification helper](/home/doanlong/extra/benchmark/tools/verify_nvidia.py).

## Phase 5 — Main và xác nhận cuối trong ngân sách một tuần

**How this serves the primary goal:** Đánh giá khả năng tổng quát hóa của candidate
đã khóa, thay vì tiếp tục chọn prompt thuận lợi cho bộ đề đã xem.

- Main đầy đủ: 178 × 3 run × 3 arm = **1.602 trial**.
- Holdout: 43 × 3 × 3 = **387 trial**, mở một lần sau main; tổng **1.989**.
- Pilot bốn-condition + main/holdout = **2.253 trial**, chưa tính smoke/recovery hoặc
  kiểm tra target model khác. Đây là số lượng, không phải hứa hẹn đủ quota/thời gian.
- Nếu thêm OT B0 trên main để đo nguyên nhân cải thiện, thêm **534 trial**. Không bắt
  buộc cho câu hỏi “candidate so với hai đối chứng”; phải đăng ký từ trước nếu muốn.
- Ước lượng wall time từ pilot **đại diện**, request count và lỗi quota; giữ khoảng
  dự phòng tối thiểu 25%. Không ngoại suy thời gian ba smoke sang L3–L5 dài hơn.
  Chốt subset phân tầng theo capability/level/payload family bằng IDs/seed **trước**
  main nếu run đầy đủ vượt ngân sách. Report power giới hạn, không hứa phát hiện 7pp.
- CI primary mới: task-paired bootstrap với simultaneous policy đã đăng ký; báo
  sensitivity theo payload hash và stable McNemar/Holm. Không coi 3 run cùng task
  hoặc các câu dùng cùng dữ liệu là các quan sát hoàn toàn độc lập.
- Holdout là xác nhận consistency của prompt đã khóa; overlap 27 payload vẫn công
  bố. Không chỉnh prompt/grader theo holdout, không tuyên bố unseen-document sạch.

**References:** [PRE-REGISTER](/home/doanlong/extra/benchmark/PRE-REGISTER.md),
[paired statistics hiện có](/home/doanlong/extra/benchmark/tools/metrics.py:426),
[holdout/freeze gates](/home/doanlong/extra/benchmark/tools/run_manifest.py).

**Verification:** complete/scheduled counts, đúng receipt, paired task đủ run, mọi
subgroup/failed trial hiện diện; interval/p-value/cost coverage không bị chọn lại.
**Guards:** main/holdout không là dữ liệu prompt tuning; nếu sửa critical bug khi đã
mở main thì ghi protocol deviation, dừng kết luận và lập version nghiên cứu mới.

## Phase 6 — Verify và bàn giao

**How this serves the primary goal:** Người dùng nhận được prompt dùng được và bằng
chứng giới hạn rõ ràng về việc nó có vượt đối chứng hay không.

**What to deliver**

- Bốn file prompt native mới, finance fragment và mapping từ candidate draft; phiên
  bản/changelog/hash, không chỉ một đoạn system dài không biết được nạp ở đâu.
- Tests của JSON/units/period/success/error/recovery/evidence/clock và mutation hash.
- Full suite, native mock wire capture, NVIDIA smoke, certificate/freeze/resume.
- Báo cáo tất cả variant pilot; một main candidate; main/holdout artifacts, CI và
  error taxonomy. Ghi tách: prompt tốt hơn, protocol được sửa chung, native agent loop.
- Kết luận theo ngưỡng đã đăng ký: **thắng cả hai / thắng một / chưa đủ bằng chứng /
  thua**, không thay bằng “prompt tốt hơn về mặt cảm giác”.

**Final verification:** rà implementation theo Allowed APIs; grep các anti-pattern
trong nội dung runtime có hiệu lực (`không dán JSON` tuyệt đối, clock máy thay as-of,
evidence `N/A`, gold/task-ID special case, retry không giới hạn, override qua subagent);
kiểm ngữ cảnh trước/sau để không cấm nhầm câu phủ định hợp lệ. Run tests cần thiết;
đối chiếu số đo bằng ledger, không chỉ tin cờ pass.

**Không dùng để chứng minh:** “prompt có checklist” không chứng minh hiểu tài chính;
unit/mock pass không chứng minh model giỏi; thắng dataset snapshot không chứng minh
filings gốc đúng hoặc đầu tư có lãi. Chỉ ghi phạm vi đã đo.

**Documentation references:** [driver regression](/home/doanlong/extra/benchmark/tools/tests/test_reproducibility.py),
[readiness regression](/home/doanlong/extra/benchmark/tools/tests/test_readiness.py),
[independent finance checks](/home/doanlong/extra/benchmark/tools/tests/test_independent_snapshot.py),
[native mocked agent tests](/home/doanlong/OpenTrading/test/agent.test.ts).

## Lịch một tuần đề xuất

| Ngày | Mốc kết thúc |
|---|---|
| 1 | Phase 0–1: protocol/error/hash/clock/variant discovery và regression nền tảng. |
| 2 | Phase 2: prompt contract + finance fragment, test xung đột và capture native. |
| 3 | Phase 3: pilot hữu hạn, error analysis, chọn một ứng viên; quyết định target model trước vòng xác nhận. |
| 4 | Phase 4: target pilot nếu đổi model, fresh smoke, freeze, chốt full/subset theo budget. |
| 4–6 | Phase 5 main, dùng resume; giữ cửa sổ dự phòng quota/recovery. |
| 7 | Holdout một lần nếu đủ ngân sách, Phase 6 phân tích/bàn giao; không sửa prompt khi biết holdout. |

Nếu cần tích hợp một provider/effort chưa hỗ trợ và không hoàn thành sớm, ưu tiên một
nghiên cứu hoàn chỉnh trên model đã xác minh; study của model mới có lịch riêng.
Không bỏ bước kiểm chứng chỉ để kịp nói đã thắng trong một tuần.

## Tài liệu kèm

- [Prompt core v0.1, chưa kiểm chứng](/home/doanlong/extra/benchmark/plans/financial-prompt-candidates/core-v0.1.md)
- [Finance checks, fragment dự thảo](/home/doanlong/extra/benchmark/plans/financial-prompt-candidates/finance-checks-v0.1.md)
- [Output contract, fragment dự thảo](/home/doanlong/extra/benchmark/plans/financial-prompt-candidates/output-contract-v0.1.md)

Các fragment là thiết kế để phân phối lại vào các layer hoặc candidate prompt dir,
không append nguyên khối dưới prompt cũ rồi giữ các lệnh đối lập có cùng priority.
