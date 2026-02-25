# EVD 5 — Issue-to-Experiment-to-Result Flow

### Of 130 claimed experiments, 50 produced formal results (139 RES nodes), with 15% of claiming involving cross-person idea exchange

---
![Figure 5. Issue-to-experiment-to-result flow](fig5_alluvial_flow.png)

**Figure 5. Of 130 claimed experiments, 50 (38%) produced formal results (139 RES nodes), and 15% of claiming involved cross-person idea exchange.** Alluvial (Sankey) diagram showing all 130 claimed experiments flowing through three stages: Issue Created (left), Issue Claimed (center), and Result Created (right). Band width is proportional to the number of experiments. Green bands indicate self-claiming; purple bands indicate cross-person claiming (idea exchange). Researcher names are anonymized (R1–R11); the PI (Matt Akamatsu) is identified.

[Narrative post](https://experiment.com/u/Hd2AYg#:~:text=2.%2038%25%20of%20claimed%20issues%20led%20to%20a%20new%20research%20result)

### Supplemental

> An [interactive HTML version of the key figure](fig5_alluvial_flow.html) allows hovering to inspect individual flows (download and open locally).

![Supplemental. Aggregate funnel view](fig5_funnel_supplemental.png)

**Supplemental Figure. Of 130 claimed experiments, 50 (38%) produced formal results, from an initial pool of 445 issues (29% claimed).** (Left) Horizontal bar chart showing progressive attrition. (Right) Stage-by-stage composition breakdown.
---

## Evidence description

The issue-to-result funnel was constructed by tracking the attrition of issues through three stages: creation, claiming, and result production. All 445 identifiable issues (320 formal ISS nodes plus 125 experiment pages with inferred claiming) formed the top of the funnel. Of these, 130 (29%) were claimed — 69 explicitly claimed (with `Claimed By::` field), 56 inferred as claimed (experimental log entries by the page creator), and 5 ISS pages with experimental log activity. This represents a 29% issue-to-experiment conversion rate.

Of the 130 claimed experiments, 50 (38%) had at least one linked RES (Result) node, representing experiments that produced a formally recorded result. The remaining 80 claimed experiments either have work still in progress or recorded their outputs in formats other than formal `[[RES]]` pages. The 50 result-producing experiments generated a total of 139 RES nodes, averaging 2.8 results per experiment. Overall, 11% of all issues progressed through the full funnel from creation to formal result production.

## Summary

This evidence bundle traces the full lifecycle of research questions in the MATSUlab discourse graph — from issue creation through experiment claiming to formal result production — and reveals who is involved at each stage.

### Conversion funnel

| Stage | Count | Rate |
|-------|------:|-----:|
| Total issues | 445 | — |
| Claimed as experiments | 130 | 29% of issues |
| Produced formal results | 50 | 38% of claimed |
| Total RES nodes | 139 | 2.8 avg per experiment |

### Idea exchange

| Flow type | Count | Rate |
|-----------|------:|-----:|
| Self-claimed (same person) | 106 | 85% |
| Cross-person claiming | 19 | 15% |

The 19 cross-person claiming cases represent **idea exchange** — cases where a researcher picked up an issue created by someone else. The alluvial diagram reveals the specific pathways: which researchers create issues that others claim, and who ultimately produces the results.

### Key observations from the flow diagram

- **R1** created the most issues and claimed the most experiments, with most being self-claimed
- **Matt Akamatsu** created issues that were claimed by multiple different researchers, serving as a hub for idea distribution
- **80 of 130 claimed experiments** have not yet produced a formal RES node (shown as "No Result Yet" on the right), indicating work-in-progress or informal output recording
- Cross-person flows (purple bands) connect diverse researcher pairs, with Matt Akamatsu as the primary issue source for cross-person claiming

## Grounding context

In the discourse graph system, the path from question to answer follows a structured workflow: **Issue (ISS)** → **Experiment** (someone claims the issue and begins work) → **Result (RES)** (formal result node linked back to the experiment). The alluvial diagram visualizes this three-stage flow at the researcher level.

This bundle shares the same underlying metrics pipeline as EVD 1. Readers should be aware of the following when interpreting the flow diagram:

- **Claiming detection is metadata-dependent.** Claiming was assessed via the `Claimed By::` page attribute, page authorship, or authorship of dated log entries within experiment pages. Issues informally transferred between researchers — without updating the metadata — are not captured.
- **Inferred claiming defaults to self-claimed.** When no `Claimed By::` field is present, the claiming is attributed to the page creator, likely **underestimating** cross-person idea exchange.
- **Attribution priority chain.** When multiple metadata fields exist (`Made By::`, `Claimed By::`, `Author::`, JSON-LD creator), the pipeline uses the first available in that order. If fields disagree about who created or claimed the issue, only the highest-priority field is used.
- **"No Result Yet" is ambiguous.** 80 of 130 claimed experiments show no linked RES node. This could mean work is in progress, results were recorded informally, or the experiment was abandoned. The diagram does not distinguish between these cases.
- **Cross-person flows require known authorship on both sides.** If either the issue creator or the person who claimed is unknown, that experiment is excluded from the self-claimed / cross-person classification (but still counted in the total). This may further underestimate cross-person exchange.
- **Flows reflect formal metadata, not informal collaboration.** A researcher who contributed ideas, code review, or analysis support but is not listed in the `Claimed By::` or `Made By::` fields will not appear in the diagram.



## Methods

Metrics pipeline: [`src/calculate_metrics.py`](../../../src/calculate_metrics.py)
Alluvial diagram: [`src/handoff_visualizations.py`](../../../src/handoff_visualizations.py)
Funnel chart: [`src/generate_visualizations.py`](../../../src/generate_visualizations.py)
Bundle generator: [`src/create_evidence_bundle.py`](../../../src/create_evidence_bundle.py)
Full pipeline trace: [`notebooks/evd1_evd7_analysis.ipynb`](../../../notebooks/evd1_evd7_analysis.ipynb)

See [`methods_excerpt.md`](methods_excerpt.md) for detailed methodology covering node identification, claiming detection, and RES linking.

## Data

- [`data/funnel_summary.json`](data/funnel_summary.json) — Aggregated funnel counts, conversion rates, and claiming authorship breakdown
- [`data/experiment_details.csv`](data/experiment_details.csv) — Per-experiment rows with anonymized creator, person who claimed, claiming type, timestamps, result counts, and time metrics (130 rows)

## Metadata

- [`evidence.jsonld`](evidence.jsonld) — Canonical JSON-LD metadata (evidence statement, observable, method, provenance)
- [`ro-crate-metadata.json`](ro-crate-metadata.json) — RO-Crate 1.1 manifest

## Source material

Contact [The Discourse Graphs Project](mailto:discoursegraphsATgmailDOTcom) for read access to the following source material:
- [Experimental log](https://roamresearch.com/#/app/discourse-graphs/page/E5UYzWC6b)
- [Result page: EVD 5](https://roamresearch.com/#/app/discourse-graphs/page/EBoRlwI78)
- Raw data: MATSUlab graph in JSON-LD and JSON

## Attribution

- **Analysis and evidence bundles:** [Matt Akamatsu](https://orcid.org/0000-0002-0286-5310) and [Claude](https://claude.ai) (Anthropic)
- **Review:** [Joel Chan](https://orcid.org/0000-0003-3000-4160)
- **Discourse graph system:** [Discourse Graphs Project](https://discoursegraphs.com/), [Joel Chan](https://orcid.org/0000-0003-3000-4160), [Matt Akamatsu](https://orcid.org/0000-0002-0286-5310)
- **Lab discourse graph data:** [Akamatsu Lab](https://matsulab.com), University of Washington
- **Discourse Graph extension:** [DiscourseGraphs](https://github.com/DiscourseGraphs/discourse-graph)

## License

[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)
