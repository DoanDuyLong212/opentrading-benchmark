# Forensic review v3: lời gọi MCP và giai đoạn OpenTrading mất điểm

Ngày 05/11/2026. Chỉ đọc toàn bộ artifact smoke 18 + pilot 176; không chạy inference, không đổi grader, task, prompt, runtime hoặc output metric gốc. `opentrading` trong smoke v3 là candidate finance; pilot tách rõ baseline/finance. Kết quả không tự đại diện cho prompt baseline đang mặc định ở app OpenTrading gốc và không đo MCP live.

## Kết luận có bằng chứng trực tiếp

1. Phần lớn lỗi gọi tool là **không khớp request được replay**, không phải JSON-schema invalid: pilot 90/106 rejection = 84,9%. Cùng schema/catalog server gây trở ngại cho cả bốn điều kiện. Gọi chung mọi rejection là “tool-call sai” hoặc lỗi của MCP live sẽ sai phạm vi.
2. OT thực sự sai kiểu tham số nhiều hơn hai đối chứng: baseline 12/65 calls, finance 4/66, OpenCode và DSH 0/66. Finance giảm lỗi kiểu nhưng chuyển nhiều call sang schema-valid/replay-mismatch; tổng rejection vẫn 27 như baseline.
3. **Không điều kiện nào sửa được chính tool/request đã bị từ chối.** Metric cũ “4 recovered trials” mỗi arm chỉ là có một tool khác thành công sau rejection; cả bốn trial đó vẫn sai primary.
4. Phần thua DSH không chỉ ở MCP: mỗi biến thể OT có đúng sáu cặp thua, không cặp thắng; ba thua trước khi truy xuất thành công, ba thua sau tool thành công vì đổi đơn vị, thiếu evidence hoặc namespace source. Chỉ sửa mô tả tool sẽ không xử lý toàn bộ khoảng cách quan sát được.
5. Mô tả tool trong smoke/pilot **không phải docstring MCP live**. Replay server thay bằng cùng mẫu generic và danh sách request. Schema tham số không có mô tả property nào. Có đủ điều kiện để mô hình tự đoán tham số theo ý nghĩa tự nhiên thay vì mẫu replay, nhưng đây là cơ chế khả dĩ; log quan sát không cô lập quan hệ nhân quả prompt/MCP/model.

## Đếm lại từ ledger và captures

| Pilot /44 trial mỗi condition | Baseline OT | Finance OT | OpenCode | DSH |
|---|---:|---:|---:|---:|
| MCP calls | 65 | 66 | 66 | 66 |
| MCP successful / available | 38 / 36 | 39 / 37 | 39 / 37 | 41 / 39 |
| Actual empty thành công | 2 | 2 | 2 | 2 |
| Schema invalid | 12 | 4 | 0 | 0 |
| Schema-valid, not recorded | 15 | 23 | 27 | 25 |
| MCP operational error / unknown tool | 0 | 0 | 0 | 0 |
| Trial có rejection | 19 | 19 | 19 | 17 |
| Trial có rejection và không MCP success nào | 13 | 13 | 13 | 11 |
| Sửa được cùng tool sau rejection | 0 | 0 | 0 | 0 |
| Tool khác success sau rejection | 4 | 4 | 4 | 4 |
| Primary success | 12 | 12 | 14 | 18 |
| DNF theo định nghĩa đã đăng ký | 1 | 1 | 1 | 5 |

Tám actual-empty call là `symbol_resolve` cho mã không tồn tại; tất cả đều được xử lý đúng. Câu kỳ tương lai là yêu cầu kỳ không có trong payload thành công, không phải MCP operational error. Provider failure/timeout và JSON DNF vẫn giữ trong 44 trial; không gộp chúng vào lỗi server MCP.

Smoke: mỗi arm 14 calls. OT finance có 12 schema-invalid (hai HPG + mười calls năm ngân hàng); OpenCode/DSH mỗi bên 10 schema-valid/replay mismatch (năm ngân hàng × hai lần). Hai actual-empty call/arm đều đúng. Vì vậy smoke không cung cấp bằng chứng rằng toàn bộ 12 OT errors do backend không có dữ liệu.

