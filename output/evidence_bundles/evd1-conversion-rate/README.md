# EVD 1 — Issue Conversion Rate

### 29% of MATSUlab issues were claimed as experiments, and 38% of those produced at least one formal result node

---

## Figure

![Figure 1. Issue conversion rate and claiming authorship](fig1_conversion_rate.png)

**Figure 1. Issue conversion rate and claiming authorship in the MATSUlab discourse graph.** **(Left)** Stacked horizontal bar showing the composition of all 445 issues. Blue: explicitly claimed via `Claimed By::` metadata field (n=69). Green: inferred as claimed based on experimental log entries authored by the page creator (n=56). Amber: ISS pages with experimental log activity but no formal conversion to experiment format (n=5). Grey: unclaimed ISS pages with no evidence of active work (n=315). Bracket indicates total claimed issues (130, 29.2%). **(Right)** Donut chart showing claiming authorship breakdown among the 125 claimed experiments with known creator–claimer pairs. Orange: self-claimed where the issue creator and the person claiming were the same person (n=106, 85%). Purple: cross-person claiming where a different researcher claimed the issue (n=19, 15%).

> An [interactive HTML version](fig1_conversion_rate.html) is also included (download and open locally).

---

## Evidence description

The issue conversion rate was computed across all identifiable issues in the MATSUlab Roam Research discourse graph. Issues were identified as either formal ISS (Issue) nodes (n=320) or experiment pages with inferred claiming that lacked formal ISS metadata (n=125), giving a total of 445 issues. An experiment page is identified by a title starting with `@` followed by a type prefix (e.g., `@analysis/...`, `@experiment/...`).

An issue was considered "claimed" if it had been converted to an experiment page — detected via a `Claimed By::` metadata field (explicitly claimed, n=69) or the presence of experimental log entries authored by the page creator (inferred claiming, n=56), plus 5 ISS pages with experimental log activity. This yielded 130 claimed experiments out of 445 total issues (29.2%).

Of the 130 claimed experiments, 50 (38%) had at least one linked RES (Result) node, representing experiments that produced a formally recorded result. The 50 result-producing experiments generated a total of 139 RES nodes, averaging 2.8 results per experiment. The remaining 80 claimed experiments either have work still in progress or recorded their outputs in formats other than formal `[[RES]]` pages.

Among the 125 claimed experiments with known creator–claimer pairs, 85% (106) were self-claimed and 15% (19) were cross-person claiming where the issue creator and the person who claimed it were different people.

## Summary

The issue conversion rate measures how many research questions (Issues) in the lab's discourse graph progressed to active work (Experiments) and formal outputs (Results).

| Stage | Count | Rate |
|-------|------:|-----:|
| Total issues | 445 | — |
| Claimed as experiments | 130 | 29% of issues |
| Produced at least one result | 50 | 38% of claimed |
| Total RES nodes produced | 139 | 2.8 per experiment |

Among the 125 claimed experiments with known authorship:
- **106 (85%)** were self-claimed — the same person who created the issue also worked on it
- **19 (15%)** were cross-person claiming — a different researcher picked up the issue, representing **idea exchange** between lab members

## Grounding context

The MATSUlab discourse graph uses the [Discourse Graph](https://discoursegraph.com) framework in Roam Research. Researchers create **ISS** (Issue) nodes to articulate research questions, then claim them as **experiments** (`@analysis/...` or `@experiment/...` pages) by adding a `Claimed By::` field or by starting an experimental log. Results are recorded as **RES** nodes that reference the parent experiment.

Readers should be aware of the following when interpreting the numbers above:

- **Claiming detection is metadata-dependent.** Claiming was assessed via the `Claimed By::` page attribute, page authorship, or authorship of dated log entries within experiment pages. Issues that were informally transferred between researchers — without updating the metadata — are not captured.
- **Inferred claiming defaults to self-claimed.** When no `Claimed By::` field is present, the claiming is attributed to the page creator. Cross-person transfers that happened without updating the metadata are therefore counted as self-claimed, likely **underestimating** the true idea exchange rate.
- **Issue count depends on naming conventions.** The 445 total issues comprise 320 formal `[[ISS]]` pages plus 125 experiment pages identified by the `@type/` prefix. Research questions articulated in other formats (e.g. daily notes, meeting notes) are not counted.
- **Result linking uses a three-tier fallback.** RES nodes are matched to experiments via (1) explicit JSON-LD relation instances, (2) backreferences in RES titles, or (3) substring matching on experiment descriptions (≥20 characters). Results stored informally — in daily notes, figures without RES pages, or external tools — are not captured. The 38% result rate is therefore a lower bound.
- **Snapshot date.** All counts reflect a single February 2026 export. Work in progress at the time of export is counted as "no result yet."

## Methods

Claiming detection: [`src/calculate_metrics.py`](../../../src/calculate_metrics.py)
Visualization: [`src/generate_visualizations.py`](../../../src/generate_visualizations.py)
Full pipeline trace: [`notebooks/evd1_evd7_analysis.ipynb`](../../../notebooks/evd1_evd7_analysis.ipynb)

See [`docs/methods_excerpt.md`](docs/methods_excerpt.md) for detailed methodology.

## Data

- [`data/conversion_data.json`](data/conversion_data.json) — Aggregated conversion rates, claiming type breakdown, and result statistics

## Metadata

- [`evidence.jsonld`](evidence.jsonld) — Canonical JSON-LD metadata (evidence statement, observable, method, provenance)
- [`ro-crate-metadata.json`](ro-crate-metadata.json) — RO-Crate 1.1 manifest

## Source material

Contact [The Discourse Graphs Project](mailto:discoursegraphsATgmailDOTcom) for read access to the following source material:
- [Experimental log](https://roamresearch.com/#/app/discourse-graphs/page/E5UYzWC6b)
- Raw data: MATSUlab graph in JSON-LD and JSON

## Attribution

- **Analysis and evidence bundles:** [Matt Akamatsu](https://orcid.org/0000-0002-0286-5310) and [Claude](https://claude.ai) (Anthropic)
- **Discourse graph system:** [Discourse Graphs Project](https://discoursegraphs.com/), [Joel Chan](https://orcid.org/0000-0003-3000-4160), [Matt Akamatsu](https://orcid.org/0000-0002-0286-5310)
- **Lab discourse graph data:** [Akamatsu Lab](https://matsulab.org), University of Washington
- **Discourse Graph extension:** [DiscourseGraphs](https://github.com/DiscourseGraphs/discourse-graph)

## License

[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)
