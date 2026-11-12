# BÁO CÁO TOÀN DIỆN VỀ KẾT QUẢ BENCHMARK SMOKE & PILOT
## ĐIỀU TRA NGUYÊN NHÂN OPENTRADING (OT) HOẠT ĐỘNG KÉM HIỆU QUẢ HƠN OPENCODE VÀ DSH TRONG LĨNH VỰC TÀI CHÍNH

**Ngày thực hiện:** 05/11/2026  
**Phạm vi điều tra:** Toàn bộ session codex, logs và kết quả từ các harness benchmark (`smoke-final`, `v2-nvidia-smoke-final-20261105`, `financial-prompt-v3-smoke-20261105`, `financial-prompt-v3-pilot-20261105`), mã nguồn thực thi của OpenTrading (`/home/doanlong/OpenTrading/src`), mã nguồn wrapper benchmark (`tools/runners/ot_headless.ts`), và các tài liệu audit tương ứng.

---

### I. TỔNG QUAN KẾT QUẢ BENCHMARK (SMOKE & PILOT)

Sau khi trích xuất và phân tích toàn bộ dữ liệu từ hơn 194 trials (305 lượt gọi MCP), số liệu thống kê thực tế giữa ba hệ thống (OpenTrading, OpenCode, DSH) như sau:

#### 1. Bộ chạy Smoke (Kiểm tra cơ bản & bài test bẫy)
* **`smoke-final` (3 task chuẩn L1-L4):**
  * **DSH:** 3/3 (100%)
  * **OpenCode:** 3/3 (100%)
  * **OpenTrading:** 3/3 (100%)
* **`v2-nvidia-smoke-final-20261105` & `financial-prompt-v3-smoke` (nhiệm vụ có bẫy schema & replay restriction):**
  * **DSH:** 4/6 (66.7%) — lỗi `sai_so`: 2
  * **OpenCode:** 4/6 (66.7%) — lỗi `sai_so`: 2
  * **OpenTrading:** 2/6 (33.3% - 40.0%) — lỗi `sai_so`: 3 đến 4

#### 2. Bộ chạy Pilot diện rộng (`financial-prompt-v3-pilot-20261105` - 168 trials, 22 tasks × 2 runs)
| Harness | Tỷ lệ Pass | Tỷ lệ Thành công | Phân rã lỗi chi tiết |
| :--- | :---: | :---: | :--- |
| **DSH** | **18/39** | **46.2%** | Sai số (14), Sai kỳ (3), Sai nguồn (2), Sai kết quả (2) |
| **OpenCode** | **14/43** | **32.6%** | Sai số (19), Sai kỳ (4), Sai nguồn (3), Sai kết quả (2), Không trả lời (1) |
| **OpenTrading (Baseline Prompt)** | **12/43** | **27.9%** | Sai số (22), Sai kỳ (4), Thiếu bằng chứng/evidence (2), Sai kết quả (2), Sai nguồn (1) |
| **OpenTrading (Finance Prompt)** | **12/43** | **27.9%** | Sai số (20), Sai kỳ (4), Sai nguồn (3), Thiếu bằng chứng (2), Sai kết quả (2) |

> 📌 **Nghịch lý trọng tâm:** OpenTrading là harness được định vị chuyên biệt cho phân tích và đầu tư tài chính, nhưng lại đạt tỷ lệ vượt qua thấp nhất trong cả 3 hệ thống (27.9% so với 32.6% của OpenCode và 46.2% của DSH). Thậm chí khi chuyển sang biến thể prompt tài chính mới (`opentrading_finance`), kết quả vẫn không cải thiện (cùng đạt 12/43 pass).

---

### II. BẢN ĐỒ CHI TIẾT TỪNG NHIỆM VỤ THẤP ĐIỂM (PILOT MATRIX)

Kết quả đối soát trên từng bài toán tài chính trong bộ pilot:

