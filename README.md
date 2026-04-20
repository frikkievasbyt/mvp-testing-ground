# George Directory Site (starter)

Hugo-based static directory for George, Western Cape businesses.

## Current scope
- Category: Coffee shops
- Data source format: YAML (one business per file)
- Starter listing page: `/coffee/`

## Why YAML first
- Easy PR review and editing
- Good for branch-based update workflow
- Compatible with Hugo data templates

## Project structure

- `config.yaml` - site config
- `content/coffee/_index.md` - coffee category page content
- `data/businesses/coffee/*.yaml` - business records
- `layouts/coffee/list.html` - coffee listing renderer
- `static/css/site.css` - base styling
- `scripts/import_coffee_from_obsidian.py` - optional seed importer

## Local run

```bash
cd george-directory-site
hugo server -D
```

Open http://localhost:1313/coffee/

## Data schema (per shop)

```yaml
slug: mugg-and-bean-george
name: Mugg & Bean
category: coffee_shop
subcategories: [franchise]
address:
  street: Morris Avenue
  suburb: null
  city: George
  postal_code: "6530"
  full: Morris Avenue, George, 6530
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
  google_maps: https://www.google.com/maps/search/?api=1&query=Mugg+%26+Bean,+George
hours: []
photos: []
verification:
  last_verified_at: "2026-04-18"
  confidence: low
  sources:
    - OpenStreetMap / Nominatim
notes: Needs branch-level verification.
```

## Update workflow (as discussed)

1. Create/update branch: `update/YYYY-MM-DD-<topic>`
2. Edit YAML records and templates
3. Preview locally with Hugo
4. Commit updates
5. Push branch, open PR
6. Review, merge, deploy

## Feedback form

Planned to wire to Google Form (end-user friendly). Placeholder currently shown on page.

## Low-human-touch quality pipeline (free-first)

This repo includes an automated quality pipeline that uses free sources first.

### Run refresh

```bash
./scripts/run_refresh.sh
```

This will automatically create/use `.venv`, install deps, then:
- enrich records using free sources (Overpass + Nominatim)
- set quality score + publish readiness
- run quality gate checks
- write report: `data/quality-report.md`

### Optional paid enhancement (later)

If you set `GOOGLE_MAPS_API_KEY`, the pipeline also runs Google Places enrichment as an extra quality layer.

```bash
export GOOGLE_MAPS_API_KEY="<your-key>"
./scripts/run_refresh.sh
```

### Scripts
- `scripts/enrich_free_sources.py`
- `scripts/google_places_enrich.py` (optional)
- `scripts/quality_gate.py`
- `scripts/run_refresh.sh`

## Next build steps

- Add per-business profile pages
- Add verification badges and confidence legend in UI
- Wire feedback form
- Add nightly update pipeline + publish gate
