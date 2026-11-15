@FinDaHuman: review chuỗi PR #260–#267 và kết quả đo lại tầng compute trên `main` sau khi bỏ `calculate`/`compute`.

## TL;DR
- Đã chạy lại **60 trial compute** (30 task × 2 lượt) của benchmark v4.6u trên `main` @ `6ae8db9`, cùng model `deepseek/deepseek-v4.1-flash-1017` (OpenRouter trả phí), cùng cài đặt và cùng luật chấm như or16.
- **Primary: 49/60, so với 53/60 ở or16** (runtime `38f8adb`). Chênh −6,7 điểm %, CI95 [−21,7; +6,7], **chưa có ý nghĩa thống kê**.
- **C3 tụt rõ: 16/16 xuống 10/16.** Một trong các ca fail là lỗi hạ tầng (provider trả 502 "Network connection lost" ở request đầu, `fin-c3-rschain-423` r1); bỏ ca này khỏi mẫu số thì C3 là 10/15.
- Số request và token giảm mạnh đúng như kỳ vọng của #263. Đổi lại, **56% lệnh shell bị cổng quyền từ chối** và **35% câu trả lời phải "tự tính"**, tức là tính nhẩm.
- Cơ chế (bảng bên dưới): grammar "chỉ-toán" quá hẹp so với cách model thật viết lệnh. Lệnh rơi vào cổng duyệt và nhận câu "đừng… lệnh viết lại". Model chuyển sang tính nhẩm trong reasoning, rồi chạm trần 8.192 output token, đúng kiểu DNF của DSH trong or16.
- **Cổng merge mà chính #263 đặt ra ("chạy eval bằng key thật trước khi merge cả 3 PR") chưa được thực hiện.** #260–#263 được merge trong khoảng 30 giây, không có review và không có số đo nào.

## Kết quả (OT `opentrading_baseline`, tầng compute)

| | or16 (`38f8adb`, calculate/compute) | `main` `6ae8db9` (shell) |
|---|---:|---:|
| **Primary** /60 | **53** | **49** |
| C1 / C2 / C3 / C4 | 15/16 · 15/16 · **16/16** · 7/12 | 16/16 · 16/16 · **10/16** · 7/12 |
| Strict (grader cũ) | 53 | 45 |
| DNF | 1 | 3 |
| Request/trial (TB / max) | 7,35 / 25 | **3,75 / 12** |
| Loop-guard chặn | 30 lần ở 15 trial | **0** |
| Input token/trial (TB) | 238k | **76k (−68%)** |
| Chi phí 60 trial | $0,61 | $0,52 (−14%) |
| Thời gian p50 / p90 | 26,9 s / 84,9 s | 26,2 s / 94,5 s |

- Task tốt hơn: `fin-c1-chg-402`, `fin-c2-ma-409`, `fin-c4-stagger-425`, `fin-c4-stagger-430`. Đây đúng là nhóm từng bị loop `calculate` hoặc DSML.
- Task kém hơn: `fin-c3-maladder-419`, `fin-c3-rschain-423`, `fin-c3-volregime-420`, `fin-c3-volshare-421`, `fin-c4-signal-429`. Đây là các task cần nhiều bước tính: lợi suất log, độ biến động, chuỗi RS.
- Lưu ý khi đọc mức giảm request/token: một phần đến từ chính lỗi. Sau khi bị từ chối, model ngừng gọi tool và suy luận bằng text, nên p90 tăng từ 84,9 s lên 94,5 s. Không nên coi −68% token là lợi thuần.

### Shell chạy được hay không quyết định kết quả

| Trial | Primary đúng | Có output chạm trần 8.192 token |
|---|---:|---:|
| Có ít nhất 1 lệnh tính chạy được (25) | **24/25** | 1 |
| Mọi lệnh shell đều bị từ chối (34) | **25/34** | 11 |
| Không gọi shell (1, lỗi 502 hạ tầng) | 0/1 | 0 |

