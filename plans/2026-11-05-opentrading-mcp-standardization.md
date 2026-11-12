# Kế hoạch chuẩn hóa OpenTrading và MCP server sau forensic v3

Ngày 05/11/2026, Asia/Bangkok. **Trạng thái: kế hoạch, chưa triển khai.** Phần điều tra Phase 0 đã hoàn tất trong lượt này. Không sửa source production, benchmark, dữ liệu/gold; không chạy thêm model.

## Primary goal

Người dùng nhận câu trả lời tài chính đúng đối tượng, kỳ, đơn vị và phép tính, có bằng chứng thật; khi gọi tool sai, OpenTrading sửa được lỗi có thể sửa thay vì kết luận thiếu dữ liệu. Chất lượng phải được đo trên cùng hợp đồng công cụ và ngân sách với OpenCode/DSH; không hứa một prompt sẽ bảo đảm chiến thắng.

## Điểm xuất phát và giới hạn

[Review tổng](../audits/2026-11-05/comprehensive-review/REVIEW.md) có trace, source anchors, script tái lập và giới hạn. Pilot v3: OT baseline/finance cùng12/44, OC14/44, DSH18/44. Rejections pilot106/263 gồm16 sai schema và90 schema-valid nhưng không có replay; không gọi cả90 là hợp lệ production. Cả hai OT variant có3/6 cặp thua DSH ở retrieval và3/6 sau retrieval. Tất cả điều kiện không sửa được request của cùng tool sau lỗi.

Candidate finance hiện chỉ là thử nghiệm. Original OT giữ prompt baseline; hai runtime hooks promptDir/clockPolicy đã cài ở lượt trước. V3/certificate/receipt và dữ liệu gốc phải giữ bất biến; mọi sửa contract/code/model cần manifest/certificate mới.

## Nguyên tắc thiết kế và phạm vi một tuần

- Giữ Python/FastMCP v1 đang dùng; không viết lại MCP hoặc chuyển framework trong đợt này.
- Tái sử dụng `schemas.make_envelope`, `schemas.mcp_tool_error`, `units.py`, `financial_contracts.py` và OT registry/refs. Các kiểu mới dưới đây là thiết kế cần thêm, không phải API đã tồn tại.
- Ưu tiên17 tool đã dùng. Áp dụng chuẩn catalog cho174 tool nhưng chỉ chặn release ở nhóm ưu tiên và các contract đặc biệt liên quan; không hứa kiểm hết correctness174 provider trong tuần.
- Mọi canonicalization phải được mô tả và test. Không tự đổi symbol, quý/năm, USD/USDT, basis giá, đơn vị hay scope để làm request pass.
- Không sửa đáp án trong benchmark wrapper; không đưa hidden gold/task ID vào runtime; không thêm tool đặc quyền cho riêng OT trong track đang giữ parity.
- Giữ riêng controlled task-scoped track và full-product discovery track. Không dùng điểm hai track thay thế cho nhau.
- No-data thật, invalid request và provider failure là ba trạng thái khác nhau. Unknown/partial là dữ liệu cần bảo toàn, không phải số0.

## Phase 0 — Documentation discovery và baseline có thể tái lập

**How this serves the primary goal:** Mỗi thay đổi được gắn với một lỗi thật và một API thực có, tránh tối ưu nhầm mô tả không xuất hiện trong thí nghiệm.

**Đã hoàn tất:** source/trace forensic trong [architecture/FACTS](../audits/2026-11-05/comprehensive-review/architecture/FACTS.md), [forensics/FINDINGS](../audits/2026-11-05/comprehensive-review/forensics/FINDINGS.md), [mcp/FINDINGS](../audits/2026-11-05/comprehensive-review/mcp/FINDINGS.md). Đã đọc tài liệu MCP chính thức và API package đang cài. Metadata-only probe remote không hoàn tất handshake/list; chưa có bằng chứng version/catalog deployment trùng local. Không có model hoặc financial-provider call trong audit này.

