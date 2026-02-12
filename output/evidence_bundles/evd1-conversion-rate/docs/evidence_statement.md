# EVD 1 — Issue Conversion Rate

## Evidence Statement

18% of MATSUlab issues (n=389) were claimed as experiments and 36% of those claimed at least one formal result node, yielding 44 total RES nodes.

## Evidence Description

The issue conversion rate was computed across all identifiable issues in the MATSUlab Roam Research discourse graph. Issues were identified as either formal ISS (Issue) nodes (n=320) or experiment pages with inferred claims that lacked formal ISS metadata (n=0), giving a total of 389 issues.

An issue was considered "claimed" if it had (a) a `Claimed By::` field populated with a researcher name (explicit claim, n=0), (b) experimental log entries authored by the page creator but no `Claimed By::` field (inferred claim, n=0), or (c) an ISS page with experimental log content indicating active work (n=0). This yielded 69 claimed experiments out of 389 total issues (17.7%).

Of the 69 claimed experiments, 25 (36%) had at least one linked RES (Result) node, representing experiments that produced a formally recorded result. The 25 result-producing experiments generated a total of 44 RES nodes, averaging 1.8 results per experiment. The remaining 44 claimed experiments either have work still in progress or recorded their outputs in formats other than formal `[[RES]]` pages.

Among the 69 experiment-page claims with known creator–claimer pairs, 72% (50) were self-claims and 28% (19) were cross-person claims where the issue creator and claimer were different people.

## Figures

- `fig1_conversion_rate.png` — Static figure (matplotlib)
- `fig1_conversion_rate.html` — Interactive version (HTML/JS)

## Figure Legend

**Figure 1. Issue conversion rate and claim authorship in the MATSUlab discourse graph.** **(Left)** Stacked horizontal bar showing the composition of all 389 issues. Blue: explicit claims identified via `Claimed By::` metadata field (n=0). Green: inferred claims identified by experimental log entries authored by the page creator (n=0). Amber: ISS pages with experimental log activity but no formal conversion to experiment format (n=0). Grey: unclaimed ISS pages with no evidence of active work (n=320). Bracket indicates total claimed issues (69, 17.7%). **(Right)** Donut chart showing claim authorship breakdown among the 69 experiment-page claims. Orange: self-claims where the issue creator and claimer were the same person (n=50, 72%). Purple: cross-person claims where a different researcher claimed the issue (n=19, 28%).
