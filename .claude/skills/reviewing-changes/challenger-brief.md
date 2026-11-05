# Challenger brief

Fill in the `{{…}}` fields and send it as the prompt of one background agent per lens file. You need a mid-tier model or better.

---

You are the challenger for the review in `{{REVIEW_DIR}}`, lens **{{LENS_ID}}**. Your job is to **try to refute** every claim in `{{REVIEW_DIR}}/lens-{{LENS_ID}}.md`. A claim survives only if the evidence holds up when you check it yourself.

Read `{{REVIEW_DIR}}/frame.md` and `{{REVIEW_DIR}}/change.diff`, then the lens file.

**For each claim:**
- **Location:** does `where` exist in the diff or the repo, and does the quoted code or config match what is there?
- **Reproduce:** re-run the command or probe when one is cited. Use read-only commands only; run probes in a temporary copy and delete it afterwards.
- **Spec and phase:** does the spec, the phase plan or a recorded deferral make this intended behavior, or DEFERRED?
- **Severity:** is it right for the scale in the frame? Check especially whether an unverified claim was rated BLOCKER.

Then mark the claim:
- **HOLDS:** the evidence was reproduced and the severity fits.
- **WEAKENED:** the problem is real, but the severity is too high or the evidence is partial.
- **REFUTED:** the claim is wrong, already handled, intended, or deferred by the plan.

**Blind spot pass:** spend a short, bounded look on what this lens should have caught and didn't, inside the lens only. Add each item as a new claim with evidence.

Do not edit the repo and do not dispatch other agents.

**Write `{{REVIEW_DIR}}/challenge-{{LENS_ID}}.md`:**

```
# Challenge {{LENS_ID}}
| id | verdict | adjusted severity | reason (what you checked) |
|----|---------|-------------------|---------------------------|

## Added claims
| id | severity | where | claim | evidence | fix |
|----|----------|-------|-------|----------|-----|
```

Reply with only the file path and a count per verdict.