Xác minh tổng 194 trial, 305 calls, 779 native/effective capture files. Số `tool_call_count` của provider đúng bằng số ledger MCP ở từng condition; không thấy call do SDK bỏ mất trước server theo đối chiếu đếm này. Cả 138 rejection smoke+pilot đều xuất hiện trong ngữ cảnh model request kế tiếp. OT nhận error JSON trực tiếp; OpenCode bọc `tool.execution`; DSH thêm `Error: `. Không có bằng chứng ở v3 rằng server làm lỗi bị ẩn khỏi model.

Bảng máy đọc: [summary.json](summary.json), [calls.csv](calls.csv), [trials.csv](trials.csv). Đếm thất bại theo check có overlap và có lỗi dây chuyền sau rejection; không cộng `value/period/provenance` thành số nguyên nhân độc lập.

## Request bị từ chối chính xác ở đâu

Pilot schema-invalid gồm:

- OT baseline: `columns: "close"` 10 calls năm ngân hàng; `symbols: "USDVND"` một call; `metrics: "P/E, P/B, ROE"` một call. Các field tương ứng đều yêu cầu array hoặc null, không nhận scalar string.
- OT finance: `columns: "close"` hai HPG calls; `symbols: "USDVND"` hai calls FX. Không phải tool name sai.
- OC/DSH không có schema-invalid trong pilot. Tất cả 16 invalid calls dùng property có thật; việc OT SDK mất `additionalProperties:false` không giải thích trực tiếp các lỗi kiểu này.

90 schema-valid/replay mismatch phân theo tool: `vn_quote_history` 39, `vn_msn_fx_gold` 20, `financial_detail` 14, `vn_index_ohlcv` 8, `market_movers` 7, `financial_statements` 2. Cần phân biệt ba nhóm:

| Request model sinh | Request catalog khả dụng | Ý nghĩa |
|---|---|---|
| quote HPG/ngân hàng thêm `days=1`, `interval=1d/day/1day` | Chỉ `symbol` | Kiểu string/integer hợp schema nhưng khác mặc định/recording. `day/1day` có được live backend nhận hay không phải kiểm tra riêng; JSON schema không có enum. |
| financial_detail MWG thêm `periods_n=1` hoặc 3 | `symbol=MWG,statement=KQKD`; default periods_n=4 | Thu hẹp kỳ theo nhu cầu có vẻ tự nhiên nhưng replay không có request này. |
| market_movers `top_n=3` | `top_n=5` | Hỏi top 3 khiến model tự tối ưu request; replay chỉ có top 5, phải lấy rồi lọc. |
| FX/gold `symbols=[XAUUSD]` hoặc `[USDVND]` | Batch `[USDVND,XAUUSD]` | Symbol không sai; subset hợp kiểu vẫn bị replay từ chối. |
| VNINDEX `count=10` | Symbol-only; default count=100 | Đề yêu cầu vài phiên nhưng replay giữ cửa sổ mặc định. |

Các tham số xuất hiện trong mismatch, không cộng độc lập: `days` thêm non-default 52 calls; `symbols` đổi batch 18; `interval` thêm non-default 14; `periods_n` 14; `count` 8; `top_n` đổi 7; `statement` thêm non-default 2. Đây là đo lệch hợp đồng replay, chưa chứng minh request live có nghĩa đúng, provider thực chấp nhận, hoặc có đủ dữ liệu trả lời.

Nguồn quyết định: [mcp_snapshot_server.py:41](/home/doanlong/extra/benchmark/tools/mcp_snapshot_server.py:41) so khớp đúng recorded/default; [validation:67](/home/doanlong/extra/benchmark/tools/mcp_snapshot_server.py:67) phân schema và not_recorded; [error result:149](/home/doanlong/extra/benchmark/tools/mcp_snapshot_server.py:149), [isError:193](/home/doanlong/extra/benchmark/tools/mcp_snapshot_server.py:193). Schema array cho metrics ở [snapshot_tool_schemas.json:130](/home/doanlong/extra/benchmark/tools/snapshot_tool_schemas.json:130); quote schema ở [line 321](/home/doanlong/extra/benchmark/tools/snapshot_tool_schemas.json:321).

## Model thực sự thấy catalog nào

Mọi 305 call đều có tool/schema và đúng `snapshot_requests` hiện diện trong first native model request của trial, không phải chỉ tồn tại trong metadata. Tool definitions luôn bắt đầu:

