# C014 — V2 feature branch and Draft PR governance audit

**C014 checklist creation/segregation gate: PASS (2/2).** The branch and Draft PR were already present before this verification. This is a verification record, **not** a claim that GitHub branch protection is enabled.

## Verified from live GitHub, 2026-11-06

| Item | Live evidence | Verdict |
| --- | --- | --- |
| Repository default branch | `main` | PASS |
| Stable main commit | `9db79a35eabcf7b14a524d0dc9fa73ffd38e843d` (initial commit) | PASS: unchanged within observed V2 feature development ancestry |
| V2 feature branch | `feature/v2-research-rebuild` at `5c9a86be7d6377fd688b91cb8309826ededd55fa` before this document commit | PASS |
| Draft pull request | [#1](https://github.com/1976haru/newvideo/pull/1), OPEN / DRAFT / merged=false | PASS |
| PR direction | `feature/v2-research-rebuild` → `main` | PASS |
| Git comparison | Feature is 64 commits ahead of main, 0 behind; merge-base is `9db79a3` | PASS |
| `main` GitHub `protected` flag | **false** | **RISK / ENFORCEMENT GAP** |
| Repository rulesets | API returned an empty list `[]` | **RISK / ENFORCEMENT GAP** |
| Detailed branch protection endpoint | Connector returned HTTP 403 `Resource not accessible by integration` | Cannot inspect/edit protection via this connector |

**Interpretation:** Repository development has proceeded only on the feature branch and Draft PR #1 is unmerged; the checklist's branch+Draft PR setup is complete. However, a **process rule in `AGENTS.md` does not amount to server-side enforcement**. A direct push or unreviewed merge to `main` may not be blocked by GitHub. We must not describe main as technically protected yet.

## Process safety rules in force

- `main` remains the stable target; never directly change it for C014 or development.
- Implement on feature branch → run Windows/Ubuntu CI → keep Draft PR → review → merge only when all relevant acceptance gates pass.
- Do not force push, auto-merge or mark the Draft PR ready before required acceptance tests. The incomplete R1/R2/R3/R4/R5 functionality makes merging premature.
- C007/C009/C010/C012 outstanding V2 Windows and data-preservation gates remain open. C014 PASS does **not** imply product readiness.
- Do not modify user data, keyring credentials, existing V1 program or backups as part of Git policy verification.

## GitHub manual safety-hardening action (not yet executed)

The connected GitHub integration cannot access the branch-protection administration endpoint (403) and has no writable ruleset action. A repository administrator should configure GitHub `Settings → Rules → Rulesets` (or `Settings → Branches → Add branch protection rule` where supported) with branch target `main`:

1. Require a pull request before merging; at least one reviewer approval if available for repository type/plan; dismiss stale approval after new commits where supported.
2. Require all currently meaningful Windows/Ubuntu Python CI checks, C012 preservation gate, Windows Qt smoke and PowerShell backup test **after identifying the exact check names** from a passing run. Do not guess or set a stale required check.
3. Block force pushes, branch deletion and bypass, including administrators when available.
4. Confirm whether repository/org restrictions actually enforce the desired rules, then re-query the branch's `protected` flag and review a failed direct-push simulation in a *non-main test branch*, never experimentally push to `main`.
5. Keep PR #1 as Draft until release criteria are met.

**Required follow-up:** obtain administrator screenshot/ruleset evidence and verify active protection independently. This is a separate hardening gap, not an excuse to merge or alter `main`.

## Commands / evidence sources

Equivalent local read-only checks:

```sh
git branch -a
gh pr view 1 --json number,state,isDraft,baseRefName,headRefName,mergedAt
git rev-parse main
git rev-parse feature/v2-research-rebuild
git rev-list --left-right --count main...feature/v2-research-rebuild
```

Actual verification in this review was via the GitHub connector, not by pretending to have run the above local commands. GitHub Actions at code commit `5c9a86be7d6377fd688b91cb8309826ededd55fa`: workflow runs [42120558218](https://github.com/1976haru/newvideo/actions/runs/42120558218) and [42120547354](https://github.com/1976haru/newvideo/actions/runs/42120547354) completed SUCCESS. No new tests are required for this documentation-only governance audit.
