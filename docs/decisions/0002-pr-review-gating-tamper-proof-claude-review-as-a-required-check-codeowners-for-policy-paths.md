# ADR 0002 — PR review gating: tamper-proof Claude review as a required check, CODEOWNERS for policy paths

- **Status:** Accepted
- **Date:** 2026-08-23
- **Deciders:** operator + agent
- **Context source:** operator request to match the review protections of the operator's public repos before making this one public

## Context

This repository is going public. Its Claude review workflow was the early form: prompt inline in the yml, no fork guard, no fail-closed step, no required check, no branch protection at all. A PR could edit the reviewer's own instructions and get reviewed against them, and a PR could be merged with no review.

## Decision

Automated code review follows the pattern the operator's other public repos use:

- `.github/workflows/claude-code-review.yml` runs `anthropics/claude-code-action` on non-draft, non-fork PRs. Review instructions live in `.github/review-prompt.md` (+ `.github/review-guides/`) and are **materialized from the default branch** with `git show`, never read from the PR checkout. The job **fails closed** if the action did not run (its anti-tamper gate self-skips when the PR's copy of the workflow differs from main) or if no formal `gh pr review` was recorded.
- `claude-review` is a **required status check** on `main`, together with Lint, the Unit Tests matrix, Integration (Uptime Kuma 2.x) and Build Collection. `main` requires one approving review, conversation resolution, and forbids force pushes and deletion.
- `.github/CODEOWNERS` names the operator on exactly the paths the review prompt tells the reviewer to defer on (decisions, the protocol layer, release/dependency surface, the rules and the review machinery). No blanket owner: that would make the automated review advisory.
- `.github/workflows/claude.yml` handles on-demand `@claude` mentions with the same materialized-instructions pattern.

## Rejected alternatives

- **Keep the inline prompt.** A long `prompt: |` block is a parse hazard and the PR can edit it; materializing from main removes both.
- **Blanket `* @GoodOlClint` CODEOWNERS.** Puts a human on every routine PR, which is what the automated reviewer exists to avoid.
- **Pass-on-skip for the anti-tamper case.** A PR that edits the reviewer would then go green without being reviewed; red is the correct signal.

## Consequences

- PRs that change the review workflow, its prompts, CODEOWNERS or branch protection need operator review and an admin merge — by design.
- Fork PRs get no automated review (no secrets); the maintainer reviews them directly.
- The prompt's "defer to operator" list and CODEOWNERS must be kept in sync by hand.
- Private infrastructure references are now a hard-constraint violation in review (prompt rule 10); deployment-specific analysis lives in the deployment's own repo.
