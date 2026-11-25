# Milestones

Each milestone is built on its own branch, reviewed in its own pull request, and has a
document here explaining what was built, why, which libraries are used and how it was
verified. See [../workflow.md](../workflow.md) for the process.

| # | Milestone | Branch | Status | Doc |
|---|---|---|---|---|
| 0 | Foundation: stack, fake cameras, health checks, CI | `milestone/0-foundation` | In review | [00-foundation.md](00-foundation.md) |
| 1 | Baseline pipeline: detection, tracking, zone, pretrained OCR | `milestone/1-baseline-pipeline` | Planned | |
| 2 | Data + training: plate detector, region classifier, OCR fine-tune | `milestone/2-training` | Planned | |
| 3 | Accuracy layer: region rules, OCR correction, voting, evaluation | `milestone/3-accuracy` | Planned | |
| 4 | Backend: event ingestion, storage, search, auth, audit log | `milestone/4-backend` | Planned | |
| 5 | Dashboard + alerts: React UI, live video, watchlists, Telegram | `milestone/5-dashboard-alerts` | Planned | |
| 6 | Production hardening: ONNX/TensorRT, load test, monitoring, HTTPS | `milestone/6-hardening` | Planned | |
| 7 | Documentation + demo | `milestone/7-docs-demo` | Planned | |

New milestone docs start from [_template.md](_template.md).
