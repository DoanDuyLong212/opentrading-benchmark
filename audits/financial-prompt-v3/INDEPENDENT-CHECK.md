# Kiểm tra độc lập sau khi kết thúc pilot v3

Ngày 05/11/2026. Đã review đúng dữ liệu hoàn tất, không gọi model bổ sung, không đổi prompt/grader/dữ liệu hoặc thay trial lỗi. Nguồn: [smoke](../../results/financial-prompt-v3-smoke-20261105/manifest.json), [pilot](../../results/financial-prompt-v3-pilot-20261105/manifest.json), [protocol đăng ký trước](../../plans/2026-11-05-compact-pilot-protocol.md). Kết quả tái tính và bằng chứng chi tiết nằm trong [independent-evidence.json](independent-evidence.json).

## Tính toàn vẹn và vận hành

Smoke đủ 18 trial: 3 câu × 2 lần × 3 harness canonical; primary OpenTrading 2/6, OpenCode 4/6, DSH 4/6. Tất cả có đáp án JSON, status `ok`, schema hợp lệ và usage đầy đủ. 72 file capture native/effective đã được đối chiếu.

Pilot đủ **176 trial = 22 câu × 2 lần × 4 điều kiện**, mỗi điều kiện 44 trial. ID, thứ tự và fingerprint khớp chính xác manifest, không trial trùng hoặc thay thế; mỗi điều kiện xuất hiện 11 lần ở từng vị trí trong bốn vị trí chạy. Không có main/holdout trong nghiên cứu này.

Đã chạy lại grader cho từng đáp án được lưu, ghi kết quả riêng vào thư mục tạm; trial không có đáp án JSON được giữ thất bại. Primary được tái tính từ grade, trạng thái/thời gian và ledger của attempt cuối. Không có sai lệch so với 176 dòng trial. Đã kiểm tra:

- Hash source benchmark, protocol, task/gold, binary, source/prompt/calendar và dependency package được manifest pin; không drift.
- Cùng native loop OpenTrading, chỉ khác trusted prompt directory giữa baseline và finance. Bốn file prompt thực sự xuất hiện trong request model, không chỉ metadata inventory; tool schema wire của hai biến thể OT giống nhau theo task.
- Cùng instruction và catalog snapshot. Chỉ tool snapshot được đưa lên wire; schema adapter giữa các SDK được lưu nguyên bản, không giả định byte-identical giữa ba harness.
- 707 file capture pilot: raw/canonical SHA-256, danh sách field path, đúng model NVIDIA Bolt E4B, temperature 0, top_p 1 và output cap 2048. Một request bị từ chối trước upstream không có effective capture; trường hợp này được ghi rõ, không tính là gọi upstream thành công.
- Giới hạn thực thi 24 upstream requests, 48.000 token theo chính sách đã đăng ký và timeout 240 giây; retry driver bằng 0. Trial lỗi được giữ nguyên.
- Mốc as-of chung theo snapshot; OT truyền native `now` cố định bằng API. Clock native của OpenCode/DSH không được tuyên bố pin, các request thực được lưu để đối chiếu.
- Mỗi evidence được chấm grounded đều khớp đủ bảy trường với response thành công trong ledger thật và call ID/response hash có trong ngữ cảnh model thực sự nhận. Không nhận error record hoặc placeholder làm bằng chứng tài chính hợp lệ.

## Kết quả tái tính độc lập

| Điều kiện | Primary /44 | Semantic /44 | Schema /44 | DNF /44 | Từ chối oan /40 câu có dữ liệu | FP /4 câu không có dữ liệu | Usage đầy đủ /44 |
|---|---:|---:|---:|---:|---:|---:|---:|
| OT baseline | 12 | 14 | 43 | 1 | 17 | 0 | 43 |
| OT finance | 12 | 14 | 43 | 1 | 15 | 0 | 44 |
| OpenCode | 14 | 15 | 42 | 1 | 14 | 0 | 44 |
| DSH | 18 | 18 | 39 | 5 | 11 | 0 | 42 |

Primary là đúng đủ schema/semantic/provenance, khớp ledger thật, status `ok` và đúng hạn. Semantic tách riêng để không che lỗi hợp đồng/evidence. DNF dùng định nghĩa hoàn thành JSON đúng hạn trong trạng thái chạy thành công; không đồng nghĩa mọi sai đáp án hoặc mọi schema fail đều DNF.

Trên 44 cặp task/run, finance và baseline cùng đúng 11, cùng sai 31; finance thắng một cặp `fin-l1-quote-02` lần 1, thua một cặp `fin-l5-compare-01` lần 1. Finance so với OpenCode: thắng 2/thua 4 cặp; so với DSH: thắng 0/thua 6 cặp. Đây là mô tả cặp của pilot nhỏ, không phải kết luận thống kê thắng cả hai harness.

| Điều kiện | Request có usage / tổng request gateway | Input token đã biết | Output token đã biết | Diễn giải |
|---|---:|---:|---:|---|
| OT baseline | 86/88 | 307.477 | 13.525 | Lower bound; một request upstream thiếu usage và một request bị gateway từ chối trước upstream |
| OT finance | 88/88 | 259.187 | 16.611 | Đầy đủ |
| OpenCode | 88/88 | 151.757 | 17.398 | Đầy đủ |
| DSH | 88/90 | 114.683 | 18.762 | Lower bound; hai request thiếu usage |

