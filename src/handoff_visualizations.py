#!/usr/bin/env python3
"""
Handoff Visualizations for Idea Exchange
==========================================
Creates specialized visualizations showing the flow of ideas between researchers:
1. Alluvial/Flow diagram: Issue Creator → Claimer → Result Creator
2. Chord diagram: Bi-directional relationships between researchers
3. Left-to-right flow with node sizes by activity

Author: Matt Akamatsu (with Claude)
Date: 2026-01-25
"""

import json
from pathlib import Path
from collections import defaultdict, Counter

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

from anonymize import anonymize_name


def get_abbrev(name: str) -> str:
    """Get abbreviation for a researcher name (returns anonymized pseudonym)."""
    if name is None:
        return '?'
    # Anonymize first, then return the pseudonym as-is (R1, R2, etc.)
    anon = anonymize_name(name)
    return anon if anon else '?'


def normalize_name(name: str) -> str:
    """Normalize and anonymize researcher names."""
    if name is None:
        return None
    name = name.strip()
    return anonymize_name(name)


def extract_handoff_data(metrics: dict) -> dict:
    """
    Extract handoff flow data from metrics.

    Returns dict with:
    - issue_to_claim: {(creator, claimer): count}
    - claim_to_result: {(claimer, result_creator): count}
    - full_chains: [(creator, claimer, result_creators), ...]
    """
    issue_to_claim = Counter()
    claim_to_result = Counter()
    full_chains = []

    # Get contributor details
    contributors = metrics['metrics']['unique_contributors']['details']
    cross_person = metrics['metrics']['cross_person_claims']['cross_person_details']

    # Build issue→claim edges from cross-person claims
    for claim in cross_person:
        creator = normalize_name(claim.get('issue_created_by'))
        claimer = normalize_name(claim.get('claimed_by'))
        if creator and claimer:
            issue_to_claim[(creator, claimer)] += 1

    # Build full chains from contributor data
    for exp in contributors:
        creator = normalize_name(exp.get('issue_created_by'))
        claimer = normalize_name(exp.get('claimed_by'))
        all_contributors = [normalize_name(c) for c in exp.get('contributors', [])]

        # Result creators are contributors who aren't the creator or claimer
        result_creators = [c for c in all_contributors if c and c not in [creator, claimer]]

        if creator and claimer:
            full_chains.append({
                'creator': creator,
                'claimer': claimer,
                'result_creators': result_creators,
                'title': exp.get('title', '')[:50],
            })

            # Track claim→result edges
            for rc in result_creators:
                claim_to_result[(claimer, rc)] += 1

    return {
        'issue_to_claim': issue_to_claim,
        'claim_to_result': claim_to_result,
        'full_chains': full_chains,
    }


