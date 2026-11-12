# v4.6 execution protocol — instrumentation repair of frozen v4.5

Registered 2026-11-09 BEFORE inference. Study: experiments/finance-v46-study (copy of frozen v45 + the eight
instrumentation repairs below). The frozen v45 study (MINI diagnostic + PAUSE stateless manifests) stays
byte-identical; nothing in it is edited, rescued or re-graded.

## Repairs (from NEXT-INSTRUMENTATION-VALIDATION-PLAN.md, audits/financial-memory-v45/)

1. Schema generation: ECMA-262 unicode-mode-compatible literal escaping in tools/mcp_snapshot_server.py
   (root cause of six uncompilable finite schemas / 65 affected tasks; Python matcher semantics unchanged —
   verified 154/154 positive + 154/154 negative on recorded args, and 0 compile failures through the actual
   pinned Bun/Ajv validator on all 156 unique schemas).
2. Parallel tool-call binding by assistant tool-list ordinal (v45_call_binding.py), never SDK-id lexical order.
3. Per-model sampling read from sealed experiment options (no hardcoded super/other split).
4. OpenCode reversible quote-wrapper grammar authenticated for user-prompt binding (one decode level).
5. Tool-failure classification (7 classes): wrong-name / malformed / schema-invalid / validator-compile-crash
   (infrastructure) / schema-valid-unsupported-captured-query / invalid-production-query / transport.
   Validator crashes and unknown-tool calls reconcile as infrastructure admission failures; failed calls and
   their costs stay preserved; never financial evidence; never a quality rescue.
6. MCP-rejected reconciliation with the authenticated public replay error (private wording or the public
   unsupported_snapshot_query code).
7. Replayed historical rejection notices bind to the ORIGINAL generation in their own session (never a later
   session's call).
8. Notebook search description states literal whole-substring semantics.

## Frozen inputs

Models, sampling, caps, arms, corpus, tasks, graders, schedule design: identical to the frozen v45
stateless registration (plans/2026-11-08-v45-finalization-plan.md + plans/2026-11-08-v45-execution-protocol.md):
- Super: nvidia/nemotron-3.5-super-vl-120b-a12b (route-v2; returned private alias; checkpoint UNVERIFIED),
  temperature 1 / top_p 0.95. DeepSeek: deepseek-v4.1-flash, temperature 0 / top_p 1.
- devsmoke 12 tasks x2 repeats x4 arms =96/model; pilot 22 x2 x4 =176/model (denominator 44/arm);
  main 183 x2 x3 =1098/model. Gates: preregistered in tools/v45_gate.py (unchanged thresholds).
- Memory MINI stays the frozen v45 diagnostic (N=3, uncertified); no memory inference in v46.

## Launch order

devsmoke (both models, separately audited + gated) -> pilot (only if own-model devsmoke gate passes)
-> main (only if pilot gate + manual financial review + user-delivered report). No tuning between cohorts.
