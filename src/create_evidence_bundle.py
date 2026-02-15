#!/usr/bin/env python3
"""
Evidence Bundle Generator
=========================
Creates self-contained evidence bundles that package an evidence statement,
its associated visualization, underlying data, and metadata into a shareable
data package using JSON-LD (native discourse graph vocabulary) and RO-Crate.

Each bundle is a folder containing:
  - evidence.jsonld          (canonical metadata in JSON-LD)
  - ro-crate-metadata.json   (RO-Crate wrapper for FAIR sharing)
  - fig<N>_<name>.png        (the visualization)
  - data/                    (underlying data files)
  - docs/                    (evidence statement + methods excerpt)

Author: Matt Akamatsu (with Claude)
Date: 2026-01-27
"""

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from anonymize import anonymize_name, anonymize_title


def create_evd5_bundle(metrics: dict, output_dir: Path, viz_dir: Path) -> Path:
    """
    Create the evidence bundle for EVD 5 (issue-to-experiment-to-result funnel).

    Args:
        metrics: Full metrics dict from calculate_all_metrics()
        output_dir: Base output directory (e.g., output/)
        viz_dir: Directory containing visualizations (e.g., output/visualizations/)

    Returns:
        Path to the created bundle directory
    """
    bundle_dir = output_dir / 'evidence_bundles' / 'evd5-issue-funnel'
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / 'data').mkdir(exist_ok=True)
    (bundle_dir / 'docs').mkdir(exist_ok=True)

    # Copy the primary figure (alluvial flow diagram)
    alluvial_png = viz_dir / 'handoff_alluvial.png'
    alluvial_html = viz_dir / 'handoff_alluvial.html'
    if alluvial_png.exists():
        shutil.copy2(alluvial_png, bundle_dir / 'fig5_alluvial_flow.png')
    if alluvial_html.exists():
        shutil.copy2(alluvial_html, bundle_dir / 'fig5_alluvial_flow.html')

    # Copy the supplemental figure (funnel bar chart)
    fig_src = viz_dir / 'fig5_funnel.png'
    if fig_src.exists():
        shutil.copy2(fig_src, bundle_dir / 'fig5_funnel_supplemental.png')

    # Generate data files
    _write_funnel_summary(metrics, bundle_dir / 'data' / 'funnel_summary.json')
    _write_experiment_details(metrics, bundle_dir / 'data' / 'experiment_details.csv')

    # Generate doc files
    _write_evidence_statement(metrics, bundle_dir / 'docs' / 'evidence_statement.md')
    _write_methods_excerpt(output_dir, bundle_dir / 'docs' / 'methods_excerpt.md')

    # Generate JSON-LD metadata
    _write_evidence_jsonld(metrics, bundle_dir / 'evidence.jsonld')

    # Generate RO-Crate metadata
    _write_ro_crate_metadata(bundle_dir / 'ro-crate-metadata.json')

    print(f"Evidence bundle created: {bundle_dir}")
    return bundle_dir


def _write_funnel_summary(metrics: dict, path: Path):
    """Write aggregated funnel data as JSON."""
    conv = metrics['metrics']['conversion_rate']
    ttr = metrics['metrics']['time_to_first_result']

    total_issues = conv['total_issues']
    total_claimed = conv['total_claimed']
    with_results = ttr['count']
    total_res = sum(d['total_linked_res'] for d in ttr['details']) if ttr['details'] else 0

    summary = {
        "description": "Aggregated funnel data for EVD 5: Issue-to-Experiment-to-Result Conversion",
        "snapshot_date": datetime.now().strftime('%Y-%m-%d'),
        "system": "MATSUlab discourse graph",
        "funnel": {
            "total_issues": total_issues,
            "claimed_experiments": total_claimed,
            "experiments_with_results": with_results,
            "total_res_nodes": total_res,
        },
        "conversion_rates": {
            "issue_to_claim_percent": conv['conversion_rate_percent'],
            "claim_to_result_percent": round(with_results / total_claimed * 100, 1) if total_claimed > 0 else 0,
            "issue_to_result_percent": round(with_results / total_issues * 100, 1) if total_issues > 0 else 0,
        },
        "claiming_type_breakdown": {
            "explicitly_claimed": conv['explicit_claims'],
            "inferred_claiming": conv['inferred_claims'],
            "iss_with_activity": conv['iss_with_activity'],
        },
        "result_breakdown": {
            "claimed_with_results": with_results,
            "claimed_without_results": total_claimed - with_results,
            "avg_res_per_producing_experiment": round(total_res / with_results, 1) if with_results > 0 else 0,
        },
        "claiming_authorship": {
            "self_claimed": conv['self_claims'],
            "cross_person_claiming": conv['cross_person_claims'],
            "idea_exchange_rate_percent": metrics['metrics']['cross_person_claims']['idea_exchange_rate'],
        },
    }

    with open(path, 'w') as f:
        json.dump(summary, f, indent=2)


def _write_experiment_details(metrics: dict, path: Path):
    """Write per-experiment detail rows as CSV."""
    conv = metrics['metrics']['conversion_rate']
    ttr = metrics['metrics']['time_to_first_result']
    ttc = metrics['metrics']['time_to_claim']

    # Build lookup maps for time-to-claim and time-to-result by experiment title
    ttc_by_title = {}
    for d in ttc.get('details', []):
        ttc_by_title[d['title']] = d

    ttr_by_title = {}
    for d in ttr.get('details', []):
        ttr_by_title[d['experiment_title']] = d

    # Collect all claimed experiments
    claimed = conv.get('claimed_experiment_list', [])

    fieldnames = [
        'title', 'creator', 'claimer', 'claim_type',
        'issue_created_by', 'page_created', 'claimed_timestamp',
        'has_results', 'num_results', 'first_result_date',
        'time_to_claim_days', 'time_to_first_result_days',
    ]

    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for exp in claimed:
            title = exp['title']
            ttc_data = ttc_by_title.get(title, {})
            ttr_data = ttr_by_title.get(title, {})

            row = {
                'title': anonymize_title(title),
                'creator': anonymize_name(exp.get('creator', '')) or '',
                'claimer': anonymize_name(exp.get('claimed_by', '')) or '',
                'claim_type': exp.get('claim_type', ''),
                'issue_created_by': anonymize_name(exp.get('issue_created_by', '')) or '',
                'page_created': _fmt_dt(exp.get('page_created')),
                'claimed_timestamp': _fmt_dt(exp.get('claimed_by_timestamp')),
                'has_results': 'yes' if title in ttr_by_title else 'no',
                'num_results': ttr_data.get('total_linked_res', 0),
                'first_result_date': _fmt_dt(ttr_data.get('first_res_created')),
                'time_to_claim_days': ttc_data.get('days_to_claim', ''),
                'time_to_first_result_days': ttr_data.get('days_to_first_result', ''),
            }
            writer.writerow(row)


def _fmt_dt(dt) -> str:
    """Format a datetime or string for CSV output."""
    if dt is None:
        return ''
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d')
    if isinstance(dt, str):
        return dt[:10] if len(dt) >= 10 else dt
    return str(dt)


