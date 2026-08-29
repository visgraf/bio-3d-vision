# Workflow — the four-station loop

One task travels a fixed circuit. Each station does one job and hands on.

```
   ┌─────────────────────────────────────────────────────────────┐
   │                                                             │
   ▼                                                             │
 User ──────────▶ Chat ──────────▶ User ──────────▶ Code ────────┘
  sets the       writes the        relays the       does the work,
  goal           specification     spec verbatim    reports back
                                                          │
                                                          ▼
                                                        Chat
                                                   verifies in-repo,
                                                   returns a verdict
                                                          │
                                          advance ┌───────┴───────┐ escalate
                                                  ▼               ▼
                                                User            User
                                              (next task)     (decides)
                                                  ▲
                                          retry ──┘
```

**User** holds the goal and the authority. Decides what matters, adjudicates
escalations, and is the only station that can change what the project is for.

**Chat** writes specifications and reviews results. It never edits the
repository.

**User relays.** The specification reaches Code through the User, verbatim. This
is not a formality: it is the User's read of the spec before any work is spent
on it, and the point at which a spec that asks for the wrong thing is cheapest to
stop. A spec that could go straight from Chat to Code has skipped its only
review.

**Code** does the work in the repository and reports what it did, what it
measured, and what it could not do.

## The rules

### Every specification carries a falsifier

Not a success criterion — a **falsifier for the specification itself**: a
statement of what result would mean *this specification asked the wrong
question*. It is not about whether the work succeeds. It is about whether the
task was worth specifying.

> If more than roughly a third of items land in `decide`, the criterion is not
> discriminating enough to govern the migration and needs sharpening before it
> is used.

That is the shape. It names a result, a threshold, and the conclusion that the
spec — not the worker — was wrong. Code reports against it whichever way it
comes out, including when it does not fire.

A specification with no falsifier cannot fail, and by this repository's own rule
it does not carry. Chat should refuse to write one without it.

### Every specification states the repository state it assumes

Named explicitly at the top: the branch, the commit, what is tracked, what does
not exist yet, the SHAs of any reference checkout. Code's **first action** is to
verify those assumptions and **reject the task and report** if any is false.

This exists because a specification is written from a snapshot and executed
later, against a repository other work has moved. The predecessors lost an
amendment exactly this way — drafted against a state that had changed by the
time it could land, and lost silently to a merge. An assumption stated is an
assumption that can fail loudly. An assumption unstated fails quietly and much
later.

### Chat clones and verifies in-repo

Chat does not review from excerpts, transcripts, diffs, or grep output. It
clones the branch and checks the claim against the files.

A reviewer working from excerpts can only check that the report is internally
consistent, which is the one thing a wrong report is most likely to be. Numbers
arriving in a report are **hypotheses with pointers** until read at their source.
Line references are checked by opening the line.

### Chat's review returns exactly one of three verdicts

- **advance** — the work is right and the loop moves to the next task.
- **retry** — something specific is wrong and Code can fix it with what it
  already has. Name the defect and the file:line. A retry is not a rewrite of the
  goal.
- **escalate** — the specification was wrong, ambiguous, or asked a question
  whose answer changes what the project should do next. Goes to the User, who
  decides. Chat does not resolve it by rewriting the spec.

**Escalation is expected, not exceptional.** It is the loop's normal way of
discovering that a specification was mis-aimed, which is a thing that happens
often and should. A stretch of tasks with no escalations means either the
specifications are unusually good or the reviewer is not looking hard enough,
and the second is more likely. A reviewer who never escalates is not reviewing;
a reviewer who escalates everything is not reviewing either.

The verdict is stated as one of the three words. "Looks good with some notes" is
not a verdict.

## What crosses the boundary

`docs/state.yaml` is **written by Code and read by Chat, never the reverse.**
Chat does not edit it — that is what keeps it a report of what is true rather
than a record of what was intended. It is the only durable channel from Code back
to Chat, and it is why Chat can start a session without being briefed.

`docs/inherited-measurements.yaml` is what either station cites when it uses a
predecessor's number. Cite the `id`. Every one of them is `inherited`, so citing
one is always the declaration of an assumption.