### Allowed APIs đã xác minh

| Thành phần thực có | Pattern được phép copy | Nguồn |
|---|---|---|
| MCP Python1.30.0 / Pydantic2.13.5 | `FastMCP.tool(...,annotations=...,structured_output=...)`; `Literal`, `Annotated` + `Field`, output `BaseModel` | [SDK signatures](../audits/2026-11-05/comprehensive-review/mcp/sdk-apis.json), [ví dụ schema đã sinh](../audits/2026-11-05/comprehensive-review/mcp/proposed_schema_example.py) |
| Tool errors | SDK `ToolError` → `isError:true`; khi cần structured error, kiểm chứng actual CallToolResult wire thay vì trả dict error rồi mặc định success | [FastMCP1.30 server guide](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v1.30.0/docs/server.md), [repro handler](../audits/2026-11-05/comprehensive-review/mcp/repro_contracts.py) |
| Low-level MCP | `Server.call_tool(validate_input=True)`; `CallToolResult(content=...,structuredContent=...,isError=...)` | SDK signatures ở trên; snapshot v3 là ví dụ error có thật |
| MCP contracts | inputSchema/outputSchema/structuredContent và actionable tool errors | [Tools2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/tools), [Tools2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) |
| Financial metadata hiện có | `make_envelope(...,data_time=...)`; `coverage_for_tool(tool,data)`; `financial_contract_reference()`; `with_units(tool,result)` | [schemas.py:102](/home/doanlong/MCP-server/src/opentrading_mcp/schemas.py:102), [financial_contracts.py:287](/home/doanlong/MCP-server/src/opentrading_mcp/financial_contracts.py:287), [units.py:98](/home/doanlong/MCP-server/src/opentrading_mcp/units.py:98) |
| AI SDK7.0.137/provider-utils5.0.58 | `jsonSchema(schema,{validate})` với ValidationResult; phải chọn/khai báo validator dependency thật | [API extraction](../audits/2026-11-05/comprehensive-review/architecture/FACTS.md), registry hiện tại [registry.ts:189](/home/doanlong/OpenTrading/src/core/tools/registry.ts:189) |
| Parse/schema repair | `streamText({repairToolCall})`; callback error là NoSuchToolError/InvalidToolInputError, trả repaired call hoặc null | API extraction trên; `experimental_repairToolCall` chỉ là alias deprecated đang dùng |
| Model structured output | `streamText({output:Output.object({schema,...})})` | `ai/src/generate-text/output.ts:94`, API extraction trên; chưa có option tương ứng ở RunOptions và chưa chứng minh route NVIDIA hỗ trợ strict mode |
| Native agent | `runAgent(opts)` với `promptDir`, `clockPolicy`, `now`, `maxSteps`, history/signal | [agent.ts:103](/home/doanlong/OpenTrading/src/core/agent.ts:103) |

**Exit gate:** lưu source/catalog/SDK/protocol identity; mỗi finding có test hoặc trace; mọi API chưa xác minh phải được ghi là thiết kế mới/capability gate. Không copy ví dụ latest MCP2.x vào deployment1.x.

## Phase 1 — Chuẩn hóa input contract và mô tả MCP

**How this serves the primary goal:** Model nhìn thấy cách gọi đúng trong schema; sai interval/kỳ/cột bị phát hiện trước truy cập nguồn thay vì làm mất dữ liệu hoặc trả nhầm báo cáo.

**What to implement**

