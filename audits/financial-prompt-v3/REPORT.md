# Kết quả sửa runtime, smoke và pilot prompt tài chính v3

Hoàn tất ngày 05/11/2026 (Asia/Bangkok). **Prompt finance chưa cải thiện tỷ lệ đúng so với OpenTrading baseline và chưa đánh bại hai đối chứng.** Đã áp dụng các sửa lỗi runtime vào OpenTrading gốc; giữ nguyên prompt baseline mặc định. Prompt finance được giữ làm ứng viên thử nghiệm, không sửa tiếp theo kết quả pilot này.

## Phạm vi và kiểm tra vận hành

Chạy đúng protocol đã đăng ký tại [compact-pilot-protocol](../../plans/2026-11-05-compact-pilot-protocol.md): 18 smoke, sau đó 176 pilot = 22 task × 2 run × 4 condition. NVIDIA `nvidia/nemotron-3.5-bolt-e4b` duy nhất, effort `none`, temperature 0, top_p 1; timeout 240 giây/trial, tối đa 24 request, 2.048 output token/request, policy tổng 48.000 token, retry 0, khoảng cách request tối thiểu 2 giây. Không chạy main/holdout/Google/Go. Hai task pilot bị quarantine từ trước không được đưa vào chấm chính.

Hai condition OT dùng cùng native runtime và agent loop, chỉ khác thư mục prompt đáng tin cậy. Mọi condition dùng snapshot server v3 đã sửa trạng thái lỗi MCP. OT được pin native clock theo snapshot; không tuyên bố đã pin clock nội bộ OpenCode/DSH. Actual native/effective requests, tool schemas, usage và ledger được lưu để kiểm tra chênh lệch SDK.

- Preflight offline 4/4 pass bên ngoài sandbox; sandbox hạn chế stdio làm lần kiểm tra đầu timeout trước inference.
- Certificate mới đạt sau **250 pytest pass**, kiểm tra artifact smoke và native inventory: [certificate](../../results/financial-prompt-v3-ready-20261105.json).
- Native OpenTrading trong bản thí nghiệm: full suite **466 pass, 0 fail**, typecheck pass trước inference; [implementation evidence](../../experiments/opentrading-implementation-evidence.json). Sau cài runtime-only vào dự án gốc: **56 test agent/prompt hiện có pass, 0 fail** và typecheck pass; [native log](postinstall-native-tests.log), [typecheck log](postinstall-typecheck.log). Các nhóm kiểm tra này có phạm vi riêng, không cộng thành một suite duy nhất.
- Smoke hoàn tất 18/18: OT finance 2/6, OpenCode 4/6, DSH 4/6; DNF 0, usage coverage 100%. HPG OT 0/2, tổng hợp năm ngân hàng cả ba 0/2; trap mã không tồn tại cả ba 2/2. Đây là operational gate, không phải chứng nhận model đủ giỏi tài chính.
- Pilot hoàn tất 176/176, không thay thế trial lỗi. Bắt đầu 14:51:47 và kết thúc 15:54:18 giờ Bangkok, khoảng 62,5 phút.
- Code, runtime/dependency inventory, protocol và toàn bộ 22 task fingerprints còn khớp manifest sau chạy.
- Resume smoke: 18 row, 36 provider request; resume pilot: 176 row, 354 provider request. Manifest/trials/provider-ledger hashes trước và sau đều bằng nhau, **không thêm inference**. Xem [smoke proof](smoke-resume-check.json), [pilot proof](pilot-resume-check.json).

## Kết quả pilot đầy đủ

Primary = đúng toàn bộ, đúng schema/evidence, grounded bằng ledger thật, đúng hạn và status thành công. Semantic được báo riêng vì có thể đúng số nhưng sai nguồn/evidence. Mỗi condition bắt đầu đúng 44 trial.

| Condition | Primary /44 | Semantic /44 | DNF /44 | Từ chối oan /44 | FP /44 | Usage đủ |
|---|---:|---:|---:|---:|---:|---:|
| OT baseline | 12 (27,3%) | 14 | 1 | 17 | 0 | 43/44 |
| OT finance | 12 (27,3%) | 14 | 1 | 15 | 0 | 44/44 |
| OpenCode | 14 (31,8%) | 15 | 1 | 14 | 0 | 44/44 |
| DSH | 18 (40,9%) | 18 | 5 | 11 | 0 | 42/44 |

