# EVD 7 — Undergraduate Researcher Onboarding Timeline

### All three undergraduate researchers produced a formal result within ~4 months, with two reaching their first result within ~1 month

---

## Figure

![Figure 7. Undergraduate researcher onboarding timeline](fig7_student_timelines.png)

**Figure 7. Use of the issues board led to three undergraduate researchers producing results in 125, 47, and 36 days from start date.** Timeline showing the progression of three anonymized undergraduate researchers (A, B, C) from lab start to first formal result (RES node). Milestones tracked: first day in lab, first experiment, first plot, and first RES node. Numbers indicate days from lab start. Researcher A followed a self-directed exploration pathway (125 days to RES). Researcher B was assigned an entry project (47 days). Researcher C was directly assigned to an existing experiment (36 days).

> An [interactive HTML version](fig7_student_timelines.html) is also included (download and open locally).

---

## Evidence description

The onboarding timeline was reconstructed for three undergraduate researchers by tracing key milestones through their daily notes and the discourse graph: (1) first day in lab, (2) first experiment reference in daily notes, (3) first plot (linked image in notes), and (4) first formal RES node creation. Dates were extracted from Roam Research page metadata and daily log entries.

Researcher A joined the lab on February 23, 2024 and claimed their first experiment (`@analysis/Quantify the percentage of simulated endocytic events that assemble detectable amounts of actin`) on April 5, 2024 (42 days). They produced their first plot on June 20, 2024 (118 days) and first RES node on June 27, 2024 (125 days). This represents a self-directed exploration pathway where the student browsed the Issues board and claimed an experiment matching their interests.

Researcher B joined on October 10, 2024 and was assigned an entry project (`@analysis/Plot the number of bound Hip1R over time for different Arp2/3 distributions in endocytosis simulations`) explicitly designed "to get acquainted with our simulations and the analysis framework." They began work on October 15, 2024 (5 days), producing plots the same day. Their first RES node was created November 26, 2024 (47 days).

Researcher C joined on June 23, 2025 and was assigned to an existing experiment (`@analysis/correlate segmented endocytic spots to cell location (apical, basal, lateral) in 3D`) via the "Possible Contributors" field. They began work on June 30, 2025 (7 days), produced first plots on July 7, 2025 (14 days), and created their first RES node on July 29, 2025 (36 days) — the fastest time-to-result among the three.

The mean time-to-first-RES for undergraduate researchers (69 days) was faster than the overall lab average (88.3 days), suggesting that structured onboarding pathways — whether through assigned entry projects or direct experiment assignment — accelerate early productivity while maintaining result quality.

## Summary

This evidence bundle quantifies how quickly undergraduate researchers produced formal results after joining the lab, comparing three different onboarding pathways through the discourse graph's issue board.

### Milestone timeline

| Researcher | Start date | Days to experiment | Days to plot | Days to RES | Pathway |
|:----------:|:----------:|-------------------:|-------------:|------------:|---------|
| **A** | Feb 23, 2024 | 42 | 118 | **125** | Self-directed exploration |
| **B** | Oct 10, 2024 | 5 | 5 | **47** | Assigned entry project |
| **C** | Jun 23, 2025 | 7 | 14 | **36** | Direct assignment |

### Comparison to lab average

| Metric | Undergrad mean | Lab average |
|--------|---------------:|------------:|
| Days to first RES | **69** | 88 |

All three undergraduates reached their first formal result faster than the lab-wide average of 88 days, suggesting that structured onboarding through the issue board accelerates early productivity.

### Onboarding pathways

**Researcher A — Self-directed exploration (125 days)**
Browsed the issue board independently and claimed an experiment matching their interests. Longest ramp-up time (42 days to first experiment), but produced a result autonomously with minimal direction.

**Researcher B — Assigned entry project (47 days)**
Was assigned a specific experiment designed to introduce the lab's simulation and analysis framework. Began producing plots within 5 days of starting. The structured entry point provided a clear on-ramp.

