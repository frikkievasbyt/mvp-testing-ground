#!/usr/bin/env python3
"""Seed/update coffee YAML files from Obsidian research list.

Input expected format per item in markdown:
1. **Shop Name**
   - Address: ...
"""

from pathlib import Path
import re
import unicodedata

SOURCE = Path('/Users/frikkievasbyt/Documents/Obsidian/memory/Research/George Coffee Shops - Verified Pass 2.md')
OUT_DIR = Path('/Users/frikkievasbyt/.openclaw/workspace/george-directory-site/data/businesses/coffee')


def slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-zA-Z0-9]+', '-', text).strip('-').lower()
    return text


def parse_items(md: str):
    pattern = re.compile(r'^\d+\.\s+\*\*(.+?)\*\*\s*$\n\s*-\s+Address:\s+(.+?)\s*$', re.M)
    return pattern.findall(md)


def build_yaml(name: str, address: str) -> str:
    slug = slugify(name)
    q = name.replace(' ', '+') + '+George'
    return f"""slug: {slug}
name: {name}
category: coffee_shop
subcategories: [coffee_shop]
address:
  street: null
  suburb: null
  city: "George"
  postal_code: null
  full: "{address.replace('"', '\\"')}"
  latitude: null
  longitude: null
contact:
  phone: null
  whatsapp: null
  email: null
links:
  website: null
  facebook: null
  instagram: null
  menu: null
  google_maps: "https://www.google.com/maps/search/?api=1&query={q}"
hours: []
photos: []
verification:
  last_verified_at: "2026-04-18"
  confidence: "low"
  sources:
    - "Obsidian Research Pass 2"
notes: "Auto-seeded from research list. Fill details manually."
"""


def main():
    if not SOURCE.exists():
        raise SystemExit(f'Missing source file: {SOURCE}')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    items = parse_items(SOURCE.read_text(encoding='utf-8'))

    created = 0
    for name, address in items:
        slug = slugify(name)
        out = OUT_DIR / f'{slug}.yaml'
        if out.exists():
            continue
        out.write_text(build_yaml(name, address), encoding='utf-8')
        created += 1

    print(f'Parsed {len(items)} items, created {created} new YAML files.')


if __name__ == '__main__':
    main()