def _write_evidence_statement(metrics: dict, path: Path):
    """Write the EVD 5 evidence statement and figure legend as markdown."""
    conv = metrics['metrics']['conversion_rate']
    ttr = metrics['metrics']['time_to_first_result']
    total_res = sum(d['total_linked_res'] for d in ttr['details']) if ttr['details'] else 0

    ti = conv['total_issues']
    tc = conv['total_claimed']
    wr = ttr['count']
    ec = conv['explicit_claims']
    ic = conv['inferred_claims']
    ia = conv['iss_with_activity']
    uc = conv['unclaimed_iss']
    cr = conv['conversion_rate_percent']
    c2r = round(wr / tc * 100, 0) if tc > 0 else 0
    i2r = round(wr / ti * 100, 0) if ti > 0 else 0
    avg_res = round(total_res / wr, 1) if wr > 0 else 0
    no_res = tc - wr
    iss_formal = len([i for i in range(ti) if True])  # placeholder; use unclaimed + iss_with_activity as ISS count
    # ISS formal nodes = unclaimed ISS + ISS with activity (pages still named [[ISS]])
    iss_formal_count = uc + ia
    # Experiment pages = explicitly + inferred claiming
    exp_pages_count = ec + ic

    content = f"""# EVD 5 — Issue-to-Experiment-to-Result Conversion Funnel

## Evidence Statement

Of {ti} total issues in the MATSUlab discourse graph, {tc} ({cr:.0f}%) were claimed as experiments and {wr} ({i2r:.0f}%) produced at least one formal result node, yielding {total_res} total RES nodes (avg {avg_res} per result-producing experiment).

## Evidence Description

The issue-to-result funnel was constructed by tracking the attrition of issues through three stages: creation, claiming, and result production. All {ti} identifiable issues ({iss_formal_count} formal ISS nodes plus {exp_pages_count} experiment pages with inferred claiming) formed the top of the funnel. Of these, {tc} ({cr:.0f}%) were claimed through any mechanism — {ec} explicitly claimed (with `Claimed By::` field), {ic} inferred as claimed (experimental log entries by the page creator), and {ia} ISS pages with experimental log activity. This represents a {cr:.0f}% issue-to-experiment conversion rate.

Of the {tc} claimed experiments, {wr} ({c2r:.0f}%) had at least one linked RES (Result) node, representing experiments that produced a formally recorded result. The remaining {no_res} claimed experiments either have work still in progress or recorded their outputs in formats other than formal `[[RES]]` pages. The {wr} result-producing experiments generated a total of {total_res} RES nodes, averaging {avg_res} results per experiment. Overall, {i2r:.0f}% of all issues progressed through the full funnel from creation to formal result production.

## Figure

`fig5_alluvial_flow.png` (primary) | `fig5_alluvial_flow.html` (interactive)

## Figure Legend

**Figure 5. Issue-to-experiment-to-result flow in the MATSUlab discourse graph.** Alluvial (Sankey) diagram showing all {tc} claimed experiments flowing through three stages: Issue Created (left, who created the issue), Claimed By (center, who claimed the experiment), and Result Created (right, who created the first formal result). Band width is proportional to the number of experiments. Green bands indicate self-claiming (same person created the issue and claimed the experiment); purple bands indicate cross-person claiming (idea exchange, where a different researcher claimed the issue). Of the {tc} claimed experiments, {wr} produced at least one formal result node, yielding {total_res} total RES nodes. Researcher names are anonymized (R1–R11); the PI (Matt Akamatsu) is identified. An interactive HTML version (`fig5_alluvial_flow.html`) allows hovering to inspect individual flows.

## Supplemental Figure

`fig5_funnel_supplemental.png`

**Supplemental Figure. Issue-to-experiment-to-result conversion funnel (aggregate view).** **(Left)** Horizontal bar chart showing progressive attrition across three stages: all issues (n={ti}), claimed experiments (n={tc}, {cr:.0f}%), and experiments with at least one formal result (n={wr}, {i2r:.0f}%). Annotations between bars indicate the stage-to-stage pass-through rate ({cr:.0f}% of issues claimed; {c2r:.0f}% of claimed experiments produced results). **(Right)** Stage-by-stage breakdown showing the composition at each level.
"""
    with open(path, 'w') as f:
        f.write(content)


def _write_methods_excerpt(output_dir: Path, path: Path):
    """Extract relevant methods sections for the bundle."""
    methods_path = output_dir / 'methods.md'

    # Sections relevant to EVD 5: conversion rate, claiming detection, RES linking
    sections_to_extract = [
        '## 2. Node Identification',
        '## 3. Claiming Detection',
        '## 5. Linking Result (RES) Nodes to Experiments',
        '## 6. Metric Definitions and Calculations',
    ]

    if not methods_path.exists():
        # Write a stub referencing the full methods
        with open(path, 'w') as f:
            f.write("# Methods Excerpt\n\nSee `output/methods.md` for full methodological detail.\n")
        return

    with open(methods_path, 'r') as f:
        full_text = f.read()

    lines = full_text.split('\n')
    extracted = ["# Methods Excerpt (EVD 5)\n"]
    extracted.append("This excerpt contains the methods sections relevant to the issue-to-experiment-to-result conversion funnel analysis. For the complete methods document, see `output/methods.md`.\n")
    extracted.append("---\n")

    # Extract each target section
    for section_header in sections_to_extract:
        in_section = False
        section_lines = []
        for line in lines:
            if line.strip().startswith(section_header):
                in_section = True
                section_lines.append(line)
                continue
            if in_section:
                # Stop at the next ## header (same level or higher)
                if line.strip().startswith('## ') and not line.strip().startswith(section_header):
                    break
                section_lines.append(line)

        if section_lines:
            extracted.extend(section_lines)
            extracted.append('\n---\n')

    with open(path, 'w') as f:
        f.write('\n'.join(extracted))


