#!/usr/bin/env python3
"""Auditor amendment (j) 2026-11-11 (user chose "Amendment auditor" after seeing the or16 merged-main audit):
tools/audit_v45_run.py with ONE extra binding rule, applied from outside tools/ (tools/ stays frozen by the or16 seal,
which the holdout still needs).

Case: the model sends a `calculate` operand with BOTH a source reference (from_call/field/path/...) AND a typed
`value`; the OpenTrading runtime keeps only {value, unit} and marks the result lineage "unverified". The exact-args
binding then fails for an ok native execution (Fix #10 only covers status=error).

Rule (j): when the exact claim fails, bind the native execution to the generated occurrence with the same SDK id, tool
and provider turn iff the generated args, after dropping the reference keys from operands that carry a numeric `value`,
equal the persisted args exactly. Additionally, every such typed value must equal (exactly) a number this same trial
obtained earlier from a bound native execution (an input value or result in native-derived.jsonl before this call);
otherwise the trial gets an audit error. Every relaxed binding is disclosed in audit-v45.json under
`amendment_j_relaxed_bindings`. Nothing else in the audit changes.

  python3 analysis/audit_v45_amended.py --run RUN_DIR
"""
import argparse, json, sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
import v45_call_binding as cb  # noqa: E402
import audit_v45_run  # noqa: E402

REF_KEYS = ('from_call', 'field', 'path', 'from_symbol', 'at', 'symbol', 'ref')
RELAXED = []
_claim = cb.CallBindings.claim


def strip_refs(args):
    if not isinstance(args, dict) or not isinstance(args.get('values'), dict):
        return None
    out, typed = dict(args), {}
    vals = {}
    for name, leaf in args['values'].items():
        if isinstance(leaf, dict) and isinstance(leaf.get('value'), (int, float)) and any(k in leaf for k in REF_KEYS):
            vals[name] = {k: v for k, v in leaf.items() if k not in REF_KEYS}
            typed[name] = leaf['value']
        else:
            vals[name] = leaf
    out['values'] = vals
    return out, typed


def claim_j(self, sdk_id, tool, args, proof=lambda context: True, scope=None, request_bounds=None, provider_index=None):
    key = _claim(self, sdk_id, tool, args, proof=proof, scope=scope, request_bounds=request_bounds,
                 provider_index=provider_index)
    if key or cb.canonical(tool) != cb.canonical('calculate'):
        return key
    sig = cb._sig(args)
    cands = []
    for g in self.generated:
        if g['key'] in self.claimed or g['id'] != sdk_id or g['tool'] != cb.canonical(tool):
            continue
        if provider_index is not None and g['provider_index'] != provider_index:
            continue
        if scope is not None and g['scope'] != scope:
            continue
        s = strip_refs(g['arguments'])
        if not s or not s[1] or cb._sig(s[0]) != sig:
            continue
        contexts = [c for c in self.contexts if c['id'] == sdk_id and c['tool'] == g['tool']
                    and c['arguments'] == g['arguments'] and proof(c)]
        if contexts and not any(c.get('generation_keys') == [g['key']] for c in contexts):
            continue
        cands.append((g, s[1], contexts))
    if len(cands) != 1:
        return None
    g, typed, contexts = cands[0]
    self.claimed.add(g['key'])
    self.claims.append({'generation': g, 'contexts': contexts})
    RELAXED.append({'sdk_call_id': sdk_id, 'provider_index': g['provider_index'], 'typed_values': typed,
                    'generated_arguments': g['arguments'], 'persisted_arguments': args})
    return g['key']


def numbers(x):
    if isinstance(x, bool):
        return
    if isinstance(x, (int, float)):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from numbers(v)
    elif isinstance(x, list):
        for v in x:
            yield from numbers(v)


def typed_value_provenance(run):
    """Each typed value must equal a number from an earlier ok native execution (inputs bound to a source ref, or a
    result) in the same trial's native-derived ledger."""
    errors = []
    ledgers = list(Path(run).glob('trials/*/attempts/*/runner/native-derived.jsonl'))
    for rel in RELAXED:
        hit = None
        for led in ledgers:
            recs = [json.loads(l) for l in led.read_text().splitlines() if l.strip()]
            idx = next((i for i, r in enumerate(recs) if r.get('sdk_call_id') == rel['sdk_call_id']), None)
            if idx is None:
                continue
            tid = led.parts[-5]
            prior = set()
            for r in recs[:idx]:
                if r.get('status') != 'ok' or not isinstance(r.get('result'), dict):
                    continue
                res = r['result'].get('derived_result', r['result'])
                prior.update(numbers(res.get('result')))
                for leaf in res.get('inputs', []):
                    if leaf.get('ref') or leaf.get('sdk_call_id'):
                        prior.update(numbers(leaf.get('value')))
            missing = {k: v for k, v in rel['typed_values'].items() if v not in prior}
            hit = dict(rel, trial_id=tid, typed_values_traced=not missing, untraced=missing)
            if missing:
                errors.append({'trial_id': tid, 'check': 'amendment_j_typed_value_provenance',
                               'error': 'Typed calculate operand not equal to an earlier bound value: %s' % missing})
            break
        if hit is None:
            hit = dict(rel, trial_id=None, typed_values_traced=False)
            errors.append({'trial_id': None, 'check': 'amendment_j_typed_value_provenance',
                           'error': 'Relaxed binding %s has no native ledger record' % rel['sdk_call_id']})
        rel.clear(); rel.update(hit)
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    a = ap.parse_args()
    cb.CallBindings.claim = claim_j
    result = audit_v45_run.audit(a.run)
    extra = typed_value_provenance(a.run)
    result['errors'] = result['errors'] + extra
    result['pass'] = not result['errors']
    result['amendment_j_relaxed_bindings'] = RELAXED
    result['amendment'] = ('j 2026-11-11: calculate operand with source ref + typed value, runtime kept value only; '
                           'bound by SDK id/tool/turn + stripped-args equality + typed value traced to earlier bound '
                           'value (plans/2026-11-11-v46u-auditor-typed-value-amendment.md)')
    from v45_control import atomic_json
    atomic_json(Path(a.run) / 'audit-v45.json', result)
    print(json.dumps({'pass': result['pass'], 'errors': result['errors'], 'relaxed': RELAXED,
                      'fabricated_evidence_accepted': result['fabricated_evidence_accepted'],
                      'wins': result['financial_or_strict_wins']}, ensure_ascii=False, indent=1))
    raise SystemExit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
