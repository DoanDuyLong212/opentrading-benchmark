"""Seal reviewed native changes. Does not write to the installed OpenTrading project."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent.parent
baseline=json.loads((root/'experiments/opentrading-source-baseline.json').read_text())
paths=['src/core/agent.ts','src/core/prompt/assemble.ts','prompts/identity.md','prompts/tools.md','prompts/citations.md','prompts/style.md','test/agent.test.ts','test/prompt.test.ts','test/financial-prompt.test.ts']
records={p:{'before_sha256':baseline['tracked_worktree_sha256'].get(p),'after_sha256':hashlib.sha256((root/'experiments/opentrading-runtime'/p).read_bytes()).hexdigest()}for p in paths}
(root/'experiments/opentrading-install-manifest.json').write_text(json.dumps({'destination':baseline['source'],'files':records},indent=2)+'\n')
print('Sealed',len(records),'reviewed source/prompt/test files')