1. Tạo một registry contract dùng chung cho schema, doc, aliases, defaults và output metadata; mở rộng nền financial contracts hiện có, không tạo thêm bộ quy tắc độc lập trong benchmark.
2. Ưu tiên `vn_quote_history`, `vn_equity_quote_batch`, `vn_index_ohlcv`, `vn_msn_fx_gold`, `financial_statements`/`vs_financeinfo`, `financial_detail`, `peer_compare`, `signals_technical`, `valuation_run`; hoàn thiện17 tool trước khi mở rộng toàn174.
3. Mô tả mỗi tool: trả cái gì/không trả gì; khi dùng/không dùng; đơn vị và basis; kỳ/date ordering; output shape; một ví dụ hợp lệ; lỗi thường gặp và cách sửa. Các field có description trực tiếp trong inputSchema.
4. Dùng enum/Literal cho interval/period/statement/method đã được backend hỗ trợ, constraints cho số lượng/cỡ batch. Chốt limit theo backend và chính sách tài nguyên; nếu chọn range1..365 cho nến phải coi là thay đổi contract có version, không coi doc cũ đã được enforce.
5. Chốt canonical OHLCV fields và aliases có nghĩa tương đương. Với API legacy `t/o/h/l/c/v`, phải mô tả rõ; `columns:["close"]` chỉ được map sang`c` nếu alias công khai, còn unknown field phải báo invalid_column, không trả `[{}]`. V2 có thể dùng tên đầy đủ; v1 adapter giữ tương thích.
6. Reject period lạ trước network. Nếu hỗ trợ `quarterly→quarter`, canonicalize ở boundary và trả requested/resolved period; không để mọi chuỗi khác quarter rơi xuống annual.
7. Sửa `valuation_run`/search hints đúng năng lực hiện có: observed PER/PB không phải fair-value band/DCF/ensemble. Reject method không thực hiện; không echo `dcf` như thể đã tính. Chưa triển khai target/band thì phải nói không hỗ trợ.
8. Peers vượt giới hạn phải báo rõ/reject hoặc trả omitted list có reason; không cắt thầm. Statement không match không được tự trả toàn bảng như thể đúng statement đã yêu cầu.

**Copy references:** [MCP source findings](../audits/2026-11-05/comprehensive-review/mcp/FINDINGS.md); [typed schema example](../audits/2026-11-05/comprehensive-review/mcp/proposed_schema_example.py); [vn.py:57](/home/doanlong/MCP-server/src/opentrading_mcp/tools/vn.py:57), [financeinfo:999](/home/doanlong/MCP-server/src/opentrading_mcp/providers/vietstock.py:999), [project_rows:74](/home/doanlong/MCP-server/src/opentrading_mcp/tools/shared.py:74), [valuation_run:266](/home/doanlong/MCP-server/src/opentrading_mcp/tools/compute_financial.py:266).

**Verification checklist:** kiểm actual `tools/list`, không chỉ model Python; bảng valid/invalid args theo từng field; interval day, period quarterly/garbage, columns scalar/unknown, peers quá giới hạn, method dcf; negative cases không gọi provider; doc và generated schema có cùng enum/default/limit. Test độ tương thích client cũ và policy alias.

**Anti-pattern guards:** không thêm enum “cho đẹp” không khớp backend; không quảng cáo capability chưa có; không global coerce list/string hoặc dates; không nhét request/đáp án của benchmark vào docs để tăng điểm.

## Phase 2 — Chuẩn hóa errors, output và lineage tài chính

**How this serves the primary goal:** OT biết cần sửa request, đợi nguồn hay từ chối vì dữ liệu thật sự không có; số liệu giữ được kỳ/đơn vị và bằng chứng khi đi qua nhiều tool.

**What to implement**

