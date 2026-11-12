# Forensic review Super R3 v4.6 — offline, không sửa điểm frozen

Phạm vi: `experiments/finance-v46-study/results/financial-v46-20261109-r3/super-devsmoke`, 96 trial = 12 DEV synthetic × 2 repetition × 4 arm. Chỉ đọc artifact; không inference, không sửa source/task/gold/grade cũ. Bản JSON đi kèm lưu hash manifest/trials, final đã parse, đối chiếu 7 trường evidence, namespace alias và native final events cho cả 96 trial.

## 1. Đối chiếu yêu cầu “7 thất bại”

`opencode-review.md` tại lượt đọc có 1050 dòng, kết thúc §18.6; không chứa phụ lục phân tích 7 thất bại. Cohort R3 đã hoàn tất 96: OT-fin **18/24 strict, 18/24 grounded, 1 DNF** → **6**, không phải 7, thất bại primary. Không gán số 7 vào một cohort khác chưa tìm thấy. Đây chưa phải điểm đã chứng nhận bởi audit/manual all-arm.

| Arm | Strict/24 | Grounded/24 | DNF | Stable 2/2 task |
|---|---:|---:|---:|---:|
| OT baseline |18|18|0|8/12|
| OT-fin |18|18|1|7/12|
| OpenCode |13|14|1|5/12|
| DSH |16|18|1|6/12|

OT-fin chưa vượt B0 hoặc DSH trên grounded; B0 ổn định hơn và ít DNF hơn. Chênh lệch OpenCode không đủ tuyên bố vượt trội lĩnh vực tài chính: 12 synthetic task, 2 lần/task, thiếu PASS audit.

## 2. Sáu failure primary của OT-fin, nguyên nhân thực

Các đường dẫn trial đều ở dưới cohort nêu trên; `FORENSIC-SMOKE.json` lưu đường dẫn ledger/grade/native-derived đầy đủ.

| Trial suffix | Đáp án / dữ liệu | Frozen lỗi | Chẩn đoán và sửa prospective |
|---|---|---|---|
| `11-trap-period…r1` | `value:null`; chỉ có Q2/2026=420, Q3/2026=483; “không có kỳ Q4/2026” | `refusal_reason hit=[]`, `khong_tra_loi` | Từ chối đúng nghĩa và đúng evidence. Grader phụ thuộc cụm từ nguyên văn; dùng rubric nhận định thiếu kỳ có cấu trúc và kiểm phủ định, không chỉ thêm chuỗi đúng case này. Giữ điểm cũ. |
| `07-aggregate…r1` | DGC81.7, DCM34.8, DPM42.1 nghìn đồng cùng 2026-10-29; mean=52.866666…; trả52.87 | `sai_so`, tolerance1e-6 | Sai precision output theo metric hiện hành, không sai chọn số/công thức. Instruction chung không nêu precision. Nêu precision chung mọi arm; preserve output calculator đủ chữ số. Không âm thầm nới tolerance. |
| `05-scale…r1` | Quote FRT92.4 nghìn đồng, target92400đ/cp; không có final | provider424/DNF | Trước đó native calculate bị chặn do unit source tự thêm `/cổ phiếu`; sau đó provider stream không có finish_reason trong240s, partial usage. Hai nguyên nhân cần tách: unit-call correction vs transport. Không chấm đúng dựa vào số trung gian. |
| `06-ratio…r1` | 78/600=0.13, `unit:""`, Q3/2026 hợp nhất DCM | `sai_don_vi`, grader báo accept `ty_dong` | GOLD thực là **tỷ lệ**. `canon_unit('tỷ lệ')` bị broad alias `ty` ánh xạ thành tỷ đồng. Không sửa model trả tỷ đồng. Chuẩn hóa dimensionless/tỷ lệ/lần; unit rỗng vẫn là representation thiếu nhãn rõ, phải quyết định theo contract chung trước run mới. |
| `02-resolve…r2` | Resolver Nhà Khang Điền→KDH;37.25 nghìn,2026-10-29; đủ2receipt; source chỉ`vn_quote_history` | `sai_nguon` | Truy nguồn nội dung đủ nhưng top-level field thiếu`symbol_resolve` theo gold. Không phải hallucination. Chuẩn hóa full source chain từ các receipt thực, tránh biến utility thành market source. |
| `07-aggregate…r2` | mean52.87, native calculate thật thành công nhưng `decimals:2` | `sai_so` | Precision như r1; lần này thấy rõ model yêu cầu calculator làm tròn. Lỗi selector `data.last` rồi alignment cross-entity gây thêm2call correction trước thành công. |

