# Review OpenTrading: prompt, tool execution và nguyên nhân trượt smoke

Review ngày 05/11/2026. Không thay đổi source OpenTrading, grader, runner, config hoặc
artifact benchmark đã đóng băng. Bằng chứng mới nằm riêng trong thư mục review này.

## Kết luận có thể bảo vệ bằng dữ liệu

Chưa có căn cứ kết luận OpenTrading suy luận tài chính yếu hơn hai harness còn lại.
Trong smoke cuối, **toàn bộ chênh lệch điểm đến từ một câu HPG được lặp hai lần**.
OpenTrading chọn request không replay được rồi dừng, coi lỗi request như thiếu dữ liệu.
OpenCode và DSH dùng đúng request được ghi nhận. Đây là lỗi chọn tham số và phục hồi
tool trong môi trường snapshot, trước khi diễn ra việc đọc giá hay tính toán tài chính.

| Câu smoke, hai lần mỗi arm | OpenTrading | OpenCode | DSH |
|---|---:|---:|---:|
| Giá HPG | 0/2 | 2/2 | 2/2 |
| Trung bình năm ngân hàng | 0/2 | 0/2 | 0/2 |
| Từ chối mã XYZX không tồn tại | 2/2 | 2/2 | 2/2 |
| Tổng primary pass | 2/6 | 4/6 | 4/6 |

Không được coi hai lần cùng câu là hai bài toán tài chính độc lập. Model dùng ở đây
là NVIDIA Bolt E4B nhỏ; không suy ra hành vi DeepSeek/Go hoặc toàn bộ bộ đề.

## 1. Nguyên nhân trực tiếp: sai request rồi kết luận thiếu dữ liệu

Mẫu replay HPG là `{"symbol":"HPG"}`. Các tham số mặc định hợp lệ có thể tương đương
sau chuẩn hóa; không thể thay cửa sổ/khoảng thời gian tùy ý rồi dùng lại cùng payload.

| Arm | Run 1 | Run 2 |
|---|---|---|
| OpenTrading | `{"days":1,"symbol":"HPG"}` → rejected | `{"days":30,"interval":"day","symbol":"HPG"}` → rejected |
| OpenCode | `{"symbol":"HPG"}` → ok | `{"symbol":"HPG"}` → ok |
| DSH | `{"symbol":"HPG"}` → ok | `{"symbol":"HPG"}` → ok |

OpenTrading chỉ gọi một lần ở mỗi trial HPG, rồi trả `null`. Nó còn tạo evidence với
`source:"opentrading"`, `matched_entry_id:"N/A"`, `response_sha256:"N/A"`: những trường
này không có trong phản hồi tài chính thành công. Driver đã chặn đúng, không cho
evidence giả làm primary pass. Không phải grader đọc nhầm một giá HPG đúng.

Trong aggregation run 1, OpenTrading nói đã lấy lịch sử năm mã nhưng ledger/provider
chứng minh **không có tool call nào**. Phản hồi gồm văn xuôi + JSON fence nên cũng
không đáp ứng đầu ra chỉ một object JSON. Run 2 có năm call nhưng đều bị từ chối.
Đây là hành vi model/native agent thật trong log, không phải extractor làm mất một
đáp án hợp lệ. OpenCode/DSH cũng trượt aggregation vì request không khớp snapshot.

`days=1` có thể là request hợp lý với API tài chính live. Điểm trượt ở đây đo khả năng
tuân thủ request snapshot đã công bố, không chứng minh model không hiểu giá đóng cửa.
Cần báo riêng lỗi request/replay, đọc dữ liệu và tính toán khi công bố benchmark.

## 2. System prompt có xung đột thật với hợp đồng benchmark

Đã thu **request native thực** của cả ba adapter qua provider giả lập cục bộ.
Không gọi model ở bước capture; usage giả lập được đánh dấu riêng, không đưa vào
benchmark hoặc báo chi phí. Các request đầy đủ nằm tại
[capture](/home/doanlong/extra/benchmark/audits/2026-11-05/opentrading-review/capture).

| Arm | Ký tự system prompt của request capture |
|---|---:|
| OpenTrading | 7.892 |
| OpenCode | 1.769 |
| DSH | 307 |

Đây là số ký tự, không phải token. Prompt OpenCode có đường dẫn workspace nên độ dài
có thể thay đổi theo nơi chạy. Prompt OpenTrading không chỉ dài; có các mệnh lệnh đối
lập yêu cầu JSON/evidence của user:

- [style.md:16](/home/doanlong/OpenTrading/prompts/style.md:16): “không dán JSON”.
- [style.md:4](/home/doanlong/OpenTrading/prompts/style.md:4): câu đơn giản phải trả
  văn xuôi; các dòng khác ưu tiên mở đầu kết luận, bảng/biểu đồ.
- [tools.md](/home/doanlong/OpenTrading/prompts/tools.md): không nêu tên tool nếu
  người dùng không hỏi, và nói một câu trước lần gọi tool đầu tiên.
