# Review toàn diện OpenTrading, MCP và giao diện benchmark

Ngày: 05/11/2026, Asia/Bangkok. Phạm vi: điều tra mã nguồn và toàn bộ log v3 đã hoàn tất; không chạy thêm inference, không sửa production/benchmark/grader hoặc thay trial lỗi.

## Kết luận

OpenTrading chưa thua chỉ vì system prompt dài hoặc mô tả MCP kém. Có ba lớp vấn đề đồng thời: giao diện replay không đại diện đầy đủ MCP production; OT yếu ở tuân thủ kiểu tham số và phục hồi request; sau khi lấy được dữ liệu, OT vẫn sai phép đổi đơn vị/kỳ và thiếu hoặc sai provenance. MCP production cũng có các hợp đồng ngầm và lỗi semantic thực sự cần sửa, nhưng mô tả production không phải mô tả mà model đã thấy trong pilot.

Ưu tiên cải tiến: **chuẩn hóa hợp đồng MCP và giao diện đánh giá → validate/repair ở OT → chuẩn hóa số liệu, kỳ, đơn vị và đầu ra → tối ưu prompt ngắn theo hợp đồng → đo lại bằng thí nghiệm mới**. Chưa có bằng chứng bảo đảm các thay đổi sẽ đánh bại OpenCode/DSH; cần đối chứng và dữ liệu mới để xác nhận.

## Phạm vi thực sự đã kiểm tra

- 18 trial smoke + 176 trial pilot; 305 lời gọi MCP và 779 file capture native/effective. Pilot gồm 22 câu × 2 run × 4 condition; giữ nguyên mọi lỗi và dữ liệu gốc.
- 127 file TypeScript/TSX hiện tại của OT được lập inventory/hash và đều khớp runtime đã nghiên cứu. Soi sâu prompt, native loop, registry/schema conversion, error feedback, MCP client/result handling, provider, output và các kiểm soát ngân sách. TUI và các nhánh không kích hoạt chỉ được lập bản đồ, không tuyên bố đã review thủ công mọi dòng.
- Đăng ký source-local toàn bộ 174 MCP tool; soi sâu 17 tool trong snapshot; kiểm tra deterministic bằng provider stub, không lấy số liệu thị trường mới.
- Skills, memory, subagents, web, full-catalog discovery, compaction nhiều lượt và UI không hoạt động trong track pilot. Không suy kết quả pilot thành đánh giá toàn bộ năng lực sản phẩm có những tính năng này.
- Mô tả/code MCP local và deployment remote là hai đối tượng khác nhau; kết quả probe metadata remote được lưu riêng trong [deployed-metadata.json](mcp/deployed-metadata.json). Không suy version remote từ git local hoặc chỉ từ tên server.

Nguồn chi tiết: [forensics](forensics/FINDINGS.md), [kiến trúc OT](architecture/FACTS.md), [MCP](mcp/FINDINGS.md), [báo cáo pilot nguyên gốc](../../financial-prompt-v3/REPORT.md).

## 1. Định nghĩa lại “gọi tool sai” trước khi sửa

| Pilot condition | MCP calls | Thành công | Sai JSON schema | Đúng JSON schema nhưng không có request replay |
|---|---:|---:|---:|---:|
| OT baseline | 65 | 38 | 12 | 15 |
| OT finance | 66 | 39 | 4 | 23 |
| OpenCode | 66 | 39 | 0 | 27 |
| DSH | 66 | 41 | 0 | 25 |
| Tổng | 263 | 157 | 16 | 90 |

106/263 call bị từ chối (40,3%), nhưng chỉ 16/263 sai JSON schema (6,1%). 90/263 còn lại đúng kiểu schema nhưng không khớp request snapshot (34,2%). “Đúng JSON schema” **không bảo đảm hợp lệ với domain/backend**: `interval:"day"` vẫn qua schema string tự do rồi sai domain; `days:1` lại có nghĩa hợp lệ ở provider live. Không gộp cả hai thành một lỗi model hoặc coi mọi replay mismatch là lỗi production.

Ví dụ có thể tái lập:

| Request `vn_quote_history` | JSON schema | Source live | Replay HPG hiện tại |
|---|---|---|---|
| `{"symbol":"HPG"}` | Hợp lệ | Request mặc định | Thành công |
| `{"symbol":"HPG","days":1}` | Hợp lệ | Có nghĩa lấy một candle | `not_recorded` |
| `{"symbol":"HPG","columns":"close"}` | Sai kiểu | Pydantic reject | `invalid_request` |
| `{"symbol":"HPG","columns":["close"]}` | Hợp lệ | Có thể âm thầm project thành `{}` vì field thật là `c` | `not_recorded` |
| `{"symbol":"HPG","interval":"day"}` | Hợp lệ | Provider reject; tool đang biến thành unavailable | `not_recorded` |