- Trong 10 trial fail không do hạ tầng, 9 trial có **toàn bộ** lệnh shell bị từ chối. 8 trong số đó có từ 1 tới 4 request output đúng 8.192 token: tính nhẩm và bị cắt.
- Ví dụ `fin-c3-volregime-420` r2: output theo request là 557, 5909, 3939, 8192, 8192, 8192, 8192.

### Hành vi `shell` (các số #263 đặt làm cổng merge)

| Chỉ số | Giá trị |
|---|---|
| Lệnh `shell` | 87 |
| Chạy được (chỉ-toán) | **36 (41%)**, toàn bộ là dạng `awk 'BEGIN{printf …}'` một dòng |
| Bị cổng quyền từ chối ("cần người dùng xác nhận… Đừng làm đúng việc này bằng… lệnh viết lại") | **49 (56%)** |
| Lỗi tham số JSON | 2 |
| Nhận gợi ý near-miss (`mathNearMiss`) | **0** |
| Trial có ít nhất 1 lệnh tính chạy được | 25/60 |
| Câu trả lời ghi "tự tính" (tính nhẩm) | **21/60 (35%)** |
| Câu trả lời cuối là DSML text | 1/60 (thêm 1 ca ở lượt chạy thử) |
| Thời gian mỗi lệnh / số trong lệnh truy được về tool | chưa đo |

Phân loại 51 lệnh bị từ chối:

| Dạng lệnh | Số lệnh |
|---|---:|
| `python3 -c` nhiều dòng hoặc heredoc `cat > /tmp/calc.py << 'EOF'` | 17 |
| `awk` có biến (`awk 'BEGIN{k=250/119; a=log(x)*k; printf …}'`) | 14 |
| `awk` nhiều dòng | 12 |
| `awk` một dòng nhưng vượt `MATH_MAX_CHARS` = 500 (843–5.142 ký tự: cộng 20+ phiên volume) | 5 |
| `awk` một dòng có `\n` giữa format (`"%.0f\n%.0f\n…\n"`) | 3 |

Ví dụ một lệnh bị từ chối:

```
awk 'BEGIN{
k=250/119;
stb=log(66.3/73.5)*k; mwg=log(74.0/81.33)*k; ...
```

## Vì sao chạm trần 8.192 token output

- **Trần đến từ protocol của benchmark v4.6u, không đến từ OT.** Protocol đăng ký *"Max output 8192 tokens"* cho mỗi request (không phải cho cả trial; một trial được tới 24 request và 3,6M token). Gateway chung ép `max_tokens = min(harness yêu cầu, 8192)`.
- **Request gốc của từng harness, trước khi qua gateway:**

  | Harness | `max_tokens` harness tự gửi | Sau gateway |
  |---|---|---|
  | DSH | **8192** (mặc định của DSH) | 8192 |
  | OpenCode | **8192** (mặc định của OpenCode) | 8192 |
  | OpenTrading | không gửi | 8192 (benchmark áp) |

  DSH và OpenCode chạy ngoài benchmark vẫn bị cắt ở 8.192. Riêng OT khi chạy thật dùng mặc định của provider.
- **Vì sao chạm trần:** DeepSeek V4.1 Flash vẫn suy nghĩ dù benchmark yêu cầu `effort: none`, và reasoning được tính vào output. Không có tool tính toán thì model khai triển `ln`/`exp`/luỹ thừa bằng tay trong reasoning, nên 8.192 token hết rất nhanh. Ví dụ ở trial DSH `fin-c4-stagger-425` r1 (or16), 8.192/8.192 token đều là reasoning, và bị cắt giữa phép `exp(...)`.
- **Khi chạm trần, mỗi harness xử lý khác nhau, và đó là chỗ tạo ra DNF:**
  - OpenCode gửi request tiếp, nên chạm trần 18 lần ở or16 mà không DNF.
  - DSH kết thúc lượt (`turn_end: max-tokens`), nên có 17 DNF ở or16, toàn ở tầng compute.
  - OT `main`: stop-gate nhắc trả lời tiếp, tối đa 2 lần. Model lại tính nhẩm và lại bị cắt, hết lượt nhắc thì bỏ cuộc hoặc trả lời sai.
