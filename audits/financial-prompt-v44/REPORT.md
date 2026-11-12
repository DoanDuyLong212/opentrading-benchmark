# Báo cáo kết quả cuối cùng v4.4

## Kết luận và phạm vi

**Không nâng cấp OpenTrading finance và không chạy pilot cho cả hai mô hình.** Hai đợt smoke đã hoàn tất 24/24 trial mỗi mô hình, tổng cộng 48 trial. B1 (`opentrading_finance`) đạt primary 2/6 ở cả hai mô hình; cả hai đều không vượt ngưỡng chất lượng đã đăng ký trước. Auditor đã ghim của DeepSeek báo lỗi bốn kiểm soát: hai lần không nhận diện được chặn lệnh cục bộ và hai lỗi đối soát tương ứng. Supervisor dừng ở `smoke-deepseek-audit`. Kết quả audit gốc vẫn là **FAIL**, kể cả khi phụ lục truy vết giải thích được nguyên nhân.

Không có lệnh suy luận pilot nào được thực hiện. Manifest pilot 176 trial/mô hình chỉ là lịch đã đăng ký, không phải kết quả hay baseline pilot đã hoàn tất. Main và holdout chưa được mở. Không cài vào production hoặc tự động nâng cấp.

Mỗi mô hình có bốn điều kiện × ba tác vụ smoke × hai lần lặp. Mẫu số mỗi điều kiện là sáu: bốn trial có thể trả lời và hai trial bẫy không đủ dữ liệu. Đây là ba cụm tác vụ phát triển đã biết; không gộp hai mô hình để tuyên bố ưu thế tài chính. Công cụ `analytics_compute` được cấp chung cho bốn điều kiện, nên cũng không thể quy chênh lệch với các phiên bản cũ hoàn toàn cho OpenTrading.

## Dấu niêm phong và kiểm chứng kỹ thuật

State SHA-256 của startupfix1: `5e4add17dab9d6eb5891c29afa5e34c1a257dc53aaf4f9be2353602e7fbc7f1a`. SHA-256 auditor đã ghim: `743045848cd17165ddaec9c54530cdc487f44fcbf9ce8fd3c0e40a7089a78bde`. Source, prompt, cấu hình, tác vụ, evaluator và auditor được giữ nguyên trong suốt suy luận.

Lần khởi động đầu tiên dừng trước suy luận vì biểu diễn số nguyên/số thực của `retry_backoff` làm khác fingerprint manifest. Bản sửa startup đã được duyệt chỉ truyền tường minh cùng giá trị bốn giây và dùng thư mục kết quả mới; bằng chứng không có suy luận cùng các hiện vật gốc được giữ lại.

Bằng chứng kỹ thuật trước chạy ghi nhận 1.096 native test đạt, hai test bỏ qua; 393 benchmark test đạt và 14 kiểm tra CLI startup đạt. Các kiểm tra này chứng minh khía cạnh triển khai, không chứng minh chất lượng câu trả lời tài chính.

## Kết quả tài chính

Primary là tiêu chí chặt chung về hợp đồng đầu ra, bằng chứng và tài chính. Điểm frozen v4.1/v3 và semantic được báo riêng để phân tích độ nhạy. Cột hợp lệ hợp đồng công khai tính trên cả sáu trial, bao gồm trial thiếu đầu ra; hợp lệ định dạng không đồng nghĩa đúng tài chính. DNF dùng `metrics.is_answered`, không chỉ trạng thái `ok`. FR là từ chối sai trên bốn trial có thể trả lời; FP trên hai trial bẫy.

### nvidia/nvidia/nemotron-3.5-bolt-e4b

Hoàn tất 24/24; kiểm soát audit đã ghim **PASS**. Cờ canary số độc lập lưu là **PASS**, nhưng đúng theo nghĩa rỗng: **không có numeric win để kiểm chứng, không phải đạt năng lực truy xuất số**.

