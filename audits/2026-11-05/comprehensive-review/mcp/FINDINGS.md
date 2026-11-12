# MCP contract review — 2026-11-05

Phạm vi: toàn bộ catalog đăng ký từ source `/home/doanlong/MCP-server` (174 tool), soi sâu 17 tool có schema benchmark, đối chiếu mô tả trên request capture pilot thực tế; kiểm tra provider bằng stub offline. Không gọi model, không fetch số liệu tài chính, không sửa code/config/runtime. Không đồng nhất catalog audit với việc chứng minh correctness của mọi provider hay 174 phép tính.

## Kết luận quan trọng nhất

**Smoke/pilot hiện tại không đo tác dụng mô tả MCP production.** `tools/mcp_snapshot_server.py:86` thay mô tả gốc bằng chuỗi `Frozen MCP snapshot...snapshot_requests=...`. Bốn condition đều thấy mô tả replay này; capture mẫu aggregate được lưu trong `representative-wire-tool-definitions.json`. Vì vậy lỗi của pilot là bằng chứng về khả năng sử dụng giao diện replay và vòng xử lý OT; không đủ để nói mô tả production gây ra bao nhiêu lỗi hay sửa mô tả production sẽ tăng bao nhiêu điểm. So sánh bốn harness trên cùng replay vẫn hữu ích, nhưng tính đại diện production bị giới hạn.

Không có bằng chứng live field descriptions/enum/bounds bị exporter làm mất: chúng **đã không tồn tại ở live source**. Exporter làm mất mô tả tool (9.287 ký tự gộp trên 17 tool), metadata search và outputSchema; thêm `additionalProperties:false` mà live schema không có. Live outputSchema vốn chỉ là object tùy ý.

## Định lượng có thể tái lập

| Catalog | Tool | Top-level input properties | Property descriptions | Enum | Bounds/pattern | outputSchema | outputSchema có typed fields |
|---|---:|---:|---:|---:|---:|---:|---:|
| Source đăng ký đầy đủ | 174 | 331 | 0 | 0 | 0 | 174 | 0 |
| 17 tool trong frozen schemas | 17 | 52 | 0 | 0 | 0 | 17 | 0 |

`live-source-tool-catalog.json` là kết quả `await FastMCP.list_tools()` sau `register_all`; không phải AST dự đoán. `deterministic-contract-evidence.json` và `repro_contracts.py` tái lập số đếm và các tình huống dưới đây. 331 là số property cấp tham số. Scan đệ quy bổ sung qua toàn bộ inputSchema/anyOf cũng xác nhận không có keyword description, enum, const, bounds, pattern hay $defs; chi tiết trong recursive-input-schema-keywords.json. Không khẳng định mọi ràng buộc logic đều vắng khỏi phần thân provider. Trên catalog thực tế không có model input/output typed chi tiết.

Tất cả 17 `x-source-sha256` trong `tools/snapshot_tool_schemas.json` vẫn khớp source module hiện tại. Việc mô tả khác là do đường export/replay, không phải module tool vừa bị sửa sau khi freeze.

## Findings theo mức ưu tiên

### P1 — Schema cho phép giá trị sai; nhiều lỗi bị báo thành không có dữ liệu

- `/home/doanlong/MCP-server/src/opentrading_mcp/tools/vn.py:57` dùng `interval:str`, `days:int`, `columns:list[str]|None`; không Literal/Field bounds. Mô tả nói interval `1D/1W/1M`, nhưng JSON Schema chấp nhận `"day"`.
- Provider thực sự kiểm tra interval tại `/home/doanlong/MCP-server/src/opentrading_mcp/providers/vnstock.py:93`; `day` gây `ProviderBadData`. Tool bắt lỗi tại `tools/vn.py:104`, gọi `_na` tại dòng31, trả envelope `availability:"unavailable"`, warnings chứa lỗi tham số, nhưng không có typed error phân biệt lỗi input và không có dữ liệu.
- Repro đi qua handler MCP low-level thật với upstream stub: `isError:false` + structuredContent unavailable cho ProviderBadData; trong khi `columns:"close"` bị Pydantic reject và `isError:true`. Cùng một nhóm lỗi tham số có hai biểu diễn khác nhau. Đây là nguy cơ production riêng; v3 snapshot đã trả `isError:true` đúng cho rejection và không cấp evidence.
- `columns:["close"]` đúng kiểu nhưng sai tên field: `project_rows` tại `tools/shared.py:74` âm thầm bỏ field không tồn tại, output `[{}]` từ một candle đầy đủ `t/o/h/l/c/v`. Mô tả `columns giữ trường nêu tên` không liệt kê tên hợp lệ, JSON Schema cũng không enum. Model dễ dùng `close` theo tool OHLCV khác thay vì `c`. Lỗi này tái lập thuần Python, không cần network.