- [citations.md:6](/home/doanlong/OpenTrading/prompts/citations.md:6): tiền trình bày
  bằng đồng, dấu phân cách nghìn, phần trăm một chữ số; benchmark có thể yêu cầu giữ
  nghìn đồng, số JSON không phân cách hoặc độ chính xác khác.
- [identity.md:13](/home/doanlong/OpenTrading/prompts/identity.md:13): system đứng
  trên user; các quy tắc trình bày không được ghi rõ là mặc định có ngoại lệ.

Vì thế user yêu cầu JSON không giải quyết được mâu thuẫn một cách nhất quán. Cần
system tự quy định ngoại lệ cho structured output, không hạ ưu tiên các bất biến về
nguồn dữ liệu/an toàn. Quy tắc không bịa số, không đặt lệnh và không tư vấn cá nhân
hóa không phải thứ cần xóa để cải thiện bài tra cứu giá này.

Prompt dài hơn có chi phí quan sát được: sáu trial OpenTrading dùng 39.136 input token,
OpenCode 19.639, DSH 14.723. Không quy toàn bộ chênh token cho system vì số call và
lịch sử hội thoại cũng khác. OpenTrading **không chậm hơn** trên smoke này: p50
14.377 ms, so với OpenCode 22.654 ms, DSH 22.976 ms; trả thiếu/sai sớm có thể nhanh.
Không đồng nhất latency thấp với hiệu quả trả lời cao.

## 3. Lỗi protocol chung của benchmark làm phục hồi khó hơn

[mcp_snapshot_server.py:187](/home/doanlong/extra/benchmark/tools/mcp_snapshot_server.py:187)
luôn trả danh sách `TextContent`, kể cả khi `replay_call` ghi `status:"rejected"`.
MCP không nhận `CallToolResult(isError=True)` trong nhánh đó. Trace OpenTrading do đó
ghi `tool-end ok:true` dù JSON bên trong có `error` và `availability:not_in_snapshot`.

Không phải OpenTrading làm mất cờ isError:
[convert.ts:59](/home/doanlong/OpenTrading/src/core/mcp/convert.ts:59) thực sự xử lý cờ
này nếu server gửi. Đây là lỗi chung ở server snapshot, không thể dùng riêng nó để
giải thích chênh lệch giữa các arm. Tuy nhiên nó biến lỗi thao tác có thể sửa thành
một “kết quả dữ liệu” dễ bị hiểu nhầm, đúng chuỗi thất bại quan sát được ở HPG.

Rejection còn có object `benchmark_evidence` thiếu provider/as_of/entry/response hash.
Model nhỏ có thể cố điền nốt bằng `N/A` hoặc đoán. Ledger cần giữ mọi request, nhưng
financial evidence nên chỉ xuất hiện trên kết quả hợp lệ; request lỗi dùng trường
chẩn đoán riêng và mã lỗi rõ ràng, kèm request mẫu để phục hồi.

## 4. Thời gian và dấu vết prompt chưa được đóng băng đầy đủ

OpenTrading [agent.ts:599](/home/doanlong/OpenTrading/src/core/agent.ts:599) mặc định
dùng `new Date()`. [assemble.ts:208](/home/doanlong/OpenTrading/src/core/prompt/assemble.ts:208)
luôn chèn phiên thị trường vào user reminder khi bắt đầu conversation. Trial thực gửi
giờ 05/11 trong khi dữ liệu cố định ngày 01/11, đồng thời nhắc lịch tới 29/09 và gọi
`current_time` nếu cần, dù tool đó đã bị loại khỏi track này. OpenCode cũng chèn ngày
hiện tại, nhưng không có cùng reminder nghiệp vụ phiên thị trường; DSH capture không
có clock tương đương. Đây là nhiễu thời gian, chưa chứng minh là nguyên nhân hai lỗi HPG.

Review này còn phát hiện một thiếu sót tái lập của benchmark hiện tại:
[run_manifest.py:87](/home/doanlong/extra/benchmark/tools/run_manifest.py:87) hash
`src/**/*.ts/json`, commit, package và lockfile OpenTrading, **chưa hash**
`prompts/*.md` hoặc `market/calendar.json`. Thay file prompt locally mà không đổi
commit có thể không làm inventory đổi, trong khi assembly đọc prompt mỗi lượt.
Certificate trước xác nhận vận hành, chưa bảo đảm tính bất biến đầy đủ của prompt.
Current inventory vẫn khớp run B; review không sửa những file đó. Thiếu sót này cần
được sửa trước nghiên cứu chính, không âm thầm áp vào receipt cũ.

## 5. Các thành phần khác đã kiểm tra

- Schema upstream OpenTrading bỏ `additionalProperties:false`; OpenCode/DSH giữ.
  [schema.ts:184](/home/doanlong/OpenTrading/src/core/mcp/schema.ts:184) giải thích
  phép biến đổi. Đây là khác biệt strictness cần theo dõi, nhưng `days`/`interval`
  vốn là properties được khai báo nên không giải thích trực tiếp lỗi HPG vừa thấy.
- Mô tả request HPG không bị cắt: cả ba gửi cùng description 262 ký tự, có đủ
  `snapshot_requests`. Description lớn nhất toàn bộ task là 465, dưới cap 2.048
  của OpenTrading. Không có bằng chứng tool description bị mất gây lỗi này.
