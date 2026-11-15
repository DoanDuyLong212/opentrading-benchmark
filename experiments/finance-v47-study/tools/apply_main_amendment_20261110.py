#!/usr/bin/env python3
"""Main amendment 2026-11-10 (user-approved): corpus + config changes before the B0 study seal.

1. A8: add one bullet to the common v4.6u contract block of every non-memory, non-devsmoke
   study instruction: `period` holds only the asked data period (no snapshot/as_of date).
   Devsmoke is deliberately untouched so the audited or7 devsmoke cohort remains an honest
   prerequisite.
2. Migrate the canonical root holdout (60 tasks) into the study: the 50 financial tasks get the
   v4.6u contract suffix (+A8) and the study financial grader; the 10 memory tasks already exist.
3. Config: gate b0_judge_primary, arms_main = B0/OpenCode/DSH, main allowed, request cap 8000,
   cost reporting from OpenRouter usage.cost.
Idempotent; registers files in audits/CORPUS-MIGRATION.json.
"""
import hashlib
import json
import shutil
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
ORIGIN = STUDY.parents[1]
T = STUDY / 'tasks'
OLD_SOURCE_BULLET = ('- `source` ghi đầy đủ tên các tool nguồn cần thiết để trả lời yêu cầu, gồm resolver nếu yêu cầu '
                     'phân giải tên/mã, ngăn bằng ` + `. Ghi tên tool chính xác, không thêm tiền tố harness; utility tính '
                     'toán được ghi ở lineage/note khi cần, không thay thế tool nguồn.\n')
A8_BULLET = ('- `period` chỉ ghi kỳ/ngày của dữ liệu được hỏi (VD `30/10/2026`, `Q3/2026`, hoặc hai kỳ khi đề yêu cầu '
             'so sánh); không ghi kèm ngày snapshot, thời điểm lấy dữ liệu hay `as_of` vào trường này.\n')
CHANGED = {}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(path, text):
    path = Path(path)
    if path.exists() and path.read_text(encoding='utf-8') == text:
        return
    CHANGED[str(path.relative_to(STUDY))] = sha(path) if path.exists() else None
    path.write_text(text, encoding='utf-8')


def add_a8(path):
    text = path.read_text(encoding='utf-8')
    if A8_BULLET in text:
        return
    if text.count(OLD_SOURCE_BULLET) != 1:
        raise SystemExit('%s: contract source bullet not found exactly once' % path)
    write(path, text.replace(OLD_SOURCE_BULLET, OLD_SOURCE_BULLET + A8_BULLET))


def contract_suffix():
    root = (ORIGIN / 'tasks/main/fin-l1-bctc-109/instruction.md').read_text(encoding='utf-8')
    study = (T / 'main/fin-l1-bctc-109/instruction.md').read_text(encoding='utf-8')
    assert study.startswith(root), 'reference pair diverged'
    return study[len(root):]


def migrate_holdout():
    suffix = contract_suffix()
    assert A8_BULLET in suffix
    grader = (T / 'main/fin-l1-bctc-109/tests/grader.py').read_text(encoding='utf-8')
    migrated = []
    for src in sorted((ORIGIN / 'tasks/holdout').iterdir()):
        if not src.is_dir() or src.name.startswith('fin-mem-'):
            continue
        dst = T / 'holdout' / src.name
        if not dst.exists():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__'))
            CHANGED[str((dst / 'instruction.md').relative_to(STUDY))] = None
        root_ins = (src / 'instruction.md').read_text(encoding='utf-8')
        write(dst / 'instruction.md', root_ins + suffix)
        write(dst / 'tests/grader.py', grader)
        for rel in ('solution/gold.json', 'solution/oracle.py', 'task.toml', 'environment/payloads.json'):
            if (src / rel).read_bytes() != (dst / rel).read_bytes():
                write(dst / rel, (src / rel).read_text(encoding='utf-8'))
        migrated.append(src.name)
    return migrated


def config():
    p = STUDY / 'tools/bench_config_deepseek_openrouter.json'
    cfg = json.loads(p.read_text())
    cfg.update({
        'gate': 'b0_judge_primary',
        'arms_main': ['opentrading_baseline', 'opencode', 'dsh'],
        'allowed_inference_splits': ['devsmoke', 'pilot', 'main'],
        'experiment_protocol_dependencies': ['plans/2026-11-10-v46u-judge-primary-amendment.md',
                                             'plans/2026-11-10-v46u-main-b0-amendment.md'],
        'cost_reporting': 'OpenRouter usage.cost per request (authoritative); price_per_1m is the published list price '
                          'and under-estimated or10 billing ~2.8x (0.1284 vs 0.3653 USD for 132 trials)',
    })
    cfg['provider_options']['openrouter_paid_budget'] = 8000
    write(p, json.dumps(cfg, ensure_ascii=False, indent=1))
    prov = STUDY / 'tools/runners/provider.py'
    text = prov.read_text(encoding='utf-8')
    new = text.replace('OPENROUTER_PAID_REQUEST_BUDGET = 1900', 'OPENROUTER_PAID_REQUEST_BUDGET = 8000')
    if new != text:
        write(prov, new)


def register(migrated):
    mp = STUDY / 'audits/CORPUS-MIGRATION.json'
    m = json.loads(mp.read_text())
    for rel, before in CHANGED.items():
        if not rel.startswith('tasks/'):
            continue
        entry = m['changed'].get(rel)
        root = ORIGIN / rel
        m['changed'][rel] = {'root_sha256': entry['root_sha256'] if entry else (sha(root) if root.exists() else None),
                             'study_sha256': sha(STUDY / rel)}
    m['holdout'] = ('60-task canonical holdout: 10 memory (batch-3) + 50 financial migrated 2026-11-10 with the v4.6u '
                    'contract suffix (+A8) and study grader; 11 former main replicas replaced first '
                    '(audits/gold-audit-2026-11-10/holdout-replacements.json)')
    m.setdefault('content_corrections', {})['main-amendment-2026-11-10'] = (
        'A8 period bullet in common contract (pilot/smoke/main/holdout; devsmoke untouched); holdout migration %d tasks'
        % len(migrated))
    mp.write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n')


def main():
    for split in ('pilot', 'smoke', 'main'):
        for ins in sorted((T / split).glob('*/instruction.md')):
            if (ins.parent / 'environment/turns.json').exists():
                continue
            add_a8(ins)
    migrated = migrate_holdout()
    for ins in sorted((T / 'holdout').glob('fin-l*/instruction.md')):
        add_a8(ins)
    config()
    register(migrated)
    print('changed files:', len(CHANGED), '| holdout migrated:', len(migrated))


if __name__ == '__main__':
    main()
