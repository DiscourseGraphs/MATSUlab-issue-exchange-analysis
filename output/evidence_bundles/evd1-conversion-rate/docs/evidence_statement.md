# EVD 1 — Issue Conversion Rate

## Evidence Statement

29% of MATSUlab issues (n=445) were claimed as experiments, and 15% of those were claimed by a different lab member than the issue creator.

## Evidence Description

The issue conversion rate was computed across all identifiable issues in the MATSUlab Roam Research discourse graph. Issues were identified as either formal ISS (Issue) nodes (n=320) or experiment pages with inferred claiming that lacked formal ISS metadata (n=125), giving a total of 445 issues.

An issue was considered "claimed" if it had (a) a `Claimed By::` field populated with a researcher name (explicitly claimed, n=69), (b) experimental log entries authored by the page creator but no `Claimed By::` field (inferred as claimed, n=56), or (c) an ISS page with experimental log content indicating active work (n=5). This yielded 130 claimed experiments out of 445 total issues (29.2%).

Of the 130 claimed experiments, 50 (38%) had at least one linked RES (Result) node, representing experiments that produced a formally recorded result. The 50 result-producing experiments generated a total of 139 RES nodes, averaging 2.8 results per experiment. The remaining 80 claimed experiments either have work still in progress or recorded their outputs in formats other than formal `[[RES]]` pages.

Among the 125 claimed experiments with known creator–claimer pairs, 85% (106) were self-claimed and 15% (19) were cross-person claiming where the issue creator and the person who claimed it were different people.

## Figures

- `fig1_conversion_rate.png` — Static figure (matplotlib)
- `fig1_conversion_rate.html` — Interactive version (HTML/JS)

## Figure Legend

**Figure 1. 29% of MATSUlab issues (n=445) were claimed as experiments, and 15% of those were claimed by a different lab member than the issue creator.** **(Left)** Stacked horizontal bar showing the composition of all 445 issues. Blue: explicitly claimed via `Claimed By::` metadata field (n=69). Green: inferred as claimed based on experimental log entries authored by the page creator (n=56). Amber: ISS pages with experimental log activity but no formal conversion to experiment format (n=5). Grey: unclaimed ISS pages with no evidence of active work (n=315). Bracket indicates total claimed issues (130, 29.2%). **(Right)** Donut chart showing claiming authorship breakdown among the 125 claimed experiments. Orange: self-claimed where the issue creator and the person claiming were the same person (n=106, 85%). Purple: cross-person claiming where a different researcher claimed the issue (n=19, 15%).
