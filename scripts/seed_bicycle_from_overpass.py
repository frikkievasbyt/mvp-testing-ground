#!/usr/bin/env python3
import json
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

import yaml

REPO = Path('/Users/frikkievasbyt/Documents/git-repos/mvp-testing-ground')
OUT_DIR = REPO / 'data' / 'businesses' / 'bicycle'


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text


def overpass_fetch():
    query = '[out:json][timeout:90];(nwr["shop"="bicycle"](around:35000,-33.9649,22.4594););out center tags;'
    endpoints = [
        'https://overpass-api.de/api/interpreter',
        'https://overpass.kumi.systems/api/interpreter',
    ]

    for ep in endpoints:
        try:
            out = subprocess.check_output([
                'curl', '-sS', '--data-urlencode', f'data={query}', ep
            ], text=True, timeout=120)
            return json.loads(out).get('elements', [])
        except Exception:
            continue

    return []


def reverse_city(lat: float, lon: float):
    url = f'https://nominatim.openstreetmap.org/reverse?format=jsonv2&addressdetails=1&lat={lat}&lon={lon}&zoom=18'
    out = subprocess.check_output([
        'curl', '-sS', '-A', 'OpenClaw-Seed/1.0', '--max-time', '12', url
    ], text=True, timeout=20)
    j = json.loads(out)
    a = j.get('address', {})
    city = a.get('city') or a.get('town') or a.get('village') or ''
    return city, j.get('display_name', '')


def build_record(name: str, full_addr: str, lat: float, lon: float, phone: str, website: str):
    return {
        'slug': slugify(name),
        'name': name,
        'category': 'bicycle_shop',
        'subcategories': ['bicycle'],
        'address': {
            'street': None,
            'suburb': None,
            'city': 'George',
            'postal_code': None,
            'full': full_addr,
            'latitude': lat,
            'longitude': lon,
        },
        'contact': {
            'phone': phone or None,
            'whatsapp': None,
            'email': None,
        },
        'links': {
            'website': website or None,
            'facebook': None,
            'instagram': None,
            'menu': None,
            'google_maps': f'https://www.google.com/maps/search/?api=1&query={quote(name + " " + full_addr)}',
        },
        'hours': [],
        'photos': [],
        'verification': {
            'last_verified_at': str(time.strftime('%Y-%m-%d')),
            'confidence': 'medium',
            'score': 70,
            'publish_ready': True,
            'sources': ['OpenStreetMap Overpass', 'Nominatim'],
        },
        'notes': 'Auto-seeded bicycle listing from free-source pipeline.',
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    els = overpass_fetch()

    seen = set()
    created = 0
    for el in els:
        tags = el.get('tags', {})
        name = tags.get('name')
        if not name:
            continue

        lat = el.get('lat') or (el.get('center') or {}).get('lat')
        lon = el.get('lon') or (el.get('center') or {}).get('lon')
        if lat is None or lon is None:
            continue

        try:
            city, display = reverse_city(float(lat), float(lon))
            time.sleep(1.0)
        except Exception:
            city, display = '', ''

        # Keep George-only core scope, exclude nearby non-George towns
        dlow = display.lower()
        if 'sedgefield' in dlow or 'knysna' in dlow:
            continue
        if city.lower() != 'george' and 'george' not in dlow:
            continue

        key = name.strip().lower()
        if key in seen:
            continue
        seen.add(key)

        full = tags.get('addr:full') or display or 'George'
        phone = tags.get('phone') or tags.get('contact:phone')
        website = tags.get('website') or tags.get('contact:website')

        rec = build_record(name.strip(), full.strip(), float(lat), float(lon), phone, website)
        out = OUT_DIR / f"{rec['slug']}.yaml"
        out.write_text(yaml.safe_dump(rec, sort_keys=False, allow_unicode=True), encoding='utf-8')
        created += 1

    print(f'Created {created} bicycle shop records in {OUT_DIR}')


if __name__ == '__main__':
    main()