def create_three_column_flow(metrics: dict, output_dir: Path):
    """
    Create a three-column flow diagram:
    Column 1: Issue Creators
    Column 2: Claimers
    Column 3: Result Creators

    Lines connect the flow with thickness proportional to count.
    """
    data = extract_handoff_data(metrics)

    # Collect all people by role
    creators = Counter()
    claimers = Counter()
    result_creators = Counter()

    for chain in data['full_chains']:
        if chain['creator']:
            creators[chain['creator']] += 1
        if chain['claimer']:
            claimers[chain['claimer']] += 1
        for rc in chain['result_creators']:
            result_creators[rc] += 1

    # Also add issue→claim flows
    for (c, cl), count in data['issue_to_claim'].items():
        creators[c] += count
        claimers[cl] += count

    fig, ax = plt.subplots(figsize=(14, 10))

    # Column positions
    col_x = [0.15, 0.5, 0.85]

    # Get sorted lists of people for each column
    creator_list = sorted(creators.keys(), key=lambda x: -creators[x])
    claimer_list = sorted(claimers.keys(), key=lambda x: -claimers[x])
    result_list = sorted(result_creators.keys(), key=lambda x: -result_creators[x])

    # Calculate y positions for each person in each column
    def get_y_positions(people_list, counts):
        if not people_list:
            return {}
        total = sum(counts[p] for p in people_list)
        positions = {}
        y = 0.9
        for person in people_list:
            height = max(0.03, (counts[person] / total) * 0.7)
            positions[person] = y - height/2
            y -= height + 0.02
        return positions

    creator_y = get_y_positions(creator_list, creators)
    claimer_y = get_y_positions(claimer_list, claimers)
    result_y = get_y_positions(result_list, result_creators)

    # Color palette
    colors = plt.cm.tab20(np.linspace(0, 1, 20))
    person_colors = {}
    all_people = set(creator_list) | set(claimer_list) | set(result_list)
    for i, person in enumerate(sorted(all_people)):
        person_colors[person] = colors[i % 20]

    # Draw nodes (boxes) for each person in each column
    def draw_nodes(x, y_positions, counts, column_name):
        for person, y in y_positions.items():
            abbrev = get_abbrev(person)
            count = counts[person]
            height = max(0.03, 0.05 + count * 0.01)

            rect = FancyBboxPatch(
                (x - 0.06, y - height/2),
                0.12, height,
                boxstyle="round,pad=0.01,rounding_size=0.01",
                facecolor=person_colors[person],
                edgecolor='black',
                linewidth=1.5,
                alpha=0.8,
            )
            ax.add_patch(rect)
            ax.text(x, y, f"{abbrev}\n({count})", ha='center', va='center',
                   fontsize=9, fontweight='bold', color='white')

    draw_nodes(col_x[0], creator_y, creators, 'Issue Creators')
    draw_nodes(col_x[1], claimer_y, claimers, 'Claimers')
    if result_y:
        draw_nodes(col_x[2], result_y, result_creators, 'Result Creators')

    # Draw flow lines (Issue Creator → Claimer)
    max_flow = max(data['issue_to_claim'].values()) if data['issue_to_claim'] else 1
    for (creator, claimer), count in data['issue_to_claim'].items():
        if creator in creator_y and claimer in claimer_y:
            y1 = creator_y[creator]
            y2 = claimer_y[claimer]
            width = 1 + (count / max_flow) * 5
            ax.annotate('',
                xy=(col_x[1] - 0.07, y2),
                xytext=(col_x[0] + 0.07, y1),
                arrowprops=dict(
                    arrowstyle='-|>',
                    color=person_colors[creator],
                    alpha=0.4,
                    lw=width,
                    connectionstyle='arc3,rad=0.1'
                ))

    # Draw flow lines (Claimer → Result Creator)
    if data['claim_to_result']:
        max_flow2 = max(data['claim_to_result'].values())
        for (claimer, rc), count in data['claim_to_result'].items():
            if claimer in claimer_y and rc in result_y:
                y1 = claimer_y[claimer]
                y2 = result_y[rc]
                width = 1 + (count / max_flow2) * 5
                ax.annotate('',
                    xy=(col_x[2] - 0.07, y2),
                    xytext=(col_x[1] + 0.07, y1),
                    arrowprops=dict(
                        arrowstyle='-|>',
                        color=person_colors[claimer],
                        alpha=0.4,
                        lw=width,
                        connectionstyle='arc3,rad=0.1'
                    ))

    # Column headers
    ax.text(col_x[0], 0.97, 'Issue\nCreators', ha='center', va='bottom',
           fontsize=14, fontweight='bold')
    ax.text(col_x[1], 0.97, 'Claimers', ha='center', va='bottom',
           fontsize=14, fontweight='bold')
    ax.text(col_x[2], 0.97, 'Result\nCreators', ha='center', va='bottom',
           fontsize=14, fontweight='bold')

    # Legend with full names
    legend_text = "Abbreviations:\n" + "\n".join(
        f"{get_abbrev(p)} = {p}" for p in sorted(all_people)
    )
    ax.text(0.02, 0.02, legend_text, transform=ax.transAxes,
           fontsize=8, verticalalignment='bottom',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.set_title('Idea Handoff Flow: Issue Creator → Claimer → Result Creator',
                fontsize=16, fontweight='bold', pad=20)

    plt.tight_layout()
    output_path = output_dir / 'handoff_flow_3col.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path}")


def create_directed_flow_diagram(metrics: dict, output_dir: Path):
    """
    Create a left-to-right directed flow diagram with:
    - Nodes sized by total activity (issues created + claims made)
    - Edge thickness proportional to number of transfers
    """
    data = extract_handoff_data(metrics)

    fig, ax = plt.subplots(figsize=(14, 8))

    # Calculate activity scores for each person
    activity = Counter()
    for (creator, claimer), count in data['issue_to_claim'].items():
        activity[creator] += count  # Created issues that got claimed
        activity[claimer] += count  # Claimed issues

    # Get unique people and sort by activity
    people = sorted(activity.keys(), key=lambda x: -activity[x])
    n_people = len(people)

    if n_people == 0:
        print("  Skipping directed flow diagram (no data)")
        return

    # Position nodes in a circle or arc
    # Put high-activity people (creators) on the left, claimers on the right
    creators_set = set(c for (c, _) in data['issue_to_claim'].keys())
    claimers_set = set(c for (_, c) in data['issue_to_claim'].keys())

    # Separate into net-creators and net-claimers
    net_role = {}
    for person in people:
        created = sum(cnt for (c, _), cnt in data['issue_to_claim'].items() if c == person)
        claimed = sum(cnt for (_, c), cnt in data['issue_to_claim'].items() if c == person)
        net_role[person] = created - claimed  # Positive = net creator

    # Sort: net creators on left, net claimers on right
    sorted_people = sorted(people, key=lambda x: -net_role[x])

    # Calculate positions
    positions = {}
    for i, person in enumerate(sorted_people):
        # X based on net role (creators left, claimers right)
        x = 0.2 + (i / max(1, n_people - 1)) * 0.6 if n_people > 1 else 0.5
        # Stagger Y to avoid overlap
        y = 0.5 + 0.3 * np.sin(i * np.pi / 2)
        positions[person] = (x, y)

    # Colors based on net role
    colors = {}
    for person in people:
        if net_role[person] > 0:
            colors[person] = '#27ae60'  # Green for net creators
        elif net_role[person] < 0:
            colors[person] = '#9b59b6'  # Purple for net claimers
        else:
            colors[person] = '#3498db'  # Blue for balanced

    # Draw edges first (so nodes are on top)
    max_count = max(data['issue_to_claim'].values())
    for (creator, claimer), count in data['issue_to_claim'].items():
        x1, y1 = positions[creator]
        x2, y2 = positions[claimer]
        width = 1 + (count / max_count) * 6

        # Draw curved arrow
        ax.annotate('',
            xy=(x2 - 0.03, y2),
            xytext=(x1 + 0.03, y1),
            arrowprops=dict(
                arrowstyle='-|>',
                color='#34495e',
                alpha=0.5,
                lw=width,
                connectionstyle='arc3,rad=0.2' if y1 != y2 else 'arc3,rad=0.3'
            ))

        # Label with count
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2 + 0.05
        ax.text(mid_x, mid_y, str(count), ha='center', va='center',
               fontsize=8, color='#34495e', fontweight='bold')

    # Draw nodes
    max_activity = max(activity.values())
    for person in people:
        x, y = positions[person]
        size = 800 + (activity[person] / max_activity) * 2000

        ax.scatter([x], [y], s=size, c=[colors[person]],
                  edgecolors='black', linewidths=2, zorder=5, alpha=0.8)

        abbrev = get_abbrev(person)
        ax.text(x, y, abbrev, ha='center', va='center',
               fontsize=10, fontweight='bold', color='white', zorder=6)

        # Activity count below
        ax.text(x, y - 0.08, f"({activity[person]})", ha='center', va='top',
               fontsize=8, color='#666')

    # Legend
    creator_patch = mpatches.Patch(color='#27ae60', label='Net Idea Creator')
    claimer_patch = mpatches.Patch(color='#9b59b6', label='Net Idea Claimer')
    balanced_patch = mpatches.Patch(color='#3498db', label='Balanced')
    ax.legend(handles=[creator_patch, claimer_patch, balanced_patch],
             loc='upper left', fontsize=10)

    # Abbreviation legend
    legend_text = "\n".join(f"{get_abbrev(p)} = {p}" for p in sorted_people)
    ax.text(0.98, 0.02, legend_text, transform=ax.transAxes,
           fontsize=8, ha='right', va='bottom',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.set_xlim(0, 1)
    ax.set_ylim(0.1, 0.9)
    ax.axis('off')
    ax.set_title('Idea Exchange Network\n(Arrow thickness = number of handoffs, node size = total activity)',
                fontsize=14, fontweight='bold')

    plt.tight_layout()
    output_path = output_dir / 'handoff_directed_flow.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path}")


def create_alluvial_sankey(metrics: dict, output_dir: Path):
    """
    Create an alluvial/Sankey diagram showing ALL claimed experiments
    flowing through three stages:
    1. Issue Created (who created the issue)
    2. Issue Claimed (who claimed/worked on it)
    3. Result Created (who created the first result, for experiments with results)

    All issue creators are represented in the left column.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("  Skipping alluvial diagram (plotly not installed)")
        return

    conv = metrics['metrics']['conversion_rate']
    ttr = metrics['metrics']['time_to_first_result']

    # Build lookup for result creators by experiment title
    # Use primary_contributor (attribution-aware) with fallback to creator
    result_info = {}
    for d in ttr['details']:
        res_person = d.get('first_res_primary_contributor') or d.get('first_res_creator')
        result_info[d['experiment_title']] = {
            'first_res_creator': normalize_name(res_person),
            'total_linked_res': d.get('total_linked_res', 0),
        }

    # Count flows for all claimed experiments
    creator_to_claimer = Counter()
    claimer_to_result = Counter()
    claimer_no_result = Counter()

    all_creators = set()
    all_claimers = set()
    all_result_creators = set()

    for exp in conv['claimed_experiment_list']:
        # Issue creator: use issue_created_by if available, fall back to creator
        issue_creator = normalize_name(exp.get('issue_created_by') or exp.get('creator'))
        claimer = normalize_name(exp.get('claimed_by'))

        if not issue_creator or not claimer:
            continue

        all_creators.add(issue_creator)
        all_claimers.add(claimer)
        creator_to_claimer[(issue_creator, claimer)] += 1

        # Check if this experiment has results
        title = exp['title']
        if title in result_info:
            res_creator = result_info[title]['first_res_creator']
            if res_creator:
                all_result_creators.add(res_creator)
                claimer_to_result[(claimer, res_creator)] += 1
        else:
            claimer_no_result[claimer] += 1

    # Sort people by total activity for consistent ordering
    def total_activity(person):
        c1 = sum(v for (p, _), v in creator_to_claimer.items() if p == person)
        c2 = sum(v for (_, p), v in creator_to_claimer.items() if p == person)
        c3 = sum(v for (p, _), v in claimer_to_result.items() if p == person)
        c4 = sum(v for (_, p), v in claimer_to_result.items() if p == person)
        return c1 + c2 + c3 + c4

    sorted_creators = sorted(all_creators, key=lambda x: -total_activity(x))
    sorted_claimers = sorted(all_claimers, key=lambda x: -total_activity(x))
    sorted_result_creators = sorted(all_result_creators, key=lambda x: -total_activity(x))

    # Build node list
    nodes = []
    node_indices = {}

    # Column 1: Issue Created
    for person in sorted_creators:
        key = f"created_{person}"
        node_indices[key] = len(nodes)
        count = sum(v for (p, _), v in creator_to_claimer.items() if p == person)
        nodes.append(f"{get_abbrev(person)} ({count})")

    # Column 2: Issue Claimed
    for person in sorted_claimers:
        key = f"claimed_{person}"
        node_indices[key] = len(nodes)
        count = sum(v for (_, p), v in creator_to_claimer.items() if p == person)
        nodes.append(f"{get_abbrev(person)} ({count})")

    # Column 3: Result Created (only for experiments with results)
    for person in sorted_result_creators:
        key = f"result_{person}"
        node_indices[key] = len(nodes)
        count = sum(v for (_, p), v in claimer_to_result.items() if p == person)
        nodes.append(f"{get_abbrev(person)} ({count})")

    # Add a "No Result Yet" node for experiments without results
    total_no_result = sum(claimer_no_result.values())
    if total_no_result > 0:
        node_indices["no_result"] = len(nodes)
        nodes.append(f"No Result Yet ({total_no_result})")

    # Build links
    sources = []
    targets = []
    values = []
    link_colors = []

    # Color palette for flows
    color_self = 'rgba(149, 165, 166, 0.4)'  # Grey for self-claims
    color_cross = 'rgba(52, 152, 219, 0.5)'  # Blue for cross-person
    color_result = 'rgba(155, 89, 182, 0.5)'  # Purple for results
    color_no_result = 'rgba(189, 195, 199, 0.3)'  # Light grey for no result

    # Links: Issue Created → Issue Claimed
    for (creator, claimer), count in creator_to_claimer.items():
        src_key = f"created_{creator}"
        tgt_key = f"claimed_{claimer}"
        if src_key in node_indices and tgt_key in node_indices:
            sources.append(node_indices[src_key])
            targets.append(node_indices[tgt_key])
            values.append(count)
            # Color based on self vs cross-person
            if creator == claimer:
                link_colors.append(color_self)
            else:
                link_colors.append(color_cross)

    # Links: Issue Claimed → Result Created
    for (claimer, res_creator), count in claimer_to_result.items():
        src_key = f"claimed_{claimer}"
        tgt_key = f"result_{res_creator}"
        if src_key in node_indices and tgt_key in node_indices:
            sources.append(node_indices[src_key])
            targets.append(node_indices[tgt_key])
            values.append(count)
            link_colors.append(color_result)

    # Links: Issue Claimed → No Result Yet
    if total_no_result > 0:
        for claimer, count in claimer_no_result.items():
            src_key = f"claimed_{claimer}"
            if src_key in node_indices:
                sources.append(node_indices[src_key])
                targets.append(node_indices["no_result"])
                values.append(count)
                link_colors.append(color_no_result)

    if not sources:
        print("  Skipping alluvial diagram (no flow data)")
        return

    # Node colors based on column
    node_colors = []
    for i, node in enumerate(nodes):
        if i < len(sorted_creators):
            node_colors.append('#27ae60')  # Green for creators
        elif i < len(sorted_creators) + len(sorted_claimers):
            node_colors.append('#3498db')  # Blue for claimers
        elif 'No Result' in node:
            node_colors.append('#bdc3c7')  # Light grey for no result
        else:
            node_colors.append('#9b59b6')  # Purple for result creators

    # Set x positions to create 3 clear columns
    n_creators = len(sorted_creators)
    n_claimers = len(sorted_claimers)
    n_results = len(sorted_result_creators) + (1 if total_no_result > 0 else 0)

    x_positions = []
    y_positions = []

    # Column 1: x=0.01
    for i in range(n_creators):
        x_positions.append(0.01)
        y_positions.append((i + 0.5) / max(n_creators, 1))

    # Column 2: x=0.5
    for i in range(n_claimers):
        x_positions.append(0.5)
        y_positions.append((i + 0.5) / max(n_claimers, 1))

    # Column 3: x=0.99
    for i in range(n_results):
        x_positions.append(0.99)
        y_positions.append((i + 0.5) / max(n_results, 1))

    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',
        node=dict(
            pad=15,
            thickness=25,
            line=dict(color='black', width=1),
            label=nodes,
            color=node_colors,
            x=x_positions,
            y=y_positions,
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
        )
    )])

    # Add column headers using annotations
    fig.update_layout(
        title=dict(
            text=f"Issue → Experiment → Result Flow (All {conv['total_claimed']} Claimed Experiments)",
            font=dict(size=16),
        ),
        font_size=11,
        height=700,
        width=1100,
        annotations=[
            dict(x=0.01, y=1.08, xref='paper', yref='paper', showarrow=False,
                 text='<b>Issue Created</b>', font=dict(size=14)),
            dict(x=0.5, y=1.08, xref='paper', yref='paper', showarrow=False,
                 text='<b>Issue Claimed</b>', font=dict(size=14)),
            dict(x=0.99, y=1.08, xref='paper', yref='paper', showarrow=False,
                 text='<b>Result Created</b>', font=dict(size=14)),
            # Legend
            dict(x=0.01, y=-0.08, xref='paper', yref='paper', showarrow=False,
                 text='<span style="color:#95a5a6">━</span> Self-claim  '
                      '<span style="color:#3498db">━</span> Cross-person  '
                      '<span style="color:#9b59b6">━</span> Result created',
                 font=dict(size=10), align='left'),
        ],
    )

    output_path = output_dir / 'handoff_alluvial.html'
    fig.write_html(str(output_path))
    print(f"  Saved: {output_path}")

    try:
        png_path = output_dir / 'handoff_alluvial.png'
        fig.write_image(str(png_path), scale=2)
        print(f"  Saved: {png_path}")
    except Exception as e:
        print(f"  Note: Could not save as PNG ({e})")


def create_matrix_heatmap(metrics: dict, output_dir: Path):
    """
    Create a matrix/heatmap showing handoff counts between researchers.
    Rows = Issue creators, Columns = Claimers
    """
    data = extract_handoff_data(metrics)

    # Get all people involved
    all_people = set()
    for (c, cl) in data['issue_to_claim'].keys():
        all_people.add(c)
        all_people.add(cl)

    people = sorted(all_people)
    n = len(people)

    if n == 0:
        print("  Skipping matrix heatmap (no data)")
        return

    # Build matrix
    matrix = np.zeros((n, n))
    for (creator, claimer), count in data['issue_to_claim'].items():
        i = people.index(creator)
        j = people.index(claimer)
        matrix[i, j] = count

    fig, ax = plt.subplots(figsize=(10, 8))

    # Create heatmap
    im = ax.imshow(matrix, cmap='Blues', aspect='auto')

    # Labels
    abbrevs = [get_abbrev(p) for p in people]
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(abbrevs, fontsize=10, fontweight='bold')
    ax.set_yticklabels(abbrevs, fontsize=10, fontweight='bold')

    # Add value annotations
    for i in range(n):
        for j in range(n):
            val = int(matrix[i, j])
            if val > 0:
                ax.text(j, i, str(val), ha='center', va='center',
                       fontsize=12, fontweight='bold',
                       color='white' if val > matrix.max()/2 else 'black')

    ax.set_xlabel('Claimer →', fontsize=12, fontweight='bold')
    ax.set_ylabel('← Issue Creator', fontsize=12, fontweight='bold')
    ax.set_title('Idea Handoff Matrix\n(Row creates issue, Column claims it)',
                fontsize=14, fontweight='bold')

    # Colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Number of Handoffs', fontsize=10)

    # Legend
    legend_text = "\n".join(f"{get_abbrev(p)} = {p}" for p in people)
    ax.text(1.25, 0.5, legend_text, transform=ax.transAxes,
           fontsize=9, va='center',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

    plt.tight_layout()
    output_path = output_dir / 'handoff_matrix.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path}")


def generate_all_handoff_visualizations(metrics: dict, output_dir: Path):
    """Generate all handoff visualization variants."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nGenerating handoff visualizations...")

    create_three_column_flow(metrics, output_dir)
    create_directed_flow_diagram(metrics, output_dir)
    create_alluvial_sankey(metrics, output_dir)
    create_matrix_heatmap(metrics, output_dir)

    print("\nHandoff visualization generation complete!")


if __name__ == '__main__':
    import sys

    base_path = Path(__file__).parent.parent
    metrics_path = sys.argv[1] if len(sys.argv) > 1 else str(base_path / 'output' / 'metrics_data.json')

    print(f"Loading metrics from: {metrics_path}")
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    output_dir = base_path / 'output' / 'visualizations'
    generate_all_handoff_visualizations(metrics, output_dir)