**Researcher C — Direct assignment (36 days)**
Was added as a contributor to an existing experiment via the `Possible Contributors::` field. Fastest time to result (36 days), benefiting from existing infrastructure and clear deliverables.

## Grounding context

The MATSUlab discourse graph uses an **Issues board** — a shared collection of research questions (ISS nodes) that any lab member can browse and claim. This evidence bundle asks: how effectively does this system support new researcher onboarding? Four milestones were tracked for each researcher: first day in lab, first experiment, first plot, and first formal RES node.

Unlike EVD 1 and EVD 5, this analysis is a manually curated case study rather than an automated pipeline output. Readers should keep the following in mind:

- **Milestone dates were manually extracted** by reviewing daily notes and experiment page metadata in Roam Research. They are not computationally derived from the graph export. Dates reflect the analyst's judgment about when each milestone was first reached.
- **Small sample (n = 3).** The three researchers joined the lab at different times (Feb 2024, Oct 2024, Jun 2025) under potentially different lab conditions, mentorship availability, and issue board maturity. The sample size does not support statistical generalization.
- **Pathway classification is post-hoc.** The labels "self-directed exploration," "assigned entry project," and "direct assignment" were assigned by the PI based on recollection of how each student was onboarded. They are not properties inferred from the discourse graph structure.
- **Timeline measures elapsed days, not effort.** Researchers had varying course loads, lab hours, and prior experience. A shorter time-to-result does not necessarily indicate a more effective pathway — it may reflect more available time or more relevant prior skills.
- **"First RES node" measures formal output, not quality.** The milestone tracks when a formal result page was created in the discourse graph, not whether the result was complete, correct, or publishable.
- **Lab average comparison (88 days) is drawn from a different population.** The lab-wide average includes all researchers (faculty, graduate students, undergraduates) across the full history of the graph. The undergraduate mean (69 days) is not directly comparable because the populations and time periods differ.

## Methods

Timeline analysis: [`src/student_timeline_analysis.py`](../../../src/student_timeline_analysis.py)
Bundle generator: [`src/create_evidence_bundle.py`](../../../src/create_evidence_bundle.py)
Full pipeline trace: [`notebooks/evd1_evd7_analysis.ipynb`](../../../notebooks/evd1_evd7_analysis.ipynb)

See [`methods_excerpt.md`](methods_excerpt.md) for detailed methodology.

## Data

- [`data/student_milestones.json`](data/student_milestones.json) — Per-researcher milestone dates, days-from-start, and pathway classification

## Metadata

- [`evidence.jsonld`](evidence.jsonld) — Canonical JSON-LD metadata (evidence statement, observable, method, provenance)
- [`ro-crate-metadata.json`](ro-crate-metadata.json) — RO-Crate 1.1 manifest

## Source material

Contact [The Discourse Graphs Project](mailto:discoursegraphsATgmailDOTcom) for read access to the following source material:
- [Experimental log](https://roamresearch.com/#/app/discourse-graphs/page/E5UYzWC6b)
- [Result page: EVD 7](https://roamresearch.com/#/app/discourse-graphs/page/0FU6ssOwH)
- Raw data: MATSUlab graph in JSON-LD and JSON

## Attribution

- **Analysis and evidence bundles:** [Matt Akamatsu](https://orcid.org/0000-0002-0286-5310) and [Claude](https://claude.ai) (Anthropic)
- **Discourse graph system:** [Discourse Graphs Project](https://discoursegraphs.com/), [Joel Chan](https://orcid.org/0000-0003-3000-4160), [Matt Akamatsu](https://orcid.org/0000-0002-0286-5310)
- **Lab discourse graph data:** [Akamatsu Lab](https://matsulab.org), University of Washington
- **Discourse Graph extension:** [DiscourseGraphs](https://github.com/DiscourseGraphs/discourse-graph)

## License

[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)