def _write_evidence_jsonld(metrics: dict, path: Path):
    """Write the canonical JSON-LD evidence bundle metadata."""
    conv = metrics['metrics']['conversion_rate']
    ttr = metrics['metrics']['time_to_first_result']
    total_res = sum(d['total_linked_res'] for d in ttr['details']) if ttr['details'] else 0

    jsonld = {
        "@context": {
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcterms": "http://purl.org/dc/terms/",
            "prov": "http://www.w3.org/ns/prov#",
            "schema": "https://schema.org/",
            "dgb": "https://discoursegraphs.com/schema/dg_base/",
            "dge": "https://discoursegraphs.com/schema/dg_evidence/",
        },
        "@type": "dge:EvidenceBundle",
        "@id": "evd5-issue-funnel",
        "dc:title": (
            f"[[RES]] - {conv['conversion_rate_percent']:.0f}% of MATSUlab issues "
            f"(n={conv['total_issues']}) were claimed as experiments "
            f"and {round(ttr['count'] / conv['total_claimed'] * 100) if conv['total_claimed'] > 0 else 0}% "
            f"of those claimed at least one formal result node, yielding "
            f"{total_res} total RES nodes - [[@analysis/quantify issue claiming from MATSUlab]]"
        ),
        "dc:creator": "Matt Akamatsu",
        "dc:date": datetime.now().strftime('%Y-%m-%d'),
        "dcterms:license": "https://creativecommons.org/licenses/by/4.0/",
        "dge:evidenceStatement": (
            f"Of {conv['total_issues']} total issues in the MATSUlab discourse graph, "
            f"{conv['total_claimed']} ({conv['conversion_rate_percent']:.0f}%) were claimed as experiments and "
            f"{ttr['count']} ({round(ttr['count'] / conv['total_issues'] * 100) if conv['total_issues'] > 0 else 0}%) "
            f"produced at least one formal result node, yielding {total_res} total RES nodes "
            f"(avg {round(total_res / ttr['count'], 1) if ttr['count'] > 0 else 0} per result-producing experiment)."
        ),
        "dge:observable": {
            "@type": "dge:Observable",
            "dc:title": "Issue-to-experiment-to-result conversion rate",
            "dc:description": (
                f"The proportion of issues that progress through claiming and result "
                f"production stages in a discourse graph, measuring the funnel from "
                f"issue creation (n={conv['total_issues']}) through experiment claiming "
                f"(n={conv['total_claimed']}) to formal "
                f"result production (n={ttr['count']}, yielding {total_res} RES nodes)."
            ),
        },
        "dge:method": {
            "@type": "dge:Method",
            "dc:title": "Discourse graph funnel analysis",
            "dc:description": (
                "Automated pipeline parsing JSON-LD and Roam JSON exports to identify "
                "issue nodes, detect claiming (explicit via Claimed By:: field and inferred "
                "via experimental log presence), link result nodes using a 3-tier matching "
                "strategy (relation instances, backreference matching, full description "
                "matching), and compute stage-by-stage attrition rates."
            ),
            "prov:used": [
                {"@id": "src/calculate_metrics.py", "dc:description": "Metric calculation and data merging"},
                {"@id": "src/parse_jsonld.py", "dc:description": "JSON-LD export parser"},
                {"@id": "src/parse_roam_json.py", "dc:description": "Roam JSON streaming parser"},
                {"@id": "src/generate_visualizations.py", "dc:description": "Funnel visualization generator"},
                {"@id": "src/handoff_visualizations.py", "dc:description": "Alluvial flow diagram generator"},
            ],
            "schema:codeRepository": "node-metrics",
        },
        "dge:system": {
            "@type": "dge:System",
            "dc:title": "MATSUlab discourse graph",
            "dc:description": (
                f"Akamatsu Lab Roam Research discourse graph, "
                f"{datetime.now().strftime('%B %Y')} snapshot. "
                f"Contains {conv['total_issues']} identifiable issues "
                f"({conv['unclaimed_iss'] + conv['iss_with_activity']} formal ISS nodes + "
                f"{conv['explicit_claims'] + conv['inferred_claims']} experiment pages), "
                f"{conv['total_claimed']} claimed experiments, and "
                f"{metrics['summary']['total_res_nodes']} result nodes."
            ),
            "schema:memberOf": "Akamatsu Lab, University of Washington",
            "dcterms:temporal": datetime.now().strftime('%Y-%m-%d'),
        },
        "dge:figure": {
            "@type": "schema:ImageObject",
            "schema:contentUrl": "fig5_alluvial_flow.png",
            "schema:encodingFormat": "image/png",
            "schema:alternateName": "fig5_alluvial_flow.html",
            "dge:figureLegend": (
                f"Figure 5. Issue-to-experiment-to-result flow in the MATSUlab discourse "
                f"graph. Alluvial (Sankey) diagram showing all {conv['total_claimed']} claimed "
                f"experiments flowing through three stages: Issue Created (left, who created "
                f"the issue), Claimed By (center, who claimed the experiment), and Result "
                f"Created (right, who created the first formal result). Band width is "
                f"proportional to number of experiments. Green bands indicate self-claiming; "
                f"purple bands indicate cross-person claiming (idea exchange). Of the "
                f"{conv['total_claimed']} claimed experiments, {ttr['count']} produced at "
                f"least one formal result node. Researcher names are anonymized (R1–R11); "
                f"PI (Matt Akamatsu) is identified. An interactive HTML version is included."
            ),
        },
        "dge:supplementalFigure": {
            "@type": "schema:ImageObject",
            "schema:contentUrl": "fig5_funnel_supplemental.png",
            "schema:encodingFormat": "image/png",
            "dge:figureLegend": (
                f"Supplemental Figure. Issue-to-experiment-to-result conversion funnel "
                f"(aggregate view). (Left) Horizontal bar chart showing progressive "
                f"attrition across three stages: all issues (n={conv['total_issues']}), "
                f"claimed experiments (n={conv['total_claimed']}, "
                f"{conv['conversion_rate_percent']:.0f}%), and experiments with at least one "
                f"formal result (n={ttr['count']}, "
                f"{round(ttr['count'] / conv['total_issues'] * 100) if conv['total_issues'] > 0 else 0}%). "
                f"(Right) Stage-by-stage breakdown showing composition at each level."
            ),
        },
        "dge:groundingData": [
            {
                "@type": "schema:DataDownload",
                "schema:contentUrl": "data/funnel_summary.json",
                "schema:encodingFormat": "application/json",
                "dc:description": "Aggregated funnel data with stage counts, conversion rates, and breakdowns",
            },
            {
                "@type": "schema:DataDownload",
                "schema:contentUrl": "data/experiment_details.csv",
                "schema:encodingFormat": "text/csv",
                "dc:description": "Per-experiment detail rows with claiming type, timestamps, and result counts",
            },
        ],
        "dge:documentation": [
            {
                "@type": "schema:TextDigitalDocument",
                "schema:contentUrl": "docs/evidence_statement.md",
                "dc:description": "Evidence statement, evidence description, and figure legend",
            },
            {
                "@type": "schema:TextDigitalDocument",
                "schema:contentUrl": "docs/methods_excerpt.md",
                "dc:description": "Relevant methods sections for claiming detection, RES linking, and metric calculation",
            },
        ],
        "prov:wasGeneratedBy": {
            "@type": "prov:Activity",
            "prov:startedAtTime": "2026-01-25",
            "prov:endedAtTime": datetime.now().strftime('%Y-%m-%d'),
            "prov:used": [
                Path(metrics['data_sources']['jsonld']).name if 'data_sources' in metrics else "akamatsulab_discourse-graph-json-LD.json",
                Path(metrics['data_sources']['roam_json']).name if 'data_sources' in metrics else "akamatsulab-whole-graph-json.json",
            ],
            "prov:wasAssociatedWith": [
                {"@type": "prov:Agent", "dc:title": "Matt Akamatsu", "schema:affiliation": "University of Washington"},
                {"@type": "prov:SoftwareAgent", "dc:title": "Claude", "schema:provider": "Anthropic"},
            ],
        },
        "dge:summaryMetrics": {
            "total_issues": conv['total_issues'],
            "claimed_experiments": conv['total_claimed'],
            "explicitly_claimed": conv['explicit_claims'],
            "inferred_claiming": conv['inferred_claims'],
            "iss_with_activity": conv['iss_with_activity'],
            "experiments_with_results": ttr['count'],
            "total_res_nodes": total_res,
            "conversion_rate_percent": conv['conversion_rate_percent'],
            "claiming_to_result_percent": round(ttr['count'] / conv['total_claimed'] * 100, 1) if conv['total_claimed'] > 0 else 0,
        },
    }

    with open(path, 'w') as f:
        json.dump(jsonld, f, indent=2, ensure_ascii=False)


def _write_ro_crate_metadata(path: Path):
    """Write the RO-Crate metadata manifest."""
    rocrate = {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": [
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "about": {"@id": "./"},
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            },
            {
                "@id": "./",
                "@type": "Dataset",
                "name": (
                    "EVD 5: Issue-to-Experiment-to-Result Conversion Funnel — "
                    "MATSUlab Discourse Graph"
                ),
                "description": (
                    "Evidence bundle for the finding that 29% of MATSUlab issues "
                    "(n=445) were claimed as experiments and 11% produced at least "
                    "one formal result node, yielding 139 total RES nodes. "
                    "Contains the evidence statement, figure, underlying data, "
                    "and methodological documentation."
                ),
                "datePublished": "2026-02-14",
                "creator": [
                    {"@id": "#matt-akamatsu"},
                ],
                "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
                "hasPart": [
                    {"@id": "evidence.jsonld"},
                    {"@id": "fig5_alluvial_flow.png"},
                    {"@id": "fig5_alluvial_flow.html"},
                    {"@id": "fig5_funnel_supplemental.png"},
                    {"@id": "data/funnel_summary.json"},
                    {"@id": "data/experiment_details.csv"},
                    {"@id": "docs/evidence_statement.md"},
                    {"@id": "docs/methods_excerpt.md"},
                ],
            },
            {
                "@id": "#matt-akamatsu",
                "@type": "Person",
                "name": "Matt Akamatsu",
                "affiliation": {"@id": "#uw"},
            },
            {
                "@id": "#uw",
                "@type": "Organization",
                "name": "University of Washington",
            },
            {
                "@id": "evidence.jsonld",
                "@type": "File",
                "name": "Evidence Bundle Metadata (JSON-LD)",
                "description": (
                    "Canonical evidence bundle metadata using the dge: "
                    "(Discourse Graph Evidence) vocabulary. Contains the evidence "
                    "statement, observable/method/system attributes, provenance, "
                    "and references to all bundle contents."
                ),
                "encodingFormat": "application/ld+json",
            },
            {
                "@id": "fig5_alluvial_flow.png",
                "@type": ["File", "ImageObject"],
                "name": "Figure 5: Issue-to-Experiment-to-Result Alluvial Flow",
                "description": (
                    "Alluvial (Sankey) diagram showing all claimed experiments flowing "
                    "through three stages: Issue Created → Claimed By → Result Created. "
                    "Band width proportional to experiment count; color indicates self-claiming "
                    "(green) vs cross-person claiming (purple). Researcher names anonymized."
                ),
                "encodingFormat": "image/png",
            },
            {
                "@id": "fig5_alluvial_flow.html",
                "@type": ["File", "ImageObject"],
                "name": "Figure 5 (interactive): Alluvial Flow Diagram",
                "description": (
                    "Interactive Plotly version of the alluvial flow diagram. "
                    "Hover to see experiment counts per flow path."
                ),
                "encodingFormat": "text/html",
            },
            {
                "@id": "fig5_funnel_supplemental.png",
                "@type": ["File", "ImageObject"],
                "name": "Supplemental: Issue-to-Experiment-to-Result Conversion Funnel",
                "description": (
                    "Supplemental aggregate view. Left: horizontal funnel bar chart "
                    "showing progressive attrition. Right: stage-by-stage composition "
                    "breakdown by claiming type and result status."
                ),
                "encodingFormat": "image/png",
            },
            {
                "@id": "data/funnel_summary.json",
                "@type": "File",
                "name": "Funnel Summary Data",
                "description": (
                    "Aggregated funnel counts, conversion rates, claiming type breakdown, "
                    "and result statistics."
                ),
                "encodingFormat": "application/json",
            },
            {
                "@id": "data/experiment_details.csv",
                "@type": "File",
                "name": "Experiment Details",
                "description": (
                    "Per-experiment rows with title, creator, claimed by, claiming type, "
                    "timestamps, result counts, and time metrics."
                ),
                "encodingFormat": "text/csv",
            },
            {
                "@id": "docs/evidence_statement.md",
                "@type": "File",
                "name": "Evidence Statement and Figure Legend",
                "description": "EVD 5 evidence statement, evidence description, and figure legend in markdown.",
                "encodingFormat": "text/markdown",
            },
            {
                "@id": "docs/methods_excerpt.md",
                "@type": "File",
                "name": "Methods Excerpt",
                "description": (
                    "Relevant sections from the full methods document covering "
                    "node identification, claiming detection, RES linking, and metric definitions."
                ),
                "encodingFormat": "text/markdown",
            },
        ],
    }

    with open(path, 'w') as f:
        json.dump(rocrate, f, indent=2, ensure_ascii=False)


