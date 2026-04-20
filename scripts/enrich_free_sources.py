#!/usr/bin/env python3
import json
import math
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import quote
from urllib.request import urlopen

import yaml

REPO = Path('/Users/frikkievasbyt/Documents/git-repos/mvp-testing-ground')
DATA_DIR = REPO / 'data' / 'businesses' / 'coffee'
QUALITY_REPORT = REPO / 'data' / 'quality-report.md'

GEORGE_CENTER = (-33.9649, 22.4594)
GEORGE_RADIUS_M = 35000


def normalize_name(s: str) -> str:
    s = s.lower()
    s = s.replace('caffè', 'caffe').replace('café', 'cafe')
    s = re.sub(r'\b(rooted|branch\s*\d+)\b', '', s)
    s = re.sub(r'\b(coffee|cafe|caffe|koffiewinkel|roastery|shop)\b', '', s)
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def haversine_m(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def fetch_overpass() -> list:
    query = f'''[out:json][timeout:90];
(
  nwr["amenity"="cafe"](around:{GEORGE_RADIUS_M},{GEORGE_CENTER[0]},{GEORGE_CENTER[1]});
  nwr["shop"="coffee"](around:{GEORGE_RADIUS_M},{GEORGE_CENTER[0]},{GEORGE_CENTER[1]});
  nwr["cuisine"~"coffee|coffee_shop",i](around:{GEORGE_RADIUS_M},{GEORGE_CENTER[0]},{GEORGE_CENTER[1]});
);
out center tags;'''

    endpoints = [
        'https://overpass-api.de/api/interpreter',
        'https://overpass.kumi.systems/api/interpreter',
    ]

    for ep in endpoints:
        try:
            cmd = ['curl', '-sS', '--data-urlencode', f'data={query}', ep]
            out = subprocess.check_output(cmd, text=True, timeout=120)
            payload = json.loads(out)
            return payload.get('elements', [])
        except Exception:
            continue

    return []


def nominatim_search(query: str) -> Optional[dict]:
    url = f'https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&addressdetails=1&q={quote(query)}'
    req = urlopen(url, timeout=20)
    arr = json.loads(req.read().decode('utf-8'))
    if not arr:
        return None
    # prefer george matches
    arr = sorted(arr, key=lambda r: ('george' in (r.get('display_name', '').lower()), r.get('importance', 0)), reverse=True)
    return arr[0]


def yaml_load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def yaml_save(path: Path, data: dict):
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding='utf-8')


@dataclass
class Quality:
    score: int
    confidence: str
    publish_ready: bool
    reasons: list


def compute_quality(rec: dict, checks: dict) -> Quality:
    score = 0
    reasons = []

    addr = rec.get('address') or {}
    links = rec.get('links') or {}
    contact = rec.get('contact') or {}

    if addr.get('full'):
        score += 20
    else:
        reasons.append('missing full address')

    if addr.get('latitude') is not None and addr.get('longitude') is not None:
        score += 20
    else:
        reasons.append('missing coordinates')

    if contact.get('phone'):
        score += 15
    else:
        reasons.append('missing phone')

    if links.get('website'):
        score += 15
    elif links.get('facebook'):
        score += 10
    else:
        reasons.append('missing website/facebook')

    if links.get('google_maps'):
        score += 10
    else:
        reasons.append('missing maps link')

    if checks.get('nominatim_match'):
        score += 10
    else:
        reasons.append('no nominatim match')

    if checks.get('overpass_match'):
        score += 10
    else:
        reasons.append('no overpass match')

    if checks.get('address_consistent'):
        score += 10
    else:
        reasons.append('address inconsistency')

    confidence = 'high' if score >= 75 else 'medium' if score >= 55 else 'low'

    addr = rec.get('address') or {}
    links = rec.get('links') or {}
    publish_ready = (
        score >= 70
        and bool(addr.get('full'))
        and addr.get('latitude') is not None
        and addr.get('longitude') is not None
        and bool(links.get('google_maps'))
    )

    return Quality(score=score, confidence=confidence, publish_ready=publish_ready, reasons=reasons)


def best_overpass_match(name: str, lat: Optional[float], lon: Optional[float], elements: list) -> Optional[dict]:
    n0 = normalize_name(name)
    best = None
    best_score = -1.0

    for el in elements:
        tags = el.get('tags') or {}
        nm = tags.get('name')
        if not nm:
            continue
        n1 = normalize_name(nm)
        sim = SequenceMatcher(a=n0, b=n1).ratio()
        score = sim

        el_lat = el.get('lat') or (el.get('center') or {}).get('lat')
        el_lon = el.get('lon') or (el.get('center') or {}).get('lon')
        if lat is not None and lon is not None and el_lat is not None and el_lon is not None:
            d = haversine_m((lat, lon), (float(el_lat), float(el_lon)))
            if d < 800:
                score += 0.25
            elif d < 2500:
                score += 0.1

        if score > best_score:
            best_score = score
            best = el

    if best is None or best_score < 0.63:
        return None
    return best


