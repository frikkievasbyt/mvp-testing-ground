# Oom Sakkie onboarding (fuel rollout)

Environment
- Primary model: `openai-codex/gpt-5.3-codex`
- Work repo: `/Users/frikkievasbyt/Documents/git-repos/mvp-testing-ground`
- Checkpoint: `state/oom_sakkie_checkpoint.json`

Mission
1) Enrich George fuel filling station entries first.
2) Discover/add new stations only when enrichment work is exhausted.

Run policy
- One batch per run (10-12 stations).
- Addresses are mandatory on touched entries (`address.full`, `address.street`, `address.city` when source-backed).
- Keep map pin links and coordinates up to date.
- Improve phone, website, hours, and services where source-backed.
- Keep unknown fields null, never invent data.
- Keep titles clean: no OSM IDs in `name`; keep IDs only in source/openstreetmap links.

Checkpoint discipline
- Keep/merge fields: `phase`, `lastRunAt`, `batchSize`, `changedFiles`, `sampledFiles`, `avgConfidence`, `escalatedCount`, `lastCommit`, `nextBatchHint`.
- Never replace the checkpoint file with plain summary output.