def create_evd7_bundle(output_dir: Path, viz_dir: Path, metrics: dict = None) -> Path:
    """
    Create the evidence bundle for EVD 7 (undergraduate researcher onboarding timeline).

    Args:
        output_dir: Base output directory (e.g., output/)
        viz_dir: Directory containing visualizations (e.g., output/visualizations/)
        metrics: Optional full metrics dict for deriving lab average time-to-result

    Returns:
        Path to the created bundle directory
    """
    bundle_dir = output_dir / 'evidence_bundles' / 'evd7-student-onboarding'
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / 'data').mkdir(exist_ok=True)
    (bundle_dir / 'docs').mkdir(exist_ok=True)

    # Copy the figure
    fig_src = viz_dir / 'fig7_student_timelines.png'
    fig_dst = bundle_dir / 'fig7_student_timelines.png'
    if fig_src.exists():
        shutil.copy2(fig_src, fig_dst)

    # Copy the milestone JSON data
    milestones_src = output_dir / 'student_milestones.json'
    milestones_dst = bundle_dir / 'data' / 'student_milestones.json'
    if milestones_src.exists():
        shutil.copy2(milestones_src, milestones_dst)

    # Generate doc files
    _write_evd7_evidence_statement(bundle_dir / 'docs' / 'evidence_statement.md')

    # Generate JSON-LD metadata
    lab_avg = None
    if metrics and 'metrics' in metrics:
        ttr = metrics['metrics'].get('time_to_first_result', {})
        if ttr.get('count', 0) > 0:
            lab_avg = ttr['avg_days']
    _write_evd7_evidence_jsonld(bundle_dir / 'evidence.jsonld', lab_avg_days_to_res=lab_avg)

    # Generate RO-Crate metadata
    _write_evd7_ro_crate_metadata(bundle_dir / 'ro-crate-metadata.json')

    print(f"Evidence bundle created: {bundle_dir}")
    return bundle_dir


def _write_evd7_evidence_statement(path: Path):
    """Write the EVD 7 evidence statement and figure legend as markdown."""
    content = """# EVD 7 — Undergraduate Researcher Onboarding Timeline

## Evidence Statement

All three undergraduate researchers generated an original result from their analysis projects within ~4 months of joining the lab, with two creating a result within ~1 month.

## Evidence Description

The onboarding timeline was reconstructed for three undergraduate researchers by tracing key milestones through their daily notes and the discourse graph: (1) first day in lab, (2) first experiment reference in daily notes, (3) first plot (linked image in notes), and (4) first formal RES node creation. Dates were extracted from Roam Research page metadata and daily log entries.

Researcher A joined the lab on February 23, 2024 and started their first experiment (`@analysis/Quantify the percentage of simulated endocytic events that assemble detectable amounts of actin`) on April 5, 2024 (41 days). They produced their first plot on June 20, 2024 (118 days) and first RES node on June 27, 2024 (125 days). This represents a self-directed exploration pathway where the student browsed the Issues board and chose an experiment matching their interests.

Researcher B joined on October 10, 2024 and was assigned an entry project (`@analysis/Plot the number of bound Hip1R over time for different Arp2/3 distributions in endocytosis simulations`) explicitly designed "to get acquainted with our simulations and the analysis framework." They began work on October 15, 2024 (5 days), producing plots the same day. Their first RES node was created November 26, 2024 (47 days).

Researcher C joined on June 23, 2025 and was assigned to an existing experiment (`@analysis/correlate segmented endocytic spots to cell location (apical, basal, lateral) in 3D`) via the "Possible Contributors" field. They began work on June 30, 2025 (7 days), produced first plots on July 7, 2025 (14 days), and created their first RES node on July 29, 2025 (36 days) — the fastest time-to-result among the three.

The mean time-to-first-RES for undergraduate researchers (69 days) was faster than the overall lab average (88.3 days), suggesting that structured onboarding pathways — whether through assigned entry projects or direct experiment assignment — accelerate early productivity while maintaining result quality.

## Figure

`fig7_student_timelines.png`

## Figure Legend

**Figure 7. Undergraduate researcher onboarding timeline in the MATSUlab discourse graph.** Gantt-style chart showing the progression of three anonymized undergraduate researchers (A, B, C) from lab start to first formal result (RES node). Horizontal bars indicate phases: blue = onboarding (first day to first experiment reference), green = development (first experiment to first plot), purple = result production (first plot to first RES). Colored markers indicate milestones: black = first day, red = first experiment, orange = first plot, green = first RES. Numbers above markers show days from lab start. Researcher A followed a self-directed exploration pathway (41 days to experiment, 125 days to RES). Researcher B was assigned an entry project (5 days to experiment, 47 days to RES). Researcher C was directly assigned to an existing experiment (7 days to experiment, 36 days to RES). All three pathways successfully produced formal results within 4 months, with structured assignment pathways yielding faster time-to-result.
"""
    with open(path, 'w') as f:
        f.write(content)


def _write_evd7_evidence_jsonld(path: Path, lab_avg_days_to_res: float = None):
    """Write the canonical JSON-LD evidence bundle metadata for EVD 7."""
    jsonld = {
        "@context": {
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcterms": "http://purl.org/dc/terms/",
            "prov": "http://www.w3.org/ns/prov#",
            "schema": "https://schema.org/",
            "dgb": "https://discoursegraphs.com/schema/dg_base/",
            "dge": "https://discoursegraphs.com/schema/dg_evidence/",
        },
        "@type": "dge:EvidenceBundle",
        "@id": "evd7-student-onboarding",
        "dc:title": (
            "[[RES]] - All three undergraduate researchers generated an original result "
            "from their analysis projects within ~4 months of joining the lab, with two "
            "creating a result within ~1 month - [[@analysis/quantify researcher onboarding from MATSUlab]]"
        ),
        "dc:creator": "Matt Akamatsu",
        "dc:date": "2026-01-31",
        "dcterms:license": "https://creativecommons.org/licenses/by/4.0/",
        "dge:evidenceStatement": (
            "All three undergraduate researchers generated an original result from their "
            "analysis projects within ~4 months of joining the lab, with two creating a "
            "result within ~1 month."
        ),
        "dge:observable": {
            "@type": "dge:Observable",
            "dc:title": "Undergraduate researcher onboarding time-to-result",
            "dc:description": (
                "The time from a researcher's first day in the lab to their first formal "
                "result (RES node) creation, measured for three undergraduate researchers "
                "following different onboarding pathways."
            ),
        },
        "dge:method": {
            "@type": "dge:Method",
            "dc:title": "Discourse graph milestone tracing",
            "dc:description": (
                "Manual extraction of key milestones from daily notes exports and experiment "
                "page metadata. Milestones tracked: (1) first day in lab, (2) first experiment "
                "reference in daily notes, (3) first plot (linked image), (4) first RES node "
                "creation date. Researchers anonymized as A, B, C in outputs."
            ),
            "prov:used": [
                {"@id": "src/student_timeline_analysis.py", "dc:description": "Timeline extraction and visualization"},
            ],
            "schema:codeRepository": "node-metrics",
        },
        "dge:system": {
            "@type": "dge:System",
            "dc:title": "MATSUlab discourse graph",
            "dc:description": (
                "Akamatsu Lab Roam Research discourse graph, January 2026 snapshot. "
                "Includes daily notes, experiment pages, and result nodes for three "
                "undergraduate researchers spanning February 2024 to July 2025."
            ),
            "schema:memberOf": "Akamatsu Lab, University of Washington",
            "dcterms:temporal": "2026-01-31",
        },
        "dge:figure": {
            "@type": "schema:ImageObject",
            "schema:contentUrl": "fig7_student_timelines.png",
            "schema:encodingFormat": "image/png",
            "dge:figureLegend": (
                "Figure 7. Undergraduate researcher onboarding timeline in the MATSUlab "
                "discourse graph. Gantt-style chart showing the progression of three "
                "anonymized undergraduate researchers (A, B, C) from lab start to first "
                "formal result (RES node). Researcher A: 41 days to experiment, 125 days "
                "to RES. Researcher B: 5 days to experiment, 47 days to RES. Researcher C: "
                "7 days to experiment, 36 days to RES."
            ),
        },
        "dge:groundingData": [
            {
                "@type": "schema:DataDownload",
                "schema:contentUrl": "data/student_milestones.json",
                "schema:encodingFormat": "application/json",
                "dc:description": "Per-researcher milestone data with days from start and pathway type",
            },
        ],
        "dge:documentation": [
            {
                "@type": "schema:TextDigitalDocument",
                "schema:contentUrl": "docs/evidence_statement.md",
                "dc:description": "Evidence statement, evidence description, and figure legend",
            },
        ],
        "prov:wasGeneratedBy": {
            "@type": "prov:Activity",
            "prov:startedAtTime": "2026-01-31",
            "prov:endedAtTime": "2026-01-31",
            "prov:used": [
                "Researcher A daily notes (anonymized)",
                "Researcher B daily notes (anonymized)",
                "Researcher C daily notes (anonymized)",
            ],
            "prov:wasAssociatedWith": [
                {"@type": "prov:Agent", "dc:title": "Matt Akamatsu", "schema:affiliation": "University of Washington"},
                {"@type": "prov:SoftwareAgent", "dc:title": "Claude", "schema:provider": "Anthropic"},
            ],
        },
        "dge:summaryMetrics": {
            "researchers_analyzed": 3,
            "mean_days_to_res": 69.3,
            "min_days_to_res": 36,
            "max_days_to_res": 125,
            "lab_average_days_to_res": lab_avg_days_to_res if lab_avg_days_to_res is not None else 88.3,
            "pathways_identified": [
                "Self-directed exploration",
                "Assigned entry project",
                "Direct assignment",
            ],
        },
    }

    with open(path, 'w') as f:
        json.dump(jsonld, f, indent=2, ensure_ascii=False)