Các cột /44 là normalization theo cohort bắt đầu, dùng cho rollout guard. Chúng không phải rủi ro có điều kiện trên câu không thể trả lời. Mỗi condition có 40 trial có đáp án và 4 trial refusal:

| Condition | Success / đã trả lời | Từ chối oan /40 có đáp án bắt đầu | Từ chối oan / có đáp án đã trả lời | FP /4 refusal |
|---|---:|---:|---:|---:|
| OT baseline | 12/43 | 17/40 | 17/39 | 0/4 |
| OT finance | 12/43 | 15/40 | 15/39 | 0/4 |
| OpenCode | 14/43 | 14/40 | 14/39 | 0/4 |
| DSH | 18/39 | 11/40 | 11/35 | 0/4 |

Không loại DNF khỏi primary. DSH có hai trial timeout provider với usage không đầy đủ; thêm một trial hết output budget tạo JSON bị cắt, và hai trial JSON không hợp lệ. Baseline có một provider failure; finance và OpenCode mỗi bên có một DNF vì output không thành JSON hợp lệ. Tất cả vẫn nằm trong mẫu số 44.

| Condition | Request gateway | MCP gọi / thành công / từ chối | Phục hồi sau từ chối (trial) | Input/output đã đo đủ usage* | Median latency / p90 |
|---|---:|---:|---:|---:|---:|
| OT baseline | 88 | 65 / 38 / 27 | 4 | 307.477 / 13.525 (43 trial) | 14,586 / 21,873 giây |
| OT finance | 88 | 66 / 39 / 27 | 4 | 259.187 / 16.611 (44 trial) | 15,296 / 22,146 giây |
| OpenCode | 88 | 66 / 39 / 27 | 4 | 151.757 / 17.398 (44 trial) | 17,443 / 28,464 giây |
| DSH | 90 | 66 / 41 / 25 | 4 | 112.537 / 18.675 (42 trial) | 23,121 / 30,869 giây |

\* Tổng chỉ cộng các trial có usage hoàn chỉnh, không gán 0 cho phần thiếu. Tổng token toàn cohort baseline/DSH là N/A; không dùng tổng bị thiếu để tuyên bố tiết kiệm chính xác. Median input token baseline 7.051, finance 5.814; output median tương ứng 276 và 359. Chi phí USD N/A vì chưa đóng băng giá/entitlement được xác minh.

354 request gateway tương ứng 353 upstream request thật: baseline 87/88 request được gửi upstream (một lần bị chặn cục bộ sau usage không rõ); ba condition còn lại gửi upstream toàn bộ. “Phục hồi” yêu cầu một MCP `ok` xuất hiện sau MCP `rejected` trong cùng trial; không khẳng định đã sửa chính request/tool vừa lỗi hoặc đáp án cuối đúng.

## Diễn giải và lỗi còn lại

Prompt finance giảm hai false refusal, nhưng số primary đúng không đổi. Theo task, finance tăng `fin-l1-quote-02` từ 1/2 lên 2/2 và giảm `fin-l5-compare-01` từ 1/2 xuống 0/2. Không có cơ sở chọn riêng task có lợi. Xem đầy đủ [22 task](pilot-task-success.csv) và [176 trial](pilot-trials.csv).

Strict request matching vẫn là trở ngại lớn: OT finance và baseline mỗi bên có 13 trial bị từ chối request mà chưa có MCP thành công. Ví dụ HPG finance thêm `columns=close, days=1, interval=day`, khác request được replay. Prompt recovery chưa giải quyết được hành vi này trên tiny model; không nới server để biến request sai thành đúng.

Một nhóm khác truy xuất và evidence đúng nhưng đáp án tài chính vẫn sai. Ví dụ growth finance run 1 trả `value=-5.63` và kỳ Q2 so Q1; note lại tự nêu Q3 so Q2 là khoảng `-2.03` mà không cập nhật trường JSON. Grader giữ lỗi đúng kỳ/số; lấy được dữ liệu không đồng nghĩa đã tính đúng yêu cầu. Các RSI multi-symbol còn sai trường kỳ.