| Điều kiện | Primary /6 | Frozen v4.1 /6 | Frozen v3 /6 | Semantic /6 | Hợp lệ hợp đồng công khai /6 | DNF /6 | FR /4 | FP /2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| opentrading_baseline | 2 | 2 | 2 | 2 | 4 | 0 | 4 | 0 |
| opentrading_finance | 2 | 2 | 2 | 2 | 6 | 0 | 4 | 0 |
| opencode | 1 | 2 | 2 | 2 | 3 | 0 | 4 | 0 |
| dsh | 1 | 1 | 1 | 1 | 6 | 0 | 4 | 0 |

Cả bốn điều kiện đều từ chối sai 4/4 trial có thể trả lời, đồng thời chưa lấy đủ dữ liệu nguồn ở các trial này. Tất cả primary thành công của Bolt đều thuộc tác vụ bẫy. B1 và B0 cùng đạt 2/6; B1 hợp lệ hợp đồng 6/6 so với B0 4/6 chỉ cho thấy khác biệt về định dạng, không chứng minh cải thiện tài chính. Sáu lượt acquisition của B1 có hai lần lấy được biên nhận nguồn đầu tiên và đi kèm hai primary ở tác vụ bẫy, không phải thắng ở truy vấn giá hoặc tính tổng hợp.

### nvidia/deepseek-ai/deepseek-v4.1-flash

Hoàn tất 24/24; kiểm soát audit đã ghim **FAIL**; canary số độc lập **PASS**, với hai numeric win thực được kiểm chứng (B1 quote lần 1 và DSH quote lần 2).

| Điều kiện | Primary /6 | Frozen v4.1 /6 | Frozen v3 /6 | Semantic /6 | Hợp lệ hợp đồng công khai /6 | DNF /6 | FR /4 | FP /2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| opentrading_baseline | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 0 |
| opentrading_finance | 2 | 2 | 2 | 2 | 2 | 4 | 0 | 0 |
| opencode | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 0 |
| dsh | 1 | 3 | 3 | 3 | 1 | 3 | 0 | 0 |

B1 có bốn DNF; hai primary là quote lần 1 và trap lần 2. DSH có một primary ở quote lần 2. Không điều kiện nào có primary ở aggregation. B0 và OpenCode có semantic 3/6 nhưng primary 0/6 do hợp đồng đầu ra; DSH có semantic 3/6, primary 1/6. Vì vậy primary 2/6 của B1 không đủ để tuyên bố ưu thế tài chính: semantic thấp hơn và DNF cao hơn các đối chứng này.

Bốn lỗi audit gốc nằm ở `smoke-agg-01__opentrading_finance__r1` và `r2`: mỗi trial có một lỗi `local_rejection` (“Unrecognized policy guard rejection”) và một lỗi `tool_call_reconciliation`. Không sửa kết quả FAIL này bằng phụ lục bổ sung.

Canary số PASS nghĩa là không phát hiện đáp án số đã được primary chấp nhận nhưng sai nguồn/giá trị trong phạm vi kiểm tra; không có nghĩa mọi điều kiện đều tạo được một đáp án số thành công.

## Quyết định theo ngưỡng đã đăng ký

| Mô hình | Điều kiện có đáp án số đạt primary, có nguồn thực | B1 strict /6 (yêu cầu ≥4) | B1 FR /4 (yêu cầu ≤1) | B1 DNF /6 (yêu cầu 0) | B1 strict traps /2 (yêu cầu 2) | Đủ điều kiện chất lượng |
|---|---|---:|---:|---:|---:|---|
| Bolt | không có | 2 | 4 | 0 | 2 | Không |
| DeepSeek | opentrading_finance, dsh | 2 | 0 | 4 | 1 | Không |

Cả hai mô hình đều không đáp ứng yêu cầu cả bốn điều kiện có ít nhất một primary số với nguồn thực. Lỗi chất lượng vốn đã loại pilot của từng mô hình; lỗi kiểm soát DeepSeek còn chặn supervisor. Giải thích bổ sung cho auditor không làm các ngưỡng chất lượng này trở thành đạt.

Chín primary được chấp nhận đều có biên nhận nguồn thực và ngữ cảnh công cụ hiển thị khớp. Không có primary được chấp nhận dùng biên nhận không tồn tại hoặc bị sửa trong phạm vi kiểm tra; điều này không chứng nhận mọi phát biểu sinh ra hoặc mọi lệnh bị chặn là đúng.