def _write_evd7_ro_crate_metadata(path: Path):
    """Write the RO-Crate metadata manifest for EVD 7."""
    rocrate = {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": [
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "about": {"@id": "./"},
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            },
            {
                "@id": "./",
                "@type": "Dataset",
                "name": (
                    "EVD 7: Undergraduate Researcher Onboarding Timeline — "
                    "MATSUlab Discourse Graph"
                ),
                "description": (
                    "Evidence bundle for the finding that all three undergraduate "
                    "researchers generated an original result from their analysis "
                    "projects within ~4 months of joining the lab, with two creating "
                    "a result within ~1 month. Contains the evidence statement, figure, "
                    "underlying data, and methodological documentation."
                ),
                "datePublished": "2026-01-31",
                "creator": [
                    {"@id": "#matt-akamatsu"},
                ],
                "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
                "hasPart": [
                    {"@id": "evidence.jsonld"},
                    {"@id": "fig7_student_timelines.png"},
                    {"@id": "data/student_milestones.json"},
                    {"@id": "docs/evidence_statement.md"},
                ],
            },
            {
                "@id": "#matt-akamatsu",
                "@type": "Person",
                "name": "Matt Akamatsu",
                "affiliation": {"@id": "#uw"},
            },
            {
                "@id": "#uw",
                "@type": "Organization",
                "name": "University of Washington",
            },
            {
                "@id": "evidence.jsonld",
                "@type": "File",
                "name": "Evidence Bundle Metadata (JSON-LD)",
                "description": (
                    "Canonical evidence bundle metadata using the dge: "
                    "(Discourse Graph Evidence) vocabulary."
                ),
                "encodingFormat": "application/ld+json",
            },
            {
                "@id": "fig7_student_timelines.png",
                "@type": ["File", "ImageObject"],
                "name": "Figure 7: Undergraduate Researcher Onboarding Timeline",
                "description": (
                    "Gantt-style chart showing progression of three anonymized "
                    "undergraduate researchers from lab start to first RES node."
                ),
                "encodingFormat": "image/png",
            },
            {
                "@id": "data/student_milestones.json",
                "@type": "File",
                "name": "Student Milestones Data",
                "description": (
                    "Per-researcher milestone data including days to experiment, "
                    "days to plot, days to RES, and onboarding pathway type."
                ),
                "encodingFormat": "application/json",
            },
            {
                "@id": "docs/evidence_statement.md",
                "@type": "File",
                "name": "Evidence Statement and Figure Legend",
                "description": "EVD 7 evidence statement, evidence description, and figure legend in markdown.",
                "encodingFormat": "text/markdown",
            },
        ],
    }

    with open(path, 'w') as f:
        json.dump(rocrate, f, indent=2, ensure_ascii=False)


def create_evd1_bundle(metrics: dict, output_dir: Path, viz_dir: Path) -> Path:
    """
    Create the evidence bundle for EVD 1 (issue conversion rate).

    Args:
        metrics: Full metrics dict from calculate_all_metrics()
        output_dir: Base output directory (e.g., output/)
        viz_dir: Directory containing visualizations (e.g., output/visualizations/)

    Returns:
        Path to the created bundle directory
    """
    bundle_dir = output_dir / 'evidence_bundles' / 'evd1-conversion-rate'
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / 'data').mkdir(exist_ok=True)
    (bundle_dir / 'docs').mkdir(exist_ok=True)

    # Copy figures
    fig_files = [
        'fig1_conversion_rate.png',
        'fig1_conversion_rate.html',
        'fig0_issue_timeline.png',
        'fig0_issue_timeline.html',
        'fig0b_creator_heatmap.png',
        'fig0b_creator_heatmap.html',
        'fig0c_discourse_growth.png',
        'fig0_issue_timeline_animated.gif',
    ]
    for fname in fig_files:
        src = viz_dir / fname
        dst = bundle_dir / fname
        if src.exists():
            shutil.copy2(src, dst)

    # Generate data files
    _write_evd1_conversion_data(metrics, bundle_dir / 'data' / 'conversion_data.json')
    _write_evd1_timeline_data(metrics, bundle_dir / 'data' / 'issue_timeline_data.json')

    # Generate doc files
    _write_evd1_evidence_statement(metrics, bundle_dir / 'docs' / 'evidence_statement.md')
    _write_evd1_methods_excerpt(output_dir, bundle_dir / 'docs' / 'methods_excerpt.md')

    # Generate JSON-LD metadata
    _write_evd1_evidence_jsonld(metrics, bundle_dir / 'evidence.jsonld')

    # Generate RO-Crate metadata
    _write_evd1_ro_crate_metadata(bundle_dir / 'ro-crate-metadata.json')

    print(f"Evidence bundle created: {bundle_dir}")
    return bundle_dir


def _write_evd1_conversion_data(metrics: dict, path: Path):
    """Write aggregated conversion rate data as JSON."""
    conv = metrics['metrics']['conversion_rate']
    ttr = metrics['metrics']['time_to_first_result']
    total_res = sum(d['total_linked_res'] for d in ttr['details']) if ttr['details'] else 0

    summary = {
        "description": "Aggregated conversion rate data for EVD 1: Issue Conversion Rate",
        "snapshot_date": datetime.now().strftime('%Y-%m-%d'),
        "system": "MATSUlab discourse graph",
        "conversion": {
            "total_issues": conv['total_issues'],
            "total_claimed": conv['total_claimed'],
            "conversion_rate_percent": conv['conversion_rate_percent'],
            "unclaimed_iss": conv['unclaimed_iss'],
        },
        "claiming_type_breakdown": {
            "explicitly_claimed": conv['explicit_claims'],
            "inferred_claiming": conv['inferred_claims'],
            "iss_with_activity": conv['iss_with_activity'],
        },
        "claiming_authorship": {
            "self_claimed": conv['self_claims'],
            "cross_person_claiming": conv['cross_person_claims'],
            "claimed_experiments_with_known_authorship": conv['self_claims'] + conv['cross_person_claims'],
            "idea_exchange_rate_percent": metrics['metrics']['cross_person_claims']['idea_exchange_rate'],
        },
        "result_production": {
            "claimed_with_results": ttr['count'],
            "claimed_without_results": conv['total_claimed'] - ttr['count'],
            "claim_to_result_percent": round(ttr['count'] / conv['total_claimed'] * 100, 1) if conv['total_claimed'] > 0 else 0,
            "total_res_nodes": total_res,
            "avg_res_per_producing_experiment": round(total_res / ttr['count'], 1) if ttr['count'] > 0 else 0,
        },
        "issue_composition": {
            "formal_iss_nodes": conv['unclaimed_iss'] + conv['iss_with_activity'],
            "experiment_pages_with_inferred_claiming": conv['explicit_claims'] + conv['inferred_claims'],
            "description": (
                f"Total issues = {conv['unclaimed_iss'] + conv['iss_with_activity']} formal ISS nodes + "
                f"{conv['explicit_claims'] + conv['inferred_claims']} experiment pages = {conv['total_issues']}"
            ),
        },
    }

    with open(path, 'w') as f:
        json.dump(summary, f, indent=2)