| Task ID | Nội dung bài toán tài chính | DSH | OpenCode | OT Baseline | OT Finance | Nguyên nhân OpenTrading thất bại |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `fin-l1-quote-01` | Giá đóng cửa HPG phiên gần nhất | **2/2** | **2/2** | 0/2 | 0/2 | **Retrieval Loss:** Truyền sai kiểu `columns: "close"` (scalar thay vì list), server báo lỗi nhưng OT không sửa mà kết luận sai là "không có dữ liệu"; Run 2 Baseline tìm được số đúng 21.0 nghìn đồng nhưng thiếu mảng `evidence`. |
| `fin-l1-quote-02` | Giá đóng cửa VNM phiên gần nhất | **2/2** | **2/2** | 1/2 | **2/2** | OT Baseline bị lỡ 1 lần do lỗi format; OT Finance đạt chuẩn. |
| `fin-l1-bctc-01` | Lợi nhuận sau thuế VCB theo BCTC | 1/2 | 0/2 | 0/2 | 0/2 | **Post-retrieval Loss:** Lấy được đúng số `14.550.959.000.000 VND` nhưng chia sai đơn vị (trả lời `14,550959 tỷ` thay vì `14.550,96 tỷ`). |
| `fin-l1-gold-01` | Giá vàng SJC | 1/2 | 0/2 | 0/2 | 0/2 | Sai số trong quá trình trích xuất chỉ số vàng. |
| `fin-l2-growth-01` | Tăng trưởng doanh thu thuần VNM | 0/1 | 0/2 | 0/2 | 0/2 | **Post-retrieval Loss:** Dữ liệu có đủ từ Q4/2025 đến Q3/2026. OT chọn nhầm số liệu Q2/Q1 (-5.63%) thay vì kỳ gần nhất Q3/Q2 (-2.03%). Trường `note` giải thích đúng Q3/Q2 nhưng trường `value` giữ nguyên số sai. |
| `fin-l2-tech-01` | Chỉ báo kỹ thuật RSI SSI | 0/2 | 0/2 | 0/2 | 0/2 | **Semantic Misalignment:** Tính đúng giá trị RSI nhưng gán `period: "1D"` (nhầm chu kỳ interval với ngày phiên giao dịch). |
| `fin-l3-tech-multi-01`| RSI đa khung thời gian | 0/1 | 0/2 | 0/2 | 0/2 | Tương tự lỗi trên, nhầm độ hạt nến thành ngày quan sát (`sai_ky`). |
| `fin-l5-compare-01` | So sánh định giá nhóm cổ phiếu | **2/2** | **2/2** | 1/2 | 0/2 | **Provenance Failure:** Tính toán đúng toàn bộ 15 chỉ tiêu và xếp hạng chính xác, nhưng trường `source` bị thêm tiền tố SDK (`mcp__opentrading__peer_compare`) hoặc bỏ quên `evidence`. |
| `fin-l5-valuation-01` | Định giá cơ bản cổ phiếu | **2/2** | 1/2 | **2/2** | **2/2** | Cả hai biến thể OT đều pass tốt. |

---

### III. NGUYÊN NHÂN CỐT LÕI KHIẾN OPENTRADING KÉM HIỆU QUẢ HƠN

Điều tra sâu vào log tương tác tool/model (`run.log`, `provider-requests`, `native.json`), kiến trúc agent (`OT native loop`), schema xử lý MCP và logic chấm điểm chỉ ra **4 nhóm nguyên nhân chính**:

#### 1. Lỗi gọi MCP Tool: Sai kiểu tham số (Argument Schema Invalidation) & Không tự phục hồi (Zero Self-Repair)
* **Thống kê lỗi gọi tool ở Pilot:**
  * **OpenCode:** 0/66 cuộc gọi sai JSON Schema.
  * **DSH:** 0/66 cuộc gọi sai JSON Schema.
  * **OpenTrading Baseline:** **12/65** cuộc gọi sai JSON Schema (18.5%).
  * **OpenTrading Finance:** **4/66** cuộc gọi sai JSON Schema.
* **Chi tiết cơ chế lỗi:**
  * Khi cần lấy giá HPG (`fin-l1-quote-01`), OT truyền: `{"columns": "close", "days": 1, "symbol": "HPG"}`. Trong khi schema Pydantic của server chỉ chấp nhận `columns` dạng danh sách mảng `list[str]`, không chấp nhận scalar string `"close"`.
  * MCP server trả về lỗi hướng dẫn rất rõ ràng:
    ```json
    {
      "error": {
        "code": "invalid_request",
        "message": "invalid request arguments: 'close' is not valid under any of the given schemas",
        "retryable_with_corrected_arguments": true,
        "snapshot_requests": [{"symbol": "HPG"}],
        "guidance": "Correct the request using the schema and snapshot_requests. A rejected request does not establish missing financial data."
      },
      "request_rejected": true
    }
    ```
  * **Khuyết tật chết người ở Native Loop của OT:** Khi nhận lỗi này, Native Agent Loop của OT không có cơ chế sửa tham số (argument repair). Model lập tức bỏ cuộc và kết luận:
    > *"Không tìm thấy dữ liệu giá đóng cửa cho HPG trong phạm vi truy xuất... Dữ liệu không tồn tại"* $\rightarrow$ trả về `{"value": null}`.
  * Trong khi đó, OpenCode và DSH ngay từ bước 1 đã gọi đúng tham số tối giản `{"symbol": "HPG"}` và nhận dữ liệu chính xác.
  * Toàn bộ 168 trials pilot cho thấy: **Tỷ lệ sửa thành công cùng một tool sau khi bị từ chối của OT là 0%**.