> Frozen MCP snapshot; only snapshot_requests below are replayable.

Sau đó là câu về defaults và evidence; mẫu request đặt cuối description. Đây là mô tả giống nhau cho mọi tool, không giải thích nghiệp vụ, output fields, đơn vị, kỳ, lựa chọn giá close, mã FX hay metric tài chính. Việc bỏ docstring live là hành vi [build_tool_defs:88](/home/doanlong/extra/benchmark/tools/mcp_snapshot_server.py:88), không phải OT đọc sai docstring live trong các run này.

Trong 44 first requests/condition có 50 tool definitions (catalog hẹp theo task). Cả 50/50 tool definitions OT baseline và finance mất root `additionalProperties:false`; cả 50/50 OpenCode/DSH giữ lại. Không có property description nào ở mọi condition. Các capture được giữ tại [captures.json](captures.json), có full description/schema và path nguồn. Chưa đánh giá năng lực chọn tool trong toàn catalog production: mỗi task chỉ cung cấp tool snapshot của task. Không xuất hiện `unknown_tool`; thất bại chính quan sát được là arguments, replay adherence và answer contract, không phải chọn sai tool trong hàng trăm tool live.

## Phục hồi: metric cũ cần đổi tên

Mỗi condition bốn trial có MCP success sau rejection là `fin-l4-2nguon-01` và `fin-l5-profile-01`, hai repeat/task:

- `vn_quote_history` bị từ chối → `vs_overview_trading` thành công.
- `financial_detail` bị từ chối → `stock_overview` thành công.

Không request nào quay lại cùng tool bằng mẫu hợp lệ. Tất cả bốn trial mỗi condition vẫn sai primary. Có thêm hai trial/condition chứa cả success và rejection nhưng thứ tự ngược, không được đếm phục hồi. OT baseline/finance/OC mỗi trial đều đúng hai gateway requests, DSH 42 trial có hai và hai trial có ba; cap 24 không cản một vòng sửa request. Không có bằng chứng timeout/MCP transport khiến OT không thể sửa request. Cần đo riêng `same request repaired`, `required evidence coverage restored` và `final primary recovered`; không gọi “any later tool success” là tool repair.

## Các cặp OT thua đối chứng

Mỗi OT variant thua DSH sáu cặp, thắng không cặp nào. Chia theo giai đoạn, mỗi variant có ba retrieval-stage và ba post-tool-stage loss. Finance thua:

| Task/run | MCP / đáp án thực | Giai đoạn mất điểm |
|---|---|---|
| HPG close r1, r2 | columns string; server hướng dẫn symbol-only, model kết thúc null | Hai schema-invalid + không repair |
| XAUUSD r1 | Chỉ gọi subset XAUUSD thay batch catalog; null | Replay mismatch + không repair |
| VCB LNST r1 | MCP đúng, số gốc 14.550.959.000.000 VND; đáp 14,550959 tỷ thay 14.550,96 tỷ, source/evidence.tool thêm SDK prefix | Unit arithmetic + namespace |
| Peer compare r1 | MCP đúng, các số và ranking đúng, không có evidence array | Output contract |
| Peer compare r2 | MCP đúng, evidence đúng; top-level source là `mcp__opentrading__peer_compare` | Source namespace |

Baseline ba retrieval loss là XAUUSD subset r1, HPG thêm days=1 r1, peer_compare metrics scalar r2. Ba post-tool loss là LNST unit r1, BTC quote r1 thiếu evidence, HPG r2 thiếu evidence. HPG baseline r2 **đúng số 21, đúng đơn vị và ngày**; không được mô tả là sai tính toán.

So với OpenCode: mỗi variant thua bốn, thắng hai. Hai cặp thắng của OT là future r1 (OpenCode không hoàn thành answer contract) và valuation r2 (OC source SDK prefix). Lỗi namespace/format cũng xuất hiện ở đối chứng. [matched-losses.json](matched-losses.json) có đủ 20 cặp loss, đáp án, failed checks, đường dẫn grade và ledger.

## Các lỗi tài chính sau khi đã lấy được dữ liệu

Không nên gộp những lỗi sau thành MCP failure:

