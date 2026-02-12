# EVD 1 — Issue Conversion Rate

> **18% of MATSUlab issues (n=389) were claimed as experiments and 36% of those claimed at least one formal result node, yielding 44 total RES nodes.**

---

## Figure

![Figure 1. Issue conversion rate and claim authorship](fig1_conversion_rate.png)

**Figure 1. Issue conversion rate and claim authorship in the MATSUlab discourse graph.** (Left) Stacked horizontal bar showing the composition of all 389 issues: unclaimed ISS pages (grey, n=320) and claimed experiments (blue, n=69, 18%). (Right) Donut chart showing claim authorship: self-claims where the issue creator and claimer were the same person (orange, n=50, 72%) vs. cross-person claims where a different researcher claimed the issue (purple, n=19, 28%).

> An [interactive HTML version](fig1_conversion_rate.html) is also included (download and open locally).

---

## Summary

The issue conversion rate measures how many research questions (Issues) in the lab's discourse graph progressed to active work (Experiments) and formal outputs (Results).

| Stage | Count | Rate |
|-------|------:|-----:|
| Total issues | 389 | — |
| Claimed as experiments | 69 | 18% of issues |
| Produced at least one result | 25 | 36% of claimed |
| Total RES nodes produced | 44 | 1.8 per experiment |

Among the 69 claimed experiments:
- **50 (72%)** were self-claims — the same person who created the issue also worked on it
- **19 (28%)** were cross-person claims — a different researcher picked up the issue, representing **idea exchange** between lab members

## Context

The MATSUlab discourse graph uses the [Discourse Graph](https://discoursegraph.com) framework in Roam Research. Researchers create **ISS** (Issue) nodes to articulate research questions, then claim them as **experiments** (`@analysis/...` or `@experiment/...` pages) by adding a `Claimed By::` field or by starting an experimental log. Results are recorded as **RES** nodes that reference the parent experiment.

An issue was counted as "claimed" if it met any of these criteria:
1. A `Claimed By::` field populated with a researcher name (explicit claim)
2. Experimental log entries by the page creator with no `Claimed By::` field (inferred claim)
3. An ISS page with experimental log content indicating active work

## Methods

Claim detection: [`src/calculate_metrics.py`](../../../src/calculate_metrics.py)
Visualization: [`src/generate_visualizations.py`](../../../src/generate_visualizations.py)
Full pipeline trace: [`notebooks/evd1_evd7_analysis.ipynb`](../../../notebooks/evd1_evd7_analysis.ipynb)

See [`docs/methods_excerpt.md`](docs/methods_excerpt.md) for detailed methodology.

## Data

- [`data/conversion_data.json`](data/conversion_data.json) — Aggregated conversion rates, claim type breakdown, and result statistics

## Metadata

- [`evidence.jsonld`](evidence.jsonld) — Canonical JSON-LD metadata (evidence statement, observable, method, provenance)
- [`ro-crate-metadata.json`](ro-crate-metadata.json) — RO-Crate 1.1 manifest

## License

[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)
