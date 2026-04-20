#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import urllib.parse

BBOX = (-34.12, 22.20, -33.82, 22.70)  # George area
MEDICAL_OUT_DIR = os.path.join('data', 'businesses', 'medical')
ANIMAL_OUT_DIR = os.path.join('data', 'businesses', 'animal-services')


def run_curl(url: str, timeout: int = 30) -> str:
    p = subprocess.run(['curl', '-s', '--max-time', str(timeout), url], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or f'curl failed for {url}')
    return p.stdout


def overpass_fetch() -> list:
    q = (
        '[out:json][timeout:60];'
        '('
        f'nwr["amenity"~"hospital|clinic|doctors|pharmacy|dentist|veterinary"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});'
        f'nwr["healthcare"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});'
        ');'
        'out center tags 700;'
    )
    url = 'https://overpass-api.de/api/interpreter?' + urllib.parse.urlencode({'data': q})
    raw = run_curl(url, timeout=60)
    payload = json.loads(raw)
    return payload.get('elements', [])


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s or 'medical-provider'


def yq(v):
    if v is None:
        return 'null'
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"


def provider_kind(tags: dict, name: str) -> str:
    amenity = (tags.get('amenity') or '').lower()
    healthcare = (tags.get('healthcare') or '').lower()
    t = f"{amenity} {healthcare}".lower()
    n = (name or '').lower()

    if 'veterinary' in t or 'vet' in n or 'animal hospital' in n:
        return 'veterinary'
    if 'pharmacy' in t or 'pharmacy' in n:
        return 'pharmacy'

    # Prefer OSM healthcare/doctors tags over name text when a listing includes mixed wording like
    # "Doctor and Dentist".
    if amenity == 'doctors' or healthcare == 'doctor' or n.startswith('dr ') or n.startswith('dr.') or n.startswith('drs '):
        return 'doctor'

    if 'dentist' in t or 'dentist' in n:
        return 'dentist'
    if 'optometrist' in t or 'optometrist' in n:
        return 'optometrist'
    if 'hospital' in t:
        return 'hospital'
    if 'clinic' in t:
        return 'clinic'
    return 'medical_service'


def expertise_for(tags: dict, kind: str, name: str) -> str:
    speciality = (
        tags.get('healthcare:speciality')
        or tags.get('healthcare:specialty')
        or tags.get('medical_speciality')
        or tags.get('speciality')
        or tags.get('specialty')
    )
    if speciality:
        spec = str(speciality).replace('_', ' ').strip()
        if kind == 'doctor' and spec.lower() in {'general', 'general practice', 'general practitioner'}:
            return 'General Practitioner'
        return spec.title()

    n = (name or '').lower()

    # Mixed wording appears in some OSM names where both services are offered.
    if 'doctor' in n and 'dentist' in n:
        return 'General Practitioner;Dentist'

    if 'biokinetic' in n:
        return 'Biokinetics'
    if 'pathcare' in n or 'laborator' in n or 'laboratory' in n or 'lab' in n:
        return 'Pathology / Medical Laboratory'
    if 'blood service' in n or 'blood donor' in n:
        return 'Blood Donor Services'

    if kind == 'doctor':
        if 'optometrist' in n:
            return 'Optometrist'
        if 'paediatric' in n or 'pediatric' in n:
            return 'Paediatrician'
        if 'gynae' in n or 'gyne' in n:
            return 'Gynaecologist'
        return 'General Practitioner'
    if kind == 'dentist':
        return 'Dentist'
    if kind == 'optometrist':
        return 'Optometrist'
    if kind == 'pharmacy':
        return 'Pharmacy Services'
    if kind == 'clinic':
        return 'Clinic Services'
    if kind == 'hospital':
        return 'Hospital Services'
    if kind == 'veterinary':
        return 'Veterinary Care'
    return 'General Medical Service'


def map_query(name: str, city: str = 'George') -> str:
    q = urllib.parse.quote_plus(f'{name} {city}')
    return f'https://www.google.com/maps/search/?api=1&query={q}'


def medpages_query(name: str, city: str = 'George') -> str:
    q = urllib.parse.quote_plus(f'site:medpages.info {name} {city}')
    return f'https://www.google.com/search?q={q}'