Đây là kiểm tra local/stub, không phải gọi provider live. Không sửa replay để bỏ qua args hay trả nguyên chuỗi 365 candle cho query một candle. Muốn hỗ trợ query mới phải capture riêng hoặc định nghĩa phép biến đổi dữ liệu có kiểm chứng và provenance trong protocol mới.

Finance candidate giảm số call sai schema 12→4 so với baseline, nhưng replay mismatch tăng 15→23; tổng rejected vẫn 27. Chưa phải một ablation tách riêng tác dụng từng câu prompt, nên không quy nhân quả cho một câu hướng dẫn.

## 2. Điều gì trực tiếp làm OT kém hai đối chứng trong pilot?

Primary: OT baseline 12/44, OT finance 12/44, OpenCode 14/44, DSH 18/44. Đây là pilot nhỏ trên một model NVIDIA, không phải chứng nhận mọi model/harness.

Đối chiếu đúng từng task/run: cả hai biến thể OT đều có **6 cặp thua DSH, không có cặp thắng**; mỗi biến thể có 3 cặp thua ở truy xuất và 3 cặp thua sau khi tool đã thành công. Vì vậy sửa mô tả hoặc request đơn thuần không xử lý hết khoảng cách.

| OT finance thua DSH | Stage quan sát được | Bằng chứng |
|---|---|---|
| HPG, run 1 và 2 | Sai kiểu tham số | `columns:"close"`, có schema array/null nhưng vẫn gửi và bị reject; OC/DSH dùng request replay được |
| Giá vàng, run 1 | Replay mismatch | Chọn subset/request khác catalog; không chứng minh provider live không đáp ứng được |
| BCTC VCB, run 1 | Sau retrieval | Số đổi VND→tỷ sai 1.000 lần; evidence còn dùng SDK namespace thay raw tool |
| Peer compare, run 1 | Sau retrieval | Các số/ranking có nhưng hợp đồng evidence chưa đúng/đủ |
| Peer compare, run 2 | Sau retrieval | Số, ranking, kỳ và evidence phù hợp; top-level `source` dùng SDK namespace thay tên tool canonical |

Baseline cũng có lỗi sau retrieval: BTC run 1 và HPG run 2 báo đúng số nhưng thiếu evidence; BCTC sai đổi đơn vị. Với OpenCode, OT có 4 cặp thua và 2 cặp thắng: các đối chứng cũng có lỗi format/namespace. Không suy “DSH có engine toán chắc chắn” hoặc “OpenCode hiểu tài chính tổng quát hơn” từ các cặp này.

Case tăng trưởng VNM minh họa lỗi chung sau retrieval: finance run 1 trả `value:-5.63`, kỳ Q2 so Q1, nhưng note tự nêu phép tính Q3 so Q2 khoảng `-2.03` mà không cập nhật trường kết quả. Provenance được lấy đúng. Đây là lỗi chọn kỳ/đồng bộ phép tính và object cuối, không phải MCP thiếu dữ liệu.

Xem [matched-losses.json](forensics/matched-losses.json), [trials.csv](forensics/trials.csv), [selected-traces.json](architecture/selected-traces.json). Các failed checks có thể chồng lấn/cascade sau một lỗi truy xuất; không cộng chúng thành các nhóm nguyên nhân độc lập.

## 3. Luồng OT: các thiếu sót đã xác minh và giới hạn nhân quả

### 3.1 Tham số MCP không được validate ở client

[registry.ts:189](/home/doanlong/OpenTrading/src/core/tools/registry.ts:189) tạo `jsonSchema(...)` không truyền `validate`. SDK đang cài thực sự coi giá trị là hợp lệ khi validator vắng. JSON Schema có gửi cho model nhưng chưa là hàng rào thực thi phía OT. Các call sai kiểu ở trên tới được server.

Hook repair tại [agent.ts:223](/home/doanlong/OpenTrading/src/core/agent.ts:223) chỉ sửa tên tool `NoSuchToolError`. Chưa có chính sách sửa `InvalidToolInputError` hoặc request bị server từ chối. Gắn validator có thể chặn call sai sớm và tạo feedback tốt hơn; bản thân validator chưa bảo đảm model sẽ sửa đúng hoặc primary tăng.

### 3.2 Error feedback không bị mất; repair thực sự bằng 0