## Cơ chế quan sát được và việc dùng công cụ

| Mô hình | Điều kiện | Tổng lệnh MCP | MCP thành công | MCP từ chối | Lệnh compute | Từ chối cục bộ được auditor nhận diện | Lượt vào acquisition | Biên nhận thành công đầu tiên trong acquisition | Primary có acquisition |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| nvidia/nvidia/nemotron-3.5-bolt-e4b | opentrading_baseline | 13 | 2 | 11 | 0 | 0 | 0 | 0 | 0 |
| nvidia/nvidia/nemotron-3.5-bolt-e4b | opentrading_finance | 2 | 2 | 0 | 0 | 1 | 6 | 2 | 2 |
| nvidia/nvidia/nemotron-3.5-bolt-e4b | opencode | 14 | 2 | 12 | 0 | 0 | 0 | 0 | 0 |
| nvidia/nvidia/nemotron-3.5-bolt-e4b | dsh | 14 | 2 | 12 | 0 | 0 | 0 | 0 | 0 |
| nvidia/deepseek-ai/deepseek-v4.1-flash | opentrading_baseline | 16 | 13 | 3 | 3 | 0 | 0 | 0 | 0 |
| nvidia/deepseek-ai/deepseek-v4.1-flash | opentrading_finance | 17 | 13 | 4 | 4 | 0 | 0 | 0 | 0 |
| nvidia/deepseek-ai/deepseek-v4.1-flash | opencode | 20 | 14 | 6 | 6 | 0 | 0 | 0 | 0 |
| nvidia/deepseek-ai/deepseek-v4.1-flash | dsh | 13 | 9 | 4 | 4 | 0 | 0 | 0 | 0 |

Tổng lệnh MCP đã bao gồm compute khi có; không cộng compute thêm lần nữa. Bolt không dùng compute trong suy luận thực. DeepSeek có 17 lệnh compute và cả 17 bị từ chối: bảy lệnh dùng `/data/` (khóa rỗng ở cuối), mười lệnh dùng `/data` (chưa phải lá số dưới `/data/`). Không lệnh nào chọn lá số thực `/data/last`; đơn vị và ID nguồn đều khớp. Đây là lỗi chọn đường dẫn quan sát được, chưa phải bằng chứng mô hình không thể làm số học.

Schema công khai cho phép hai dạng gốc nói trên nhưng runtime cần một lá số. `invalid_derivation` không nằm trong danh sách lỗi được native repair xử lý; compute không khai báo `x-repair-fields`, nên đổi pointer hoặc số toán hạng bị tính là ý định mới, không phải sửa cùng ý định. DeepSeek có 42 lệnh quote và bảy lệnh resolver thành công; Bolt có 35 lệnh quote bị từ chối và tám resolver thành công.

Cột chặn cục bộ chỉ đếm các lý do auditor gốc nhận diện được. Vì thế giá trị 0 của DeepSeek B1 không bao gồm hai lần chặn chưa nhận diện. Truy vết native/provider/run-log đối soát được B1 có 19 lệnh sinh ra = 17 lệnh MCP + hai lần chặn trùng cục bộ. Phụ lục này giải thích lỗ hổng bao phủ của auditor, không sửa kết quả audit gốc.

Có 14 lỗi provider: ba lỗi metadata model nhưng không giữ được raw response (`response_models=[]`), hai timeout, hai lần chặn tiếp do usage chưa biết và bảy lần chặn trước request bởi ngân sách token bảo thủ. Thiếu metadata không chứng minh model khác đã trả lời. Các sự kiện acquisition/repair là telemetry thực thi, chưa chứng minh quan hệ nhân quả với chất lượng.

## Giả thuyết ưu tiên cho nghiên cứu tiếp: diễn giải schema khi giải mã ràng buộc

