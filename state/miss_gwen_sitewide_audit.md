# Sitewide Audit Summary

Generated: 2026-04-23 16:56:43 SAST

## Categories Audited
- animal-services
- bicycle
- coffee
- fuel
- medical

## Severity Summary
- Critical: 17
- High: 75
- Medium: 96
- Low: 0

## Critical Findings
- Missing coords in 13 entries
- Missing address.full in 2 entries
- Missing source in 2 entries

## Duplicate Clusters
- Confidence 75%: data/businesses/medical/dis-chem-pharmacy.yaml, data/businesses/medical/walk-in-doctor-and-dentist.yaml, data/businesses/medical/walk-in-doctors-dentist.yaml
- Confidence 75%: data/businesses/medical/dr-c-w-roux-incorporated.yaml, data/businesses/medical/dr-j-h-meyer.yaml, data/businesses/medical/dr-r-h-faul.yaml
- Confidence 75%: data/businesses/medical/dr-fouche-incorporated.yaml, data/businesses/medical/dr-heinrich-van-rensburg.yaml
- Confidence 75%: data/businesses/medical/dr-j-l-van-heerden.yaml, data/businesses/medical/the-sports-doc.yaml
- Confidence 75%: data/businesses/medical/dr-michiel-daniel-cornelius-bekker.yaml, data/businesses/medical/dr-willem-jacobus-janse-breytenbach.yaml
- Confidence 75%: data/businesses/medical/dr-nicke-theron.yaml, data/businesses/medical/swart-a-l-partner-incorporated.yaml
- Confidence 75%: data/businesses/medical/drs-augustyn-de-la-bat-ferreira.yaml, data/businesses/medical/drs-de-neckers-zoomers-burchell.yaml

## Do Next
1. Fix critical data gaps first (coords/address/source).
2. Resolve duplicate candidates with source-backed confirmation.
3. Backfill phone and hours where verifiable.
4. Validate website links and clear invalid ones.
