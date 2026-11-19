"""Offline-validated paid admission and durable, fail-closed USD accounting.

Receipts are reviewed inputs, not a claim that this module queried a provider.
OpenRouter usage.cost is total account charge:
https://openrouter.ai/docs/cookbook/administration/usage-accounting
"""
import contextlib
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
import fcntl
import hashlib
import json
import os
from pathlib import Path
import uuid


class BudgetError(ValueError):
    pass


def usd(value, positive=False):
    if isinstance(value, bool) or value is None:
        raise BudgetError('USD amount must be finite and nonnegative')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise BudgetError('USD amount must be finite and nonnegative')
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise BudgetError('USD amount must be finite and positive' if positive else 'USD amount must be finite and nonnegative')
    return result


def total_usd(values):
    values = list(values)
    # Exact addition even when provider JSON has more digits than the ambient
    # Decimal context; never round an admission comparison downward.
    precision = max([28] + [len(v.as_tuple().digits) + abs(v.as_tuple().exponent) for v in values]) + len(str(len(values))) + 2
    with localcontext() as context:
        context.prec = precision
        return sum(values, Decimal(0))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def fsync_directory(path):
    fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic(path, value):
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temp.open('xb') as fp:
        fp.write(canonical(value) + b'\n'); fp.flush(); os.fsync(fp.fileno())
    temp.chmod(0o600)
    os.replace(temp, path)
    fsync_directory(path.parent)