### P1 — Một request hợp lệ với production bị replay từ chối

`{"symbol":"HPG","days":1}` hợp lệ theo live schema, provider có ý nghĩa lấy 1 candle. Replay chỉ có `{"symbol":"HPG"}` (default days365), nên `select_entry` từ chối `not_recorded`. Cần tách khỏi `columns:"close"` vốn sai kiểu thật, và `interval:"day"` vốn sai domain thật. Các hạng error không nên cộng chung thành "tool gọi sai schema".

Không nên nới replay bằng cách bỏ qua args hay trả nguyên payload365 candle cho truy vấn1 candle. Để benchmark production sát hơn, cần snapshot thêm truy vấn hợp lệ hoặc deterministic projection/slicing được công bố trước, bảo toàn provenance và oracle; giữ replay nghiêm cho corpus hiện tại.

### P1 — Doc capability và implementation `valuation_run` không đồng nhất

- `tools/compute_financial.py:267` nói ensemble PER/PB, vùng giá trị hợp lý, vùng mua an toàn; dòng271 còn hướng model dùng output vùng `per_pb/pb`.
- Code `:304–414` trả price/EPS/BVPS và tính quotients `per`, `pb`; **không có target price, assumption multiple, low/high band, sensitivity hay ensemble calculation**. `method`/btype chủ yếu đổi chuỗi nhãn `method` (`:374–386`), không chọn một phép định giá khác.
- `method:str` chấp nhận giá trị tùy ý. Stub input price100/EPS5/BVPS50 trả PER20/PB2 với cả auto, per và `dcf`; `dcf` được echo ở `method` dù không có phép DCF. Repro chỉ chứng minh hành vi code, không số liệu thị trường.
- `hints.py:103` searchHint chứa `DCF`, trái với docstring “DCF/EV CHƯA có”. Điều này có thể route task DCF vào công cụ không hỗ trợ trong production; pilot không hề dùng searchHint này nên không thể quy lỗi pilot cho hint.
- Output có các cờ `price_unit/eps_unit/adjustment_basis:unverified`; đây là khai báo hạn chế tốt. Tuy nhiên cần schema typed và policy rõ khi các bội số không được xác nhận tương thích; không để phần mô tả hứa "fair value" trong khi output chỉ là observed multiples.

### P1 — Sai period có thể âm thầm lấy báo cáo năm

`providers/vietstock.py:999` đặt `term=2 if period=="quarter" else1`, `pages=3 if quarter else1`. Stub `_post` chứng minh `quarterly` và `garbage` đều gửi `ReportTermType:1` (năm), sau đó output còn echo period sai ban đầu. Input tool `financial_statements.period`/`vs_financeinfo.period` là string tự do. Đây là lỗi tài chính nghiêm trọng hơn việc JSON parse fail: câu trả lời có số hợp lệ nhưng sai kỳ. Cần enum quarter/year và reject sớm; alias nào được chấp nhận phải canonicalize rõ.

### P2 — Limit/columns/peers còn hợp đồng ngầm và silent coercion

- `vn_quote_history` doc `tools/vn.py:73` nói tối đa365 nến; provider `providers/vnstock.py:96–138` không cap365. days<=0 bị floor thành1 (`rows[-max(days,1):]`). Schema không báo min/max.
- `peer_compare` doc `compute_financial.py:547` nói tối đa5 peers; code `:571` cắt `[symbol,*peers][:6]` im lặng thay vì reject hoặc báo omitted. Metrics alias được normalize là tốt; cần enum/valid field discovery và explicit missing/unknown metrics.
- `align_financeinfo` tại `providers/vietstock.py:1117` nếu statement không khớp sẽ warning và trả toàn bộ statements. Hợp lệ cho một API khám phá, nhưng không nên model hiểu là đã nhận đúng requested statement. Typed requested/resolved statement và error code giúp tránh đọc nhầm bảng.
- Các tool lân cận có candle schema khác nhau (`vn_quote_history:c`; `vn_index_ohlcv:close`). Nên canonicalize output mà vẫn giữ raw source path, hoặc liệt kê rõ columns và aliases ở schema. Không đổi tên field ngầm làm hỏng client cũ.

