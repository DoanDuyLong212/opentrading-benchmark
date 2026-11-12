# Native finance policy prototype (v4)

Research opt-in: `runAgent({financePolicy:{enabled:true,machineResponse:true}, ...})`.
Baseline omits this option. The same native SDK loop, provider, retry middleware,
signal, tool timeout/output limits and external request/token budget remain active.

Candidate validates authoritative raw MCP schemas locally with Ajv, without
coercion, defaults or removal of fields, and exposes those raw constraints to the
model. Actual SDK input rejection emits the normal tool events plus
`tool-end.localRejection:{code,tool,rawInput}`, correlated by real `callId`.
The next actual native request carries the SDK tool-error; no MCP call is invented.

A failed read-only parse/schema/query may receive one changed-argument correction
for that tool intent. Identical rejected arguments and changed entity/currency are
blocked; auth/no-data/write failures are ineligible. Ordinary SDK tool continuation
is retained. If the model finishes prematurely, one bounded correction generation
can call only eligible failed tools and then produce its final answer. An output
contract problem shares that single correction generation. It does not select the
first replay request, read a task ID, inspect gold, compute gold math or fabricate
successful calls/evidence.

JSON field shapes come from public user examples; evidence field mapping comes
from public user JSON path strings. The model must supply rows matching an actual
successful result and actual registered public MCP name. Full provenance strings
are never manufactured. MCP outputSchema checks occur after execution outside the
manager retry loop; malformed output does not replay a completed write.
StructuredContent is preserved in strict mode; semantically identical JSON text
and structure are deduplicated. Baseline conversion remains unchanged.

Machine-response text is buffered until the contract passes. The invalid original
and correction remain in model/session history and request captures. Persistent
contract failure is a failed native outcome with no falsely validated final text.
This is no arithmetic/period/coverage oracle: a well-formed wrong answer can pass
native structural checks and still fail the shared benchmark grader.

Dependency reuse: Ajv **8.20.0** is already installed in the original dependency
tree (read-only node_modules symlink). This isolated prototype declares Ajv8.20.0
as a direct package dependency and in the bun.lock root workspace, reusing the
existing exact Ajv8.20.0 package entry, dependency ranges and registry integrity.
No lock package resolution/integrity was invented and no dependency was installed.
The actual reused module tree is separately hashed. Original app manifests/lock
remain unchanged. A clean independent frozen-lock install is still a production
rollout check; never install through this reused read-only symlink.

Verified API sources: installed ai7.0.137 `src/generate-text/{parse-tool-call,
tool-call-repair-function,stream-text}.ts`; provider-utils5.0.58 `src/schema.ts`
(validate callback); Ajv8.20.0 `dist/ajv.d.ts`. No guessed provider strict-output API.