def reverse_geocode(lat: float, lon: float):
    url = (
        'https://nominatim.openstreetmap.org/reverse?'
        + urllib.parse.urlencode({'format': 'jsonv2', 'lat': lat, 'lon': lon, 'addressdetails': 1})
    )
    p = subprocess.run(
        ['curl', '-s', '--max-time', '20', '-H', 'User-Agent: mvp-testing-ground-medical-seed/1.0', url],
        capture_output=True,
        text=True,
    )
    if p.returncode != 0 or not p.stdout.strip().startswith('{'):
        return None
    try:
        return json.loads(p.stdout)
    except Exception:
        return None


def normalize_city(raw_city: str | None) -> str:
    if not raw_city:
        return 'George'
    city = str(raw_city).strip()
    city_l = city.lower()
    if city_l in {'george', 'george, south africa'}:
        return 'George'
    if 'municipality' in city_l or 'district' in city_l:
        return 'George'
    if city_l.startswith('george '):
        return 'George'
    if ',' in city:
        return 'George'
    return city


def build_record(el: dict, phase: str, seen_slugs: set, name_dupe_counter: dict):
    tags = el.get('tags', {}) or {}
    name = (tags.get('name') or tags.get('brand') or tags.get('operator') or '').strip()
    if not name:
        return None

    lat = el.get('lat')
    lon = el.get('lon')
    if lat is None or lon is None:
        c = el.get('center') or {}
        lat = c.get('lat')
        lon = c.get('lon')
    if lat is None or lon is None:
        return None

    kind = provider_kind(tags, name)
    expertise = expertise_for(tags, kind, name)

    city = normalize_city(tags.get('addr:city') or 'George')
    street = tags.get('addr:street')
    house = tags.get('addr:housenumber')
    suburb = tags.get('addr:suburb')
    postal = tags.get('addr:postcode')
    full = None

    if street and house:
        full = f'{house} {street}, {city}'
    elif street:
        full = f'{street}, {city}'

    hours_list = []
    if tags.get('opening_hours'):
        hours_list = [tags.get('opening_hours')]

    phone = tags.get('contact:phone') or tags.get('phone')
    email = tags.get('contact:email') or tags.get('email')
    website = tags.get('contact:website') or tags.get('website')
    facebook = tags.get('contact:facebook') or tags.get('facebook')

    if phase == 'enrich':
        rev = reverse_geocode(lat, lon)
        if rev:
            addr = rev.get('address') or {}
            display = rev.get('display_name')
            street = street or addr.get('road') or addr.get('pedestrian') or addr.get('street')
            suburb = suburb or addr.get('suburb') or addr.get('neighbourhood') or addr.get('quarter')
            city = normalize_city(city or addr.get('city') or addr.get('town') or addr.get('municipality') or 'George')
            postal = postal or addr.get('postcode')
            if not full:
                if street:
                    number = addr.get('house_number')
                    full = f"{(number + ' ') if number else ''}{street}, {city}" if city.lower() not in street.lower() else f"{(number + ' ') if number else ''}{street}"
                elif display:
                    full = display

    base_slug = slugify(name)
    n = name_dupe_counter.get(base_slug, 0) + 1
    name_dupe_counter[base_slug] = n
    slug = base_slug if n == 1 else f'{base_slug}-{n}'
    while slug in seen_slugs:
        n += 1
        slug = f'{base_slug}-{n}'
    seen_slugs.add(slug)

    today = dt.date.today().isoformat()
    object_url = f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}"

    confidence = 'low'
    score = 45
    publish_ready = False

    if phase == 'enrich':
        has_address = bool(full or street)
        has_contact = bool(phone or website or email)
        if has_address and has_contact:
            confidence = 'medium'
            score = 72
            publish_ready = True
        elif has_address:
            confidence = 'medium'
            score = 64
            publish_ready = False
        else:
            confidence = 'low'
            score = 50
            publish_ready = False

    target = 'animal' if kind == 'veterinary' else 'medical'

    return {
        'slug': slug,
        'name': name,
        'kind': kind,
        'expertise': expertise,
        'street': street,
        'suburb': suburb,
        'city': city or 'George',
        'postal': postal,
        'full': full,
        'lat': float(lat),
        'lon': float(lon),
        'phone': phone,
        'email': email,
        'website': website,
        'facebook': facebook,
        'hours': hours_list,
        'map': map_query(name, city or 'George'),
        'medpages': medpages_query(name, city or 'George'),
        'object_url': object_url,
        'date': today,
        'confidence': confidence,
        'score': score,
        'publish_ready': publish_ready,
        'phase': phase,
        'target': target,
    }


