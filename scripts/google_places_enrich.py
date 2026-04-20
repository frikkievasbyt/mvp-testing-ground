#!/usr/bin/env python3
import os
import sys
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import yaml

REPO = Path('/Users/frikkievasbyt/Documents/git-repos/mvp-testing-ground')
DATA_DIR = REPO / 'data' / 'businesses' / 'coffee'
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '').strip()


def http_get_json(base_url: str, params: dict):
    url = f"{base_url}?{urlencode(params)}"
    with urlopen(url, timeout=25) as r:
        return json.loads(r.read().decode('utf-8'))


def places_text_search(query: str):
    payload = http_get_json(
        'https://maps.googleapis.com/maps/api/place/textsearch/json',
        {'query': query, 'key': API_KEY},
    )
    return payload.get('results', [])


def place_details(place_id: str):
    payload = http_get_json(
        'https://maps.googleapis.com/maps/api/place/details/json',
        {
            'place_id': place_id,
            'fields': ','.join([
                'name',
                'formatted_address',
                'formatted_phone_number',
                'international_phone_number',
                'website',
                'url',
                'geometry',
                'opening_hours',
                'rating',
                'user_ratings_total',
            ]),
            'key': API_KEY,
        },
    )
    return payload.get('result', {})


def score_confidence(record: dict):
    score = 0
    if record.get('address', {}).get('full'):
        score += 25
    if record.get('address', {}).get('latitude') and record.get('address', {}).get('longitude'):
        score += 20
    if record.get('contact', {}).get('phone'):
        score += 20
    if record.get('links', {}).get('website'):
        score += 20
    if record.get('hours'):
        score += 15
    if score >= 80:
        return 'high'
    if score >= 50:
        return 'medium'
    return 'low'


def upsert_source(record: dict, source: str):
    verification = record.setdefault('verification', {})
    sources = verification.setdefault('sources', [])
    if source not in sources:
        sources.append(source)


def enrich_file(path: Path):
    raw = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    name = raw.get('name')
    city = (raw.get('address') or {}).get('city') or 'George'

    queries = [
        f"{name}, {city}, Western Cape, South Africa",
        f"{name}, George, South Africa",
    ]

    chosen = None
    for q in queries:
        results = places_text_search(q)
        if not results:
            continue
        # Prefer entries mentioning George in the formatted address
        preferred = [r for r in results if 'george' in (r.get('formatted_address', '').lower())]
        chosen = (preferred[0] if preferred else results[0])
        if chosen:
            break

    if not chosen:
        return False, 'no_match'

    details = place_details(chosen['place_id'])
    if not details:
        return False, 'no_details'

    addr = raw.setdefault('address', {})
    contact = raw.setdefault('contact', {})
    links = raw.setdefault('links', {})

    addr['full'] = details.get('formatted_address') or addr.get('full')
    loc = ((details.get('geometry') or {}).get('location') or {})
    addr['latitude'] = loc.get('lat', addr.get('latitude'))
    addr['longitude'] = loc.get('lng', addr.get('longitude'))

    phone = details.get('international_phone_number') or details.get('formatted_phone_number')
    if phone:
        contact['phone'] = phone

    if details.get('website'):
        links['website'] = details['website']
    if details.get('url'):
        links['google_maps'] = details['url']

    opening = (details.get('opening_hours') or {}).get('weekday_text')
    if opening:
        raw['hours'] = opening

    verification = raw.setdefault('verification', {})
    verification['last_verified_at'] = str(date.today())
    verification['confidence'] = score_confidence(raw)
    upsert_source(raw, 'Google Places API')

    notes = raw.get('notes') or ''
    auto = 'Auto-enriched via Google Places.'
    if auto not in notes:
        raw['notes'] = (notes + ' ' + auto).strip()

    path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding='utf-8')
    return True, 'ok'


def main():
    if not API_KEY:
        print('ERROR: GOOGLE_MAPS_API_KEY is not set.')
        return 2

    files = sorted(DATA_DIR.glob('*.yaml'))
    ok = 0
    for f in files:
        try:
            changed, status = enrich_file(f)
            print(f'{f.name}: {status}')
            if changed:
                ok += 1
        except Exception as e:
            print(f'{f.name}: error {e}')

    print(f'Enriched {ok}/{len(files)} records.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
