#!/usr/bin/env python3
"""
check_workflow.py - scan exported n8n workflow JSON files for secrets and personal data
before you commit them to a public repository.

Usage:
  python scripts/check_workflow.py workflows/*.json            # report only
  python scripts/check_workflow.py --fix workflows/*.json      # also write *.sanitized.json

Exit code: 0 = clean, 1 = findings (so you can use it in CI or a pre-commit hook).
Standard library only. Review the output yourself; no scanner catches everything.
"""
import json, re, sys, copy, pathlib

PATTERNS = {
    'Stripe key':            re.compile(r'\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{8,}'),
    'OpenAI-style key':      re.compile(r'\bsk-[A-Za-z0-9_\-]{20,}'),
    'Anthropic key':         re.compile(r'\bsk-ant-[A-Za-z0-9_\-]{20,}'),
    'Airtable token':        re.compile(r'\bpat[A-Za-z0-9]{10,}\.[A-Za-z0-9]{20,}'),
    'Bearer token':          re.compile(r'Bearer\s+[A-Za-z0-9._\-]{20,}'),
    'Slack/Telegram token':  re.compile(r'\b(?:xox[abp]-[A-Za-z0-9\-]{10,}|[0-9]{8,10}:[A-Za-z0-9_\-]{30,})'),
    'Google API key':        re.compile(r'\bAIza[0-9A-Za-z_\-]{30,}'),
    'Phone number':          re.compile(r'(?<![A-Za-z0-9-])\+?[0-9]{10,15}(?:@c\.us)?(?![A-Za-z0-9-])'),
    'Email address':         re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}'),
    'Google calendar id':    re.compile(r'[A-Za-z0-9]{20,}@group\.calendar\.google\.com'),
}
# Things that look like phones/emails but are harmless
ALLOW = [re.compile(r'^\+?1?0{10}$'), re.compile(r'YOUR_|REPLACE|example\.com')]

def walk(node, path=''):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f'{path}.{k}' if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f'{path}[{i}]')
    elif isinstance(node, str):
        yield path, node

def scan(data):
    findings = []
    if data.get('pinData'):
        findings.append(('pinData', 'pinData', f"{len(data['pinData'])} node(s) have pinned test data (often real messages and phone numbers)"))
    if data.get('active') is True:
        findings.append(('note', 'active', 'workflow is exported as active: set to false before sharing'))
    for path, s in walk({k: v for k, v in data.items() if k != 'pinData'}):
        for label, rx in PATTERNS.items():
            for m in rx.finditer(s):
                hit = m.group(0)
                if any(a.search(hit) for a in ALLOW):
                    continue
                findings.append((label, path, hit if len(hit) < 14 else hit[:6] + '...' + hit[-4:]))
    return findings

def sanitize(data):
    d = copy.deepcopy(data)
    d.pop('pinData', None)
    d['active'] = False
    d.pop('versionId', None)
    for key in ('id', 'shared'):
        d.pop(key, None)
    if isinstance(d.get('meta'), dict):
        d['meta'].pop('instanceId', None)
    def clean(node):
        if isinstance(node, dict):
            if 'credentials' in node and isinstance(node['credentials'], dict):
                for cred in node['credentials'].values():
                    if isinstance(cred, dict):
                        cred['id'] = 'REPLACE_WITH_YOUR_CREDENTIAL'
            return {k: clean(v) for k, v in node.items()}
        if isinstance(node, list):
            return [clean(v) for v in node]
        if isinstance(node, str):
            s = PATTERNS['Google calendar id'].sub('YOUR_CALENDAR_ID@group.calendar.google.com', node)
            s = PATTERNS['Phone number'].sub(lambda m: m.group(0) if any(a.search(m.group(0)) for a in ALLOW) else '+10000000000', s)
            s = re.sub(r'^[0-9a-f]{24}$', 'YOUR_WASSENGER_DEVICE_ID', s)   # Wassenger device ids
            return s
        return node
    return clean(d)

def main(argv):
    fix = '--fix' in argv
    files = [a for a in argv if not a.startswith('--')]
    if not files:
        print(__doc__); return 2
    bad = False
    for f in files:
        p = pathlib.Path(f)
        data = json.loads(p.read_text(encoding='utf-8'))
        found = scan(data)
        print(f'\n== {p.name}')
        if not found:
            print('   clean (no findings)')
        for label, path, detail in found:
            print(f'   [{label}] {path}: {detail}')
            if label != 'note': bad = True
        if fix:
            out = p.with_suffix('.sanitized.json')
            out.write_text(json.dumps(sanitize(data), indent=2, ensure_ascii=False), encoding='utf-8')
            again = scan(json.loads(out.read_text(encoding='utf-8')))
            left = [x for x in again if x[0] != 'note']
            print(f'   wrote {out.name}: {len(left)} finding(s) remain after sanitizing')
            for label, path, detail in left:
                print(f'      still present [{label}] {path}: {detail}')
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
