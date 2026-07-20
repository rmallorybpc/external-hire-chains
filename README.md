# External Hire Chains

A study that was designed, gated, and stopped before it was built. This
repository documents why.

## The question

The parent study, [External Hire Premium](https://github.com/rmallorybpc/external-hire-premium),
tested whether externally hired S&P 500 CEOs cost more and deliver less
than internal promotions. This study asked the sequence question that
followed: when an external CEO exits early, does the board go outside
again, and does the selection pattern that produced the first hire
produce the second?

## The design

The rules were written and committed before any count was run. See
`docs/phase-0-pre-commitments.md`. Four rules governed the study:

1. **The trigger.** An external hire with tenure under 24 months,
   where the exit was forced or performance-driven. Death, illness,
   and planned bridge exits do not count.
2. **The comparison group.** Internal hires with the same short-tenure
   profile, coded by the same rule. A pattern that appears after both
   internal and external failures is failure-specific, not
   external-specific.
3. **The kill threshold.** Successors split three ways: internal,
   boomerang, external. Any single-digit cell in the external split
   stops the study.
4. **The mechanism as a question.** The deepening-lag pathway was a
   hypothesis to test, not a finding inherited from the parent.

## The result

The count killed the study at the sample gate.

The frozen parent panel holds 611 CEO transitions, 158 external. After
applying the tenure window and requiring the successor to fall inside
2010-2022, the candidate set was:

| Group | Candidates |
|---|---|
| External short-tenure | 19 |
| Internal short-tenure | 15 |

Nineteen candidates across three successor-origin cells cannot clear a
single-digit threshold under any coding outcome. The kill condition was
guaranteed by arithmetic before the manual exit-reason coding pass
began. Rule 3 resolved the study at the cost of one extraction script.

## Why publish a killed study

The result is a null count, and the null count is the finding. Chains
of consecutive short-tenure external CEO hires are too rare in an
S&P 500 panel of this window to support the study. That is worth
knowing before build time is spent, and it is only trustworthy because
the threshold was committed before the data was counted. The commit
history in this repository is the proof of order.

## Repository contents
