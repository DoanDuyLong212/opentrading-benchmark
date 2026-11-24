#!/usr/bin/env python3
"""Validate the immutable historical PRUNE receipt; never reselect or delete tasks.

The original selection followed or16 outcomes. Its historical receipt preserves
its original wording, which does not establish a model-independent absence of
selection bias. See the methodology decision packet for that limitation.
"""
import argparse
import collections
import hashlib
import json
import tomllib
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
RECEIPT = STUDY / 'audits/taskset-revision-2026-11-16/PRUNE.json'
PRUNE_SHA256 = 'd9b5378ff2543e4d29da3276ca97b54282854476ad02ad58d4ec141cdba2a8ec'
INVENTORY_SHA256 = '57bee63662f0fc6dfc416cfc8ddd20615cfb9ac5f6f196f41b5964e81c571eeb'
EXPECTED = {'main': {'lookup': 100, 'compute': 40, 'memory': 30, 'safety': 30},
            'holdout': {'lookup': 36, 'compute': 7, 'memory': 7, 'safety': 8}}


def validate_prune(receipt=RECEIPT, study=STUDY):
    raw = Path(receipt).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRUNE_SHA256:
        raise ValueError('PRUNE receipt differs from frozen historical hash; no reselection permitted')
    frozen = json.loads(raw)
    dropped = frozen['dropped']
    if len(dropped) != 40 or dropped != sorted(set(dropped)):
        raise ValueError('PRUNE must contain exactly 40 unique sorted IDs')
    if set(dropped) & set(frozen['kept_named_by_tools_or_tests']):
        raise ValueError('PRUNE protected IDs overlap dropped IDs')
    composition, inventory = {}, {}
    main_families = collections.Counter()
    for split, expected in EXPECTED.items():
        counts = collections.Counter()
        inventory[split] = []
        for task in sorted((Path(study) / 'tasks' / split).iterdir()):
            if not task.is_dir():
                continue
            if split == 'main' and task.name in dropped:
                raise ValueError('Frozen dropped task has returned to main: ' + task.name)
            inventory[split].append(task.name)
            meta = tomllib.loads((task / 'task.toml').read_text(encoding='utf-8'))
            stratum = meta.get('stratum', 'lookup')
            counts[stratum] += 1
            if split == 'main':
                main_families[meta.get('family', '?')] += 1
        # The 16/11 composition/inventory below describe that revision. PRUNE2 (2026-11-24, owner decision #13)
        # retired more tasks and added C5/M6; current composition is validated by tools/prune_saturated_20261124.py.
        composition[split] = dict(counts)
    inventory_hash = hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if composition['holdout'] != EXPECTED['holdout']:
        raise ValueError('Frozen composition mismatch in holdout: ' + repr(composition['holdout']))
    return {'valid': True, 'inventory_sha256': inventory_hash, 'prune_sha256': PRUNE_SHA256, 'dropped': dropped,
            'composition': composition, 'mutation_performed': False,
            'methodology_approval': 'owner decision 2026-11-24 (#13); superseded for main by PRUNE2'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='read-only validation; all modes are nonmutating')
    args = parser.parse_args()
    print(json.dumps(validate_prune(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