- **Ý nghĩa với chuỗi PR:** trần là chung cho mọi arm. Thứ quyết định là harness có cho model một cách tính **không tốn reasoning** hay không. OT bản `38f8adb` có `calculate`: 0 lần chạm trần và 53/60. OT `main` có `shell`, nhưng 56% lệnh bị từ chối nên model quay lại tính nhẩm: 11/34 trial bị từ chối hết lệnh có chạm trần. Vì vậy sửa grammar ở lỗi 1 chính là sửa nguyên nhân DNF.
- Muốn đo OT khi không có trần này (ví dụ 32k) thì cần đăng ký protocol mới, và kết quả sẽ không so trực tiếp được với or16.

## Lỗi tìm thấy

**1. `math.ts`: grammar hẹp, và lệnh trượt grammar bị đưa sang cổng duyệt thay vì nhận gợi ý (#261/#262/#263).**
- `mathNearMiss` chỉ bắt `python -c "print(…)"` một dòng, `echo $((…))`, `bc`, `expr` và `awk 'BEGIN{print …}'`.
- Ba dạng model viết nhiều nhất đều không được nhận và cũng không có gợi ý: awk có biến, awk nhiều dòng, script Python. Lệnh đi thẳng tới cổng, ở headless nhận câu "Đừng… lệnh viết lại", và model chuyển sang tính nhẩm.
- Đây chính là vòng lặp mà mô tả #261 muốn tránh.
- Repro offline với `mathOnlyCommand`/`mathNearMiss` trên bash: `awk 'BEGIN { printf("%.2f\n", 1/3) }'` và `awk 'BEGIN{x=5; printf "%.2f\n", x*2}'` đều trả `ASK`, không `RUN` và không `NEAR`.
- Hai giới hạn nữa chặn cả lệnh một dòng hợp lệ:
  - `MATH_MAX_CHARS = 500` quá ngắn cho task volume/MA, vì model cộng 20–60 số liệu trong một biểu thức;
  - `FORMAT` chỉ nhận `\n` ở cuối, nên `"%.0f\n%.0f\n"` bị loại.
- Không chỉ benchmark bị ảnh hưởng. Ở TUI chế độ ‖/▸, cùng các lệnh này sẽ hiện **hộp duyệt cho một phép tính**, đúng UX mà #261 muốn bỏ.
- Đề xuất, chọn một hoặc cả hai:
  - (a) Mở rộng grammar awk:
    - cho phép gán biến đơn giản `ident = expr;`, xuống dòng giữa các câu lệnh trong `BEGIN{}`, và `printf(...)`;
    - nhận `\n` ở giữa format;
    - nâng giới hạn ký tự lên khoảng 8k;
    - vẫn cấm `system`, `getline`, redirect, pipe và nháy đơn.
  - (b) Coi mọi `awk 'BEGIN…'` hoặc `python -c` có nội dung toàn số/biến là near-miss, để trả lỗi tool kèm dạng đúng thay vì đưa vào cổng.

**2. `markup.ts` (#264) không lọc định dạng tool call của DeepSeek.**

```ts
stripMarkup('Kết quả:\n<｜DSML｜function_calls>\n<｜DSML｜invoke name="calculate">\n<｜DSML｜parameter name="expression" string="true">1+2</｜DSML｜parameter>\n</｜DSML｜invoke>\n</｜DSML｜function_calls>')
// → tags: [] (không lọc gì)
```

- Trong or16, đây là nguyên nhân của 2 trial OT fail (`fin-c1-chg-402` r2, `fin-c4-rebal-426` r2).
- Lượt đo này gặp lại: câu trả lời cuối là `<｜DSML｜ invoke name="shell"> python3 -c …` dạng text.
- Đề xuất: nhận tiền tố `｜DSML｜` (ký tự `｜` U+FF5C) trước tên tag trong `CALL_TAGS`.

**3. Quy trình.**
- #263 tự ghi cổng merge "chạy eval bằng key thật… trước khi merge cả 3 PR", nhưng #260–#263 được merge ngày 13/11 lúc 15:27–15:28 mà không có số đo, review hay comment nào.
- Số liệu trong #261/#263 đúng phần lớn. Trong bộ main gộp cuối (đã thay các slot rerun), loop-guard chặn 30 lần ở 15 trial; các trial đó trung bình 12,6 request so với 3,8.
- Nhưng trong 6 trial fail thuộc nhóm đó, **chỉ 3 trial do `calculate`**: 1 trial vượt trần request và 2 trial in tool call dạng DSML text. 3 trial còn lại sai dấu hoặc sai nghĩa trường, không liên quan tới tool tính.

## Review từng PR

| PR | Đánh giá |
|---|---|
| #260 deps | ✅ Tốt. Vá 25 advisory, CI xanh trên 3 OS. |
| #261 shell math | ✅ An toàn: parser thật, chặn `system()`, redirect, `;`, pipe, biến PowerShell (đã thử). ⚠️ Grammar quá hẹp, xem lỗi 1. |
| #262 subagent shell | ✅ Thiết kế `readOnlyVariant` gọn. Chưa chạy model thật. |
| #263 bỏ calculate/compute | ⚠️ Giảm token và request đúng như kỳ vọng. Primary −4/60, C3 tụt. Merge khi chưa qua cổng eval của chính nó. |
| #264 markup | ✅ Hữu ích. Thiếu DSML, xem lỗi 2. |
| #265 gap rescue | ✅ Tốt, đã chạy lại bằng key thật. |
| #266 promise offer | ✅ Nên merge. |
| #267 no repair claim | ✅ Nên merge sau #266. |
| #259 safeguard proposal | 📄 Chỉ là docs. Kết quả 32/36 → 35/36 chưa đủ để kết luận, đúng như tác giả ghi. |

## Đề xuất
1. Sửa lỗi 1 (grammar/near-miss) và lỗi 2 (DSML), rồi chạy lại 60 trial compute này. Chi phí khoảng $0,5.
2. Đo thêm thời gian mỗi lệnh và tỷ lệ số trong lệnh truy được về tool, để đủ 6 số cổng merge.
3. Áp dụng cổng eval cho các PR đổi hành vi tool: ghi số đo vào PR trước khi merge.

## Phạm vi và giới hạn
- **Chẩn đoán, không phải kết quả confirmatory.** Không seal. Chạy trong một sandbox tách khỏi bộ benchmark đã đóng băng.
- Cài đặt giữ nguyên or16: temperature 0, 24 request, 8.192 output token, timeout 900 s, retry 0, 2 lượt.
- Thay đổi riêng của sandbox:
  - runner cho OT dùng `shell` + `read_result` thay cho `calculate`/`compute`/`read_result`;
  - prompt baseline lấy đúng 2 dòng mới của `main` (`tools.md` dòng tính bằng shell, `identity.md` dòng #264);
  - headless có cổng quyền như OT thật, nên lệnh không phải phép tính bị từ chối như ở `ot -p`/eval.
- `main` @ `6ae8db9` còn gồm #254–#257 (routing, headers, memory tabs, stop-gate figures), nên chênh lệch không chỉ do #261–#263.
- Máy chạy là Linux nên dạng tính là `awk`. Dạng PowerShell mà tác giả PR đã thử chưa được đo bằng model thật.
- Judge: Nemotron Ultra qua NVIDIA NIM, cùng prompt và cùng luật primary (judge correct ∧ numeric gate ∧ không FP/FR).
  - Con số 53 của or16 đã qua review thủ công (review chỉ được loại, đã loại 1 ca compute).
  - Con số 49 của lượt này **chưa qua review**. Review chỉ có thể làm 49 giảm thêm.
- n = 60 trên một model: chênh ±3 trial nằm trong mức nhiễu.

