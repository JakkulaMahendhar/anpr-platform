# Development workflow

## Branches

- `main` holds only reviewed, merged work. Nothing is committed to it directly.
- Each milestone has one branch: `milestone/<number>-<short-name>`,
  for example `milestone/1-baseline-pipeline`.
- A branch starts from the latest `main`, after the previous milestone is merged.
- Fixes found during review are committed on the same branch, so the PR updates.

## Pull requests

One pull request per milestone. Each PR contains:

1. The code, with tests.
2. The milestone document in `docs/milestones/NN-name.md`: what was built, why, which
   libraries and models, design decisions, verified results, a reviewer guide and
   known limitations.
3. An updated row in `docs/milestones/README.md`.

Before a PR is opened:

- `make lint` and `make test` pass.
- `make test-integration` passes with the stack running.
- The milestone's own verification steps (in its doc) were run and the results recorded.

Merge with **squash and merge**, so `main` gets one clean commit per milestone. The
detailed history stays in the PR.

## Commits

- Short imperative subject line (`Add plate OCR voting`), with details in the body.
- Never commit `.env`, video footage, plate images or model weights (see `.gitignore`).
