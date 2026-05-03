# 0012 - AI Code Review Is Advisory; Humans Approve Merges

## Status
Accepted

## Context
Several automated code-review tools post comments on every PR: `github-code-quality[bot]`, ChatGPT Codex (via `@codex review`), Vercel Agent Review, and (when configured) Claude Code Action. Their suggestions vary in quality — some surface real bugs, others propose changes based on hallucinated repo state (e.g. PR #156 received a Codex comment claiming a sibling commit and PR existed that did not). Treating any of them as a merge gate would be both expensive and dangerous.

## Decision
- Automated review output is **advisory only**. No merge protection rule depends on bot approval.
- Every PR's preferred flow is:
  1. Open as Draft unless already ready.
  2. Wait for CI to begin.
  3. Comment `@codex review` to invoke the AI pass.
  4. Address actionable feedback; reply on threads to close the loop (per `address-feedback` skill).
  5. Request human review.
- Human reviewers are responsible for merge approval. A bot's "approve" or "✅" does not constitute review.
- Bot critiques can be **declined with rationale** — silent dismissal is discouraged.

## Consequences

**Easier**
- The team gets fast first-pass feedback without owning the entire review.
- Disagreements with bot suggestions are documented in PR threads, creating an audit trail.

**Harder**
- Reviewers must know which bots are running and roughly what each is good at.
- Onboarding contributors need to be told the `@codex review` step is part of the flow.
- Threads can accumulate noise from low-quality bot suggestions if not actively triaged.

### Cross-Repo Impact
`cedh-research` only.

## Sources
- `CONTRIBUTING.md` "Pull Requests" section ("Codex review is advisory. Human reviewers are responsible for merge approval.")
- `README.md` — instructions to comment `@codex review`
- PR #156 — example of declining a hallucinated Codex suggestion
