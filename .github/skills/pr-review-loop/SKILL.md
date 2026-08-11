---
name: pr-review-loop
description: Iteratively drive a machine-calc pull/merge request to green — fixing code until GitHub Copilot (balanced) code review comments and all required CI jobs pass — then require explicit user approval, a high-level summary of all commits, and cleanup of stale branches before closing. Use whenever asked to "work on a PR/MR until it's mergeable", "address Copilot review comments", "get CI green on this PR", or "finish up and close this MR".
---

# PR Review Loop (machine-calc)

Use this skill whenever you are asked to drive an open pull request (the
user may call it an "MR") to a mergeable, closeable state: fixing code
against GitHub Copilot code review feedback and CI failures in a loop,
with explicit checkpoints before anything destructive happens (merge,
close, branch/worktree deletion).

Prefer `gh` CLI (per this repo's convention) over the GitHub MCP server for
all PR/CI/review operations below.

## 1. Setup — identify the PR and gather state

```bash
gh pr view <number-or-branch> --json number,title,url,headRefName,baseRefName,state,mergeable,reviewDecision,commits,body
gh pr checks <number-or-branch>
```

If no PR number/branch is given, infer it from the current branch
(`git branch --show-current`) and confirm with the user if ambiguous.

Keep the fetched `body` (the PR description) on hand — §2's suppression
check depends on cross-referencing it against the "Quality & Security Gate
Exceptions" table, and it can go stale if the description is edited
mid-loop, so re-fetch it whenever re-checking suppression status.

Initialize (mentally or in a scratch note) two counters for this session:
- **review-fix commit count** — commits made *specifically* to address a
  Copilot review comment or a failing CI job. Resets only if the user
  explicitly asks to continue past the 10-commit checkpoint (see §4).
- **running summary** — one line per commit describing what changed and
  why, to be presented at the 10-commit checkpoint and again at closure.

## 2. Fetch Copilot review comments, excluding suppressed ones

Copilot review runs at the "balanced" preset for this repo (see
`.github/skills/code-review/SKILL.md` for the review context Copilot
itself uses). Fetch review threads via the GraphQL API so resolved state
is available (REST `pulls/comments` does not expose it):

```bash
gh api graphql -f query='
  query($owner:String!,$repo:String!,$pr:Int!) {
    repository(owner:$owner, name:$repo) {
      pullRequest(number:$pr) {
        reviews(last:20, states:[COMMENTED, CHANGES_REQUESTED]) {
          nodes { author { login } body state }
        }
        reviewThreads(first:100) {
          nodes {
            isResolved
            isOutdated
            comments(first:10) { nodes { author { login } body path line } }
          }
        }
      }
    }
  }' -f owner=<org> -f repo=<repo> -F pr=<number>
```

A comment counts as **suppressed / not actionable** — and must be
**ignored** — if any of the following hold:

- The review thread `isResolved: true` (a maintainer already resolved it).
- The comment is about a finding that already has a matching in-code
  suppression comment (`# noqa: C901`, `# nosec B###`) **and** a
  corresponding entry in the PR description's "Quality & Security Gate
  Exceptions" table (see `.github/pull_request_template.md`) — this repo's
  documented, accepted-exception convention.
- The author is not a Copilot review bot (e.g. `copilot-pull-request-reviewer`)
  — human/other-bot comments are informational context, not a gate, unless
  the user says otherwise.

Everything else from the Copilot reviewer that is unresolved is in scope
and must be fixed or explicitly rebutted (with a reply comment) before
proceeding.

## 3. Iterate: fix → commit → push → re-check

Repeat until both are true: all required CI jobs are green **and** no
non-suppressed Copilot review comments remain unresolved.

1. Pick the highest-value unresolved item (correctness/test bugs before
   style nits) or the first failing CI job.
2. Make the fix. Follow `.github/instructions/python.instructions.md` and
   the priorities in `.github/skills/code-review/SKILL.md` (calculation
   correctness > resource limits > tests > extensibility > style).
3. Run the smallest targeted test/lint/build command locally that covers
   the change before pushing (see repo CI job list below) — don't rely on
   CI alone for feedback loop speed.
4. Commit with a message describing the specific review comment or CI
   failure addressed (not a generic "fix review comments"). Increment the
   review-fix commit counter and append a line to the running summary.
5. Push: `git push`.
6. Re-request Copilot review if it doesn't auto re-review on push:
   `gh pr comment <number> --body "@copilot review"` or re-request via
   `gh api repos/:owner/:repo/pulls/:number/requested_reviewers`.
7. Poll CI: `gh pr checks <number> --watch` (or re-poll after a short
   wait). Required jobs in this repo's `ci.yml`: `lint`, `complexity`,
   `typecheck`, `security`, `dependency-scan`, `test`, `build`, `docs`,
   plus CodeQL. `performance` and `deploy-docs`/`quality-summary` are
   supporting jobs — check `ci.yml` if unsure which are branch-protection
   required.
8. Re-fetch review threads (§2) to see what's newly resolved/added.

## 4. 10-commit checkpoint

The moment the **review-fix commit count** (from step 3, not all commits
on the PR) reaches 10, stop looping immediately — do not start another
fix — and:

1. Summarize all review-fix commits made so far in this session (one line
   each: commit SHA/message + what it addressed).
2. State current status: which CI jobs are green/red, how many Copilot
   comments remain unresolved.
3. Give a recommendation (e.g. "N items are trivial style nits left,
   recommend continuing" or "remaining items look architecturally
   significant, recommend a human look before more automated commits").
4. Ask the user, via `ask_user`, whether to continue iterating. Only
   resume the loop (§3) on explicit "yes" — do not assume.

If the user says yes, keep counting further commits and re-checkpoint
every additional 10.

## 5. Exit criteria for the loop

The loop (§3) is done only when, on a fresh fetch:
- `gh pr checks <number>` shows all required jobs passing (no pending
  jobs either — wait them out).
- No unresolved, non-suppressed Copilot review comments remain (§2).

Do not treat "PR looks fine to me" as sufficient — always do the fresh
`gh pr checks` + review-thread re-fetch before declaring done.

## 6. Closure — never automatic

Once §5's exit criteria are met, the PR is *ready* to close/merge, but you
must not merge, close, or delete anything yet. Before asking for approval:

1. Produce a high-level summary of **all** changes/commits on the PR
   (not just this session's fixes) — pull the full commit list:
   `gh pr view <number> --json commits --jq '.commits[].messageHeadline'`
   and group it into a short narrative (what the PR does overall, then
   what was fixed during review iteration).
2. Confirm CI status and review status explicitly in that summary (green
   checkmarks, 0 unresolved required comments).
3. Post an AIC usage summary comment on the PR using real markdown newlines.
   Do not use inline `--body "...\n..."` strings because GitHub CLI will post
   literal `\n` characters. Always write the comment to a file (heredoc) and
   post with `--body-file`, for example:

```bash
cat > /tmp/pr-aic-summary.md <<'EOF'
## Session usage summary for authoring this PR

### Scope
Covers the PR-authoring session, including review-loop and CI-fix work.

### Totals
- **Session window:** <start> -> <end> (~<duration>)
- **Session turns:** <turn_count>
- **AIC events:** <event_count>
- **Input tokens:** <input_tokens>
- **Output tokens:** <output_tokens>
- **Total AI usage:** <total_aiu> AIU

### By model

| Model | AIC events | Input tokens | Output tokens | AIU |
|---|---:|---:|---:|---:|
| <model> | <events> | <input> | <output> | <aiu> |

### Copilot code-review credits
- **Per-session code-review credit total:** <value or "not separately exposed in local telemetry">.
- **Attribution status:** <how review activity is/is not isolated>.

### Cost note
USD value may be unavailable from local telemetry unless billing rates are available.
EOF
gh pr comment <number> --body-file /tmp/pr-aic-summary.md
rm /tmp/pr-aic-summary.md
```

   If prior malformed summary comments exist (literal `\n`), replace them by
   editing the latest summary comment or deleting malformed ones with:
   `gh api repos/<owner>/<repo>/issues/comments/<comment_id> -X DELETE`.
4. Ask the user for explicit approval via `ask_user` — do not merge/close
   on an assumption of approval, and do not proceed on a vague or partial
   answer.

Only after explicit approval:

1. Merge/close the PR per the user's stated preference (e.g.
   `gh pr merge <number> --squash` — confirm merge method if not already
   agreed).
2. Delete the now-stale remote branch (`gh pr merge --delete-branch`, or
   `git push origin --delete <branch>` if closed without the flag).
3. Clean up local state: delete the local branch
   (`git branch -d <branch>`) and remove any associated worktree
   (`git worktree remove <path>`) — mirror the stale-branch cleanup
   pattern already used in this repo's workflow.
4. Re-run `git branch -vv` and `git worktree list` to confirm cleanup.

Note: merged PRs cannot be reopened on GitHub. If post-merge Copilot review is
required, open a follow-up PR and request review there.

## 7. Anti-patterns to avoid

- Counting all commits (docs typos, rebases) toward the 10-commit
  checkpoint instead of only review/CI-fix commits.
- Treating a resolved-but-still-`isOutdated:false`-with-new-diff thread as
  settled — GitHub can silently re-open relevance after a force-push;
  always re-fetch after pushing.
- Ignoring a Copilot comment because it "seems minor" without it actually
  meeting a suppression criterion from §2.
- Merging, closing, or deleting branches/worktrees without a fresh,
  explicit user approval in the same session.
- Treating `performance` job or opt-in test suites as blocking when they
  are not part of required status checks (verify in branch protection or
  `ci.yml` before treating a red non-required job as a blocker).