Không tính phần usage thiếu là 0, không tuyên bố tổng token chính xác cho baseline/DSH, không dùng token tie-break để quyết định triển khai. Những token đã biết ở trial usage không đầy đủ vẫn được báo cáo từ ledger provider, không bị bỏ mất.

## Evidence không khớp: phân biệt lỗi namespace và bịa placeholder

Finance có hai trial evidence không khớp, baseline không có; cả hai đều thất bại primary và semantic, không được chấp nhận thành bằng chứng đúng:

1. `fin-l1-bctc-01__opentrading_finance__r1`: tool `financial_statements` đã thành công, call ID/hash/source/as-of đều có thật. Đáp án dùng tên SDK `mcp__opentrading__financial_statements` thay namespace raw `financial_statements` trong evidence.tool và source. Đây là lỗi namespace, không phải bịa call ID. Số tài chính còn bị đổi đơn vị sai 1.000 lần: 14,550959 thay vì 14.550,96 tỷ đồng. Xem [grade](../../results/financial-prompt-v3-pilot-20261105/trials/fin-l1-bctc-01__opentrading_finance__r1/grade.json).
2. `fin-l2-crypto-01__opentrading_finance__r1`: crypto_spot thành công và BTC evidence thật; FX request sai kiểu tham số bị từ chối. Model trả null nhưng thêm FX evidence giả `unknown`, timestamp tự điền, call ID/hash `N/A`. Đây là một trường hợp bịa placeholder, không phải response thành công từ FX. Xem [grade](../../results/financial-prompt-v3-pilot-20261105/trials/fin-l2-crypto-01__opentrading_finance__r1/grade.json).

Pilot tổng cộng evidence không khớp: baseline 0, finance 2, OpenCode 5, DSH 4. Không gọi tất cả trường hợp namespace/hash không khớp là cố ý bịa. Các đáp án primary thành công đã được kiểm tra khớp ledger và ngữ cảnh tool thực.

## Guard đăng ký trước và quyết định triển khai

Guard kỹ thuật đăng ký trước **PASS**: primary 12/44 bằng baseline, FP 0/44 bằng baseline, DNF 1/44 bằng baseline, từ chối oan giảm 17/44 xuống 15/44 (giảm 4,55 điểm phần trăm trên cohort khởi chạy). Tỷ lệ có điều kiện trên 40 câu có dữ liệu giảm 42,5% xuống 37,5%. Token tie-break không cần dùng và không đủ coverage để dùng theo quy tắc thận trọng đã chốt.

Root quyết định **`runtime_only`**, giữ prompt finance ở trạng thái thử nghiệm. Đây là quyết định rollout thận trọng sau pilot: primary và semantic chưa tăng, đồng thời finance có một lỗi namespace và một trường hợp evidence placeholder mà baseline không có. Đây không phải đổi endpoint đã đăng ký trước, không phải diễn giải guard thành FAIL, và không phải phép kiểm định xác nhận bổ sung. Không chỉnh lại prompt rồi chạy lại pilot để chọn điểm thuận lợi.

Danh tính nghiên cứu vẫn giữ nguyên: canonical `opentrading` và alias `opentrading_finance` chọn candidate finance trong benchmark đã đóng băng; `opentrading_baseline` chọn prompt baseline. Việc cài `runtime_only` vào repo gốc không đổi manifest hoặc diễn giải lại các trial đã chạy thành prompt mặc định hiện đang cài.

Installer đã áp dụng đúng hai file runtime; mặc định bốn prompt gốc được giữ nguyên. Receipt `experiments/installed-backups/20261105T091212.728355Z/receipt.json` hoàn tất; hai file đích khớp after-hash, hai backup khớp before-hash, bốn prompt vẫn khớp before-hash. Trước cài đặt cả chín payload đều khớp manifest và mọi file đích đều chưa đổi.

Kiểm tra sau cài đặt trong repo OpenTrading gốc: **56 tests pass, 0 fail** trên `test/agent.test.ts` và `test/prompt.test.ts`; `bun run typecheck` exit 0. Dùng HOME tạm sạch, tắt tự nạp `.env`, không truyền API key; tests dùng provider mock, không gọi model. Không nhận nhầm số test của candidate thành số test đã cài. Log: [native tests](postinstall-native-tests.log), [typecheck](postinstall-typecheck.log). Kiểm tra receipt, backup và hash chi tiết nằm trong `independent-evidence.json`.

Kiểm tra độc lập metric “sau rejection có MCP thành công”: đúng bốn trial ở mỗi điều kiện, bằng điều kiện thời gian `rejected.ended_at < ok.started_at`. Các trial là `fin-l4-2nguon-01` và `fin-l5-profile-01`, mỗi câu hai lần. Metric này không tự chứng minh request sai đã được sửa hoặc đáp án cuối đúng; không đếm sáu trial chỉ vì có cả reject và success bất kể thứ tự.

Giới hạn: chỉ 22 câu, hai lần chạy, một model NVIDIA nhỏ; không đo stable-correct 3/3, không chứng minh thắng OpenCode/DSH, không suy rộng sang Go/DeepSeek effort medium chưa thử. Gold đo tương quan với snapshot; kiểm tra này không chứng nhận số liệu từ báo cáo tài chính gốc ngoài snapshot.
