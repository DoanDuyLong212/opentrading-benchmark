# Common MCP contract C1/v4 — implementation evidence

This is a common authoritative C1 input-contract and metadata prototype shared by all four experimental conditions. Advertised C1 domain constraints are also enforced by the snapshot server for every condition; invalid domain values produce `invalid_request`. Exact recorded request matching remains unchanged. Neither `/home/doanlong/MCP-server` nor the original OpenTrading runtime was modified. No financial provider/model calls were made during these checks. Production deployment metadata remains unverified.

The catalog restores business descriptions and metadata from the actual source-local 174-tool `FastMCP.list_tools()` capture. Its 17 benchmark tools now have descriptions for all 52 input fields. Original input types, defaults, required fields, exact recorded requests and the replay matcher remain unchanged. The existing replay `additionalProperties:false` policy is retained and explicitly identified as stricter than the production input schema. Source module hashes, source catalog hash, local commit identifiers and a digest over all tool definitions are recorded in `experiments/finance-v4-study/tools/tool_contracts_v4.json`.

`outputSchema` is preserved exactly as captured: a generic object with additional properties. This is **not** an implementation of 17 typed financial output schemas. `annotations` are retained; captured `meta` is emitted as the MCP wire spelling `_meta`. The valuation search hint and description are corrected because the source calculates observed price/EPS/BVPS quotients, not DCF, targets or fair-value bands. Other original business descriptions remain, with the unsupported 365-candle cap claim corrected.

Verified prototype domain guards:

| Tool/field | C1 rule | Source basis and limits |
|---|---|---|
| vn_quote_history.interval | 1D/1W/1M and lowercase equivalents | `providers/vnstock.py:93` canonicalizes case then checks these three values. Public spellings are explicit; no new coercion/aliases. |
| vn_quote_history.columns | null or array of t/o/h/l/c/v | `providers/vnstock.py:130` emits exactly these raw candle keys; rejects `"close"` and `["close"]` before silent projection. Other tools have different field names. |
| vn_quote_history.days | integer >=1, no artificial maximum | Provider documents candle count and floors nonpositive values. Prototype rejects that silent floor; 366 remains valid. |
| financial_statements.period | quarter/year | `providers/vietstock.py:999`: only quarter selects quarterly; arbitrary other strings select annual, so quarter/year guard prevents mislabeled annual fallback. |
| financial_detail.statement | KQKD/CDKT/LCTT/TM/BCTT, upper/lower spellings | Exact `_DETAIL_STATEMENTS` registry and normalization at `providers/vietstock.py:497,786`. |
| signals_technical.interval/convention | 1D/1W/1M case variants; offset25/classic26 | Actual checks in `tools/scan.py:420–434`. |
| valuation_run.method | auto/per/pb/ensemble | Documented labels in `tools/compute_financial.py:267–386`; arbitrary labels accepted by current production are **not** proof of implementing that valuation method. The prototype rejects unsupported DCF rather than falsely echoing it. |

Dynamic ratio `item_id` names are not restricted to the six familiar aliases: production accepts other actual source IDs. FX symbols are not restricted to USDVND/XAUUSD, which are defaults rather than a complete provider universe. Index/crypto/quote-batch column names and Market API intervals are not falsely restricted to the separate historical-candle endpoint. Field descriptions disclose these distinctions. Financial statement section names remain open because exact source labels are accepted in addition to common aliases; this prototype does not invent an unverified closed registry.

Reproduce offline checks from the benchmark root:

```sh
python3 audits/finance-v4-implementation/mcp/build_catalog.py
python3 audits/finance-v4-implementation/mcp/test_contract_v4.py
python3 audits/finance-v4-implementation/mcp/wire_guard_proof.py
```

Ten tests cover concrete schema boundaries, source identity, metadata fidelity, original type/default preservation, open metric/FX domains, and compatibility with **all 277 recorded task environments**, including smoke/pilot. They compare payload, request-contract and gold bytes against the original corpus and exercise every recorded request through the frozen replay selector. Detailed task/request counts and file hashes are in `recorded-parity.json`. A valid production-shaped `{symbol:"HPG",days:1}` remains `not_recorded` in a snapshot that recorded only `{symbol:"HPG"}`; no matcher relaxation or fabricated response is introduced.

The separate five-case `wire_guard_proof.py` uses the **actual installed MCP 1.30.0 lowlevel handler**, an in-memory C1 tool definition and a synthetic stub. It proves `interval:"day"`, string columns and unknown projected columns return `isError:true` without invoking the stub, valid projection returns a nonempty selected row, and valid-input/no-data is distinguishable with a `no_data` code and `retryable:false`. This only demonstrates desired SDK behavior; it does not patch or certify production provider error handling. Its synthetic values must not be represented as sourced financial facts. See `wire-guard-evidence.json`.

API references: [MCP tools specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/tools), [Python SDK v1.30.0 server guide](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v1.30.0/docs/server.md). Local source-local audit established MCP 1.30.0/Pydantic 2.13.5; no migration to upstream SDK 2.x APIs was attempted. Full typed envelopes, live server validation/error taxonomy and provider financial-correctness coverage remain a separate production rollout.
