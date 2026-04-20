#!/usr/bin/env python3
from pathlib import Path
import yaml

REPO = Path('/Users/frikkievasbyt/Documents/git-repos/mvp-testing-ground')
DATA_DIR = REPO / 'data' / 'businesses' / 'coffee'
REPORT = REPO / 'data' / 'quality-report.md'


def load_records():
    out = []
    for p in sorted(DATA_DIR.glob('*.yaml')):
        d = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
        out.append((p, d))
    return out


def validate(path: Path, d: dict):
    issues = []
    addr = d.get('address') or {}
    contact = d.get('contact') or {}
    links = d.get('links') or {}
    ver = d.get('verification') or {}

    if not d.get('name'):
        issues.append('missing name')
    if not addr.get('full'):
        issues.append('missing full address')
    if addr.get('latitude') is None or addr.get('longitude') is None:
        issues.append('missing coordinates')
    if not (contact.get('phone') or links.get('website')):
        issues.append('missing both phone and website')
    if not links.get('google_maps'):
        issues.append('missing google_maps link')
    if not ver.get('last_verified_at'):
        issues.append('missing last_verified_at')
    if ver.get('confidence') not in {'high', 'medium', 'low'}:
        issues.append('invalid confidence')

    return issues


def main():
    rows = load_records()
    lines = ['# Quality Report', '', f'Total records: {len(rows)}', '']
    failed = 0

    for p, d in rows:
        issues = validate(p, d)
        if issues:
            failed += 1
            lines.append(f'## ⚠️ {d.get("name") or p.name}')
            for i in issues:
                lines.append(f'- {i}')
            lines.append('')

    if failed == 0:
        lines += ['All records passed quality gate.']

    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Quality report written: {REPORT}')
    print(f'Records with issues: {failed}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