Finance có **hai trial evidence không khớp ledger**, baseline có 0. Một trường hợp dùng tên tool dạng SDK namespace thay tên tool canonical; trường hợp FX/crypto còn tạo evidence placeholder `N/A`. Cả hai bị chặn, không được tính primary đúng. OpenCode có 5 và DSH 4 claimed evidence không khớp trong các trial lỗi. Đây là diagnostic về grounding trên tất cả task, khác với FP trên bốn câu refusal; do đó FP=0 không có nghĩa không xuất hiện evidence bịa/sai.

## So sánh có ghép cặp và quyết định

Bootstrap theo 22 task, 2.000 draws, CI95% exploratory cho chênh lệch primary (finance trừ đối chứng):

| So sánh | Chênh lệch | CI95% theo task |
|---|---:|---:|
| Finance − baseline | 0 điểm % | [−6,82; +6,82] |
| Finance − OpenCode | −4,55 điểm % | [−20,45; +9,09] |
| Finance − DSH | −13,64 điểm % | [−27,27; −2,27] |

Sensitivity theo 18 payload families lần lượt là [−6,00; +6,52], [−19,05; +7,50], [−26,19; −2,38] điểm %. Đây là pilot nhỏ với hai lần chạy, không kiểm định stable-correct 3/3, không có McNemar/Holm endpoint đó, không chứng minh tiêu chí thắng main +7 điểm %/CI97,5%. Không chuyển kết luận sang Go/DeepSeek/medium chưa xác minh.

**Registered promotion guard: PASS**, đúng theo protocol trước inference: primary finance 12 ≥ baseline 12; FP 0=0, DNF 1=1; false refusal 15<17 là cải thiện nghiêm ngặt. Không dùng token tiebreak (usage baseline thiếu). Không viết lại guard sau khi xem kết quả.

**Quyết định triển khai sau review: chỉ runtime fixes; không đổi prompt mặc định.** Đây là đánh giá triển khai bổ sung, tách khỏi kết quả guard đã đăng ký: không có cải thiện primary/semantic, vẫn kém hai đối chứng trong pilot và có regression evidence mismatch 2 so 0. Guard là ngưỡng cần, không là bằng chứng thắng hoặc đủ độ tin cậy để buộc promote.

Đã cài hai file runtime `src/core/agent.ts` và `src/core/prompt/assemble.ts` vào `/home/doanlong/OpenTrading`, giữ baseline prompt gốc. Backup và hash trước/sau nằm tại [receipt runtime_only](../../experiments/installed-backups/20261105T091212.728355Z/receipt.json). Bản runtime/prompt frozen của thí nghiệm vẫn được giữ nguyên. Không thêm model call hay chỉnh candidate sau pilot.

**Alias thí nghiệm khác default đã cài:** trong bản benchmark v3 đã frozen, canonical `opentrading` (và OT trong `--arms all`) vẫn chọn **finance** để tái lập thí nghiệm. Nó không đại diện prompt mặc định hiện tại của OpenTrading gốc. Để so sánh default đã giữ lại trong một lần chạy mới, phải ghi rõ `--arms opentrading_baseline,opencode,dsh`, dùng manifest/certificate mới theo gate tương ứng. Không sửa alias frozen để che sự khác biệt này.

Ưu tiên nghiên cứu tiếp là ràng buộc kiểu kỳ/đơn vị/nguồn với số được chọn, kiểm tra phép tính và structured output, cùng request repair có giới hạn. Mỗi sửa mới cần thí nghiệm exploratory đăng ký riêng; không tăng độ dài prompt hoặc output cap để tìm điểm đẹp, không đưa gold vào prompt, không cấp replay privilege riêng cho một arm.

Nguồn dữ liệu là snapshot-grounded QA; không chứng nhận tính đúng của filings gốc. Payload families có phụ thuộc và main/holdout có overlap lịch sử đã ghi trong audit cũ. Không có main/holdout inference trong lần này.

Evidence máy đọc: [evidence.json](evidence.json), [independent review](INDEPENDENT-CHECK.md), [pilot manifest](../../results/financial-prompt-v3-pilot-20261105/manifest.json), [pilot summary](../../results/financial-prompt-v3-pilot-20261105/summary.json).
