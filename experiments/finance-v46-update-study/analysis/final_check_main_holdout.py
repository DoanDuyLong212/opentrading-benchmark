#!/usr/bin/env python3
"""Final pre-run check of main (200) and holdout (50), read-only. Prints one line per check family and every problem.

Checks per task: eligibility/stratum counts; oracle reproduces gold; a synthetic gold answer passes the grader
(semantic) and the numeric gate, and a 2%-perturbed value fails both; public JSON example parses; every payload
entry is served by the snapshot server and provenance hashes match; A8 contract bullet present (core/compute);
memory turns valid and final; no gold leak into instructions; no question duplicated across main and holdout.
"""
import json, re, subprocess, sys, tempfile, tomllib
from collections import Counter
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(STUDY / 'tools'), str(STUDY / 'tools/runners')]
from run_manifest import task_eligibility  # noqa: E402
from mcp_snapshot_server import load_entries, select_envelope, build_tool_defs, digest  # noqa: E402
from public_response_contract import public_success_example  # noqa: E402
from judge_primary import numeric_gate  # noqa: E402
from memory_runner import validate_operations  # noqa: E402
sys.path.insert(0, str(STUDY / 'tools'))
from apply_main_amendment_20261110 import A8_BULLET  # noqa: E402

problems = []
stats = Counter()


def bad(task, msg):
    problems.append('%s: %s' % (task, msg))


def setp(obj, path, v):
    ks = path.split('.'); o = obj
    for k in ks[:-1]:
        o = o.setdefault(k, {})
    o[ks[-1]] = v


def synthetic(gold):
    if gold.get('scoring') == 'refusal':
        toks = gold.get('refusal_tokens') or ['chưa có']
        ans = {'value': None, 'reason': 'Dữ liệu %s tại snapshot.' % toks[0], 'source': 'x'}
        for e in gold.get('refusal_assertions', []):
            setp(ans, e['path'], e['accept'][0])
        return ans
    ans = {}
    for e in gold.get('expects', []):
        t = e['type']
        if t == 'value':
            setp(ans, e['path'], e['gold'])
        elif t == 'period':
            setp(ans, e['path'], ' – '.join(e['accept']) if len(e['accept']) == 2 and '/' in e['accept'][0] and e['accept'][0][:2] != e['accept'][1][:2] else e['accept'][0])
        elif t == 'verdict':
            setp(ans, e['path'], e['accept'][0])
        elif t in ('unit', 'str', 'tokens'):
            setp(ans, e['path'], e['accept'][0])
        elif t == 'str_all':
            setp(ans, e['path'], ' + '.join(e['accept']))
        elif t in ('set', 'list_order'):
            setp(ans, e['path'], e['gold'])
        elif t == 'evidence':
            setp(ans, e['path'], ' '.join(str(x) for x in e.get('numbers', [])) + ' ' + ' '.join(e.get('strings', [])))
    return ans


def grade(task, ans):
    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / 'a.json'; o = Path(tmp) / 'g.json'
        a.write_text(json.dumps(ans, ensure_ascii=False))
        subprocess.run([sys.executable, str(task / 'tests/grader.py'), str(a), '-g', str(task / 'solution/gold.json'), '-o', str(o)],
                       capture_output=True)
        return json.loads(o.read_text())


def head(task):
    text = (task / 'instruction.md').read_text()
    body = text.split('## Ràng buộc chung')[0]
    return re.sub(r'\s+', ' ', re.sub(r'^#.*\n', '', body, count=1)).strip()