### P2 — OutputSchema chỉ kiểm tra “là object”, chưa bảo đảm contract tài chính

Toàn bộ174 tool annotate `dict[str,Any]`; FastMCP1.30.0 sinh `outputSchema:{type:"object",additionalProperties:true}`. Điều này là có structured output thật, **không phải** server thiếu `structuredContent`: SDK trả cả text và structuredContent cho dict, như repro. Vấn đề là schema không kiểm soát envelope, units, period, missingness, financial lineage, và tool-specific data shape. Snapshot thì hiện chỉ TextContent, không outputSchema.

`schemas.make_envelope` tại `schemas.py:109` đã có source/as_of/timezone/warnings/availability/data_time; `units.py` đã thêm units cho9 nhóm price tools; `financial_contracts.py` đã có registry nghĩa field và độ chắc chắn nguồn. Đây là nền tốt để chuẩn hóa, cần dùng lại thay vì tạo một contract thứ ba. `as_of` là thời gian fetch; `data_time` là thời điểm quan sát (`schemas.py:120`). Không dùng as_of thay ngày giao dịch/kỳ báo cáo.

### P2 — Catalog production lớn và có discovery, nhưng pilot không đo discovery này

Source `server.py:38` expose28 module/174 tool có thứ tự ổn định; `hints.py` có metadata searchHint; resources `resources.py:18` có financial contracts, `:15` term-types. OT nhận server instructions và metadata searchHint trong `src/core/mcp/manager.ts:184–202,:372`. Pilot task-scoped replay thường chỉ1 hoặc vài tool, không dùng full174/search resources. Do đó chưa có căn cứ gọi “174 tools gây context overload” là nguyên nhân đã quan sát. Chỉ coi là rủi ro production cần eval discovery riêng.

## Phiên bản, API được phép dùng và nguồn chính thức