1. Tách `invalid_argument`, `unsupported_operation`, `unknown_column`, `not_found/no_data`, `upstream_timeout`, `auth_required`, `rate_limited`, `provider_bad_data`; `not_recorded` chỉ thuộc replay. Tên chính thức cần chốt một lần trong registry/version.
2. Error có argument path, allowed values, message sửa được và retryability; `ProviderBadData` do input sai không đi qua `_na` như dữ liệu unavailable. Domain/tool error dùng MCP `isError:true`; legitimate no-data là success có availability và reason rõ.
3. Typed output cho17 tool ưu tiên: envelope chung + data model riêng, giữ `available/partial/empty/unavailable` semantics rõ. Không chỉ kiểm “là object”. Kiểm cả successful và error wire result qua FastMCP handler.
4. Tái dùng `as_of` hiện có với nghĩa fetch time, `data_time` với nghĩa observation time. Bổ sung period boundaries/frequency/scope/basis khi nguồn xác nhận; unknown giữ unknown. Không đổi nghĩa field cũ âm thầm.
5. Chuẩn hóa observation: entity, metric, value, currency/unit/scale, period hoặc observation date, consolidated/separate khi có, source field/path, quality/availability. Giá nghìn VND khác VND; % khác fraction/điểm%; USD khác USDT; current ratio khác period-end ratio.
6. Field nào chưa xác minh comparability phải có status/coverage; không coi valuation multiples với unit/basis unverified là fair value đã xác nhận. Cache phải giữ timestamp dữ liệu và contract version, không gắn lại as_of mới để che stale.
7. Trả structuredContent và text JSON tương thích từ cùng object chuẩn; tránh hai bản mâu thuẫn. Tool output schema giữ cả provenance và warnings/missingness. Không cấp financial evidence cho input error.

**Copy references:** `schemas.py:102,152`, `financial_contracts.py:145,189,287,384`, `units.py:74,98,108`; [SDK guide](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v1.30.0/docs/server.md); [offline wire repro](../audits/2026-11-05/comprehensive-review/mcp/deterministic-contract-evidence.json).

**Verification checklist:** invalid argument→isError true; actual no-data không bị đổi thành error; provider timeout không thành not_found; partial không mất field có dữ liệu; schema rejects wrong units/types/missing identity; cache stale-data test; quarter/year/YTD/TTM và financial scope cases; golden wire snapshots cho JSON text + structuredContent.

**Anti-pattern guards:** không auto điền source/as_of/call IDs; không gán unknown thành0; không retry side effect do output không conform; không dùng một schema genericdict để tuyên bố đã chuẩn hóa tài chính.

## Phase 3 — OT validate schema và phục hồi có giới hạn

**How this serves the primary goal:** Những lỗi có thể sửa không kết thúc thành “không có dữ liệu”, đồng thời không tạo vòng lặp vô hạn hoặc làm tăng chi phí không kiểm soát.

**What to implement**

1. Giữ raw MCP schema làm authoritative schema; tách schema gửi model theo capability/dialect của provider. Giữ mapping raw tool ↔ SDK name ↔ provider source rõ ràng. Sanitization phải có semantic regression tests, không xóa constraints toàn cục cho mọi provider.
2. Gắn validator vào `jsonSchema(...,{validate})` cho dynamic MCP tools. Chọn thư viện validator có dependency/format support rõ sau discovery; pin version. Không dùng JS type assertion làm validation. Reject không ép kiểu ngầm trước side effects.
3. Chuyển sang hook `repairToolCall` đã xác minh, mở rộng cho parse/schema errors có thể sửa; giữ name repair hiện có. Không giả định hook này tự xử lý execution/replay error.
4. Thêm recovery state cho execution error ở native loop: `error_received → repair_allowed → corrected_call → validated_result | terminal_failure`. Tối đa một correction cho một failed intent; cùng request sai không chạy lại. Auth/no-data không vào parameter repair. Transient retry theo policy riêng và budget hiện có.
5. Recovery phải giữ cùng entity/metric/period/scope cần trả lời; khác tool chỉ là repair nếu đáp ứng cùng intent bằng dữ liệu tương đương, được ghi rõ. Không dùng “tool khác có success” làm retrieval completion.
6. Validate output theo outputSchema mà không tự gọi lại write tool khi response invalid. Bảo toàn structuredContent dù có text; tránh duplicate text+JSON làm tăng context, giữ raw refs và render một representation chính xác.
7. Cho native caller đặt turn-wide request/step/token/deadline policies, có finish reason rõ. Dùng timeout/output cap/loop guard hiện có; không thay bằng maxSteps vô hạn hoặc tăng cap mặc định để che lỗi.

