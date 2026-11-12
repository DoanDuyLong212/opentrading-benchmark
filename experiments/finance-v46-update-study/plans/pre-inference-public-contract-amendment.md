# Pre-inference common public response endpoint

Registered 2026-11-06 before any v4.2 model inference. This closes an offline
fairness gap: the candidate's public response checks could reject a missing
period/source while a task's numerical grader accepted the same response from
another arm. This is a common endpoint correction, not candidate quality tuning.

Every v4.2 arm now requires the conjunction of task grade success, public contract
validity, receipt grounding, status `ok`, and the original trial deadline. The
public validator receives the common caller instruction and raw final response;
it reads no task identity, financial answer, gold, or oracle. The public tool
catalog supplies canonical names. It requires exactly one literal JSON object
(surrounding whitespace is allowed), the public success example's top-level
fields/types, optional and nullable declarations, canonical source names when
the instruction declares that namespace, and array evidence. Uniform refusal
requires `value:null`, a nonempty string `reason`, and array `evidence`, with no
incompatible nonempty `values`/`ranking`/`items`. Refusal legitimacy and evidence
truth remain separate task/grounding decisions; shape validity alone earns no
financial credit. No answer or receipt is filled in or rewritten.

The validator records `public_contract_valid`, `public_contract_errors`, and
`public_contract_branch`. A grader-successful response that fails this check
gets `public_contract_invalid` while retaining its semantic numeric grade.
`contract_correctness` and `grounded_correctness` now include the public check.
Frozen v4.1/v3 success metrics keep their historical grader + grounding + status
+ deadline conjunction, so the common endpoint delta remains measurable.

Public instruction inventory: all 277 instructions contain exactly one parseable
fenced JSON object, spanning nine top-level field/type families. All are
supported. Missing, malformed, multiple, or nonobject public examples fail
transparently with `unsupported_public_contract`; they are never relaxed into
automatic acceptance. This is the native policy's bounded public-example parser,
not a general natural-language or nested-schema compiler. Period/date *content*,
unit semantics, detailed nested answer requirements, and evidence completeness
remain grader/manual secondary checks; no new financial-content validation is
invented. Empty evidence shape may pass this validator while grounding fails.

The manifest must fingerprint this amendment, `tools/public_response_contract.py`,
`tools/run_benchmark.py`, public catalog, instructions, and relevant graders before
GO. Existing model, effort, request/token/time limits and original v4.1 artifacts
are unchanged. New or resumed runs may not mix pre-amendment endpoint identities.