def _write_evd1_timeline_data(metrics: dict, path: Path):
    """Write issue creation timeline data as JSON for the introductory panel."""
    from collections import OrderedDict

    conv = metrics['metrics']['conversion_rate']

    # Collect all issue creation dates
    issues = []

    # Claimed experiments
    for exp in conv.get('claimed_experiment_list', []):
        pc = exp.get('page_created')
        if pc is None:
            continue
        if isinstance(pc, datetime):
            pc = pc.isoformat()
        issues.append({
            'date': pc[:10] if isinstance(pc, str) else pc,
            'type': 'experiment',
            'claimed': True,
            'claim_type': exp.get('claim_type', 'unknown'),
        })

    # ISS nodes
    for iss in metrics.get('iss_node_list', []):
        pc = iss.get('page_created')
        if pc is None:
            continue
        if isinstance(pc, datetime):
            pc = pc.isoformat()
        issues.append({
            'date': pc[:10] if isinstance(pc, str) else pc,
            'type': 'ISS',
            'claimed': iss.get('is_claimed', False),
            'claim_type': 'iss_activity' if iss.get('is_claimed', False) else 'unclaimed',
        })

    issues.sort(key=lambda x: x['date'])

    # Monthly summary
    monthly = OrderedDict()
    cum_total = 0
    cum_claimed = 0
    for iss in issues:
        month = iss['date'][:7]
        if month not in monthly:
            monthly[month] = {'month': month, 'new_issues': 0, 'new_claimed': 0}
        monthly[month]['new_issues'] += 1
        if iss['claimed']:
            monthly[month]['new_claimed'] += 1

    monthly_list = []
    for m in monthly.values():
        cum_total += m['new_issues']
        cum_claimed += m['new_claimed']
        monthly_list.append({
            'month': m['month'],
            'new_issues': m['new_issues'],
            'new_claimed': m['new_claimed'],
            'cumulative_issues': cum_total,
            'cumulative_claimed': cum_claimed,
        })

    # Discourse node type growth
    graph_growth = metrics.get('graph_growth', {})
    node_type_dates = {}
    for node_type, nodes in graph_growth.get('nodes_by_type', {}).items():
        dates = sorted([n['created'][:10] for n in nodes if n.get('created')])
        node_type_dates[node_type] = dates

    timeline_data = {
        'description': 'Issue creation timeline data for EVD 1 introductory panel',
        'snapshot_date': datetime.now().strftime('%Y-%m-%d'),
        'total_issues': len(issues),
        'total_claimed': sum(1 for i in issues if i['claimed']),
        'issues': issues,
        'monthly_summary': monthly_list,
        'discourse_node_growth': node_type_dates,
        'total_content_nodes': graph_growth.get('total_content_nodes', 0),
    }

    with open(path, 'w') as f:
        json.dump(timeline_data, f, indent=2)


def _write_evd1_evidence_statement(metrics: dict, path: Path):
    """Write the EVD 1 evidence statement and figure legend as markdown."""
    conv = metrics['metrics']['conversion_rate']
    ttr = metrics['metrics']['time_to_first_result']
    total_res = sum(d['total_linked_res'] for d in ttr['details']) if ttr['details'] else 0

    ti = conv['total_issues']
    tc = conv['total_claimed']
    ec = conv['explicit_claims']
    ic = conv['inferred_claims']
    ia = conv['iss_with_activity']
    uc = conv['unclaimed_iss']
    cr = conv['conversion_rate_percent']
    sc = conv['self_claims']
    xp = conv['cross_person_claims']
    wr = ttr['count']
    c2r = round(wr / tc * 100, 0) if tc > 0 else 0
    avg_res = round(total_res / wr, 1) if wr > 0 else 0
    no_res = tc - wr
    known_pairs = sc + xp
    self_pct = round(sc / known_pairs * 100, 0) if known_pairs > 0 else 0
    xp_pct = round(xp / known_pairs * 100, 0) if known_pairs > 0 else 0
    iss_formal_count = uc + ia
    exp_pages_count = ec + ic

    content = f"""# EVD 1 \u2014 Issue Conversion Rate

## Evidence Statement

{cr:.0f}% of MATSUlab issues (n={ti}) were claimed as experiments and {c2r:.0f}% of those produced at least one formal result node, yielding {total_res} total RES nodes.

## Evidence Description

The issue conversion rate was computed across all identifiable issues in the MATSUlab Roam Research discourse graph. Issues were identified as either formal ISS (Issue) nodes (n={iss_formal_count}) or experiment pages with inferred claiming that lacked formal ISS metadata (n={exp_pages_count}), giving a total of {ti} issues.

An issue was considered "claimed" if it had (a) a `Claimed By::` field populated with a researcher name (explicitly claimed, n={ec}), (b) experimental log entries authored by the page creator but no `Claimed By::` field (inferred as claimed, n={ic}), or (c) an ISS page with experimental log content indicating active work (n={ia}). This yielded {tc} claimed experiments out of {ti} total issues ({cr}%).

Of the {tc} claimed experiments, {wr} ({c2r:.0f}%) had at least one linked RES (Result) node, representing experiments that produced a formally recorded result. The {wr} result-producing experiments generated a total of {total_res} RES nodes, averaging {avg_res} results per experiment. The remaining {no_res} claimed experiments either have work still in progress or recorded their outputs in formats other than formal `[[RES]]` pages.

Among the {known_pairs} claimed experiments with known creator–claimer pairs, {self_pct:.0f}% ({sc}) were self-claimed and {xp_pct:.0f}% ({xp}) were cross-person claiming where the issue creator and the person who claimed it were different people.

## Figures

- `fig1_conversion_rate.png` \u2014 Static figure (matplotlib)
- `fig1_conversion_rate.html` \u2014 Interactive version (HTML/JS)

## Figure Legend

**Figure 1. Issue conversion rate and claiming authorship in the MATSUlab discourse graph.** **(Left)** Stacked horizontal bar showing the composition of all {ti} issues. Blue: explicitly claimed via `Claimed By::` metadata field (n={ec}). Green: inferred as claimed based on experimental log entries authored by the page creator (n={ic}). Amber: ISS pages with experimental log activity but no formal conversion to experiment format (n={ia}). Grey: unclaimed ISS pages with no evidence of active work (n={uc}). Bracket indicates total claimed issues ({tc}, {cr}%). **(Right)** Donut chart showing claiming authorship breakdown among the {known_pairs} claimed experiments. Orange: self-claimed where the issue creator and the person claiming were the same person (n={sc}, {self_pct:.0f}%). Purple: cross-person claiming where a different researcher claimed the issue (n={xp}, {xp_pct:.0f}%).
"""
    with open(path, 'w') as f:
        f.write(content)


def _write_evd1_methods_excerpt(output_dir: Path, path: Path):
    """Extract relevant methods sections for EVD 1."""
    methods_path = output_dir / 'methods.md'

    sections_to_extract = [
        '## 2. Node Identification',
        '## 3. Claiming Detection',
        '## 6. Metric Definitions and Calculations',
    ]

    if not methods_path.exists():
        with open(path, 'w') as f:
            f.write("# Methods Excerpt\n\nSee `output/methods.md` for full methodological detail.\n")
        return

    with open(methods_path, 'r') as f:
        full_text = f.read()

    lines = full_text.split('\n')
    extracted = ["# Methods Excerpt (EVD 1)\n"]
    extracted.append("This excerpt contains the methods sections relevant to the issue conversion rate analysis. For the complete methods document, see `output/methods.md`.\n")
    extracted.append("---\n")

    for section_header in sections_to_extract:
        in_section = False
        section_lines = []
        for line in lines:
            if line.strip().startswith(section_header):
                in_section = True
                section_lines.append(line)
                continue
            if in_section:
                if line.strip().startswith('## ') and not line.strip().startswith(section_header):
                    break
                section_lines.append(line)

        if section_lines:
            extracted.extend(section_lines)
            extracted.append('\n---\n')

    with open(path, 'w') as f:
        f.write('\n'.join(extracted))