def enrich_record(path: Path, elements: list) -> Tuple[str, Quality]:
    rec = yaml_load(path)
    name = rec.get('name') or path.stem
    address = rec.setdefault('address', {})
    contact = rec.setdefault('contact', {})
    links = rec.setdefault('links', {})
    verification = rec.setdefault('verification', {})

    checks = {
        'nominatim_match': False,
        'overpass_match': False,
        'address_consistent': False,
    }

    # 1) Nominatim lookup
    q = f"{name}, George, Western Cape, South Africa"
    nom = None
    try:
        nom = nominatim_search(q)
        if nom:
            checks['nominatim_match'] = True
            if not address.get('full'):
                address['full'] = nom.get('display_name')
            if address.get('latitude') is None:
                address['latitude'] = float(nom.get('lat')) if nom.get('lat') else None
            if address.get('longitude') is None:
                address['longitude'] = float(nom.get('lon')) if nom.get('lon') else None
    except Exception:
        pass

    lat = address.get('latitude')
    lon = address.get('longitude')

    # 2) Overpass matching for richer business fields
    m = best_overpass_match(name, lat, lon, elements)
    if m:
        checks['overpass_match'] = True
        tags = m.get('tags') or {}
        if not contact.get('phone'):
            contact['phone'] = tags.get('phone') or tags.get('contact:phone')
        if not links.get('website'):
            links['website'] = tags.get('website') or tags.get('contact:website')
        if not links.get('facebook'):
            links['facebook'] = tags.get('contact:facebook')
        if not rec.get('hours'):
            oh = tags.get('opening_hours')
            if oh:
                rec['hours'] = [oh]

        el_lat = m.get('lat') or (m.get('center') or {}).get('lat')
        el_lon = m.get('lon') or (m.get('center') or {}).get('lon')
        if address.get('latitude') is None and el_lat is not None:
            address['latitude'] = float(el_lat)
        if address.get('longitude') is None and el_lon is not None:
            address['longitude'] = float(el_lon)

    # 3) Consistency check
    full = (address.get('full') or '').lower()
    checks['address_consistent'] = 'george' in full or bool(address.get('city') == 'George')

    # 4) ensure google maps link
    if not links.get('google_maps'):
        query = quote(f"{name}, {address.get('full') or 'George'}")
        links['google_maps'] = f'https://www.google.com/maps/search/?api=1&query={query}'

    # 5) quality outcome
    quality = compute_quality(rec, checks)
    verification['last_verified_at'] = str(date.today())
    verification['confidence'] = quality.confidence
    verification['score'] = quality.score
    verification['publish_ready'] = quality.publish_ready
    verification['checks'] = checks
    sources = verification.setdefault('sources', [])
    for s in ['OpenStreetMap Overpass', 'Nominatim']:
        if s not in sources:
            sources.append(s)

    note = rec.get('notes') or ''
    stamp = 'Auto-enriched via free-source quality pipeline.'
    if stamp not in note:
        rec['notes'] = (note + ' ' + stamp).strip()

    yaml_save(path, rec)
    return rec.get('name', path.stem), quality


def main():
    records = sorted(DATA_DIR.glob('*.yaml'))
    overpass = fetch_overpass()

    results = []
    for p in records:
        try:
            name, quality = enrich_record(p, overpass)
            results.append((name, quality))
            print(f'{p.name}: score={quality.score} confidence={quality.confidence} publish={quality.publish_ready}')
            time.sleep(0.25)
        except Exception as e:
            print(f'{p.name}: error {e}')

    # report
    lines = ['# Quality Report', '', f'Total records: {len(results)}', '']
    for name, q in sorted(results, key=lambda x: (x[1].publish_ready, x[1].score)):
        badge = '✅' if q.publish_ready else '⚠️'
        lines.append(f'## {badge} {name}')
        lines.append(f'- Score: **{q.score}**')
        lines.append(f'- Confidence: **{q.confidence}**')
        lines.append(f'- Publish ready: **{q.publish_ready}**')
        if q.reasons:
            lines.append('- Gaps:')
            for r in q.reasons:
                lines.append(f'  - {r}')
        lines.append('')

    QUALITY_REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote {QUALITY_REPORT}')


if __name__ == '__main__':
    main()
