# Contributing

## Principles

- Keep PRs small enough for a human reviewer to understand in one sitting.
- Link every PR to the issue or issue cluster it implements.
- If a surface is retired, remove its code, docs, tests, and CI references together.
- Prefer deleting dead paths over archiving them in active workflows.

## Local Setup

Requirements:
- Node.js 20+
- Python 3.12+

Environment files:
- `apps/web/.env.local` for frontend public variables
- `packages/backend/.env` for backend service variables

Safe templates:
- `./.env.example`
- `apps/web/.env.example`
- `packages/backend/.env.example`

## Pull Requests

Every PR should:
- use the PR template in `.github/pull_request_template.md`
- describe the problem, decision, scope, and non-goals clearly
- include concrete verification commands or evidence
- stay MECE with adjacent cleanup lanes where possible

Preferred review flow:
1. Open the PR as `Draft` unless it is already ready for merge review.
2. Let CI run.
3. Comment `@codex review` for an automated review pass.
4. Address actionable feedback.
5. Request human review.

Codex review is advisory. Human reviewers are responsible for merge approval.

## Hygiene Expectations

- Do not commit generated reports, test artifacts, or scratch outputs.
- When migrations change, update the data dictionary.
- Keep docs aligned with the supported surfaces in `docs/supported-surfaces.md`.
- If a workflow validates a surface, that surface should still be supported.

## Dependency Lockfile Policy

This repo uses lockfiles for both the frontend and backend to ensure reproducible CI installs.

### Frontend — `package-lock.json`

- All frontend jobs use `npm ci`, which installs from `package-lock.json` exactly.
- Never commit `package-lock.json` changes without a corresponding `package.json` change.
- To update: `npm install <pkg>` (updates both files) → commit both.

### Backend — `packages/backend/uv.lock`

- All backend CI jobs use `uv sync --frozen --project packages/backend`, which installs exact versions from `uv.lock`.
- Runtime dependencies live in `[project].dependencies` in `pyproject.toml`.
- Dev/quality tools live in `[dependency-groups].dev` in `pyproject.toml`.
- `requirements.txt` documents the ranges for human reference but is **not used by CI**.

To update a dependency:

```bash
cd packages/backend
uv add <package>          # runtime dep — updates pyproject.toml and uv.lock
uv add --dev <package>    # dev dep — same
uv lock --upgrade-package <package>   # bump a specific package within its range
uv lock --upgrade                     # bump all packages (review diff before committing)
```

Always commit `pyproject.toml` and `uv.lock` together. Never edit `uv.lock` by hand.

## Release Expectations

- Semantic version tags are for releases only.
- Continuous deploys must not create fake semver tags.
- Production deploy behavior should be verifiable from CI and GitHub metadata.