**Copy references:** [registry.ts:160](/home/doanlong/OpenTrading/src/core/tools/registry.ts:160), [schema.ts:184](/home/doanlong/OpenTrading/src/core/mcp/schema.ts:184), [agent repair:223](/home/doanlong/OpenTrading/src/core/agent.ts:223), [manager:957](/home/doanlong/OpenTrading/src/core/mcp/manager.ts:957), [convert:57](/home/doanlong/OpenTrading/src/core/mcp/convert.ts:57), [actual SDK signatures/source excerpts](../audits/2026-11-05/comprehensive-review/architecture/source-excerpts.md).

**Verification checklist:** schema-invalid columns không chạm MCP execution; feedback chứa expected/actual và allowed values; scripted native loop sửa được cùng intent rồi trả đúng; repeated wrong request bị chặn; provider error không bịa missing data; structured-only/text+structured cases đều giữ tài chính/provenance; cancel/deadline/cost ledger bao gồm cả repair; actual raw/effective capture không mất ràng buộc quan trọng.

**Anti-pattern guards:** không claim input validation đã làm model trả lời đúng; không sửa theo hidden task metadata; không retry toàn tool batch khi chỉ một call lỗi; không gọi lại completed write; không âm thầm đổi financial semantics khi repair.

## Phase 4 — Tính toán và answer contract có kiểm chứng

**How this serves the primary goal:** Dữ liệu đúng không còn bị biến thành đáp án sai1.000 lần, chọn nhầm quý hoặc mất bằng chứng trong bước viết JSON cuối.

**What to implement**

1. Một calculation path thuần deterministic nhận operands từ observations đã truy xuất, định danh period/unit/scope rõ. Hỗ trợ tối thiểu conversion scale, QoQ/YoY, mean/ranking; kiểm missing denominator/zero/negative base và số phần tử đủ trước tính. Dùng decimal/precision policy thật cho dữ liệu tiền, không thay dữ liệu bằng làm tròn sớm.
2. Kỳ “mới nhất” chọn từ observation/date/reporting period trong nguồn theo mốc người dùng/as-of; kiểm đúng hai kỳ để QoQ. Không dựa vào thứ tự row ngầm hoặc lấy wall clock làm kỳ dữ liệu. YTD không tự coi quarterly; không tính nếu basis không đồng nhất.
3. Tái dùng refs/raw results và nguồn dữ liệu thật; record formula, operands, unit transformations và lineage tới response/field. Model chọn yêu cầu và diễn giải; kết quả numeric chuẩn đến từ phép tính, không tự chữa số theo gold.
4. Evidence serializer copy immutable identities từ tool result/host ledger; tách canonical tool name khỏi SDK name và provider. Không để model tự tạo hash, ID hoặc timestamp. Với benchmark, chỉ dùng benchmark_evidence từ actual response; với sản phẩm, chỉ hiển thị chi tiết kỹ thuật khi output contract yêu cầu.
5. Thêm answer contract optional ở native API từ caller/user request thực sự. Structured model output dùng API đã xác minh nếu route hỗ trợ; luôn có post-validation schema/semantic checks. Nếu provider không hỗ trợ strict schema, dùng native JSON validation + một correction có budget, không giả metadata “strict”.
6. Các quy tắc style trở thành mặc định cho hội thoại thường; JSON/schema/unit/source namespace cụ thể của người dùng ưu tiên về presentation, giữ nguyên safety/data integrity. Không tự áp prose/table/fence trong machine mode.
7. Trong track controlled hiện tại, calculator tool mới phải là MCP read-only dùng chung cả ba harness. Nếu thêm OT-only builtin/capability riêng, phải khai báo track native-product mới và không gọi là tool parity với v3. Không đưa calculator/answer repair vào benchmark adapter để chỉ cứu OT.

