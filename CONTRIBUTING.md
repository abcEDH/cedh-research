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

## GitHub Actions Pinning

All `uses:` references in `.github/workflows/` are pinned to a full commit SHA with
the version tag in a trailing comment, for example:

```yaml
uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1
```

**Why:** Tag-based references (`@v4`) can be moved by the action author at any time.
SHA pinning ensures the exact code that CI ran today will still run tomorrow, with no
silent mutation from upstream changes (supply chain protection).

### Current pin versions

| Action | Version | SHA |
|--------|---------|-----|
| `actions/checkout` | v4.3.1 | `34e114876b0b11c390a56381ad16ebd13914f8d5` |
| `actions/setup-python` | v5.6.0 | `a26af69be951a213d495a4c3e4e4022e16d87065` |
| `actions/setup-node` | v4.4.0 | `49933ea5288caeca8642d1e84afbd3f7d6820020` |
| `actions/upload-artifact` | v4.6.2 | `ea165f8d65b6e75b540449e92b4886f43607fa02` |
| `astral-sh/setup-uv` | v5.4.2 | `d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86` |
| `taiki-e/install-action` | just | `86e1083c66fd3afa489f3a9a04a326d51621b3e6` |

### How to update a pin

1. Find the new release tag on the action's GitHub releases page.
2. Look up the commit SHA the tag points to:
   ```bash
   gh api repos/<owner>/<repo>/git/ref/tags/<tag> --jq '.object.sha'
   ```
3. Replace the SHA and update the version comment in every workflow file that uses it.
4. Update the table above.

Dependabot or a manual audit is the expected update trigger — not "it broke so I
bumped it."

## Release Expectations

- Semantic version tags are for releases only.
- Continuous deploys must not create fake semver tags.
- Production deploy behavior should be verifiable from CI and GitHub metadata.