def dump_yaml(rec: dict) -> str:
    lines = []
    lines.append(f"slug: {rec['slug']}")
    lines.append(f"name: {yq(rec['name'])}")
    lines.append('category: medical_service')
    lines.append('subcategories:')
    lines.append(f"- {rec['kind']}")
    lines.append(f"expertise: {yq(rec['expertise'])}")
    lines.append('address:')
    lines.append(f"  street: {yq(rec['street'])}")
    lines.append(f"  suburb: {yq(rec['suburb'])}")
    lines.append(f"  city: {yq(rec['city'])}")
    lines.append(f"  postal_code: {yq(rec['postal'])}")
    lines.append(f"  full: {yq(rec['full'])}")
    lines.append(f"  latitude: {rec['lat']:.7f}")
    lines.append(f"  longitude: {rec['lon']:.7f}")
    lines.append('contact:')
    lines.append(f"  phone: {yq(rec['phone'])}")
    lines.append('  whatsapp: null')
    lines.append(f"  email: {yq(rec['email'])}")
    lines.append('links:')
    lines.append(f"  website: {yq(rec['website'])}")
    lines.append(f"  facebook: {yq(rec['facebook'])}")
    lines.append('  instagram: null')
    lines.append('  menu: null')
    lines.append(f"  google_maps: {yq(rec['map'])}")
    if rec['hours']:
        lines.append('hours:')
        for h in rec['hours']:
            lines.append(f"- {yq(h)}")
    else:
        lines.append('hours: []')
    lines.append('photos: []')
    lines.append('verification:')
    lines.append(f"  last_verified_at: {yq(rec['date'])}")
    lines.append(f"  confidence: {rec['confidence']}")
    lines.append(f"  score: {rec['score']}")
    lines.append(f"  publish_ready: {'true' if rec['publish_ready'] else 'false'}")
    lines.append('  sources:')
    lines.append(f"  - {yq(rec['object_url'])}")
    lines.append('  - OpenStreetMap Overpass query (George bounding box)')
    lines.append(f"  - {yq(rec['medpages'])}")
    lines.append(f"  - {yq(rec['map'])}")
    lines.append(
        f"notes: {yq('Phase ' + rec['phase'] + ': source-backed card generated from OSM, with Medpages lookup link included for manual profile verification.') }"
    )
    return '\n'.join(lines) + '\n'


def cleanup_yaml(out_dir: str):
    if not os.path.isdir(out_dir):
        return
    for fn in os.listdir(out_dir):
        if fn.endswith('.yaml') or fn.endswith('.yml'):
            os.remove(os.path.join(out_dir, fn))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase', choices=['quick', 'enrich'], required=True)
    ap.add_argument('--limit', type=int, default=0, help='Optional max providers to write total')
    args = ap.parse_args()

    os.makedirs(MEDICAL_OUT_DIR, exist_ok=True)
    os.makedirs(ANIMAL_OUT_DIR, exist_ok=True)

    elements = overpass_fetch()
    named = [e for e in elements if (e.get('tags') or {}).get('name') or (e.get('tags') or {}).get('brand') or (e.get('tags') or {}).get('operator')]
    named.sort(key=lambda e: ((e.get('tags') or {}).get('name') or (e.get('tags') or {}).get('brand') or '').lower())

    seen_slugs = set()
    name_dupe_counter = {}
    written_medical = 0
    written_animal = 0
    written_total = 0

    cleanup_yaml(MEDICAL_OUT_DIR)
    cleanup_yaml(ANIMAL_OUT_DIR)

    for el in named:
        rec = build_record(el, args.phase, seen_slugs, name_dupe_counter)
        if not rec:
            continue

        out_dir = ANIMAL_OUT_DIR if rec['target'] == 'animal' else MEDICAL_OUT_DIR
        fn = os.path.join(out_dir, f"{rec['slug']}.yaml")
        with open(fn, 'w', encoding='utf-8') as f:
            f.write(dump_yaml(rec))

        written_total += 1
        if rec['target'] == 'animal':
            written_animal += 1
        else:
            written_medical += 1

        if args.limit and written_total >= args.limit:
            break

    print(f'wrote total={written_total} medical={written_medical} animal={written_animal} phase={args.phase}')


if __name__ == '__main__':
    main()