**Copy references:** [financial_contracts.py](/home/doanlong/MCP-server/src/opentrading_mcp/financial_contracts.py:145), [tools/refs.ts](/home/doanlong/OpenTrading/src/core/tools/refs.ts), [native registry](/home/doanlong/OpenTrading/src/core/tools/registry.ts), [growth/BCTC/peer evidence snippets](../audits/2026-11-05/comprehensive-review/forensics/SNIPPETS.md). Output.object signatures ở Phase0; native chưa có option answer contract, cần thêm và test chứ không coi đã có.

**Verification checklist:** independent calculation fixtures; VND↔nghìn↔tỷ, %↔fraction, QoQ phải chọn đúng hai quý, annual/YTD/TTM từ chối nhầm basis; missing một mã không tính mean trên subset; output numeric và note cùng lineage; evidence mismatch/placeholder bị chặn trước emit; không có gold/task ID trong runtime; native plain-conversation behavior vẫn hợp lệ.

**Anti-pattern guards:** không dùng prompt như calculator; không sửa số chỉ để khớp expected value; không cưỡng ép tài chính vào source namespace benchmark cho mọi sản phẩm; không coi `Output.object` là validator phép tính.

## Phase 5 — Chuẩn hóa giao diện benchmark v4 và metrics chẩn đoán

**How this serves the primary goal:** Nếu điểm tăng, biết do OT tốt hơn, MCP rõ hơn hay chỉ do benchmark cho interface dễ hơn; kết quả có thể chuyển thành quyết định sản phẩm đáng tin cậy.

**What to implement**

1. Export từ actual `tools/list`: description/inputSchema/outputSchema/annotations/meta/server instructions và version/catalog digest. Giữ nguyên docs production; thêm restriction replay riêng, cùng cách cho mọi condition. Phải test actual model wire, không chỉ file schema.
2. Giữ hai mode rõ: (A) production-faithful snapshot contract; (B) finite-request replay compliance với schema narrowed/oneOf hoặc explicit catalog. ModeB đo tuân thủ snapshot; không gọi đó là năng lực chọn tham số live. Không so hai mode như một endpoint.
3. Capture thêm requests hợp lệ cần cho dev cases hoặc dùng deterministic transformation được đăng ký trước, có verified semantics/lineage. Không bỏ args khỏi matching, không trả cùng payload cho request khác kỳ/units. Dữ liệu/gold v3 giữ bất biến; corpus mới có version/hash mới.
4. Đối chiếu user text sau native adapter. OpenCode CLI hiện quote/escape input; xem native API prompt path thực có trong source và thực hiện capture-only test trước khi chọn. Nếu buộc giữ native CLI, ghi rõ transform thay vì tuyên bố byte-identical. Không nâng cấp native binary một arm giữa cùng thí nghiệm.
5. Native prompt và schema differences phải được lưu; cố định as-of semantics và disclose clocks chưa pin; context/skills/discovery scope độc lập. Giữ tool parity, model/effort/sampling/caps, token coverage, condition order và resume invariants.
6. Tách metrics: generated-call parse/schema validity; server-accepted vs replay-supported; required-data completion; same-intent repair với denominator eligible errors; post-retrieval financial correctness; source/evidence contract; DNF/false refusal/FP; coverage, latency câu đúng, tokens. “Any later success” chỉ là diagnostic, không recovery.
7. Conditional-on-retrieval metrics là chẩn đoán có selection bias; primary vẫn đúng toàn bộ trên mọi trial bắt đầu. Không suy toàn bộ failed value checks là sai số học vì null sau rejected call làm check cascade.
8. Phân biệt provider request đã gửi, gateway rejection và usage đã biết/thất lạc. Không lấy usage thiếu làm tiết kiệm; mọi sửa/repair/retry đều tính vào budget và ledger.

