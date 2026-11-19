"""Build the v4.7 shell sandbox image and record local provenance.

The repository cannot claim a registry digest for an image it does not publish.
This script records what was actually built: Dockerfile hash, Docker server
version, the locally built image ID, and the package inventory observed inside a
no-network container. `--check` re-validates an existing receipt without
building. It never rewrites bench_config; promoting a new image is a separate
reviewed change.
"""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SANDBOX = ROOT / 'tools/runners/sandbox'
DEFAULT_RECEIPT = SANDBOX / 'build-receipt.json'
PACKAGE_PROBE = (
    "import json,numpy,pandas;"
    "print(json.dumps({'numpy':numpy.__version__,'pandas':pandas.__version__}))"
)


def run(argv, **kw):
    return subprocess.run(argv, check=True, text=True, capture_output=True, **kw)


def docker_server_version():
    return run(['docker', 'version', '--format', '{{.Server.Version}}']).stdout.strip()


def image_inspect(tag):
    data = json.loads(run(['docker', 'image', 'inspect', tag]).stdout)[0]
    return {
        'image_id': data['Id'],
        'architecture': data.get('Architecture'),
        'os': data.get('Os'),
        'created': data.get('Created'),
    }


def package_inventory(tag):
    out = run(['docker', 'run', '--rm', '--network', 'none', tag, 'python', '-c', PACKAGE_PROBE]).stdout
    return json.loads(out)


def dockerfile_hash():
    return hashlib.sha256((SANDBOX / 'Dockerfile').read_bytes()).hexdigest()


def base_reference():
    match = re.search(r'^FROM\s+(\S+)', (SANDBOX / 'Dockerfile').read_text(encoding='utf-8'), re.M)
    if not match:
        raise ValueError('Dockerfile has no FROM line')
    return match.group(1)


def build(tag, receipt_path):
    receipt = {
        'schema': 1,
        'scope': 'local image provenance; not a registry digest or bit-identical build claim',
        'tag': tag,
        'dockerfile': 'tools/runners/sandbox/Dockerfile',
        'dockerfile_sha256': dockerfile_hash(),
        'base_reference': base_reference(),
        'docker_server_version': docker_server_version(),
        'platform': f"{run(['docker', 'version', '--format', '{{.Server.Os}}/{{.Server.Arch}}']).stdout.strip()}",
        'build_command': f'docker build -t {tag} tools/runners/sandbox',
        'built_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    run(['docker', 'build', '-t', tag, str(SANDBOX)])
    receipt.update(image_inspect(tag))
    receipt['packages'] = package_inventory(tag)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return receipt


def check(tag, receipt_path):
    if not receipt_path.is_file():
        raise SystemExit(f'missing receipt: {receipt_path}')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    problems = []
    if receipt.get('dockerfile_sha256') != dockerfile_hash():
        problems.append('Dockerfile changed since receipt')
    current = image_inspect(receipt.get('tag', tag))
    if receipt.get('image_id') != current['image_id']:
        problems.append('local image ID differs from receipt (rebuild or stale receipt)')
    if receipt.get('packages') != package_inventory(receipt.get('tag', tag)):
        problems.append('package inventory differs from receipt')
    if problems:
        raise SystemExit('sandbox receipt check failed: ' + '; '.join(problems))
    print('sandbox receipt check passed:', receipt['tag'], receipt['image_id'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', default='ot-bench-shell:v47')
    parser.add_argument('--receipt', type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument('--check', action='store_true', help='validate receipt without building')
    args = parser.parse_args(argv)
    if args.check:
        check(args.tag, args.receipt)
    else:
        build(args.tag, args.receipt)
    return 0


if __name__ == '__main__':
    sys.exit(main())
