# GitHub Actions Pinning Policy

This repository pins every third-party GitHub Action to a full commit SHA in workflow files.

## Standard

- Use `owner/repo@<40-char-commit-sha>` for every external action.
- Keep the upstream major version in a trailing comment, for example `# v4`, so reviewers can still see the intended release line.
- Treat changes to pinned SHAs like dependency upgrades: review the upstream release notes before merging.

## Update Path

- Dependabot tracks the `github-actions` ecosystem weekly from `.github/dependabot.yml`.
- Review each update PR for the new SHA, the referenced upstream version, and any workflow-input changes before merge.
- If an urgent security or reliability fix lands before the next scheduled update, open a manual PR that updates only the affected action pins.

## Review Expectations

- Do not introduce floating refs such as `@v4`, `@v5`, `@main`, or tool-specific tags like `@just` in committed workflows.
- When a workflow needs a tool-specific install action, pin the action SHA and pass the tool name through inputs instead of relying on a moving ref.
- Keep workflow-only dependency updates isolated from unrelated product changes where possible.