**Copy references:** [snapshot_server:86](/home/doanlong/extra/benchmark/tools/mcp_snapshot_server.py:86), [schemas frozen](/home/doanlong/extra/benchmark/tools/snapshot_tool_schemas.json), [OC CLI input:288](/home/doanlong/opencode/packages/opencode/src/cli/cmd/run.ts:288), [run_manifest.py](/home/doanlong/extra/benchmark/tools/run_manifest.py), [forensic extraction](../audits/2026-11-05/comprehensive-review/forensics/extract.py).

**Verification checklist:** catalog round trip không mất docs/schema; actual-wire instruction equality hoặc transform được pin; null/missing/rejected/adversarial evidence tests; same-intent recovery khác đổi tool; budgets/usage/resume không double call; mọi đổi source/corpus/catalog làm receipt cũ không hợp lệ cho run mới; original artifacts hashes không đổi.

**Anti-pattern guards:** không viết lại metadata v3; không tăng điểm bằng replay fallback; không dùng task-scoped oracle catalog để chứng minh full174 discovery; không chỉ báo những subgroup có lợi.

## Phase 6 — Ablation giới hạn, nghiệm thu và rollout

**How this serves the primary goal:** Chỉ đưa thay đổi vào mặc định sau khi chứng minh ít lỗi hơn mà không tăng bịa dữ liệu; giữ chi phí vừa đủ và không lặp chỉnh prompt để săn điểm.

**What to implement / lịch đo đề xuất, chưa được chạy**

1. Offline trước: contract boundary/wire suite MCP; native validator/recovery/output/finance suite OT; exporter/metrics/manifest suite benchmark. Reuse test patterns hiện có, không chạy lặp fullsuite nếu không có thay đổi/lỗi mới.
2. Tạo bộ development regression từ cơ chế lỗi quan sát, có số synthetic độc lập với đáp án pilot: invalid type, domain enum, replay-only query, same-intent repair, unit scale, QoQ/annual mismatch, missing evidence/namespace, partial batch, structuredContent và invalid JSON. Bổ sung những biến thể chưa thấy; đã dùng pilot để thiết kế thì pilot không còn là holdout xác nhận.
3. Đăng ký canary mở rộng6 tình huống ×3 harness ×1 run =18 trial trên NVIDIA nhỏ, nhằm xác minh plumbing, không xếp hạng. Chỉ chạy khi user thực thi phase sau; không tự gọi inference trong lượt lập kế hoạch.
4. Một pilot chẩn đoán có giới hạn:22 task ×2 run ×4 condition =176 trial nếu còn budget; B0(native OT baseline trên contract mới), B1(native OT candidate), OC, DSH. Balanced order; tất cả dùng cùng contract mới. Pilot này dùng để chẩn đoán/rollout, không confirm vì đã đọc22 task để thiết kế. Không thêm nhiều prompt variants tùy kết quả.
5. Tách tác dụng common-MCP/interface và OT: giữ frozen v3 làm lịch sử, dùng baseline/candidate concurrent trên interface mới; nếu cần causal ablation thêm một yếu tố thì đăng ký cohort/budget riêng trước inference. Không quy toàn bộ delta v3→v4 cho OT.
6. Trước khi mở main: chốt candidate/model/interface/metrics và smoke đúng cấu hình. Confirmatory primary trên task chưa dùng để tối ưu; kiểm soát payload-family dependence/overlap đã biết. Holdout chỉ mở một lần theo gate hiện có; không dùng các task đã đọc từ holdout để tuning. Bổ sung fresh external-data validation khi muốn suy rộng về báo cáo tài chính thực.
7. Main victory +7pp L3–L5 với cả OC/DSH và task-paired CI97,5% mỗi so sánh là mục tiêu kế hoạch cũ, chưa được triển khai. Phải implement/test/re-register trước khi dùng; pilot CI95 không thay thế. Báo stable3/3 chỉ khi có đúng3 runs và đủ task. Nếu không đủ tuần/budget, báo chưa xác nhận thay vì hạ tiêu chí sau kết quả.
8. Rollout code/prompt riêng: hash-guard/backup/receipt; default chỉ promote sau review. Guard mới đăng ký trước phải bao gồm immutable evidence/mismatched evidence và wrong-period/unit diagnostics ngoài FP trên unanswerable; bằng nhau về số đúng không đủ bù việc tạo provenance sai. Không sửa lại kết quả guard v3.
9. Deployment MCP cần staged release, backward-compatible contract/version, smoke metadata+wire và rollback. Remote probe hiện chưa thành công, nên release chưa được gọi xác minh chỉ từ local tests. Không tự deploy/purchase Go trong phase lập plan.

