# Instant Spec: Quickstart Onboarding

## Goal
Give humans and agents a single command that bootstraps a usable local environment with safe defaults.

## Command
```bash
just quickstart
```

## Contract
When run from repository root, quickstart must:
1. Verify `node`, `npm`, and `python` are available.
2. Install JavaScript dependencies with `npm install`.
3. Create local env files from templates only when they do not already exist:
   - `.env` from `.env.example`
   - `apps/web/.env.local` from `apps/web/.env.example`
   - `packages/backend/.env` from `packages/backend/.env.example`
4. Install backend dependencies (`npm run backend:install`) unless frontend-only mode is requested.
5. Run docs validation commands:
   - `npm run docs:check`
   - `npm run docs:hygiene`
6. Print the next step: `npm run web:dev`.

## Frontend-only mode
```bash
just quickstart-no-backend
```
Skips backend dependency installation but still performs all other checks.

## Non-goals
- Do not overwrite existing env files.
- Do not start long-running services automatically.
- Do not require users to read multiple docs before first run.

## Validation checklist
- `just quickstart-no-backend` exits successfully on a clean runner.
- Env files are created if missing and preserved if present.
- Docs checks pass.
- README quickstart section matches this spec.