def _write_evd1_evidence_jsonld(metrics: dict, path: Path):
    """Write the canonical JSON-LD evidence bundle metadata for EVD 1."""
    conv = metrics['metrics']['conversion_rate']
    ttr = metrics['metrics']['time_to_first_result']
    total_res = sum(d['total_linked_res'] for d in ttr['details']) if ttr['details'] else 0

    jsonld = {
        "@context": {
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcterms": "http://purl.org/dc/terms/",
            "prov": "http://www.w3.org/ns/prov#",
            "schema": "https://schema.org/",
            "dgb": "https://discoursegraphs.com/schema/dg_base/",
            "dge": "https://discoursegraphs.com/schema/dg_evidence/",
        },
        "@type": "dge:EvidenceBundle",
        "@id": "evd1-conversion-rate",
        "dc:title": (
            f"[[RES]] - {conv['conversion_rate_percent']:.0f}% of MATSUlab issues "
            f"(n={conv['total_issues']}) were claimed as experiments "
            f"and {round(ttr['count'] / conv['total_claimed'] * 100) if conv['total_claimed'] > 0 else 0}% "
            f"of those claimed at least one formal result node, yielding "
            f"{total_res} total RES nodes - [[@analysis/quantify issue claiming from MATSUlab]]"
        ),
        "dc:creator": "Matt Akamatsu",
        "dc:date": datetime.now().strftime('%Y-%m-%d'),
        "dcterms:license": "https://creativecommons.org/licenses/by/4.0/",
        "dge:evidenceStatement": (
            f"{conv['conversion_rate_percent']:.0f}% of MATSUlab issues "
            f"(n={conv['total_issues']}) were claimed as experiments and "
            f"{round(ttr['count'] / conv['total_claimed'] * 100) if conv['total_claimed'] > 0 else 0}% of "
            f"those claimed at least one formal result node, yielding {total_res} total RES nodes."
        ),
        "dge:observable": {
            "@type": "dge:Observable",
            "dc:title": "Issue-to-experiment conversion rate and result production",
            "dc:description": (
                f"The proportion of issues posted to a discourse graph Issues board that "
                f"are claimed as experiments, and the subsequent proportion of those claimed "
                f"experiments that produce formal result nodes. Measured across "
                f"{conv['total_issues']} issues, {conv['total_claimed']} claimed experiments, "
                f"and {total_res} RES nodes in the MATSUlab discourse graph."
            ),
        },
        "dge:method": {
            "@type": "dge:Method",
            "dc:title": "Discourse graph conversion rate analysis",
            "dc:description": (
                f"Automated pipeline parsing JSON-LD and Roam JSON exports to identify "
                f"issue nodes ({conv['unclaimed_iss'] + conv['iss_with_activity']} formal ISS + "
                f"{conv['explicit_claims'] + conv['inferred_claims']} experiment pages), detect claiming via "
                f"a two-tier strategy (explicitly claimed via Claimed By:: field, n={conv['explicit_claims']}; inferred via "
                f"experimental log presence, n={conv['inferred_claims']}; plus {conv['iss_with_activity']} ISS pages "
                f"with activity), and link result nodes using a 3-tier matching strategy (relation instances, "
                f"backreference matching, full description matching)."
            ),
            "prov:used": [
                {"@id": "src/calculate_metrics.py", "dc:description": "Metric calculation and data merging"},
                {"@id": "src/parse_jsonld.py", "dc:description": "JSON-LD export parser"},
                {"@id": "src/parse_roam_json.py", "dc:description": "Roam JSON streaming parser"},
                {"@id": "src/generate_visualizations.py", "dc:description": "Visualization generator"},
            ],
            "schema:codeRepository": "node-metrics",
        },
        "dge:system": {
            "@type": "dge:System",
            "dc:title": "MATSUlab discourse graph",
            "dc:description": (
                f"Akamatsu Lab Roam Research discourse graph, "
                f"{datetime.now().strftime('%B %Y')} snapshot. "
                f"Contains {conv['total_issues']} identifiable issues "
                f"({conv['unclaimed_iss'] + conv['iss_with_activity']} formal ISS nodes + "
                f"{conv['explicit_claims'] + conv['inferred_claims']} experiment pages), "
                f"{conv['total_claimed']} claimed experiments, and "
                f"{metrics['summary']['total_res_nodes']} result nodes."
            ),
            "schema:memberOf": "Akamatsu Lab, University of Washington",
            "dcterms:temporal": datetime.now().strftime('%Y-%m-%d'),
        },
        "dge:figure": [
            {
                "@type": "schema:ImageObject",
                "schema:contentUrl": "fig1_conversion_rate.png",
                "schema:encodingFormat": "image/png",
                "dge:figureLegend": (
                    f"Figure 1. Issue conversion rate and claiming authorship in the MATSUlab "
                    f"discourse graph. (Left) Stacked horizontal bar showing the composition "
                    f"of all {conv['total_issues']} issues: explicitly claimed ({conv['explicit_claims']}, blue), "
                    f"inferred claiming ({conv['inferred_claims']}, green), "
                    f"ISS with activity ({conv['iss_with_activity']}, amber), "
                    f"unclaimed ({conv['unclaimed_iss']}, grey). Bracket indicates "
                    f"total claimed: {conv['total_claimed']} ({conv['conversion_rate_percent']}%). "
                    f"(Right) Donut chart showing claiming authorship "
                    f"among {conv['self_claims'] + conv['cross_person_claims']} claimed experiments: "
                    f"self-claimed ({conv['self_claims']}, "
                    f"{round(conv['self_claims'] / (conv['self_claims'] + conv['cross_person_claims']) * 100) if (conv['self_claims'] + conv['cross_person_claims']) > 0 else 0}%) "
                    f"and cross-person claiming ({conv['cross_person_claims']}, "
                    f"{round(conv['cross_person_claims'] / (conv['self_claims'] + conv['cross_person_claims']) * 100) if (conv['self_claims'] + conv['cross_person_claims']) > 0 else 0}%)."
                ),
            },
            {
                "@type": "schema:WebPage",
                "schema:contentUrl": "fig1_conversion_rate.html",
                "schema:encodingFormat": "text/html",
                "dc:description": (
                    "Interactive HTML/JS version of Figure 1 with hover tooltips, "
                    "animated transitions, and responsive layout."
                ),
            },
        ],
        "dge:groundingData": [
            {
                "@type": "schema:DataDownload",
                "schema:contentUrl": "data/conversion_data.json",
                "schema:encodingFormat": "application/json",
                "dc:description": (
                    "Aggregated conversion rate data with claiming type breakdown, "
                    "authorship statistics, and result production metrics"
                ),
            },
        ],
        "dge:documentation": [
            {
                "@type": "schema:TextDigitalDocument",
                "schema:contentUrl": "docs/evidence_statement.md",
                "dc:description": "Evidence statement, evidence description, and figure legend",
            },
            {
                "@type": "schema:TextDigitalDocument",
                "schema:contentUrl": "docs/methods_excerpt.md",
                "dc:description": (
                    "Relevant methods sections for node identification, claiming detection, "
                    "and metric calculation"
                ),
            },
        ],
        "prov:wasGeneratedBy": {
            "@type": "prov:Activity",
            "prov:startedAtTime": "2026-01-25",
            "prov:endedAtTime": datetime.now().strftime('%Y-%m-%d'),
            "prov:used": [
                Path(metrics['data_sources']['jsonld']).name if 'data_sources' in metrics else "akamatsulab_discourse-graph-json-LD.json",
                Path(metrics['data_sources']['roam_json']).name if 'data_sources' in metrics else "akamatsulab-whole-graph-json.json",
            ],
            "prov:wasAssociatedWith": [
                {"@type": "prov:Agent", "dc:title": "Matt Akamatsu", "schema:affiliation": "University of Washington"},
                {"@type": "prov:SoftwareAgent", "dc:title": "Claude", "schema:provider": "Anthropic"},
            ],
        },
        "dge:summaryMetrics": {
            "total_issues": conv['total_issues'],
            "claimed_experiments": conv['total_claimed'],
            "explicitly_claimed": conv['explicit_claims'],
            "inferred_claiming": conv['inferred_claims'],
            "iss_with_activity": conv['iss_with_activity'],
            "unclaimed_iss": conv['unclaimed_iss'],
            "conversion_rate_percent": conv['conversion_rate_percent'],
            "experiments_with_results": ttr['count'],
            "claiming_to_result_percent": round(ttr['count'] / conv['total_claimed'] * 100, 1) if conv['total_claimed'] > 0 else 0,
            "total_res_nodes": total_res,
            "avg_res_per_producing_experiment": round(total_res / ttr['count'], 1) if ttr['count'] > 0 else 0,
            "self_claimed": conv['self_claims'],
            "cross_person_claiming": conv['cross_person_claims'],
            "idea_exchange_rate_percent": metrics['metrics']['cross_person_claims']['idea_exchange_rate'],
        },
    }

    with open(path, 'w') as f:
        json.dump(jsonld, f, indent=2, ensure_ascii=False)


