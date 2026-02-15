#!/usr/bin/env python3
"""
Main Pipeline for Discourse Graph Issue Metrics
================================================
Orchestrates the full analysis pipeline:
1. Parse JSON-LD export
2. Parse Roam JSON export (with block timestamps)
3. Calculate all 5 metrics
4. Generate visualizations
5. Write reports

Author: Matt Akamatsu (with Claude)
Date: 2026-01-25
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from calculate_metrics import calculate_all_metrics, print_metrics_summary
from generate_visualizations import generate_all_visualizations
from handoff_visualizations import generate_all_handoff_visualizations
from create_evidence_bundle import create_evd1_bundle, create_evd5_bundle
from experiment_lifecycle_visualizations import generate_experiment_lifecycle_visualizations


def generate_markdown_report(metrics: dict, output_path: Path):
    """Generate a human-readable markdown report of the metrics."""
    m = metrics['metrics']
    summary = metrics['summary']

    lines = [
        "# Discourse Graph Issue Metrics Report",
        "",
        f"**Generated:** {metrics['generated']}",
        "",
        "## Overview",
        "",
        "This report analyzes the Akamatsu Lab discourse graph to quantify how effectively",
        "the 'Issues board' facilitates idea exchange between researchers.",
        "",
        "### Data Summary",
        "",
        f"- **Experiment pages:** {summary['total_experiment_pages']}",
        f"- **ISS (Issue) nodes:** {summary['total_iss_nodes']}",
        f"- **RES (Result) nodes:** {summary['total_res_nodes']}",
        "",
        "---",
        "",
        "## Metric 1: Issue Conversion Rate",
        "",
        "**Definition:** Percentage of issues that have been claimed (i.e., converted to active experiments).",
        "",
    ]

    conv = m['conversion_rate']
    lines.extend([
        f"### Results",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Conversion Rate | **{conv['conversion_rate_percent']}%** |",
        f"| Total Claimed | {conv['total_claimed']} |",
        f"| - Explicitly Claimed (Claimed By:: field) | {conv['explicit_claims']} |",
        f"| - Inferred as Claimed (experimental log by creator) | {conv['inferred_claims']} |",
        f"| - ISS with Activity | {conv['iss_with_activity']} |",
        f"| Unclaimed ISS | {conv['unclaimed_iss']} |",
        f"| Total Issues | {conv['total_issues']} |",
        "",
        "### Claiming Type Breakdown",
        "",
        f"| Type | Count |",
        f"|------|-------|",
        f"| Cross-Person Claiming | {conv['cross_person_claims']} |",
        f"| Self-Claiming | {conv['self_claims']} |",
        "",
    ])

    # Cross-person claiming examples
    if conv['cross_person_claim_list']:
        lines.extend([
            "### Cross-Person Claiming Examples (Idea Exchange)",
            "",
        ])
        for cp in conv['cross_person_claim_list'][:5]:
            lines.extend([
                f"- **{cp['title'][:70]}...**",
                f"  - Issue Created By: {cp.get('issue_created_by', 'Unknown')}",
                f"  - Claimed By: {cp.get('claimed_by', 'Unknown')}",
                "",
            ])

    lines.extend([
        "---",
        "",
        "## Metric 2: Time-to-Claiming",
        "",
        "**Definition:** Duration from when an Issue was created to when it was claimed.",
        "",
    ])

    ttc = m['time_to_claim']
    if ttc['count'] > 0:
        lines.extend([
            "### Results",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Experiments with Data | {ttc['count']} |",
            f"| Average Time | **{ttc['avg_days']} days** |",
            f"| Minimum | {ttc['min_days']} days |",
            f"| Maximum | {ttc['max_days']} days |",
            f"| Median | {ttc['median_days']} days |",
            "",
        ])
    else:
        lines.append("*No data available for time-to-claiming calculation.*\n")

    lines.extend([
        "---",
        "",
        "## Metric 3: Time-to-First-Result",
        "",
        "**Definition:** Duration from when an experiment was claimed (started) to when the first Result node was created.",
        "",
    ])

    ttr = m['time_to_first_result']
    if ttr['count'] > 0:
        lines.extend([
            "### Results",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Experiments with Results | {ttr['count']} |",
            f"| Average Time | **{ttr['avg_days']} days** |",
            f"| Minimum | {ttr['min_days']} days |",
            f"| Maximum | {ttr['max_days']} days |",
            "",
        ])
    else:
        lines.append("*No data available for time-to-first-result calculation.*\n")

    lines.extend([
        "---",
        "",
        "## Metric 4: Unique Contributors per Issue Chain",
        "",
        "**Definition:** Count of distinct researchers involved in an Issue → Experiment → Result chain.",
        "",
    ])

    cont = m['unique_contributors']
    if cont['experiments_analyzed'] > 0:
        lines.extend([
            "### Results",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Experiments Analyzed | {cont['experiments_analyzed']} |",
            f"| Average Contributors | **{cont['avg_contributors']}** |",
            f"| Multi-Contributor Experiments | {cont['multi_contributor_count']} |",
            f"| Single-Contributor Experiments | {cont['single_contributor_count']} |",
            "",
            "### Distribution",
            "",
            "| Contributors | Experiments |",
            "|--------------|-------------|",
        ])
        for n, count in sorted(cont['distribution'].items()):
            lines.append(f"| {n} | {count} |")
        lines.append("")
    else:
        lines.append("*No data available for contributor analysis.*\n")

    lines.extend([
        "---",
        "",
        "## Metric 5: Cross-Person Claiming (Idea Exchange)",
        "",
        "**Definition:** Cases where the person who claimed an issue is different from the person who created it.",
        "This is the key metric demonstrating transfer of ideas between researchers.",
        "",
    ])

    xp = m['cross_person_claims']
    lines.extend([
        "### Results",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Cross-Person Claiming | **{xp['cross_person_count']}** |",
        f"| Self-Claiming | {xp['self_claim_count']} |",
        f"| Idea Exchange Rate | **{xp['idea_exchange_rate']}%** |",
        "",
    ])

    if xp['exchange_pairs']:
        lines.extend([
            "### Idea Exchange Pairs",
            "",
            "| From (Issue Creator) | To (Claimed By) | Count |",
            "|---------------------|--------------|-------|",
        ])
        for pair in xp['exchange_pairs']:
            lines.append(f"| {pair['from']} | {pair['to']} | {pair['count']} |")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Summary",
        "",
        "The Issues board in the Akamatsu Lab discourse graph demonstrates:",
        "",
        f"1. **{conv['conversion_rate_percent']}% conversion rate** - Issues are being actively claimed and worked on",
        f"2. **{xp['cross_person_count']} cross-person claiming instances** - Ideas are being transferred between researchers",
        f"3. **{xp['idea_exchange_rate']}% idea exchange rate** - A significant portion of claiming represents idea transfer",
        "",
    ])

    if cont['experiments_analyzed'] > 0:
        lines.append(f"4. **{cont['avg_contributors']} average contributors** per experiment chain")

    lines.extend([
        "",
        "---",
        "",
        "*Report generated by discourse graph metrics analysis pipeline*",
    ])

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"Report saved to: {output_path}")


def run_pipeline(
    jsonld_path: str = None,
    roam_json_path: str = None,
    output_dir: str = None,
):
    """
    Run the full metrics analysis pipeline.

    Args:
        jsonld_path: Path to JSON-LD export (optional, uses default if not provided)
        roam_json_path: Path to Roam JSON export (optional, uses default if not provided)
        output_dir: Output directory (optional, uses default if not provided)
    """
    base_path = Path(__file__).parent.parent

    # Set defaults
    if jsonld_path is None:
        jsonld_path = str(base_path / 'graph raw data' / 'akamatsulab_discourse-graph-json-LD202602112140.json')
    if roam_json_path is None:
        roam_json_path = str(base_path / 'graph raw data' / 'akamatsulab-whole-graph-2026-02-13-22-24-27.json')
    if output_dir is None:
        output_dir = base_path / 'output'
    else:
        output_dir = Path(output_dir)

    print("=" * 80)
    print("DISCOURSE GRAPH ISSUE METRICS PIPELINE")
    print("=" * 80)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nData sources:")
    print(f"  JSON-LD: {jsonld_path}")
    print(f"  Roam JSON: {roam_json_path}")
    print(f"  Output: {output_dir}")
    print()

    # Verify files exist
    if not Path(jsonld_path).exists():
        print(f"ERROR: JSON-LD file not found: {jsonld_path}")
        return None
    if not Path(roam_json_path).exists():
        print(f"ERROR: Roam JSON file not found: {roam_json_path}")
        return None

    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'visualizations').mkdir(exist_ok=True)

    # Step 1-3: Calculate metrics (includes parsing)
    print("-" * 40)
    print("STEP 1-3: Calculating metrics...")
    print("-" * 40)
    metrics = calculate_all_metrics(jsonld_path, roam_json_path)

    # Print summary
    print_metrics_summary(metrics)

    # Step 4: Save metrics JSON
    print("-" * 40)
    print("STEP 4: Saving metrics data...")
    print("-" * 40)

    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    metrics_json_path = output_dir / 'metrics_data.json'
    with open(metrics_json_path, 'w') as f:
        json.dump(metrics, f, indent=2, default=json_serializer)
    print(f"Saved: {metrics_json_path}")

    # Step 5: Generate visualizations
    print("-" * 40)
    print("STEP 5: Generating visualizations...")
    print("-" * 40)
    viz_dir = output_dir / 'visualizations'
    generate_all_visualizations(metrics, viz_dir)

    # Step 5b: Generate handoff / alluvial visualizations
    print("-" * 40)
    print("STEP 5b: Generating handoff visualizations...")
    print("-" * 40)
    generate_all_handoff_visualizations(metrics, viz_dir)

    # Step 5c: Generate experiment lifecycle visualizations (Fig 6 series)
    print("-" * 40)
    print("STEP 5c: Generating experiment lifecycle visualizations...")
    print("-" * 40)
    generate_experiment_lifecycle_visualizations(metrics, viz_dir)

    # Step 6: Generate markdown report
    print("-" * 40)
    print("STEP 6: Generating report...")
    print("-" * 40)
    report_path = output_dir / 'metrics_report.md'
    generate_markdown_report(metrics, report_path)

    # Step 7: Generate evidence bundles
    print("-" * 40)
    print("STEP 7: Generating evidence bundles...")
    print("-" * 40)
    evd1_dir = create_evd1_bundle(metrics, output_dir, viz_dir)
    bundle_dir = create_evd5_bundle(metrics, output_dir, viz_dir)

    print()
    print("=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print(f"\nOutput files:")
    print(f"  - {metrics_json_path}")
    print(f"  - {report_path}")
    print(f"  - {viz_dir}/fig0_issue_timeline.png")
    print(f"  - {viz_dir}/fig0_issue_timeline.html")
    print(f"  - {viz_dir}/fig0b_creator_heatmap.png")
    print(f"  - {viz_dir}/fig0b_creator_heatmap.html")
    print(f"  - {viz_dir}/fig0c_discourse_growth.png")
    print(f"  - {viz_dir}/fig0_issue_timeline_animated.gif")
    print(f"  - {viz_dir}/fig1_conversion_rate.png")
    print(f"  - {viz_dir}/fig2_time_distributions.png")
    print(f"  - {viz_dir}/fig3_contributor_breadth.png")
    print(f"  - {viz_dir}/fig4_idea_exchange.png")
    print(f"  - {viz_dir}/fig5_funnel.png")
    print(f"  - {evd1_dir}/evidence.jsonld")
    print(f"  - {evd1_dir}/data/issue_timeline_data.json")
    print(f"  - {bundle_dir}/evidence.jsonld")
    print(f"  - {bundle_dir}/ro-crate-metadata.json")
    print(f"  - {bundle_dir}/data/funnel_summary.json")
    print(f"  - {bundle_dir}/data/experiment_details.csv")
    print()

    return metrics


if __name__ == '__main__':
    # Parse command line arguments
    jsonld_path = sys.argv[1] if len(sys.argv) > 1 else None
    roam_json_path = sys.argv[2] if len(sys.argv) > 2 else None
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None

    run_pipeline(jsonld_path, roam_json_path, output_dir)
