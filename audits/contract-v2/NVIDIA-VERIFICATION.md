# Xác minh benchmark v2 bằng NVIDIA

Trạng thái ngày 05/11/2026 (Asia/Bangkok): **offline đạt, smoke cuối hoàn tất và certificate
vận hành, freeze và kiểm tra resume đều đạt**. Smoke không đủ
để xếp hạng chất lượng các harness.

## Phạm vi đã sửa và kiểm tra

Ba arm OpenTrading, OpenCode và DeepSeek Harness dùng cùng NVIDIA model nhỏ
`nvidia/nemotron-3.5-bolt-e4b`, qua cùng gateway, với `effort=none`, cùng snapshot,
ngân sách và hợp đồng JSON/evidence. Tên cấu hình có thêm tiền tố provider:
`nvidia/nvidia/nemotron-3.5-bolt-e4b`. Đây là kiểm tra vận hành native harness;
không dùng vòng lặp agent mô phỏng để thay thế harness.

Key NVIDIA được giữ ở gateway cha; runner dùng credential tạm. Profile/session/workspace
riêng từng attempt và allowlist tool kiểm tra cả schema thực gửi provider. Ledger MCP
và provider là bằng chứng cho số call, grounding và usage. Đây là cách ly cấu hình/tool,
không phải sandbox OS chống mọi tiến trình thù địch.

Regression cuối: **243 tests đạt**, cùng **4/4 offline readiness checks đạt**.
Trong đó bộ grader/snapshot/independent có **143 tests**, gồm 45 phép tính tài chính
được đối chiếu độc lập từ payload. [Audit cuối](final-grader-acceptance/audit-evidence.json)
đạt 227/227 fixture, 227/227 oracle, chặn toàn bộ mutation/empty/period/source/refusal/
unknown-symbol probes; không phát hiện leakage hay sai lệch numerical expectation.
Xem [chi tiết contract](IMPLEMENTATION.md) và [xác minh độc lập](INDEPENDENT-VERIFICATION.md).

Toàn bộ 277 payload tài chính được giữ nguyên. Mechanical refresh lần hai không đổi
byte nào trong 1.699 file task. Bộ chạy mặc định gồm **178 main, 43 holdout, 22 pilot,
3 smoke**; 31 câu chỉ dùng chẩn đoán gồm 19 CPI thiếu chiều định danh chuỗi và
12 narrative có rubric evidence chưa kiểm tra đủ nội dung được hỏi.

## Phân biệt lượt lịch sử và lượt xác nhận cuối

| Lượt | Artifact | Trạng thái |
|---|---|---|
| A, lịch sử | [v2-nvidia-smoke-20261104](../../results/v2-nvidia-smoke-20261104/manifest.json) | 18 trial; primary 7/18 theo grader thời điểm đó. Phát hiện false negative với câu từ chối đúng dạng `không được tìm thấy`; không tái gắn kết quả cũ thành xác nhận của code hiện tại. |
| B, code/task đóng băng sau sửa | [v2-nvidia-smoke-final-20261105](../../results/v2-nvidia-smoke-final-20261105/manifest.json) | Hoàn tất 18/18 trial native, status `ok`, usage coverage 100%; primary grounded đúng 10/18. Certificate `operational_parity_v3` đạt. |

Sửa refusal áp dụng chung cho dạng bị động của availability predicates, không hardcode
mã chứng khoán/câu trả lời. Các regression vẫn chặn phủ định kép, khẳng định mâu thuẫn,
giá trị khác JSON null và evidence không hợp lệ. Mọi trial B dùng code mới từ đầu;
không sửa số đo lịch sử A.

Lượt B chạy từ **09:44:33 đến 09:52:05 ngày 05/11/2026, Asia/Bangkok**
(02:44:33–02:52:05 UTC). Có 35 request provider, tất cả HTTP 200 trên model Bolt;
usage được ghi nhận là **73.498 input token và 10.632 output token**. Ledger MCP
có 37 call: 10 thành công và 27 bị snapshot từ chối. Các rejection được giữ trong
kết quả để phản ánh lựa chọn tham số của model, không sửa thành call thành công.

| Arm | Trial hoàn tất | Primary grounded đúng |
|---|---:|---:|
| OpenTrading | 6/6 | 2/6 |
| OpenCode | 6/6 | 4/6 |
| DeepSeek Harness | 6/6 | 4/6 |

Cả sáu đáp án smoke trap đều đúng sau sửa generic refusal. Các lỗi còn lại được
giữ nguyên, gồm lỗi ở task aggregation; không tinh chỉnh câu hỏi/grader để nâng
điểm của model nhỏ. Ba câu × hai lần lặp chỉ xác minh pipeline và phơi bày lỗi
chất lượng, không cung cấp căn cứ thống kê để kết luận arm nào thắng.

