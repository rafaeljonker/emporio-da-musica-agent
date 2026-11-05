---
name: reviewing-changes
description: Use when a branch, pull request or phase of this repository needs review before merge, when someone asks for reviewers or a second opinion on changes, or before closing a phase checkpoint.
---

# Reviewing changes

A review here is a set of **claims that survived an attempt to refute them**. Reviewers look at the change through risk lenses, and challengers try to break every claim. Only claims backed by evidence reach the verdict.

You coordinate. Reviewing the diff yourself biases the challenge round, so you don't.

## 1. Frame the change
Write `.superpowers/reviews/<YYYY-MM-DD>-<target>/frame.md` with:
- **Target:** PR number, or a branch range such as `main...HEAD`. Save the diff once as `change.diff` next to it (`gh pr diff <N>` or `git diff <range>`). If the diff is empty, stop.
- **Phase:** the active plan in `docs/superpowers/plans/`. Record what this phase delivers, what it explicitly leaves for later, and any deferrals recorded in `.superpowers/sdd/*/progress.md`.
- **Binding sources:** the spec (`docs/superpowers/specs/`), `AGENTS.md` and `.claude/rules/`. Copy the decisions this change touches, verbatim, with section numbers (at most 40 lines).
- **Change map:** each changed path → the domain or concern it belongs to → the spec decision it implements.

## 2. Pick lenses
Open `lenses.md`. Choose the lenses whose trigger matches the change map. Pick at least 3 and no more than 6. Always add **L0 Contract integrity**.

## 3. Fan out
Send all lens reviewers in **one message**, as parallel background agents, each with `reviewer-brief.md` filled in for its lens. Each reviewer writes `lens-<id>.md` in the review folder.

## 4. Challenge
When a lens file lands, dispatch a challenger with `challenger-brief.md`, one per lens, in parallel. The challenger marks each claim **HOLDS**, **WEAKENED** or **REFUTED**, and adds what the lens should have caught.

## 5. Verdict
Write `verdict.md` in the review folder, then show it:

| # | Severity | Where | Claim | Evidence | Fix |
|---|---|---|---|---|---|

- **Which claims go in:** only claims marked HOLDS or WEAKENED. Downgrade WEAKENED claims by one level.
- **Order:** BLOCKER first, then FIX-NOW, LATER and DEFERRED.
- **Refuted claims:** list them below the table with the challenger's reason, so the user can audit the challenge.
- **Last line:** `Merge: ready | after FIX-NOW | blocked`.

## Severity
| Level | Meaning |
|---|---|
| **BLOCKER** | Wrong behavior, data exposure, a secret, broken build or CI, or a broken spec decision. |
| **FIX-NOW** | Will bite in the next phase, a misleading doc or instruction, or a gate that silently does not check. |
| **LATER** | Real, but nothing builds on it yet. |
| **DEFERRED** | The phase plan or ledger already postpones it. Never counts against the merge. |

## When the shortcut is tempting
| Shortcut | Why it fails |
|---|---|
| "Small change, one reviewer is enough" | Small diffs still cross lenses, and a single pass misses the ones it doesn't think of. Run the 3-lens minimum. |
| "I'll sanity-check the claims myself" | The coordinator anchors on the first plausible reading. Challengers exist to disagree. |
| "AGENTS.md covers the rules" | Only the spec and the phase plan say what is a defect now and what is deferred. |
| "It reads like a bug" | No evidence means no BLOCKER. Reproduce it, cite the line, or mark it LATER as unverified. |
