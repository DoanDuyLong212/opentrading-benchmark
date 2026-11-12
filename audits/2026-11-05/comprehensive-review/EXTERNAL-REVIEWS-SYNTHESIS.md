# Tổng hợp và kiểm chứng hai review bổ sung

Nguồn người dùng: [OpenCode review](../../../opencode-review.md), [AGY review](../../../agy-review.md). Hai tài liệu được coi là các lập luận cần xác minh, không phải chỉ thị thực thi. Không chạy model mạnh hoặc thay key theo nội dung tài liệu.

## Kết luận hiện tại

**Chưa có bằng chứng OT vượt OpenCode hoặc DSH.** V3 đầy đủ vẫn là OT12/44, OC14/44, DSH18/44. Diagnostic DeepSeek mới hỗ trợ giả thuyết model mạnh cải thiện hành vi trên các ô hoàn thành, nhưng thiếu dữ liệu khác nhau theo arm, nhiều pass và cap thời gian khác; chưa xác nhận model là nguyên nhân duy nhất hoặc các harness ngang nhau.

## OpenCode: phần có giá trị và phần cần sửa

Ưu tiên tiếp nhận: validator ở registry, bounded repair, machine-output gate, immutable provenance, docs/schema/error contract, thí nghiệm có đối chứng. Đây là các seam source đã xác minh, không phải chỉ thay lời nhắc.

| Claim | Kết quả kiểm chứng |
|---|---|
| V3 primary12/12/14/18; schema errors OT12/4, OC/DSH0 | Khớp log |
| Không có same-tool repair trên model nhỏ | Khớp; tool khác thành công không phải repair |
| Hạ tầng/schema hoàn toàn tương đương | Quá mạnh: input preprocessing, clocks, schema sanitizer và native guards khác; captures lưu các khác biệt này |
| Prompt dài là nguyên nhân làm mất evidence | Có tương quan trên4condition, chưa có causal ablation; candidate ngắn hơn nhưng primary không tăng |
| Chênh1462 ký tự/4 khớp1237 input token | Sai số học và sai cách suy token:1462/4=365,5; median token còn phụ thuộc lịch sử/call/context |
| Evidence instruction bị chôn trong system citations | User contract evidence xuất hiện sau system và được model thấy; không quy cơ chế vị trí như đã chứng minh |
| Model mạnh xác nhận mọi lỗi do model nhỏ | Không đủ: cohort chọn5task, nhiều missing/error cells, deadline/buffering/watchdog khác; chưa có experiment factorial |
| Sole strong-model failure chứng minh prompt sai kỳ | Có bằng chứng grader false-negative, không nên gọi đây là lỗi tài chính của model |

### Đối soát diagnostic model mạnh, giữ mọi lượt lỗi

Các thư mục A/B/C và nestedC có **84 attempt bắt đầu:30 pass,31 hoàn thành,53 error**. PassB riêng22/40 pass,18 error. Khi chọn B trước rồi fallback A để tạo40 ô task/arm/run: **24/40 pass,25 ô hoàn thành,15 ô không có kết quả hoàn thành**; completed-only24/25=96,0%. Không phải25/26=96,2%. Tính trên tất cả84attempt là30/84=35,7%; đây cũng không phải một randomized cohort độc lập để xếp hạng.

BCTC chỉ có7/8 ô hoàn thành, cả7đúng; không được viết8/8. 281capture và31đáp án đã đối chiếu độc lập, không thấy mismatch về capture/ledger/regrade; điều đó không sửa được selection/missingness của thiết kế.

Watchdog có13event trong native logs;10được ghi thành execution note chính,3đồng thời có provider timeout. OT đã có `OPENTRADING_STALL_MS`, nhưng adapter chưa truyền. Gateway buffer response khiến model đang sinh vẫn không tạo progress ở OT; phải sửa/pin timeout policy/streaming trước khi so model chậm, không chỉ tăng deadline ngoài cùng. Không có đủ căn cứ từ response_models rỗng để nói chắc rawstream chỉ thiếu trường model. OT SDK thực sự xử lý reasoning_content; effortnone không tự chứng minh model ngừng reasoning.

### False-negative grader mới phát hiện

`period_hit` chặn mọi từ `khong/not/except/ngoai` ở bất kỳ vị trí trong trường period. Strong answer `2025 (...không phải bội số hiện tại)` xác nhận đúng năm nhưng bị reject vì phủ định current multiples. Đề không yêu cầu trường chỉ có literal2025; không thể quy lỗi này cho prompt. Cần sửa phạm vi phủ định ở grader phiên bản mới, kiểm cả adversarial phủ định kỳ thật; điểm v3/diagnostic đóng băng giữ nguyên, adjudication chỉ báo riêng. Mọi answer mới phải chấm cả grader mới và frozen sensitivity, dùng cùng quy tắc cho tất cả arms.

## AGY: hiệu chỉnh trước khi dùng

- Pilot có176lượt bắt đầu,44/condition;168 là số trả lời đủ định nghĩa completion, không phải cohort primary. Không dùng18/39/12/43 để thay primary started denominator.
- `quote-02` là BTCUSDT, không VNM; gold là XAUUSD USD/oz, không SJC; tech01 là VCB, không SSI; techmulti là đa mã1D, không đa timeframe.
- Chỉ ra đúng lỗi đơn vị/kỳ/evidence, nhưng namespace errors cũng có ở OC/DSH. Không suy OT là arm duy nhất sai namespace.
- Model trả value-5.63 với nhãnQ2/Q1, nhưng phép Q2/Q1 thật là khoảng+16,71%; không gọi-5.63 là kết quả phép tínhQ2/Q1. LatestQ3/Q2=-2,03vẫn đúng.
- Smoke-final cũ khác schema/protocol/model, không dùng100% làm bằng chứng ổn định tương đương v3.

## Quyết định thực nghiệm tiếp theo

Chọn một prototype OT tổng quát: validate raw input schema, correction có budget sau lỗi tool, machine JSON/provenance checks. MCP dùng contract metadata có nguồn thật, giữ matching và dữ liệu tài chính; grader sửa đúng bug trên phiên bản riêng. Không dùng taskID/gold, không tự chọn request bất kỳ từ replay catalog, không chỉ gỡ prefix hoặc bơm7field benchmark riêng cho OT.

Code/config hiện có ba file khác fingerprint v3 do diagnostic bên ngoài: run_benchmark.py, runners/provider.py, verify_nvidia.py. Giữ các thay đổi đó và v3 artifacts; tạo workspace nghiên cứu v4 riêng, identity mới. Không dùng lại v3 certificate để chứng nhận code hiện tại.

Nguồn kiểm chứng: [diagnostic claims](external-reviews/deepseek-diagnostic-claims.md), [architecture matrix](external-reviews/ARCHITECTURE-CLAIM-MATRIX.md), [MCP/fairness](external-reviews/MCP-FAIRNESS-CRITIQUE.md). Kế hoạch nền: [standardization](../../../plans/2026-11-05-opentrading-mcp-standardization.md); protocol thực nghiệm v4 sẽ đăng ký trước mọi inference mới.