**Không có 6 JSON-invalid trong nhóm này.** Năm trial có final đều là object JSON đúng cấu trúc public cơ bản, receipt truy được. Phân loại: precision2, serialization/source1, lexical refusal1, unit normalizer1, provider1. Nói “phần lớn chết vì form” chỉ đúng theo nghĩa rộng contract/precision; cần tránh che lỗi grader/transport hoặc gọi sai số thành thắng.

## 3. Bằng chứng nguồn, kỳ, đơn vị, toán

Đọc fixture payload/instruction/gold của cả12task. Các con số được độc lập tính lại từ nguồn synthetic, không từ final:

- Quote/resolve KDH:37.25 nghìn đồng,2026-10-29.
- Growth DGC:(483/420−1)×100=15%; hai quýQ2/Q3-2026, hợp nhất.
- NLG gross margin:92/400×100=23%, Q3/2026 hợp nhất.
- FRT:92.4×1000=92400VND/cp.
- DCM profit/revenue:78/600=0.13 **dimensionless**, không% và khôngtỷđồng.
- Mean:(81.7+34.8+42.1)/3=52.866666666666… nghìn đồng, cùng2026-10-29.
- Two-source gap DGC:abs(82.1−81.7)=0.4 nghìn đồng, cùng2026-10-29. Đây là hai nguồn **synthetic** chứ không bằng chứng hai nhà cung cấp thị trường độc lập.
- Resolver Đạm Phú Mỹ→DPM; doanh thuQ3/2026=972e9VND→972tỷđồng.
- Trap resolver không có ứng viên; trapperiod không cóQ4/2026; trapempty count0,lastnull.

All96 offline join: **135 evidence entries;133 exact7field match**. Một OCratio-prefixedtool alias trở thành match nếu bỏ tên harness-prefix, nhưng strict sourcefield vẫn fail. Một **B0trapemptyr1 response_sha256 khác MCPledger** vẫn không match dù canonical tool. Không rescue receipt sai. 90/96 raw final là JSON exact;6 trial còn lại cần tách DNF/prose/fence khỏi financialvalue extraction. Offline JSON extraction chỉ phục vụ forensic, không dùng thay endpoint raw-contract.

OT-fin cả5failure có final đều evidence7field match ledger. Không thấy extra narrative bịa số thị trường ở nhómfailure; aggregater1 còn cảnh báo synthetic rõ. Trapr2 có từ tiếngHàn xen vào câu phạmvi; lỗi diễn đạt chứ không đổi số. Kết luận này không thay independent claim-level signoff cho tất cảwins.

## 4. Lỗi hệ thống nghiêm trọng ngoài sáu primaryfailure

**21/24 OT-fin trial có native event `financial_contract_invalid`, gồm16 trial mà frozen benchmarkprimary vẫn PASS.** 20/21 lượt initialfinal bị reject vì “Evidence row does not exactly match any actual successful tool response”,1lượt initial bị surroundingprose. Sau boundedrepair vẫn reject evidence.

Điều này không đồng nghĩa cả21final sai tài chính: public receipt của nhiều trial (ví dụquote,resolve,growth) matchledger. Nhưng nativegate đang không nối đúng namespace/schema thực, tốn thêm lượt sửa và làm user-visible nativeoutcome khác rawdiagnosticgrading. Phải sửa exact mapped7fieldjoin trên actualsource response, test sai hash/call/session/provider/batch, không tắt gate; báo riêng nativeaccepted/raw-grade. Đây là instrumentation/control defect quan trọng hơn việc tune thêm câu prompt.