Trước khi chỉnh prompt thêm, cần kiểm tra liệu bộ giải mã ràng buộc có diễn giải pattern khác JSON Schema hay không. Pattern thực `^/data(?:/|$)` cho phép hậu tố số nếu dùng tìm kiếm một phần; nhưng **nếu khớp toàn chuỗi thì chỉ cho phép `/data` hoặc `/data/`**—đúng hai giá trị xuất hiện trong cả 17 lệnh compute bị từ chối. Cả 17 cặp request native/effective đã đối chiếu đều mang pattern này; tổng cộng 57 lần xuất hiện toán hạng đều phù hợp. Không thấy cờ `strict`, `guided_json` hoặc cờ giải mã tương tự trong các request đã nối. Đây là giả thuyết tương thích cụ thể, chưa xác nhận backend, chế độ giải mã hoặc nguyên nhân của endpoint NVIDIA đã chạy.

[Tài liệu chuỗi JSON Schema](https://json-schema.org/understanding-json-schema/reference/string) quy định pattern có thể khớp ở bất kỳ vị trí nào. [XGrammar issue 838](https://github.com/mlc-ai/xgrammar/issues/838) báo cáo hành vi khớp toàn chuỗi; issue không xác nhận phiên bản hay hành vi deployment này. [Tài liệu structured generation NVIDIA NIM 1.15](https://docs.nvidia.com/nim/large-language-models/1.15.0/structured-generation.html) mô tả `guided_json` dùng XGrammar, nhưng chưa chứng minh endpoint hosted này áp dụng cùng cơ chế cho tham số tool.

Bước tiếp theo nên là kiểm chứng regex/capture offline, rồi một canary NVIDIA nhỏ **được cấp phép riêng**, so sánh pattern tiền tố, pattern neo đầy đủ và không có pattern. Sau đó mới xem xét smoke tài chính bốn điều kiện trên dữ liệu mới chưa dùng để tinh chỉnh. Không có canary hay suy luận mới nào được chạy khi hoàn thiện báo cáo này.

## Request và usage

Token “đã biết” chỉ là tổng usage được báo, không bù phần thiếu để coi là tổng đầy đủ. Yêu cầu gateway, số lần thử upstream và bản ghi usage là ba số khác nhau. Số trial đủ usage báo riêng. Reasoning là phần con của output/completion, cache là phần con input; không cộng lặp. Usage thiếu vẫn chưa biết. Chi phí tiền: **N/A**, vì chưa niêm phong được giá và quyền lợi tài khoản từ nguồn có thẩm quyền.

| Mô hình | Điều kiện | Yêu cầu gateway | Đã thử gửi upstream | Bản ghi usage | Trial đủ usage /6 | Input đã biết | Output đã biết | Reasoning đã biết | Cache đã biết |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| nvidia/nvidia/nemotron-3.5-bolt-e4b | opentrading_baseline | 11 | 11 | 11 | 6 | 52710 | 1492 | 0 | 42944 |
| nvidia/nvidia/nemotron-3.5-bolt-e4b | opentrading_finance | 16 | 16 | 16 | 6 | 42698 | 1549 | 0 | 32704 |
| nvidia/nvidia/nemotron-3.5-bolt-e4b | opencode | 12 | 12 | 12 | 6 | 35957 | 1831 | 0 | 16256 |
| nvidia/nvidia/nemotron-3.5-bolt-e4b | dsh | 20 | 20 | 20 | 6 | 54622 | 1754 | 0 | 46368 |
| nvidia/deepseek-ai/deepseek-v4.1-flash | opentrading_baseline | 15 | 12 | 11 | 3 | 79518 | 3638 | 844 | 10368 |
| nvidia/deepseek-ai/deepseek-v4.1-flash | opentrading_finance | 18 | 15 | 13 | 2 | 62599 | 3355 | 825 | 7360 |
| nvidia/deepseek-ai/deepseek-v4.1-flash | opencode | 18 | 16 | 16 | 4 | 73129 | 4406 | 915 | 19200 |
| nvidia/deepseek-ai/deepseek-v4.1-flash | dsh | 15 | 14 | 12 | 3 | 47602 | 3356 | 958 | 14336 |

Bolt có trường reasoning/cache cho mọi request và reasoning đã biết bằng 0. DeepSeek chỉ có các trường đó trên số bản ghi usage trong từng dòng, không phải mọi request gateway. Không dùng tổng token đã biết thấp hơn để kết luận tiết kiệm chi phí khi telemetry chưa đầy đủ.

## Kiểm chứng completed resume và bảo toàn dữ liệu

**PASS, đã được kiểm tra độc lập.** Root đã chạy completed `--resume` bằng đúng hai lệnh smoke trong supervisor startupfix1. `main()` của cả hai driver gốc đều thoát mã 0, không vào `execute_trial`, **không tạo lệnh model mới**. Mỗi smoke vẫn có đúng 24 ID lịch/hoàn tất/đã bắt đầu.

Đối chiếu trước/sau cho **8.132 file được bảo vệ** trong cả bốn thư mục kết quả đã đăng ký cho thấy SHA-256, kích thước và `mtime_ns` không đổi, bao gồm toàn bộ trial, capture, ledger provider/MCP lồng sâu và manifest hai pilot chưa chạy. Chỉ `summary.json` và `.driver.lock` ở gốc mỗi smoke được loại tường minh vì là metadata có thể tái tạo. Byte seal và supervisor không đổi. Monkeypatch chặn thực thi chỉ nằm trong wrapper ngoài và đã được khôi phục; source driver niêm phong không đổi. Không khởi chạy supervisor, pilot, main hoặc holdout.

Đây là kiểm tra kỹ thuật/bảo toàn dữ liệu, không phải cải thiện điểm tài chính; kết luận chặn pilot và FAIL audit giữ nguyên.

## Liên kết bằng chứng

- [Báo cáo cuối](/home/doanlong/extra/benchmark/audits/financial-prompt-v44/REPORT.md).
- [Regrade độc lập 48 trial](/home/doanlong/extra/benchmark/audits/financial-prompt-v44/independent-evidence.json).
- [Seal startupfix1](/home/doanlong/extra/benchmark/audits/financial-prompt-v44/preinference-seal-startupfix1.json).
- [Trạng thái supervisor](/home/doanlong/extra/benchmark/audits/financial-prompt-v44/supervisor-startupfix1/state.json).
- [Kiểm chứng độc lập cuối](/home/doanlong/extra/benchmark/audits/financial-prompt-v44/INDEPENDENT-CHECK.md).
- [Bảng số đếm độc lập](/home/doanlong/extra/benchmark/audits/financial-prompt-v44/independent-counts.json).
- [Phụ lục truy vết kỹ thuật](/home/doanlong/extra/benchmark/audits/financial-prompt-v44/FORENSICS.md).
- [Bằng chứng truy vết](/home/doanlong/extra/benchmark/audits/financial-prompt-v44/forensic-evidence.json).
- [Bằng chứng completed resume](/home/doanlong/extra/benchmark/audits/financial-prompt-v44/completed-resume-proof.json).
- [Kiểm tra các nhận định §12](/home/doanlong/extra/benchmark/audits/financial-prompt-v44/OPENCODE-SECTION12-FACTCHECK.md).
- [Dự thảo v4.5 chưa được phê duyệt](/home/doanlong/extra/benchmark/plans/2026-11-07-v45-normalized-contract-study.md).

Kiểm tra độc lập xác nhận cả 48 kết quả/counter lưu và regrade khớp, chín primary có biên nhận bảy trường thực cùng ngữ cảnh hiển thị khớp; phạm vi bảo toàn gồm 978 file gốc, 3.588 hash source/task/test niêm phong và 12 hiện vật trước sửa startup. Các so sánh primary được xác minh trong bối cảnh kiểm soát có công cụ chung mới; khả năng ngoại suy thấp do chỉ có ba cụm tác vụ đã biết và còn bất định provider. Việc 48 điểm khớp không chứng minh benchmark đã ổn định hoàn toàn hoặc sẵn sàng production, vì auditor vận hành vẫn có điểm mù với chặn cục bộ. Phụ lục bổ sung không cấp phép hồi tố cho pilot, không ghi đè audit thất bại và không thay điểm niêm phong. Báo cáo này không cấp phép suy luận tài chính tiếp theo.