def paid_policy(model, options, *, require_current=True):
    """Validate reviewed evidence before credentials, runtime preparation or dispatch.

    The approval hash must come from the separately reviewed frozen configuration.
    This intentionally cannot bootstrap approval from the receipt itself.
    """
    if options.get('provider_route') != 'openrouter_paid':
        return None
    cap = usd(options.get('budget_usd'), positive=True)
    receipt_path = options.get('paid_budget_receipt')
    approved_hash = options.get('paid_budget_receipt_sha256')
    if not receipt_path or not approved_hash:
        raise BudgetError('paid route requires separately approved key-limit and worst-case bound receipt')
    raw = Path(receipt_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != approved_hash:
        raise BudgetError('paid receipt differs from approved hash')
    receipt = json.loads(raw)
    now = datetime.now(timezone.utc)
    try:
        verified = datetime.fromisoformat(receipt['verified_at'].replace('Z', '+00:00'))
        expires = datetime.fromisoformat(receipt['expires_at'].replace('Z', '+00:00'))
        valid_time = verified < expires and 0 < (expires - verified).total_seconds() <= 86400
        if require_current:
            valid_time = valid_time and verified <= now < expires
    except (ValueError, KeyError, TypeError):
        valid_time = False
    if not valid_time or receipt.get('status') != 'reviewed_provider_evidence':
        raise BudgetError('paid receipt must have current reviewed provider evidence (maximum 24h)')
    if receipt.get('model') != model or receipt.get('route') != 'openrouter_paid':
        raise BudgetError('paid receipt model/route mismatch')
    if receipt.get('endpoint') != 'https://openrouter.ai/api/v1/chat/completions' or not receipt.get('provider_host'):
        raise BudgetError('paid receipt requires exact endpoint and pinned provider host')
    key = receipt.get('key_limit', {})
    # Names below are the actual GET /api/v1/key fields; the surrounding receipt
    # adds reviewed provenance, allocation and dedicated-key assertions.
    # https://openrouter.ai/docs/api_reference/limits
    if key.get('limit_reset') is not None or 'limit_reset' not in key:
        raise BudgetError('paid key limit must be lifetime, without reset')
    limit, remaining, used = (usd(key.get(k)) for k in ('limit', 'limit_remaining', 'usage'))
    if not (0 < cap <= remaining <= limit) or total_usd([used, remaining]) > limit:
        raise BudgetError('paid allocation exceeds verified remaining key limit')
    if receipt.get('dedicated_key') is not True or receipt.get('byok_disabled') is not True:
        raise BudgetError('paid receipt requires dedicated key and BYOK disabled')
    for field in ('key_fingerprint', 'key_response_sha256', 'bound_evidence_sha256'):
        value = receipt.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise BudgetError('paid receipt missing evidence hash: ' + field)
    bound = usd(receipt.get('attempt_upper_bound_usd'), positive=True)
    output = options.get('max_output_tokens')
    output = options.get('model_max_output_tokens') if output is None else output
    context = options.get('failed_attempt_context_bound')
    if (not isinstance(output, int) or isinstance(output, bool) or output <= 0 or
            not isinstance(context, int) or isinstance(context, bool) or context <= 0 or
            receipt.get('context_tokens') != context or receipt.get('output_tokens') != output or
            receipt.get('bound_scope') != 'all_billable_text_features_no_cache_discount' or
            not receipt.get('bound_evidence')):
        raise BudgetError('paid upper bound must cover actual full context/output and all billable text features')
    allocation = Path(str(receipt.get('allocation_path', '')))
    if not allocation.is_absolute() or str(allocation.resolve()) != str(allocation):
        raise BudgetError('paid receipt requires canonical absolute durable allocation path')
    return {'cap_usd': str(cap), 'attempt_upper_bound_usd': str(bound),
            'receipt_sha256': approved_hash, 'key_fingerprint': receipt['key_fingerprint'],
            'allocation_path': str(allocation), 'provider_host': receipt['provider_host'],
            'model': model, 'route': 'openrouter_paid', 'service_tier': 'default'}


def validate_free_identity(model, options):
    if options.get('provider_route') != 'openrouter_free':
        return None
    if not isinstance(model, str) or not model.endswith(':free') or '/' not in model:
        raise BudgetError('free exemption requires the exact admitted zero-price model/route')
    # Canonical, reviewed study admission; a route flag or external asserted file
    # cannot exempt an arbitrary paid identity from dollar accounting.
    name = 'openrouter__' + model.split('/', 1)[1].replace(':', '-') + '.json'
    path = Path(__file__).resolve().parents[1] / 'audits/model-admission' / name
    try:
        raw = path.read_bytes()
        receipt = json.loads(raw)
        price = receipt.get('pricing_verified', {})
        if (receipt.get('route') != 'openrouter_free' or receipt.get('model_requested') != model or
                receipt.get('returned_model') != model or receipt.get('user_authorized') is not True or
                'PASS' not in str(receipt.get('probes')) or not receipt.get('probes_detail') or
                usd(price.get('prompt')) != 0 or usd(price.get('completion')) != 0):
            raise BudgetError('invalid zero-price exact identity admission')
        sha = hashlib.sha256(raw).hexdigest()
        if options.get('free_admission_sha256', sha) != sha:
            raise BudgetError('free admission changed after configuration freeze')
        return sha
    except (OSError, ValueError, TypeError) as exc:
        raise BudgetError('free exemption requires canonical admitted zero-price identity: ' + str(exc)) from exc


class PaidBudget:
    """One allocation owner and journal shared by every run dispatch.

    The allocation checkpoint is written and fsynced BEFORE each append. A crash
    between those writes deliberately requires audited recovery; it never resets
    money. The checkpoint detects missing/suffix-truncated journals as well as
    the journal's hash chain detecting interior edits. Never delete these files.
    """
    def __init__(self, path, contract, initialize=False):
        self.path = Path(path).resolve()
        self.contract = contract
        self.read_only = False
        self.allocation = Path(contract['policy']['allocation_path'])
        self.lockpath = self.allocation.with_name(self.allocation.name + '.lock')
        if not self.allocation.parent.is_dir():
            raise BudgetError('durable allocation directory must already exist')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.locked():
            if initialize and not self.allocation.exists() and not self.path.exists():
                self._append([], {'kind': 'init', 'contract': contract})
            self._read()

    @contextlib.contextmanager
    def locked(self):
        with self.lockpath.open('a+b') as fp:
            os.chmod(self.lockpath, 0o600)
            fcntl.flock(fp, fcntl.LOCK_EX)
            yield

    def _read(self):
        try:
            anchor = json.loads(self.allocation.read_bytes())
            raw = self.path.read_bytes()
            if not raw.endswith(b'\n'):
                raise BudgetError('truncated paid journal')
            rows = [json.loads(line) for line in raw.splitlines()]
            previous = '0' * 64
            for seq, row in enumerate(rows):
                if row['seq'] != seq or row['previous'] != previous or row['sha256'] != digest({k: v for k, v in row.items() if k != 'sha256'}):
                    raise BudgetError('paid journal chain invalid')
                previous = row['sha256']
            if (not rows or rows[0]['kind'] != 'init' or rows[0]['contract'] != self.contract or
                    anchor != {'journal': str(self.path), 'contract_sha256': digest(self.contract),
                               'seq': len(rows)-1, 'sha256': previous}):
                raise BudgetError('paid allocation/journal identity or checkpoint mismatch')
            self._state(rows)
            return rows
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise BudgetError('paid journal missing, corrupt or incompatible; explicit reconciliation required: ' + str(exc)) from exc

    def _append(self, rows, event):
        event = {**event, 'seq': len(rows), 'previous': rows[-1]['sha256'] if rows else '0'*64}
        event['sha256'] = digest(event)
        anchor = {'journal': str(self.path), 'contract_sha256': digest(self.contract),
                  'seq': event['seq'], 'sha256': event['sha256']}
        atomic(self.allocation, anchor)
        with self.path.open('ab') as fp:
            fp.write(canonical(event) + b'\n'); fp.flush(); os.fsync(fp.fileno())
        self.path.chmod(0o600)
        fsync_directory(self.path.parent)

    def _state(self, rows):
        pending, settled = {}, {}
        measured = Decimal(0)
        breach = False
        for row in rows[1:]:
            if row['kind'] == 'halt':
                if not isinstance(row.get('reason'), str) or not row['reason']:
                    raise BudgetError('invalid paid halt event')
                continue
            identity = row['attempt_id']
            if row['kind'] == 'reserve':
                if identity in pending or identity in settled:
                    raise BudgetError('duplicate paid reservation')
                pending[identity] = usd(row['reserved_usd'], positive=True)
            elif row['kind'] == 'settle':
                if identity not in pending:
                    raise BudgetError('settlement has no pending reservation')
                cost = usd(row['cost_usd'])
                breach = breach or cost > pending.pop(identity)
                measured = total_usd([measured, cost])
                settled[identity] = row
            else:
                raise BudgetError('unknown paid journal event')
        breach = breach or measured > usd(self.contract['policy']['cap_usd'])
        return pending, settled, measured, breach

    def check_available(self):
        with self.locked():
            rows = self._read()
            pending, _, measured, breach = self._state(rows)
            if pending or breach or any(r['kind'] == 'halt' for r in rows):
                raise BudgetError('paid dispatch blocked: unresolved charge or measured bound breach')
            if total_usd([measured, usd(self.contract['policy']['attempt_upper_bound_usd'])]) > usd(self.contract['policy']['cap_usd']):
                raise BudgetError('paid USD budget exhausted')

    def reserve(self, metadata):
        if self.read_only: raise BudgetError("accounting-only budget cannot reserve")
        with self.locked():
            rows = self._read()
            pending, _, measured, breach = self._state(rows)
            bound = usd(self.contract['policy']['attempt_upper_bound_usd'], positive=True)
            if pending or breach or any(r['kind'] == 'halt' for r in rows):
                raise BudgetError('paid dispatch blocked: unresolved charge or measured bound breach')
            if total_usd([measured, *pending.values(), bound]) > usd(self.contract['policy']['cap_usd']):
                raise BudgetError('paid USD budget exhausted')
            identity = uuid.uuid4().hex
            self._append(rows, {'kind': 'reserve', 'attempt_id': identity, 'reserved_usd': str(bound), 'metadata': metadata})
            return identity

    def settle(self, identity, cost, evidence):
        if self.read_only: raise BudgetError("accounting-only budget cannot settle")
        cost = usd(cost)
        with self.locked():
            rows = self._read()
            pending, settled, _, _ = self._state(rows)
            event = {'kind': 'settle', 'attempt_id': identity, 'cost_usd': str(cost), 'evidence': evidence}
            if identity in settled:
                if any(settled[identity].get(k) != v for k, v in event.items()):
                    raise BudgetError('conflicting paid settlement')
                return
            if identity not in pending:
                raise BudgetError('unknown paid attempt')
            self._append(rows, event)
            if self._state(rows + [{**event}])[3]:
                raise BudgetError('measured paid charge breached approved upper bound; cohort stopped')

    def halt(self, reason):
        if self.read_only: raise BudgetError("accounting-only budget cannot mutate")
        with self.locked():
            rows = self._read()
            if not any(r.get('kind') == 'halt' and r.get('reason') == reason for r in rows):
                self._append(rows, {'kind': 'halt', 'reason': reason})

    def summary(self):
        with self.locked():
            rows = self._read()
            pending, settled, measured, breach = self._state(rows)
            return {'measured_cost_usd': str(measured), 'settled_requests': len(settled),
                    'reserved_usd': str(total_usd(pending.values())),
                    'unknown_requests': len(pending), 'complete': not pending,
                    'bound_breached': breach, 'halted': any(r['kind'] == 'halt' for r in rows),
                    'halt_reasons': [r['reason'] for r in rows if r['kind'] == 'halt'], 'source': 'OpenRouter usage.cost'}


def open_run_budget(out_dir, manifest_fingerprint, model, options, resume=False, *, accounting_only=False):
    policy = paid_policy(model, options, require_current=not accounting_only)
    if accounting_only and not resume:
        raise BudgetError("accounting-only access cannot initialize an allocation")
    if policy is None:
        validate_free_identity(model, options)
        return None
    contract = {'schema': 1, 'manifest_sha256': manifest_fingerprint,
                'run': str(Path(out_dir).resolve()), 'policy': policy}
    path = Path(out_dir).resolve() / 'paid-budget.jsonl'
    budget = PaidBudget(path, contract, initialize=not resume)
    budget.read_only = accounting_only
    options['paid_budget_journal'] = str(path)
    options['paid_budget_contract'] = contract
    return budget