Đã thử sitemap chính thức `https://modelcontextprotocol.io/sitemap.xml`; web tool từ chối MIME text/xml. Dùng index chính thức [llms.txt](https://modelcontextprotocol.io/llms.txt), sau đó đọc [Tools2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/server/tools), [Tools2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) và [SDK v1.30.0 server guide](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v1.30.0/docs/server.md).

Quy tắc chung bền giữa hai revision: inputSchema mô tả tham số; nếu có outputSchema, structured result phải conform; errors thực thi/input/business nên `isError:true` với feedback sửa được. StructuredContent và JSON text có thể cùng tồn tại. Tách schema tool-result khỏi structured output của model. Discovery/metadata mới2026 khác handshake legacy; không tự thêm APIv2 vào deploymentv1 chỉ vì đọc docs latest.

Local package `/home/doanlong/MCP-server/.venv` là **mcp1.30.0, Pydantic2.13.5**; pyproject giữ `mcp>=1.9,<2`. Latest upstream README đã chuyển2.x, vì vậy implementation tiếp theo phải dùng tài liệu tagv1.30.0, giữ upper bound2 và pin lock thực tế; migration2 là task riêng. Exact runtime signatures trong `sdk-apis.json`:

```python
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.lowlevel import Server
from mcp.types import CallToolResult, TextContent

FastMCP.tool(self, name=None, title=None, description=None,
             annotations=None, icons=None, meta=None, structured_output=None)
FastMCP.call_tool(self, name: str, arguments: dict[str, Any])
Server.call_tool(self, *, validate_input: bool = True)
CallToolResult(*, content: list[ContentBlock],
               structuredContent: dict[str, Any] | None = None,
               isError: bool = False, _meta=None)
```

Dùng `typing.Literal`, `typing.Annotated` + `pydantic.Field(description=...,ge=...,le=...)` để sinh schema; `BaseModel` typed cho output. Với execution error, raise `ToolError` để SDK set `isError:true`, hoặc trả `CallToolResult` typed đúng với nội dung actionable khi cần kiểm soát envelope. Phải kiểm tra actual `tools/list`/wire response qua handler trong test, không chỉ test dict Python.

Anti-patterns: copy API`MCPServer` của latestv2 vào v1; xem genericobject như typed financial contract; return unavailable cho mọi inputerror; quảng cáo DCF/fairvalue chưa được tính; tự sửa/ignore args để replay pass; suy lỗi production từ mô tả đã bị replay thay thế; nhầm as_of với trade date.

## Hướng chuẩn hóa đề nghị để root đưa vào plan

1. Freeze metadata deployment thực tế + catalog/schema digest; giữ benchmark cũ bất biến. Nâng exporter từ runtime `tools/list` đầy đủ descriptions/inputSchema/outputSchema/annotations/meta/serverinstructions; benchmark dùng cùng bản contract, thêm replay restriction riêng.
2. Bắt đầu vn_quote_history, financial_statements/vs_financeinfo, peer_compare, financial_detail, valuation_run. Định nghĩa registry dùng chung schema+docs+validation+output metadata; field enum/bounds/units/period/date rules và examples valid/invalid được generate từ cùng nguồn.
3. Tách error enum invalid_argument/not_found/no_data/upstream_timeout/auth_required/rate_limited/unsupported_operation/not_recorded; ghi argument path, allowed values, retryability. Chỉ invalid_argument/request mismatch cho phép bounded repair, không biến provider error thành financialmissing.
4. Sửa description/hint valuation đúng năng lực quan sát; không gọi fair value đến khi có công thức/assumptions/range riêng. Reject method chưa hỗ trợ. Unknown period phải reject trước network; unknown columns phải reject hoặc canonicalize alias công khai.
5. Typed output envelope giữ unknown/null và financial contracts registry hiện có; test price unit thousandVND vsVND, ratio current vsperiod-end, annual/quarter/YTD/TTM/consolidated/scope/revision, partial/missing.
6. Eval lớp contract không model: actual registeredschema + FastMCPwire + boundary args + mockedprovider + replayparity. Sau đó eval chọntool/repair trên devset đã đăng ký, với fullcatalog discovery riêng và task-scoped oracletool track riêng; không so chéo hai chế độ như một phép đo.

Không đề xuất chạy thêm main/holdout hoặc trả lời trước khi có bằng chứng tương thích production. Báo cáo này không xác nhận metadata remote giống local cho đến khi `deployed-metadata.json` có statusok; kể cả catalog giống, serverInfo tự khai không chứng minh commit/provider runtime.

## Ví dụ schema đề nghị đã xác minh với SDK cài sẵn

`proposed_schema_example.py` đăng ký một tool minh họa riêng trong memory và export `proposed_schema_example.json`; không gọi function/provider. SDK1.30.0 thực sự sinh minimum1/maximum365, enum1D/1W/1M, field descriptions và `$defs` cho typed result. Đây là example để plan dùng, chưa sửa production.

```python
from typing import Annotated, Literal
from pydantic import Field, BaseModel, ConfigDict

Days = Annotated[int, Field(ge=1, le=365, strict=True,
    description="Số nến yêu cầu, không phải số ngày lịch.")]
Interval = Literal["1D", "1W", "1M"]
# Trong function signature: days: Days = 365, interval: Interval = "1D"
# Output: một BaseModel có data/provenance/availability/units typed,
# không dùng dict[str, Any] làm hợp đồng cuối cùng.
```

Field thuộc Pydantic2.13.5, hỗ trợ `description`, `strict`, `ge`, `le`, `min_length`, `max_length`; exact signature có trong `pydantic-field-signature.txt`. Strict int ngăn `1.5` hay string số bị coi là số nến hợp lệ; strict extra cần enforce bằng model/config hoặc validator trung tâm, không chỉ thêm keyword ở JSON Schema trong khi runtime vẫn silently ignore. Với projected columns, output model phải đại diện projection rõ (ví dụ selected_fields+typed optional candle fields), không tái sử dụng full-candle required model cho mọi chế độ.

## Metadata deployment: khoảng trống đã kiểm tra

OT config thực tế `~/.opentrading/mcp.json` trỏ `https://opentrading-mcp-web.onrender.com/mcp` qua HTTP có Authorization tham chiếu credential; token không được ghi vào artifact hay log. Một probe metadata-only bằng SDK installed bị ConnectError trong sandbox; đã retry đúng quyền network ngoài sandbox, kết thúc với McpError trong chuỗi ExceptionGroup. Chỉ ghi tên exception để tránh lộ body/auth; không suy đoán đó là auth, outage hay protocol mismatch khi không có đủ bằng chứng. Không gọi tools/call. Vì handshake/list chưa thành công, production catalog và revision hiện vẫn **chưa xác minh**. `deployed-metadata.json` có trạng thái failed, không được dùng như deployment certificate. Plan cần bước kiểm tra metadata server/deployment rõ ràng trước thay đổi production.

Local source HEAD `ed934aebd0ee6f9271512150a9bb3971089d7460`; subbackend HEAD `5d291e04f43f49e41fc315efbaf45b6dcb0508a3`. Source hash chi tiết ở `source-identity.json`, không xem hash module local là bằng chứng commit deployed.