[Certificate hiện tại](../../results/v2-nvidia-ready-20261105.json) xác nhận
18 trial, hai run, protocol `operational_parity_v3`, scope
`snapshot_grounded_financial_qa`; ghi rõ 8 model-quality failures và 27 snapshot
rejections. Trước khi cấp certificate, full suite được chạy lại và **243 tests đạt
trong 45,59 giây**, cùng 4/4 offline checks và kiểm tra artifact live thực tế.
[Freeze receipt](../../results/v2-nvidia-freeze-20261105.json) được tạo thành công,
state hash `9b05b08eb0ac48ef53c3cc9ebcc3f1690f7bb3795ade816bb8d0fafd3f53b920`.
Sau đó chạy đúng lệnh B kèm `--resume` trả exit 0. So sánh SHA256 trước/sau của
18 file `provider.jsonl` và `trials.jsonl` cho thấy **19/19 file giữ nguyên**:
vẫn 18 trial và 35 provider request, **0 request mới, 0 trial trùng**.
[Bằng chứng tổng hợp](final-runtime-verification.json) ghi nhận kiểm tra này,
hash file manifest/certificate/freeze và hash ledger sau resume.

## Lệnh tái lập

Chạy từ thư mục repository, với key NVIDIA có sẵn trong môi trường:

```bash
python3 -m pytest tools/tests -q
python3 tools/ready_check.py

python3 tools/run_benchmark.py --split smoke --arms all --runs 2 \
  --out results/v2-nvidia-smoke-final-20261105 --retry 0 --pause 2 \
  --timeout 240 --effort none --max-requests 24 \
  --max-output-tokens 2048 --max-total-tokens 48000

python3 tools/analyze.py results/v2-nvidia-smoke-final-20261105 --json

python3 tools/ready_check.py --config tools/bench_config.json \
  --live-run results/v2-nvidia-smoke-final-20261105 \
  --certificate results/v2-nvidia-ready-20261105.json

python3 tools/run_manifest.py --config tools/bench_config.json \
  --certificate results/v2-nvidia-ready-20261105.json \
  --output results/v2-nvidia-freeze-20261105.json

python3 tools/run_benchmark.py --split smoke --arms all --runs 2 \
  --out results/v2-nvidia-smoke-final-20261105 --retry 0 --pause 2 \
  --timeout 240 --effort none --max-requests 24 \
  --max-output-tokens 2048 --max-total-tokens 48000 --resume
```

Một thư mục run là bất biến: nếu chạy lại từ đầu, dùng tên output mới. Để kiểm tra
resume, giữ nguyên toàn bộ tùy chọn của đúng run và thêm `--resume`. Driver phải
bỏ qua trial đã hoàn tất, không thêm request provider hoặc dòng trial trùng.

Certificate và freeze dùng file mới, không ghi đè receipt hiện có. Xem thêm
[README](../../README.md#pilot-freeze-và-mainholdout). Certificate protocol
`operational_parity_v3` kiểm tra artifact thật, model/catalog/config/hash,
thời hạn, usage và ledger; mỗi arm phải có canary tool thành công và ít nhất
một đáp án primary grounded đúng. Không bắt mọi đáp án model nhỏ đều đúng để
đánh tráo lỗi chất lượng thành lỗi hạ tầng. Ngược lại, điểm primary cao không tự
thay thế kiểm tra vận hành. Chỉ khi certificate/freeze thành công mới gọi main/holdout.

## Giới hạn và kế hoạch một tuần

Chưa chạy model holdout, chưa mua hoặc xác minh OpenCode Go/DeepSeek medium.
Adapter hiện tại chặn route/effort chưa hỗ trợ; smoke model nhỏ không suy ra chất lượng,
latency hay quota của model dự định mua. Chi phí USD chưa có bảng giá được xác minh
được báo **N/A**; token usage, subscription allowance và số tiền thực trả là các đại lượng khác nhau.

Phạm vi là **snapshot-grounded financial QA**. Không chứng nhận báo cáo gốc, khả năng
dự báo hay hiệu quả đầu tư. Holdout lịch sử có 27 payload trùng main; đây là câu hỏi
mới trên dữ liệu một phần đã dùng, không phải unseen-document generalization sạch.
Quarantine và sensitivity theo payload giúp minh bạch, không xóa giới hạn đó.

Với tập đủ điều kiện hiện tại, main + holdout ba lần cho ba arm là
`(178 + 43) × 3 × 3 = 1.989 trial`, chưa tính pilot, smoke, recovery và quota.
Quyết định chạy hết trong một tuần cần pilot có lặp trên task đại diện để đo p90,
completion, request/token và lỗi provider; không ngoại suy 3 câu smoke sang cả bộ đề.
Nếu cần subset, chốt ID/seed/phân tầng và lịch holdout trước main theo
[PRE-REGISTER](../../PRE-REGISTER.md).