def _write_evd1_ro_crate_metadata(path: Path):
    """Write the RO-Crate metadata manifest for EVD 1."""
    rocrate = {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": [
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "about": {"@id": "./"},
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            },
            {
                "@id": "./",
                "@type": "Dataset",
                "name": (
                    "EVD 1: Issue Conversion Rate \u2014 "
                    "MATSUlab Discourse Graph"
                ),
                "description": (
                    "Evidence bundle for the finding that 29% of MATSUlab issues "
                    "(n=445) were claimed as experiments and 38% of those produced "
                    "at least one formal result node, yielding 139 total RES nodes. "
                    "Contains the evidence statement, static and interactive figures, "
                    "underlying data, and methodological documentation."
                ),
                "datePublished": "2026-02-14",
                "creator": [
                    {"@id": "#matt-akamatsu"},
                ],
                "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
                "hasPart": [
                    {"@id": "evidence.jsonld"},
                    {"@id": "fig0_issue_timeline.png"},
                    {"@id": "fig0_issue_timeline.html"},
                    {"@id": "fig0b_creator_heatmap.png"},
                    {"@id": "fig0b_creator_heatmap.html"},
                    {"@id": "fig0c_discourse_growth.png"},
                    {"@id": "fig0_issue_timeline_animated.gif"},
                    {"@id": "fig1_conversion_rate.png"},
                    {"@id": "fig1_conversion_rate.html"},
                    {"@id": "data/conversion_data.json"},
                    {"@id": "data/issue_timeline_data.json"},
                    {"@id": "docs/evidence_statement.md"},
                    {"@id": "docs/methods_excerpt.md"},
                ],
            },
            {
                "@id": "#matt-akamatsu",
                "@type": "Person",
                "name": "Matt Akamatsu",
                "affiliation": {"@id": "#uw"},
            },
            {
                "@id": "#uw",
                "@type": "Organization",
                "name": "University of Washington",
            },
            {
                "@id": "evidence.jsonld",
                "@type": "File",
                "name": "Evidence Bundle Metadata (JSON-LD)",
                "description": (
                    "Canonical evidence bundle metadata using the dge: "
                    "(Discourse Graph Evidence) vocabulary."
                ),
                "encodingFormat": "application/ld+json",
            },
            {
                "@id": "fig0_issue_timeline.png",
                "@type": ["File", "ImageObject"],
                "name": "Figure 0: Issue Creation Timeline (static)",
                "description": (
                    "Cumulative issue creation over time with dual y-axis. "
                    "Left axis: cumulative issue count (claimed vs unclaimed). "
                    "Right axis: issues as percentage of total discourse nodes. "
                    "Introductory panel contextualizing when and how the 445 issues accumulated."
                ),
                "encodingFormat": "image/png",
            },
            {
                "@id": "fig0_issue_timeline.html",
                "@type": ["File", "WebPage"],
                "name": "Figure 0: Issue Creation Timeline (interactive)",
                "description": (
                    "Interactive Plotly version of the issue creation timeline. "
                    "Hover for date and count details. Toggle between discourse node "
                    "and all-content-page denominators for percentage calculation."
                ),
                "encodingFormat": "text/html",
            },
            {
                "@id": "fig0b_creator_heatmap.png",
                "@type": ["File", "ImageObject"],
                "name": "Figure 0b: Issue Creator Attribution Heatmap (static)",
                "description": (
                    "Heatmap showing issue creation by researcher and month. "
                    "Rows are anonymized researchers, columns are months, cell "
                    "intensity indicates number of issues created."
                ),
                "encodingFormat": "image/png",
            },
            {
                "@id": "fig0b_creator_heatmap.html",
                "@type": ["File", "WebPage"],
                "name": "Figure 0b: Creator Attribution Heatmap (interactive)",
                "description": (
                    "Interactive heatmap with toggles for different discourse node types "
                    "(ISS, RES, CLM, HYP, CON, EVD, QUE). Default shows issues; "
                    "selecting other types reveals per-researcher creation patterns."
                ),
                "encodingFormat": "text/html",
            },
            {
                "@id": "fig0c_discourse_growth.png",
                "@type": ["File", "ImageObject"],
                "name": "Figure 0c: Discourse Graph Growth by Node Type",
                "description": (
                    "Stacked area chart showing cumulative growth of all discourse "
                    "node types (ISS, RES, CLM, HYP, CON, EVD, QUE, Experiments) "
                    "over time. Issues' share of the graph visible as band thickness."
                ),
                "encodingFormat": "image/png",
            },
            {
                "@id": "fig0_issue_timeline_animated.gif",
                "@type": ["File", "ImageObject"],
                "name": "Figure 0 (animated): Issue Creation Timeline",
                "description": (
                    "Animated GIF showing cumulative issue creation month by month, "
                    "with running counter. Suitable for presentations."
                ),
                "encodingFormat": "image/gif",
            },
            {
                "@id": "fig1_conversion_rate.png",
                "@type": ["File", "ImageObject"],
                "name": "Figure 1: Issue Conversion Rate (static)",
                "description": (
                    "Two-panel figure. Left: stacked horizontal bar showing 445 issues "
                    "broken down by claiming type (69 explicitly, 56 inferred, 5 ISS with "
                    "activity, 315 unclaimed). Right: donut chart of claiming authorship "
                    "(106 self-claimed, 19 cross-person)."
                ),
                "encodingFormat": "image/png",
            },
            {
                "@id": "fig1_conversion_rate.html",
                "@type": ["File", "WebPage"],
                "name": "Figure 1: Issue Conversion Rate (interactive)",
                "description": (
                    "Interactive HTML/JS version of Figure 1 with hover tooltips, "
                    "animated transitions, and responsive layout. Self-contained "
                    "single-file application."
                ),
                "encodingFormat": "text/html",
            },
            {
                "@id": "data/conversion_data.json",
                "@type": "File",
                "name": "Conversion Rate Data",
                "description": (
                    "Aggregated conversion rate data with claiming type breakdown, "
                    "authorship statistics, and result production metrics."
                ),
                "encodingFormat": "application/json",
            },
            {
                "@id": "data/issue_timeline_data.json",
                "@type": "File",
                "name": "Issue Timeline Data",
                "description": (
                    "Per-issue creation dates, monthly summary with cumulative counts, "
                    "and discourse node growth data by type. Supports Figure 0 visualizations."
                ),
                "encodingFormat": "application/json",
            },
            {
                "@id": "docs/evidence_statement.md",
                "@type": "File",
                "name": "Evidence Statement and Figure Legend",
                "description": "EVD 1 evidence statement, evidence description, and figure legend in markdown.",
                "encodingFormat": "text/markdown",
            },
            {
                "@id": "docs/methods_excerpt.md",
                "@type": "File",
                "name": "Methods Excerpt",
                "description": (
                    "Relevant sections from the full methods document covering "
                    "node identification, claiming detection, and metric definitions."
                ),
                "encodingFormat": "text/markdown",
            },
        ],
    }

    with open(path, 'w') as f:
        json.dump(rocrate, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    from calculate_metrics import calculate_all_metrics

    base_path = Path(__file__).parent.parent
    jsonld_path = str(base_path / 'graph raw data' / 'akamatsulab_discourse-graph-json-LD_202601242232.json')
    roam_path = str(base_path / 'graph raw data' / 'akamatsulab-whole-graph-json-2026-01-24-23-44-15.json')

    print("Calculating metrics...")
    metrics = calculate_all_metrics(jsonld_path, roam_path)

    output_dir = base_path / 'output'
    viz_dir = output_dir / 'visualizations'

    create_evd1_bundle(metrics, output_dir, viz_dir)
    create_evd5_bundle(metrics, output_dir, viz_dir)
    create_evd7_bundle(output_dir, viz_dir)