def check(task):
    split = task.parent.name
    e = task_eligibility(task)
    if not e['confirmatory_eligible']:
        bad(task.name, 'not eligible: %s' % e['exclusion_reason']); return
    gold = json.loads((task / 'solution/gold.json').read_text())
    stratum = gold.get('stratum', 'core')
    stats[(split, stratum)] += 1
    # oracle
    r = subprocess.run([sys.executable, str(task / 'solution/oracle.py')], capture_output=True, text=True)
    if r.returncode or 'ORACLE OK' not in r.stdout:
        bad(task.name, 'oracle: ' + (r.stdout + r.stderr)[-200:])
    # grader + numeric gate on synthetic gold, and perturbation
    ans = synthetic(gold)
    g = grade(task, ans)
    if not g.get('semantic_correctness'):
        fails = [c['check'] for c in g.get('checks', []) if not c['pass'] and c['check'] != 'provenance']
        bad(task.name, 'gold answer fails grader %s' % fails)
    txt = '```json\n' + json.dumps(ans, ensure_ascii=False) + '\n```'
    if gold.get('scoring') != 'refusal' and not numeric_gate(txt, gold):
        bad(task.name, 'gold answer fails numeric gate')
    vals = [x for x in gold.get('expects', []) if x['type'] == 'value']
    if vals:
        x = vals[0]; w = json.loads(json.dumps(ans)); setp(w, x['path'], x['gold'] + max(abs(x['gold']) * 0.05, 1.0))
        if grade(task, w).get('semantic_correctness'):
            bad(task.name, 'perturbed value still passes grader (%s)' % x['path'])
    # public contract
    text = (task / 'instruction.md').read_text()
    if not isinstance(public_success_example(text), dict):
        bad(task.name, 'public JSON example does not parse')
    if stratum != 'memory' and A8_BULLET not in text:
        bad(task.name, 'A8 bullet missing')
    # payloads served + provenance
    entries, _ = load_entries(task / 'environment/payloads.json')
    build_tool_defs(entries)
    served = {}
    for k, item in entries:
        env = select_envelope(entries, item['tool'], item['params'])
        served[k] = digest(env)
    for p in gold.get('provenance_contract', []):
        if served.get(p['matched_entry_id']) != p['response_sha256']:
            bad(task.name, 'provenance hash mismatch ' + p['matched_entry_id'])
    for k in gold.get('required_payload_keys', []):
        if k not in served:
            bad(task.name, 'required payload missing ' + k)
    # memory turns
    if stratum == 'memory':
        spec = json.loads((task / 'environment/turns.json').read_text())
        state = {'entries': {}}
        finals = 0
        for s in spec['sessions']:
            for t in s['turns']:
                ops = t.get('memory_operations', [])
                try:
                    validate_operations(t['text'], ops, state)
                except ValueError as exc:
                    bad(task.name, 'memory op: %s' % exc)
                for op in ops:
                    state['entries'][op['id']] = {'deleted': op['op'] == 'delete'}
                finals += bool(t.get('final'))
        if finals != 1 or not spec['sessions'][-1]['turns'][-1].get('final'):
            bad(task.name, 'memory final turn')
        if 'benchmark_user_notebook_read' in json.dumps(spec, ensure_ascii=False):
            bad(task.name, 'shared notebook referenced')
    # gold leak: distinctive solution numbers (>=4 significant digits) must not appear in the instruction
    nums = []
    def walk(v):
        if isinstance(v, dict):
            [walk(x) for x in v.values()]
        elif isinstance(v, list):
            [walk(x) for x in v]
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            nums.append(v)
    walk(gold.get('solution', {}))
    q = head(task)
    for n in nums:
        s = ('%g' % n)
        if len(s.replace('-', '').replace('.', '').lstrip('0')) >= 4 and re.search(r'(?<![\d.])' + re.escape(s) + r'(?![\d])', q):
            bad(task.name, 'possible gold leak %s' % s)
    return head(task)


def main():
    heads = {}
    for split in ('main', 'holdout'):
        for task in sorted((STUDY / 'tasks' / split).iterdir()):
            if task.is_dir():
                h = check(task)
                if h:
                    heads.setdefault(h, []).append(split + '/' + task.name)
    dup_cross = [v for v in heads.values() if len({x.split('/')[0] for x in v}) > 1]
    dup_within = [v for v in heads.values() if len(v) > 1 and len({x.split('/')[0] for x in v}) == 1]
    for v in dup_cross:
        problems.append('question duplicated across main/holdout: %s' % v)
    print('composition', dict(stats))
    print('duplicate questions within a split:', len(dup_within), dup_within[:5])
    print('problems', len(problems))
    for p in problems:
        print('  -', p)


if __name__ == '__main__':
    main()
