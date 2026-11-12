"""Batched LLM judging (user 2026-11-11): several trials per request, per-item cache, single fallback."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import llm_judge  # noqa: E402

T = ROOT / 'tasks/main/fin-c1-pct-401'
G = json.loads((T / 'solution/gold.json').read_text())


def fake(answer_ids):
    calls = []
    def call(user, model=None, system=None, parser=None, max_tokens=None, **kw):
        calls.append(system is not None)
        ids = re.findall(r'### MỤC id=(\S+)', user)
        if parser:
            txt = json.dumps({'results': [{'id': i, 'verdict': 'correct', 'reason': 'ok', 'failed_fields': []} for i in ids if i in answer_ids]})
            return {'verdict': 'batch', 'batch': parser('thinking {not json}\n' + txt), 'usage': {}, 'returned_model': 'm'}
        return {'verdict': 'incorrect', 'reason': 'single', 'failed_fields': ['value'], 'usage': {}, 'returned_model': 'm'}
    return call, calls


def test_batch_one_request_and_single_fallback_and_cache():
    items = [('a', T, G, '{"value": 1}'), ('b', T, G, '{"value": 2}'), ('c', T, G, '{"value": 3}')]
    call, calls = fake({'a', 'b'})
    cache = {}
    r = llm_judge.judge_batch(items, cache=cache, call=call)
    assert [r[i]['verdict'] for i in 'abc'] == ['correct', 'correct', 'incorrect']
    assert r['c']['mode'] == 'single_fallback' and calls == [True, False]
    call2, calls2 = fake(set())
    r2 = llm_judge.judge_batch(items, cache=cache, call=call2)
    assert calls2 == [] and all(r2[i]['cached'] for i in 'abc')
    assert all('numeric_prepass' in r2[i] for i in 'abc')


def test_compact_answer_drops_evidence_only():
    out = json.loads(llm_judge.compact_answer('```json\n{"value": 1, "unit": "%", "evidence": [{"x": 1}]}\n```'))
    assert out == {'value': 1, 'unit': '%'}
    assert llm_judge.compact_answer('') == '(không có câu trả lời)'


def test_batch_system_keeps_single_rules():
    rules = llm_judge.SYSTEM.rsplit('Kết thúc bằng', 1)[0]
    assert llm_judge.SYSTEM_BATCH.startswith(rules) and '"results"' in llm_judge.SYSTEM_BATCH
