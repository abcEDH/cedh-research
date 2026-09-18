# cEDH Research — Agent Instructions

> **Single source of truth for every coding agent.** This file (`AGENTS.md`) is canonical.
> `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, and `.cursorrules` are
> symlinks to it, so editing `AGENTS.md` updates the instructions every agent sees — there
> is nothing to keep in sync. To onboard a new agent, symlink its expected filename to this
> file (e.g. `ln -s AGENTS.md NEWAGENT.md`).

Cross-cutting rules for this repo. Package-specific knowledge lives in each package's own
`AGENTS.md` — see [`packages/backend/AGENTS.md`](packages/backend/AGENTS.md) for backend
operations, ingestion commands, and known issues.

---

## Module Extraction (Python)

**File size limit: ~500 lines.** When a Python file contains multiple logical domains, split it.
The natural seams for `src/` scripts are:
- `<service>_client.py` — all I/O for one external service
- `<orchestrator>.py` — pipeline flow only; no inline HTTP or SQL
- Constants belong with the module that owns them

**Backward compatibility when extracting.** Maintain existing `from X import Y` call sites by
re-exporting from the original file and declaring `__all__`:

```python
# ingest.py — after SupabaseClient moved to supabase_client.py
from supabase_client import SupabaseClient, _describe_request_failure

__all__ = ["SupabaseClient", "_describe_request_failure"]
```

**Audit consumers before committing.** Run this before pushing any extraction:

```bash
grep -r "from ingest import\|import ingest" packages/backend/src packages/backend/tests
grep -r "@patch.*ingest\." packages/backend/tests
```

Skipping this step results in a cascade of follow-up fix commits.

---

## Test Patching

**Patch where behavior lives, not where it's imported.**

```python
# Wrong after HTTP code moves from ingest.py to supabase_client.py
@patch("ingest.requests.patch")

# Right
@patch("supabase_client.requests.patch")
```

---

## Optional Dependency Detection (Python)

Use `importlib.util.find_spec` to avoid creating unused imported names that CodeQL flags:

```python
import importlib.util
PSYCOPG2_AVAILABLE = importlib.util.find_spec("psycopg2") is not None
```

---

## CLI Argument Parsing (Python)

Extract into `build_arg_parser()` so `main()` is pure orchestration:

```python
def build_arg_parser() -> argparse.ArgumentParser: ...

def main() -> None:
    args = build_arg_parser().parse_args()
```

---

## Module Structure (TypeScript / Next.js)

**`page.tsx` ≤ 300 lines** — layout assembly only.

| File | Contains |
|------|----------|
| `app/<route>/page.tsx` | Layout, `await` calls, component composition |
| `lib/<domain>/fetchers.ts` | All Supabase queries; returns typed results |
| `lib/<domain>/stats.ts` | Pure math — win rates, derived metrics |
| `components/<domain>/<Name>.tsx` | One component per file; no data fetching |

Types live in `fetchers.ts`, not in consuming page components.

---

## Mobile / Responsive (TypeScript / Next.js)

The web app is mobile-first. New pages and components ship mobile-ready by
default — don't leave it as a follow-up. Conventions:

- **Breakpoints.** Mobile-first: base styles target phones, layer up with
  `sm:` (640) and `md:` (768). `md:` is the nav switch — the desktop header
  nav is `hidden md:flex` and the hamburger drawer (`MobileNav`) is `md:hidden`.
- **Touch targets.** Interactive controls on mobile paths (drawer links,
  filter triggers, pagers, chips) get ≥44px hit areas at the base breakpoint
  (`min-h-11` or taller padding), relaxed at `sm:`. Do **not** globally resize
  `ui/button.tsx` — desktop density is intentional.
- **Wide tables — column priority.** Drop secondary columns on small screens
  with `hidden sm:table-cell` / `hidden md:table-cell`, and surface the
  dropped value as a `sm:hidden` sub-line under the primary cell. See the home
  leaderboard (`app/page.tsx`) and `tournaments-list.tsx` for the pattern. Keep
  `whitespace-nowrap` on numeric cells only; let names wrap or `line-clamp`.
- **Genuinely wide content** (the pod bracket) stacks vertically below `md:`
  (`flex-col md:flex-row`, `w-full md:w-[...]`) and keeps horizontal scroll
  from `md:` up — see `tournaments/[slug]/tournament-detail-tabs.tsx`.
- **Filters.** Prefer the Radix-based `ui/select.tsx` over hand-rolled
  dropdowns — it handles small-viewport positioning and keyboard/touch for
  free.
- **Safe areas.** The layout uses `viewport-fit=cover` with
  `env(safe-area-inset-*)` padding in `globals.css`; keep new fixed/sticky
  chrome inside those insets.
- **Regression guard.** Every route must pass `expectNoHorizontalOverflow`
  (`e2e/helpers/overflow.ts`) on the mobile Playwright projects. Add new
  routes to `e2e/mobile-routes.spec.ts`. Full checklist:
  [`apps/web/docs/mobile-checklist.md`](apps/web/docs/mobile-checklist.md).

---

## Dependency Pinning (uv)

See [`docs/decisions/0010-lockfile-policy.md`](docs/decisions/0010-lockfile-policy.md) for
the full lockfile policy. One critical addendum not in that ADR:

`exclude-newer` must be an absolute RFC 3339 timestamp — relative durations recompute on every
run and make the lockfile perpetually stale, causing CI to re-resolve and time out:

```toml
# Wrong
exclude-newer = "7 days"

# Right — bump this when you intentionally want newer packages
exclude-newer = "2026-05-28T00:00:00Z"
```

After updating the timestamp, run `uv lock --project packages/backend` to regenerate.