138 rejection của cả smoke+pilot đều có nội dung trong request model tiếp theo. Hai case OT HPG và peer_compare được đọc trực tiếp: `isError` chuyển thành `ok:false`; feedback có schema error, `retryable_with_corrected_arguments:true`, request catalog và cảnh báo không suy thiếu dữ liệu. Không có bằng chứng bị cắt, mất error flag hoặc cạn budget ở những case này.

**Không condition nào sửa thành công request của cùng tool vừa lỗi.** Chỉ số “có tool thành công sau rejection” là 4 trial mỗi condition; thực tế là đổi tool (`vn_quote_history→vs_overview_trading`, `financial_detail→stock_overview`). Tất cả các trial đó vẫn trượt primary. Không gọi đây là repair thành công. Định nghĩa tương lai còn cần cùng intent/entity/scope, không chỉ cùng tên tool.

Pilot OT và OC dùng hai gateway request/trial; DSH chỉ hai trial cần ba. Cap 24 request chưa được dùng để sửa lỗi. Không có cơ sở khuyên tăng token/timeout hoặc bật retry mù làm giải pháp chính.

### 3.3 Không có postcondition tài chính/đầu ra ở native loop

Native loop hoàn tất text mà chưa kiểm JSON/schema đầu ra người dùng, kỳ, đơn vị, toán hoặc evidence. Grader phía benchmark phát hiện lỗi sau khi OT đã trả lời. OT có chart/data references, nhưng chưa có calculator tài chính tổng quát hay answer builder bảo toàn provenance. Đây là điểm cần nâng cấp sản phẩm; không được sửa đáp án trong benchmark wrapper hoặc tự tạo hash/call ID.

### 3.4 Prompt baseline xung đột thật, nhưng không giải thích toàn bộ

- [style.md:16](/home/doanlong/OpenTrading/prompts/style.md:16) cấm dán JSON.
- [tools.md:4](/home/doanlong/OpenTrading/prompts/tools.md:4) mặc định giấu tên tool.
- [citations.md:6](/home/doanlong/OpenTrading/prompts/citations.md:6) ép đơn vị/precision trình bày.

Những mặc định này xung đột user schema/source/unit khi không có ngoại lệ rõ. Candidate đã sửa và giảm độ dài, nhưng primary/semantic không tăng. Nên giữ ngoại lệ machine-output có kiểm chứng, không tiếp tục nhồi checklist rồi kỳ vọng tự sửa lỗi số học và schema.

### 3.5 Rủi ro production chưa chứng minh là nguyên nhân pilot

- [schema.ts:184](/home/doanlong/OpenTrading/src/core/mcp/schema.ts:184) bỏ `additionalProperties`; sanitizer còn có nhánh bỏ examples/flatten schema. OC/DSH giữ root false trong capture. Tuy nhiên HPG sai ở property đã khai báo, nên việc bỏ root false không trực tiếp gây lỗi đó.
- [manager.ts:957](/home/doanlong/OpenTrading/src/core/mcp/manager.ts:957) chủ động dùng low-level request thay client output validation; [convert.ts:57](/home/doanlong/OpenTrading/src/core/mcp/convert.ts:57) có thể bỏ structuredContent khi đã có text. Snapshot chỉ text JSON, nên rủi ro structured-content không phải nguyên nhân đã thấy ở pilot.
- Native có timeout, output cap, loop guard và permission; nói OT không có các kiểm soát này là sai. Default maxSteps vô hạn và thiếu turn-wide budget nội bộ vẫn là rủi ro production cần chính sách rõ.
- Full catalog có 174 tool nhưng pilot chỉ đưa catalog task-scoped nhỏ; chưa có bằng chứng context overload do 174 tool gây ra khoảng cách pilot.

## 4. MCP production: mô tả có đúng và đủ không?

**Chưa đủ; một số mô tả còn không đúng năng lực thực hiện.** Source-local catalog có 174 tool, 331 tham số cấp đầu. Không có description/enum/bounds/pattern ở input schema; scan đệ quy cũng không tìm các keyword này. Có outputSchema/structuredContent thật, nhưng 174 outputSchema đều là object tùy ý, chưa kiểm dữ liệu tài chính theo từng tool. Đây khác với khẳng định server “không có structured output”.