Aggregate r1 commoncompute lần đầu dùng localref `r1/r2/r3` trong trường đòi publicUUID→rejected; sửaUUID rồi thành công. Aggregate r2 nativecalc dùng sai selector `data.last`, tiếp theo thiếu cross_entityalignment, cuối thành công. Hai APIs có reference namespace khác nhau cần mô tả ngắn/rõ và validation errorgợi ý đúng trường; không biến repair thành đổi source/entity/period.

Scale r1 sourceunit`nghìn đồng` bị model override thành`nghìn đồng/cổ phiếu`; nativeguard đúng khi không cho đổi metadata tự tiện. Chỉ có thể thêm mô tả semantics có kiểm chứng hoặc hướng dẫn dùng exactsourceunit rồi explicitconversion, không nới unitguard vô điều kiện. Providerrequest3 nhận bytes34588, usageunknown, `provider_finish_reason_missing`, errororiginupstream_protocol, status424 sau240.126s. Không gọi đây là model trả lời sai tài chính; cũng không giả định retry được mà bỏ partialcost/DNF.

## 5. So sánh matched OC và DSH: học gì, không học gì

- Resolve: OC2/2 vàDSH2/2 dùng`source:"symbol_resolve + vn_quote_history"`, B02/2 cũngvậy. OT-fin1/2 mắc omissionfield, dù model có đủ2receipt. Source-chain serialization có thể sửa ở prospective contract/prompt; không cần model mạnh hơn.
- Aggregate: **mọi8trial/4arm đều failprecision**. DSHr2 giữ4decimals52.8667 vẫn lệch>1e-6. Không có bằng chứng OC/DSH tính mean giỏi hơn; đây là shared precision communication issue.
- Ratio: toàn8trial có số0.13 đúng; đơn vịdimensionless/lần/rỗng bị grader broad`ty` chặn, trongkhi`tỷ lệ` PASS vì cùng bị mapnhầm. OC thêm fence/prefix source; DSH có1literalunitratio đúng. Không học outputmoney để thắnggrader.
- Growth: OT-fin vàB0 mỗi2/2; OC0/2,DSH1/2 vì periodfield chỉQ3 không ghi đủQ2comparison. Điểm mạnh OT là explicitperiodalignment; cần giữ.
- Scale: OC1/2(rawprose),DSH2/2,B02/2,OTfin1/2(DNF). DSH sạch output vàreliablecompletion hơn ởcase này, nhưng N2 không đủtách modelrandomness/providerload.
- Trapperiod: DSH2/2 chứa cụm lexicon; OC0/2 vàB0/OT1/2 dù thiếuQ4 được hiểu đúng. DSH điểm cao phần này không chứng minh suy luậnavailability tốt hơn; graderlexicalconfound lớn.
- OT-fin inputmedian33667 vsOC15790,DSH14450; outputmedian3308 vs1537/2032; latency39.75s vs32.95/44.27s. Repairgate21trials và redundantreference errors là chi phí có bằng chứng; chưa phân rã được causal tokenoverhead từprompt/toolcatalog/reasoning một cách định lượng.

## 6. Thứ tự cải tiến / phạm vi phê duyệt

v4.6-update có thể sửa instrumentation/contract prospective được user ủy quyền: unitnormalizer boundary, genericrefusalrubric, common precision instructions, mapped evidence finalgate, SDK/publicref descriptions, nativeaccepted/diagnosticrawreporting, boundedeligibletransportretries vớipartialusage. Freezeversionmới; all-armmutation/offlineaudit/actualwire, rồi smoke vàpilot chỉquagate; không sửa cùngrun sauinference.

v4.7 chỉ **đề xuất để userduyệt**, chưa chỉnhcode: slimcontext+taskplan, deterministicanswerbuilderfromtypedclaims, consistentSDK/publicreferencebridge, financialdimensionalIR/sourceperiodalignment, fewerboundedrepairs, longerrealmarketstrata/memorycounterfactuals. Mỗilever cầnablation+failure/usageguards; không hứa đánhbạiOC/DSH trước thực nghiệm và không suy rộng từ12synthetictask.