- Nudge sau tool trong [agent.ts:88](/home/doanlong/OpenTrading/src/core/agent.ts:88)
  không bật cho `@ai-sdk/openai-compatible`, route đang dùng. Là một khác biệt
  đáng thử cho model nhỏ, chưa có bằng chứng sẽ giúp nếu chỉ bật nudge trình bày.
- Không có cạn step ở các trial: default maxSteps là vô hạn; log báo completed,
  không ép summary. Usage có đủ; output không chạm cap 2.048, không timeout hay
  provider HTTP error. Không có bằng chứng phải tăng token/context để sửa lỗi này.
- Skills, memory, web và subagent đều tắt trong cả ba arm. Đây là scope track đã
  chọn; không thể dùng kết quả này để đánh giá bản OpenTrading đầy đủ skills.

## 6. Phép thử prompt nhỏ: kết quả âm cần giữ nguyên

Đã gọi NVIDIA Bolt E4B **8 request**, hai lần mỗi condition; cùng user message và
schema OpenTrading capture, temperature 0, top_p 1. Chỉ đổi system trong từng condition.
Đây là kiểm tra **phản hồi đầu tiên**, không chạy trọn vòng native và không chấm như
benchmark. Streaming được chuẩn hóa false, output cap 1.024; clock capture khác giờ
trial lịch sử. Không so trực tiếp tỷ lệ này với run B.

| System condition | Phản hồi đầu có tool call replay được |
|---|---:|
| OpenTrading nguyên bản | 2/2 |
| Thêm ngoại lệ định dạng JSON | 2/2 |
| Thêm hướng dẫn request/phục hồi | 1/2 |
| Thay system bằng DSH, giữ user/tools OpenTrading | 2/2 |

User hash và tool hash giống nhau qua cả tám request. Không có bằng chứng từ phép
thử này rằng rút prompt hoặc thêm một đoạn nhắc sẽ cải thiện khả năng chọn tham số.
Một condition hướng dẫn phục hồi còn trả số/bảng không có tool call; giá `64.27`
trùng số minh họa đơn vị trong user prompt, không phải dữ liệu đã truy xuất. Điều này
cho thấy phải kiểm tra tool/evidence thật, không chỉ trông chờ lời dặn không bịa số;
chưa đủ để xác định cơ chế sao chép ví dụ. Không được
chọn một trial đẹp rồi công bố “prompt đã chữa lỗi”. Cần pilot phân tầng và chạy
paired ablation đủ task trước kết luận nhân quả. Không gọi model trên holdout,
không gọi Go/Google hoặc model khác ngoài NVIDIA Bolt đã nêu.

Raw request/response và usage tại
[prompt-ablation/summary.json](/home/doanlong/extra/benchmark/audits/2026-11-05/opentrading-review/prompt-ablation/summary.json).
Tổng usage đo được 23.306 token; tiền USD không suy ra khi chưa có bảng giá xác minh.

## Thứ tự nâng cấp đề xuất

1. **Sửa hợp đồng có cấu trúc ở OpenTrading:** safety/data integrity là bất biến;
   văn phong, bảng, đơn vị hiển thị và không dán JSON là default cho hội thoại thường.
   Khi user yêu cầu schema, giữ đúng schema/unit/source namespace và không thêm prose.
2. **Sửa lỗi request trước khi từ chối dữ liệu:** phân biệt invalid request, dữ liệu
   hợp lệ nhưng trống, unavailable, auth và transient provider error. Recovery có
   giới hạn; không retry mù. Không biến lỗi tham số thành kết luận mã không có dữ liệu.
3. **Sửa server snapshot và evidence lỗi:** gửi error state đúng MCP, giữ ledger,
   phản hồi mẫu request hợp lệ; chỉ cấp financial evidence cho response hợp lệ.
   Đây là thay đổi protocol cần version/receipt mới cho mọi arm.
4. **Bổ sung hash prompt/calendar và clock policy** vào manifest; lưu effective
   prompt hoặc bản đã redacted cùng hash. Tách event-time/as-of của dữ liệu khỏi giờ
   môi trường. Audit cả schema thực gửi provider, không chỉ tên tool.
5. **Đo lại có đối chứng:** native baseline; chỉ sửa presentation contract; chỉ sửa
   error/recovery; kết hợp; common-system-prompt track để tách prompt khỏi agent loop.
   Cùng model, task, snapshot, budget và lịch cân bằng; dùng pilot có tra cứu, số học,
   multi-tool, thiếu dữ liệu và kỳ tài chính. Không mở holdout để chỉnh prompt.

Ba nhóm kết quả cần tách khi kết luận: chọn được request và lấy dữ liệu; tính/diễn giải
đúng khi đã lấy được; xuất đúng định dạng/evidence. Hiện chênh HPG thuộc nhóm thứ nhất,
không phải bằng chứng OpenTrading không hiểu nghiệp vụ tài chính.

Bằng chứng tổng hợp có hash/source/các bảng đếm:
[review-evidence.json](/home/doanlong/extra/benchmark/audits/2026-11-05/opentrading-review/review-evidence.json).