| Ưu tiên | Finding source-local có repro | Tác động |
|---|---|---|
| P1 | `interval:str` cho qua `day`; tool bắt ProviderBadData rồi trả unavailable, `isError:false` | Biến lỗi có thể sửa thành thiếu dữ liệu |
| P1 | `period=quarterly/garbage` đi vào nhánh annual ở `financeinfo` | Có thể lấy báo cáo năm khi yêu cầu quý, vẫn echo period sai |
| P1 | `columns:["close"]` project row `t/o/h/l/c/v` thành `{}` | Request đúng kiểu nhưng âm thầm mất giá/ngày |
| P1 | `valuation_run` quảng cáo vùng fair value/ensemble nhưng chỉ trả các quotient PER/PB; `method=dcf` được echo | Hứa năng lực chưa tính; model dễ diễn giải sai kết quả |
| P1 | Search hint valuation còn nhắc DCF dù docstring nói chưa hỗ trợ | Discovery có thể chọn sai tool trong production |
| P2 | Days tối đa365 trong doc nhưng provider không cap; peers có thể bị cắt thầm | Hợp đồng không đồng bộ, dễ bỏ đối tượng được hỏi |
| P2 | Output schema object tự do | Không bắt được sai unit, kỳ, trường thiếu và lineage |

Các điểm có sẵn nên tái sử dụng: `schemas.make_envelope`, `units.py`, `financial_contracts.py`, provider availability/warnings/data_time, SDK structuredContent, registry discovery và cache. Không cần viết lại server bằng ngôn ngữ/framework khác.

Source anchors/repros đầy đủ ở [MCP FINDINGS](mcp/FINDINGS.md) và [deterministic-contract-evidence.json](mcp/deterministic-contract-evidence.json). Các repro sử dụng dữ liệu giả/provider stub để kiểm hành vi, không phải xác minh số liệu hoặc giá thị trường.

## 5. Hai nhiễu của benchmark phải sửa trước nghiên cứu mới

1. [build_tool_defs](/home/doanlong/extra/benchmark/tools/mcp_snapshot_server.py:86) thay mô tả thật của cả 17 tool bằng generic replay instructions; không đưa outputSchema và metadata discovery đầy đủ. Các input parameter descriptions không phải bị exporter làm mất: chúng vốn không có ở source live. Mọi call đều thấy snapshot catalog/schema, nên cũng không có bằng chứng “description bị cắt mất template”.
2. OpenCode native CLI [run.ts:288](/home/doanlong/opencode/packages/opencode/src/cli/cmd/run.ts:288) tự thêm quote/escape multiline argv rồi gửi text đã biến đổi. Adapter benchmark truyền argv literal đúng; capture vẫn khác OT/DSH ở hình thức instruction. Chưa biết hướng tác động chất lượng. Không được ghi “user message byte-identical” hoặc sửa log cũ để che khác biệt.

V3 vẫn hữu ích cho so sánh cùng bài toán logic trên interface replay, với chênh lệch native đã lưu. Các nhiễu giới hạn khả năng quy nguyên nhân cho mô tả MCP production và dự báo hiệu quả live. Không xóa kết quả v3, không cấp lại certificate cũ cho contract mới.

## 6. Hướng nâng cấp và tiêu chí quyết định

Kế hoạch thực thi chi tiết: [chuẩn hóa OT/MCP](../../../plans/2026-11-05-opentrading-mcp-standardization.md).

1. Giữ nguyên v3; pin catalog/deployment/version và tạo interface v4 giữ mô tả thật, schema, structuredContent, outputSchema, annotations/meta. Replay restriction là lớp bổ sung dùng chung, không thay thế docs.
2. Chuẩn hóa 17 tool đã dùng, ưu tiên giá/lịch sử, financial statements/detail, FX/gold, peers, technical và valuation. Đồng bộ tên trường, enum, giới hạn, error taxonomy, kỳ/đơn vị và output shape từ registry hiện có.
3. OT validate args theo raw schema; phân biệt parse/schema repair với execution-error recovery; giới hạn sửa một lần theo intent, không retry cùng request sai. Giữ mọi call/usage trong budget.
4. Dùng dữ liệu có provenance làm đầu vào tính toán và output builder; giữ tool name, provider, observation date và fetch time tách biệt; không để model tự viết lại hash/call ID. Thêm kiểm tra kỳ/scale và JSON trước phát hành.
5. Chỉ tối ưu prompt khi contract đã vững; tách native controlled track khỏi full-product/discovery track. Calculator dùng chung qua MCP nếu giữ tool parity của track hiện tại; không thêm lợi thế riêng trong wrapper OT.
6. Đo schema errors, replay mismatch, retrieval completion, same-intent repair, semantic, source/evidence, DNF, false refusal và token coverage riêng. So baseline/candidate trên cùng interface mới; không coi điểm tăng sau đổi đề/server là hiệu ứng OT.

Không sửa production trong lượt review này. Các thay đổi runtime_only đã cài trước đó vẫn giữ nguyên; prompt finance tiếp tục thử nghiệm. Không chạy thêm model, main/holdout hay sửa gold. Độ tin cậy cao cho hành vi source và các trace quan sát được; mức tăng điểm sau từng thay đổi còn chưa xác định.