**Verification checklist:** tất cả relevant tests pass; newcertificate/manifest valid; one completed resume không phát sinh call; no holdout leakage; complete raw/effective captures và usage coverage; report denominator cả failed/DNF; conservative rollback nếu evidence/units/period regress; installed hashes/remote catalog phù hợp release đã review.

**Anti-pattern guards:** không tạo “thắng” bằng loại timeout/bad JSON; không tăng budget chỉ cho OT; không dùng model nhỏ dự báo Go/DeepSeek medium; không retune sau khi xem holdout; không sửa default chỉ vì prompt đọc hay hơn.

## Lịch một tuần và điểm cắt phạm vi

| Ngày | Ưu tiên | Điều kiện kết thúc |
|---|---|---|
| 1 | Phase0 đã làm; Phase1 input/docs và lỗi nguy hiểm period/columns/valuation | Các request sai có lỗi rõ, không âm thầm thành dữ liệu khác |
| 2 | Phase2 typed envelope/provenance/units cho tool ưu tiên | Wire contracts và financial metadata có regression tests |
| 3 | Phase3 OT validator/recovery/structured results | Sửa cùng intent có budget; no retry side effects |
| 4 | Phase4 conversion/QoQ/evidence serializer/machine output | Các case BCTC, kỳ, namespace có kết quả deterministic đúng |
| 5 | Phase5 exporter/parity/diagnostic metrics; offline gate và canary | Không có artifact/sampling/schema drift; đủ telemetry |
| 6 | Phase6 pilot176 có giới hạn; để job chạy, review một lần khi xong | Không theo dõi liên tục; không thêm variant để săn điểm |
| 7 | Review/rollout; quyết định có đủ điều kiện confirm hay dời main | Báo đầy đủ failures/limitations, không ép hoàn tất main+holdout bằng hạ tiêu chí |

Nếu thiếu thời gian: giữ input/error contracts, OT validation/recovery và provenance/output là must-have; đưa full174 typed-output, active-skill/memory/discovery eval, DCF engine, full main/holdout và Go migration sang đợt riêng. Không có căn cứ hứa cả tuần đủ xử lý mọi capability và chạy xác nhận lớn.

## Definition of done

1. Không còn silent annual fallback/empty-column projection/unsupported-method-as-success ở nhóm ưu tiên; docs và schema có cùng nghĩa.
2. OT chặn sai schema trước execution, sửa được eligible intent theo bounded test và giữ đúng source/error state; không tự tạo evidence.
3. Unit/period/math/output checks hoạt động trên dữ liệu mới và nguồn thật đã quan sát; đúng số và đúng provenance được đo riêng.
4. Benchmark phản ánh đúng interface và native transforms, có receipt mới, không sửa lịch sử; quality không được suy ra từ pass của unit tests.
5. Có kết quả đo thực đủ để chấp nhận hoặc từ chối candidate, kể cả kết luận “chưa cải thiện/chưa thắng”.
