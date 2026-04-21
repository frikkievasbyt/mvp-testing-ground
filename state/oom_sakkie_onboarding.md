# Oom Sakkie + Gwen onboarding (fuel rollout)

Environment
- Primary model: `ollama/qwen3:latest`
- Work repo: `/Users/frikkievasbyt/Documents/git-repos/mvp-testing-ground`
- Checkpoint: `state/oom_sakkie_checkpoint.json`

Mission
1) Phase 1 (Discovery): find and list fuel filling stations in/around George.
2) Phase 2 (Enrichment): make station entries as complete as possible with map links and verified metadata.

Phase 1 outputs
- Keep a deduped inventory in `state/fuel_station_inventory.yaml`.
- Include station name, likely brand, rough location/address, source links, and confidence.
- Do not invent details.

Phase 2 outputs
- Create/update one YAML file per station under `data/businesses/fuel/*.yaml`.
- Keep unknown fields null.
- Prioritize `links.google_maps`, address quality, phone, website, and opening hours.

Checkpoint discipline
- Keep fields: `phase`, `lastRunAt`, `batchSize`, `changedFiles`, `sampledFiles`, `avgConfidence`, `escalatedCount`, `lastCommit`, `nextBatchHint`.
- Merge/update checkpoint values; do not replace file with run output summary.
