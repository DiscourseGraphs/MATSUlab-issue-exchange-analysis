# MATSUlab Issue Exchange Analysis

Metrics and evidence bundles from an analysis of the [Akamatsu Lab](https://akamatsulab.org) (MATSUlab) discourse graph, built in [Roam Research](https://roamresearch.com) using the [Discourse Graph extension](https://github.com/DiscourseGraphs/discourse-graph).

This repository accompanies a study exploring how a shared issue board promotes idea exchange, structured knowledge production, and rapid researcher onboarding in a research lab.

## What's in this repository

### Evidence Bundles

The primary outputs are three **evidence bundles** in `output/evidence_bundles/`. An evidence bundle is a self-contained package that pairs a research finding with the data, figure, methods, and metadata needed to evaluate it. Each bundle follows the [RO-Crate](https://www.researchobject.org/ro-crate/) packaging standard and uses [JSON-LD](https://json-ld.org/) metadata with a discourse graph evidence vocabulary (`dge:`).

Each bundle contains:

| File | Description |
|------|-------------|
| `evidence.jsonld` | Canonical metadata: evidence statement, observable, method, system, provenance, figure legend |
| `ro-crate-metadata.json` | RO-Crate 1.1 manifest listing all bundle contents |
| `fig*.png` | Static figure (primary visualization) |
| `fig*.html` | Interactive figure (Plotly or HTML/JS, where applicable) |
| `data/` | Underlying data files (JSON or CSV) sufficient to regenerate the figure |
| `docs/evidence_statement.md` | Human-readable evidence statement, description, and figure legend |
| `docs/methods_excerpt.md` | Relevant methods sections for the specific analysis |

#### EVD 1 — Issue Conversion Rate (`evd1-conversion-rate/`)

> 18% of MATSUlab issues (n=389) were claimed as experiments and 36% of those produced at least one formal result node, yielding 44 total RES nodes.

- **Figure:** Stacked bar chart showing issue composition + donut chart for self vs. cross-person claiming
- **Data:** `conversion_data.json`

#### EVD 5 — Issue-to-Result Flow (`evd5-issue-funnel/`)

> Of 389 total issues, 69 (18%) were claimed as experiments and 25 (6%) produced at least one formal result node, yielding 44 total RES nodes.

- **Primary figure:** Alluvial (Sankey) diagram showing researcher-level flow from Issue Created → Claimed By → Result Created
- **Supplemental figure:** Aggregate conversion funnel bar chart
- **Data:** `funnel_summary.json`, `experiment_details.csv` (anonymized)

#### EVD 7 — Undergraduate Researcher Onboarding (`evd7-student-onboarding/`)

> All three undergraduate researchers generated an original result from their analysis projects within ~4 months of joining the lab, with two creating a result within ~1 month.

- **Figure:** Pin/stem timeline showing four milestones (lab start, first experiment, first plot, first result) for three researchers
- **Data:** `student_milestones.json`

### Analysis Notebook

`notebooks/evd1_evd7_analysis.ipynb` is a pre-executed Jupyter notebook that walks through the full analysis pipeline, from raw data loading through metric computation to each evidence bundle. It serves as a transparent trace from data to results. The notebook:

- Loads and parses the discourse graph exports (JSON-LD + Roam JSON)
- Shows issue classification, claiming detection, and attribution logic
- Computes each metric with inline commentary
- Generates the data underlying each evidence bundle

> **Note:** The raw data files are not included in this repository (they contain identifiable information). The notebook is pre-executed with all outputs visible, so readers can follow the analysis without the source data.

### Source Code

| File | Purpose |
|------|---------|
| `src/main.py` | Pipeline orchestrator — runs all steps end-to-end |
| `src/parse_jsonld.py` | Parse JSON-LD discourse graph export |
| `src/parse_roam_json.py` | Stream-parse Roam JSON export (block timestamps, experimental logs) |
| `src/calculate_metrics.py` | Merge data sources and compute all metrics |
| `src/generate_visualizations.py` | Generate static figures (conversion rate, time distributions, contributor breadth, idea exchange, funnel) |
| `src/handoff_visualizations.py` | Generate alluvial/Sankey flow diagrams |
| `src/student_timeline_analysis.py` | Student onboarding timeline extraction and visualization |
| `src/create_evidence_bundle.py` | Generate RO-Crate evidence bundles |
| `src/anonymize.py` | Central de-identification module (researcher name → pseudonym mapping) |

### Conversation Log

`conversation_log.md` documents the iterative prompt-response process between Matt Akamatsu and Claude that produced this pipeline. User prompts are reproduced verbatim; Claude responses are summarized. Together they constitute the specification: any output can be traced to the prompt that requested it.

## How results trace from data to evidence bundles

```
Raw data (not in repo)
  Roam JSON export (~47 MB)          JSON-LD export (~11 MB)
        │                                    │
        ▼                                    ▼
  src/parse_roam_json.py              src/parse_jsonld.py
        │                                    │
        └──────────────┬─────────────────────┘
                       ▼
              src/calculate_metrics.py
              (merge, compute 5 metrics)
                       │
           ┌───────────┼───────────────┐
           ▼           ▼               ▼
  src/generate_    src/handoff_    src/student_timeline_
  visualizations   visualizations  analysis.py
           │           │               │
           └───────────┼───────────────┘
                       ▼
           src/create_evidence_bundle.py
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    evd1-          evd5-          evd7-
    conversion-    issue-         student-
    rate/          funnel/        onboarding/
```

The Jupyter notebook (`notebooks/evd1_evd7_analysis.ipynb`) executes this same pipeline interactively, showing intermediate results at each step.

## De-identification

Researcher names have been anonymized throughout all outputs:
- Lab members are labeled **R1–R11**
- Undergraduate researchers in EVD 7 are labeled **Researcher A, B, C**
- The PI (**Matt Akamatsu**) remains identified as evidence bundle creator

The mapping is maintained in `src/anonymize.py` and applied consistently across all generated data files, visualizations, and notebook outputs.

## Running the pipeline

```bash
pip install -r requirements.txt
python src/main.py
```

> Requires the raw Roam Research exports in `graph raw data/` (not included in this repository).

## Source material

Contact [The Discourse Graphs Project](mailto:discoursegraphsATgmailDOTcom) for read access to the following source material:
- [Experimental log
](https://roamresearch.com/#/app/discourse-graphs/page/E5UYzWC6b)
- [Result page: EVD 5
](https://roamresearch.com/#/app/discourse-graphs/page/EBoRlwI78)
- [Result page: EVD 7
](https://roamresearch.com/#/app/discourse-graphs/page/0FU6ssOwH)
- Raw data: MATSU lab graph in JSON-LD and JSON

## License

This work is licensed under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). See [LICENSE](LICENSE) for the full text.

## Attribution

- **Analysis and evidence bundles:** [Matt Akamatsu](https://orcid.org/0000-0002-0286-5310) and [Claude](https://claude.ai) (Anthropic)
- **Discourse graph system:** [Discourse Graphs Project](https://discoursegraphs.com/), [Joel Chan](https://orcid.org/0000-0003-3000-4160), [Matt Akamatsu](https://orcid.org/0000-0002-0286-5310)
- **Lab discourse graph data:** [Akamatsu Lab](https://matsulab.org), University of Washington
- **Discourse Graph extension:** [DiscourseGraphs](https://github.com/DiscourseGraphs/discourse-graph)
