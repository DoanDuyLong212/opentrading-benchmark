# Kiểm tra giữa chừng số 1 — đúng 38 trial đầu

Ngày 05/11/2026. Đây là một lần kiểm tra có giới hạn theo yêu cầu người dùng; không đổi prompt, runtime, dữ liệu, grader, lịch chạy hoặc gọi thêm model. Snapshot cố định: [interim-first38.json](interim-first38.json). Nguồn là 38 dòng đầu đã được lưu của `results/financial-prompt-v3-pilot-20261105/trials.jsonl`; hash của đúng prefix được lưu cùng snapshot.

| Điều kiện | Trial đã lưu | Primary đúng | Schema hợp lệ | DNF | Usage đầy đủ |
|---|---:|---:|---:|---:|---:|
| OpenTrading baseline | 10 | 2/10 | 10/10 | 0/10 | 10/10 |
| OpenTrading finance | 9 | 2/9 | 9/9 | 0/9 | 9/9 |
| OpenCode | 10 | 2/10 | 9/10 | 1/10 | 10/10 |
| DeepSeek Harness | 9 | 4/9 | 7/9 | 2/9 | 8/9 |

Prefix chưa cân bằng giữa các điều kiện và chưa đủ cặp task/run; các tỷ lệ trên không phải ước lượng tác dụng prompt hoặc kết luận harness nào thắng. Pilot đăng ký trước phải đủ 176 trial, tức 44 trial mỗi điều kiện, mới áp dụng guard triển khai.

Schema hợp lệ chỉ cho biết đáp án qua kiểm tra cấu trúc, không bảo đảm tài chính đúng hoặc evidence đầy đủ. Primary đòi hỏi đúng gold, đúng hợp đồng, evidence khớp ledger thật, trạng thái chạy thành công và trong thời gian. DNF tính khi không có đáp án cuối được phân tích thành JSON trong trạng thái `ok`, đúng hạn; vì vậy OpenCode có một trial `status=ok` nhưng JSON lỗi vẫn là DNF. Không gộp sai đáp án đã hoàn thành vào DNF.

Trong 28 trial chưa đạt primary, ưu tiên lỗi thực thi trước lỗi đáp án cho phân loại loại trừ nhau:

- 16 lỗi số/thiếu số (`sai_so`): 8 đáp án có null/từ chối rõ ràng, 8 có số hoặc cấu trúc số chưa đúng/đủ. Không coi toàn bộ 16 là sai phép tính.
- 5 lỗi kỳ (`sai_ky`).
- 4 lỗi kết luận (`sai_ket_qua`).
- 2 lỗi thực thi của DSH: `fin-l2-growth-01__dsh__r1` có upstream request thứ hai timeout, gateway 502 và usage không đầy đủ; `fin-l3-tech-multi-01__dsh__r1` kết thúc `max-tokens` tại 2048 output tokens, JSON bị cắt và native process exit 1.
- 1 JSON cuối không hợp lệ của OpenCode ở `fin-l3-crypto-01__opencode__r1`.

Lỗi timeout được giữ nguyên trong mẫu; phần usage thiếu là chưa biết, không được quy thành 0 hoặc tiết kiệm token. Không sửa hoặc chạy lại những trial này để cải thiện kết quả. Sau snapshot này chờ toàn bộ pilot hoàn tất rồi thực hiện một lượt review tổng hợp, re-grade độc lập, kiểm tra source/capture và áp dụng guard đã đăng ký trước. Không chỉnh candidate theo kết quả giữa chừng.