- VNM growth: cả hai repeat của hai OT variant dùng sai cặp quý. Finance còn tính lại đúng Q3/Q2 trong `note` nhưng giữ `value=-5.63` và `period=Q2 vs Q1`. Lỗi liên kết giá trị–kỳ–lập luận, không phải thiếu dữ liệu. `note` không tự sửa field JSON.
- RSI: mỗi OT variant bốn trial (single + multi, hai repeat) có đúng số nhưng `period="1D"`, nhầm độ hạt interval với ngày/kỳ. Payload chỉ có computed timestamp/data_time và interval, không có ngày phiên riêng; grader cho phép “gần nhất”, nên nên chuẩn hóa response `observation_date` thay để model suy diễn từ metadata.
- VCB LNST: baseline hai repeat sai quy đổi VND→tỷ; finance repeat1 cũng sai, repeat2 JSON DNF. MCP response gốc nêu unit VND. Đây là lỗi tính toán/model serialization, không phải backend nhân/chi số sai trong run này.
- MWG profile: finance hai repeat `market_cap_bn=1092013623640` thay ~109201,36; baseline r1 cũng sai scale, r2 đúng market cap nhưng vẫn thiếu financial_detail do request bị từ chối. Truy xuất được overview không đủ cứu phần phân tích nhiều nguồn.
- Commodities: số % thay đổi, ranking và trường bắt buộc không ổn định dù yf payload thành công. Đây là arithmetic/selection/serialization, độc lập với replay mismatch.
- Finance peer compare r1 thiếu toàn bộ evidence; r2 source namespace sai. Finance BTC→VND r1 tự điền evidence placeholder cho FX bị từ chối, dù có evidence BTC thật. Phải phân biệt placeholder bịa với canonical-name mismatch.

[SNIPPETS.md](SNIPPETS.md) trích mười case, có exact ledger line, native request capture, `tool-end`/`done` line, raw answer và failed checks. Đây là nội dung copy-ready cho report chính.

## Độ tin cậy, giới hạn và cách tái lập

Đếm ledger, loại schema lỗi, catalog thấy trên wire, thứ tự phục hồi, và cặp task/run: độ tin cậy cao, có thể tái lập không inference. Giải thích prompt dài/xung đột hoặc docs thiếu làm model chọn tham số nào: giả thuyết cơ chế; không thể gán nhân quả chỉ từ các trace này. Model NVIDIA nhỏ duy nhất, pilot 22 task × hai repeat; chưa suy rộng Go/DeepSeek hay live MCP đầy đủ.

Ngoài tool schema khác nhau, nội dung instruction OpenCode bị CLI native bọc dấu nháy/escape quote. Benchmark runner truyền argv nguyên văn tại [run_opencode.py:76](/home/doanlong/extra/benchmark/tools/runners/run_opencode.py:76); CLI tại [run.ts:288](/home/doanlong/opencode/packages/opencode/src/cli/cmd/run.ts:288) bọc các arg chứa space và [run.ts:869](/home/doanlong/opencode/packages/opencode/src/cli/cmd/run.ts:869) đưa message đó lên session. Đây là native CLI preprocessing, không phải benchmark dùng `json.dumps` sai. Chưa biết hướng ảnh hưởng; phải ghi như confound, không âm thầm sửa hoặc gán lại trial cũ.

Evidence bảy trường do benchmark thêm là hợp đồng riêng; không phải production user bình thường cần tự gõ hash. Raw snapshot có trim/ghép lại một số payload legacy và request reconstruction. Các run đo khả năng làm snapshot-grounded QA với hợp đồng đó, không chứng nhận retrieval mọi tham số live và không chứng nhận filing gốc.

Tái lập derivatives trong đúng audit directory:

```bash
python3 audits/2026-11-05/comprehensive-review/forensics/extract.py
python3 audits/2026-11-05/comprehensive-review/forensics/render_snippets.py
```

Script đầu đọc ledger/capture/raw grade/saved answer, không import hoặc chạy runner, không mutation artifact nguồn. Script thứ hai assert 194 trial, 305 calls, 779 captures; provider/MCP count equality, visible rejection equality, DSH paired deficit 3+3 mỗi OT. Hash hai source trials.jsonl ở summary.json. Các derivatives không thay thế báo cáo chấm điểm đã đóng băng.