#### 2. Lỗi Hậu Xử Lý (Post-Retrieval Failure): Toán học, Chuyển đổi đơn vị và Chọn sai kỳ báo cáo
Trong 3/6 cặp bài toán OT thua DSH, OT đã lấy được dữ liệu thành công nhưng vẫn trượt điểm do:
* **Lỗi đổi đơn vị (Unit Arithmetic):** Ví dụ bài toán VCB LNST (`fin-l1-bctc-01`), số tiền gốc là `14.550.959.000.000 VND`. Yêu cầu trả lời theo "tỷ đồng". OpenTrading chia nhầm lũy thừa 10 và trả ra `14,550959 tỷ` (thay vì `14.550,96 tỷ`), bị đánh trượt lỗi `sai_so`.
* **Lỗi liên kết kỳ và giá trị (Period-Value Disconnect):** Ở bài toán tăng trưởng VNM (`fin-l2-growth-01`), dữ liệu có đủ 4 quý. OT lấy nhầm Q2/Q1 (-5.63%) thay vì Q3/Q2 (-2.03%). Model có giải thích đúng trong trường `note` nhưng không map lại vào trường `value`.
* **Nhầm lẫn thời gian quan sát với độ phân giải nến:** Các bài toán RSI (`fin-l2-tech-01`, `fin-l3-tech-multi-01`) bị điền `period: "1D"` thay vì ngày quan sát cụ thể của phiên, dẫn đến lỗi `sai_ky`.

#### 3. Xung đột System Prompt và "Over-engineering" trong Prompt Cơ bản của OT
* **Xung đột chỉ thị cốt lõi:**
  * File prompt gốc của OT (`prompts/style.md:16`) quy định: *Cấm xuất raw JSON cho người dùng*.
  * File `prompts/tools.md:4` yêu cầu: *Ẩn tên các tool nội bộ*.
  * File `prompts/citations.md:6` ép buộc: *Tự động quy đổi tiền tệ về đồng và làm tròn 1 chữ số thập phân*.
  * Trong khi đó, đề bài benchmark đòi hỏi: **Phải trả về đúng 1 JSON object duy nhất**, trường `evidence` phải ghi rõ tên tool gốc, và giữ nguyên đơn vị theo đề bài.
  * Mặc dù cơ chế ráp prompt có gán độ ưu tiên, nhưng độ dài quá lớn của System Prompt (OpenTrading ~7,892 ký tự so với OpenCode ~1,871 ký tự và DSH chỉ ~307 ký tự) khiến mô hình bị quá tải ngữ cảnh (context clutter) và giảm khả năng tuân thủ JSON schema của bài thi.

#### 4. Thiếu hụt cơ chế Output Contract Validator & Provenance Builder
* OpenCode và DSH giữ namespace công cụ nguyên bản (`vn_quote_history`). Trong khi đó, OT thường tự ý thêm tiền tố SDK (`mcp__opentrading__vn_quote_history` hoặc `mcp__opentrading__peer_compare`) vào trường `source` hoặc `evidence[].tool`, vi phạm hợp đồng dữ liệu chuẩn $\rightarrow$ Grader đánh trượt kiểm tra `provenance`.
* Một số bài toán (như `fin-l1-quote-01__opentrading_baseline__r2`), OT tìm đúng giá `21.0 nghìn đồng`, đúng ngày `30/10/2026`, nhưng lại **quên đính kèm mảng `evidence`** $\rightarrow$ Bị phạt lỗi `thieu_bang_chung`.
* OT hoàn toàn thiếu bước kiểm định hợp đồng đầu ra (postcondition check) trước khi hoàn tất turn.

---

### IV. KẾ HOẠCH HÀNH ĐỘNG VÀ ĐỀ XUẤT KHẮC PHỤC CHO OPENTRADING

Để đưa OpenTrading vượt lên đúng với vị thế là một harness chuyên biệt về tài chính, cần thực hiện chuẩn hóa theo kế hoạch tại `plans/2026-11-05-opentrading-mcp-standardization.md`:

1. **Bổ sung Native Argument Repair Loop:**
   * Khi tool trả về `request_rejected: true` kèm `snapshot_requests` hoặc schema guidance, Native Agent Loop của OT phải có trạng thái hồi phục (Recovery Step) để thử lại với tham số chuẩn tối giản thay vì kết luận sai là không có dữ liệu.
2. **Loại bỏ xung đột trong System Prompt:**
   * Tách bạch hai chế độ rõ rệt: *Chat UI mode* và *Automated/Headless Benchmark mode*. Trong headless mode, gỡ bỏ toàn bộ quy định cấm xuất JSON, giấu tên công cụ hoặc tự làm tròn đơn vị.
3. **Chuẩn hóa Client MCP Schema & Namespace:**
   * Giữ nguyên `additionalProperties: false` và kiểu dữ liệu chuẩn (không ép scalar string vào trường array).
   * Chuẩn hóa namespace công cụ: loại bỏ tiền tố nội bộ `mcp__opentrading__` khi tạo bằng chứng `evidence` và `source`.
4. **Tích hợp Financial Postcondition Checker:**
   * Trước khi phát hành câu trả lời cuối cùng, chạy một hàm validation nội bộ:
     * Kiểm tra trường `evidence` đã đủ các trường hash và call_id chưa.
     * Kiểm tra tính toán chuyển đổi đơn vị tiền tệ (tỷ đồng vs triệu đồng vs VND).
     * Kiểm tra định dạng trường `period` (ngày giao dịch chuẩn thay vì chu kỳ nến `1D`).
