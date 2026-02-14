#!/usr/bin/env python3
"""
Generate Visualizations for Issue Metrics
==========================================
Creates publication-quality figures summarizing the discourse graph metrics:

Figure 1: Issue Conversion Rate (stacked bar + pie)
Figure 2: Time-to-Claiming and Time-to-First-Result distributions (paired histograms)
Figure 3: Contributor Breadth (bar + cumulative)
Figure 4: Idea Exchange Network (directed graph + heatmap)

Author: Matt Akamatsu (with Claude)
Date: 2026-01-25
"""

import json
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
import seaborn as sns
import networkx as nx
import numpy as np

# --- Style ---
sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams.update({
    'figure.dpi': 150,
    'savefig.dpi': 150,
    'font.family': 'sans-serif',
    'axes.titlesize': 14,
    'axes.titleweight': 'bold',
    'axes.labelsize': 12,
})

# Palette
C_EXPLICIT = '#2980b9'    # blue
C_INFERRED = '#27ae60'    # green
C_ISS_ACT  = '#f39c12'    # amber
C_UNCLAIMED = '#bdc3c7'   # light grey
C_CROSS    = '#8e44ad'    # purple
C_SELF     = '#e67e22'    # orange
C_ACCENT   = '#e74c3c'    # red for mean lines
C_MEDIAN   = '#2ecc71'    # green for median

from anonymize import anonymize_name


def _abbrev(name: str) -> str:
    """Get abbreviation for a researcher name (returns anonymized pseudonym)."""
    if name is None:
        return '?'
    anon = anonymize_name(name)
    return anon if anon else '?'


def _normalize_name(name: str) -> str:
    """Normalize and anonymize researcher names."""
    if name is None:
        return None
    name = name.strip()
    return anonymize_name(name)


# ────────────────────────────────────────────────
# Figure 1 – Conversion Rate
# ────────────────────────────────────────────────
def create_conversion_rate_figure(metrics: dict, output_dir: Path):
    """
    Left panel:  stacked horizontal bar — explicit (blue), inferred (green),
                 ISS with activity (amber), unclaimed ISS (grey)
    Right panel: donut showing self vs cross-person among experiment claims
    """
    conv = metrics['metrics']['conversion_rate']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5),
                                    gridspec_kw={'width_ratios': [1.4, 1]})

    # --- Left: stacked horizontal bar with claim type breakdown ---
    explicit = conv['explicit_claims']
    inferred = conv['inferred_claims']
    iss_act = conv['iss_with_activity']
    unclaimed = conv['unclaimed_iss']
    claimed_total = conv['total_claimed']
    total_issues = conv['total_issues']

    segments = [
        (explicit, C_EXPLICIT, 'Explicitly\nclaimed'),
        (inferred, C_INFERRED, 'Inferred\nclaiming'),
        (iss_act, C_ISS_ACT, 'ISS with\nactivity'),
        (unclaimed, C_UNCLAIMED, 'Unclaimed\nISS'),
    ]

    left = 0
    for val, color, cat in segments:
        if val > 0:
            ax1.barh(0, val, left=left, color=color, edgecolor='white',
                     linewidth=1.5, height=0.5, label=cat)
            if val > 15:
                ax1.text(left + val / 2, 0, str(val),
                         ha='center', va='center', fontweight='bold',
                         fontsize=12, color='white')
            left += val

    # Bracket annotation for claimed portion
    ax1.annotate(f'Claimed: {claimed_total}  ({conv["conversion_rate_percent"]}%)',
                 xy=(claimed_total / 2, -0.35), fontsize=12, fontweight='bold',
                 ha='center', va='top', color='#2c3e50')
    ax1.plot([0, 0, claimed_total, claimed_total],
             [-0.28, -0.31, -0.31, -0.28],
             color='#2c3e50', linewidth=1.5, clip_on=False)

    ax1.set_xlim(0, total_issues)
    ax1.set_ylim(-0.6, 0.6)
    ax1.set_yticks([])
    ax1.set_xlabel('Number of Issues')
    ax1.set_title('Issue Conversion Rate')
    ax1.legend(loc='upper right', fontsize=9, framealpha=0.9)
    ax1.spines['left'].set_visible(False)

    # --- Right: donut of self vs cross-person ---
    # Use experiment claims with known creator-claimer pairs
    known_claims = conv['self_claims'] + conv['cross_person_claims']
    sizes = [conv['self_claims'], conv['cross_person_claims']]
    labels_pie = [f'Self-claiming\n({conv["self_claims"]})',
                  f'Cross-person\nclaiming ({conv["cross_person_claims"]})']
    colors_pie = [C_SELF, C_CROSS]

    wedges, texts, autotexts = ax2.pie(
        sizes, labels=labels_pie, colors=colors_pie,
        autopct='%1.0f%%', startangle=90,
        pctdistance=0.75, labeldistance=1.18,
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2),
        textprops={'fontsize': 10},
    )
    for at in autotexts:
        at.set_fontweight('bold')
        at.set_fontsize(11)

    ax2.set_title(f'Claiming Authorship\n(among {known_claims} claimed experiments)')

    plt.tight_layout()
    path = output_dir / 'fig1_conversion_rate.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


# ────────────────────────────────────────────────
# Figure 2 – Time distributions
# ────────────────────────────────────────────────
def create_time_distributions_figure(metrics: dict, output_dir: Path):
    """
    Top panel:  Time-to-Claiming histogram (log-ish bins, plus inset of 0-day spike)
    Bottom panel: Time-to-First-Result histogram
    """
    ttc = metrics['metrics']['time_to_claim']
    ttr = metrics['metrics']['time_to_first_result']

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    # --- Top: Time-to-Claiming ---
    if ttc['count'] > 0:
        days_claim = [d['days_to_claim'] for d in ttc['details']]

        # Use custom bins: 0 gets its own bin, then 1-7, 8-30, 31-90, 91-180, 180+
        bin_edges = [0, 1, 7, 30, 90, 180, max(days_claim) + 1]
        bin_labels = ['0', '1-7', '8-30', '31-90', '91-180', '180+']

        counts_binned = []
        for i in range(len(bin_edges) - 1):
            lo, hi = bin_edges[i], bin_edges[i + 1]
            if i == 0:
                c = sum(1 for d in days_claim if d == 0)
            else:
                c = sum(1 for d in days_claim if lo <= d < hi)
            counts_binned.append(c)

        x_pos = range(len(bin_labels))
        bars = ax1.bar(x_pos, counts_binned, color=C_EXPLICIT, edgecolor='white',
                       linewidth=1.2, width=0.7)

        # Value labels
        for bar, val in zip(bars, counts_binned):
            if val > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                         str(val), ha='center', va='bottom', fontsize=10, fontweight='bold')

        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(bin_labels)
        ax1.set_xlabel('Days from Issue Creation to Claiming')
        ax1.set_ylabel('Number of Experiments')
        ax1.set_title(f'Time-to-Claiming Distribution  (n={ttc["count"]},  '
                      f'median={ttc["median_days"]}d,  mean={ttc["avg_days"]}d)')

        # Annotation for 0-day dominance
        zero_pct = counts_binned[0] / sum(counts_binned) * 100
        ax1.annotate(f'{zero_pct:.0f}% claimed\non same day',
                     xy=(0, counts_binned[0]), xytext=(1.5, counts_binned[0] * 0.85),
                     fontsize=10, ha='center',
                     arrowprops=dict(arrowstyle='->', color='#555'),
                     bbox=dict(boxstyle='round,pad=0.3', fc='#ffffcc', alpha=0.9))

    # --- Bottom: Time-to-First-Result ---
    if ttr['count'] > 0:
        days_result = [d['days_to_first_result'] for d in ttr['details']]

        # Filter out negative (just 1 case at -1)
        days_result_clean = [d for d in days_result if d >= 0]

        bin_edges_r = [0, 30, 60, 90, 120, 180, 365, max(max(days_result_clean), 366) + 1]
        bin_labels_r = ['0-29', '30-59', '60-89', '90-119', '120-179', '180-364', '365+']

        counts_r = []
        for i in range(len(bin_edges_r) - 1):
            lo, hi = bin_edges_r[i], bin_edges_r[i + 1]
            c = sum(1 for d in days_result_clean if lo <= d < hi)
            counts_r.append(c)

        x_pos_r = range(len(bin_labels_r))
        bars_r = ax2.bar(x_pos_r, counts_r, color=C_CROSS, edgecolor='white',
                         linewidth=1.2, width=0.7)

        for bar, val in zip(bars_r, counts_r):
            if val > 0:
                ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                         str(val), ha='center', va='bottom', fontsize=10, fontweight='bold')

        ax2.set_xticks(x_pos_r)
        ax2.set_xticklabels(bin_labels_r)
        ax2.set_xlabel('Days from Claiming to First Result')
        ax2.set_ylabel('Number of Experiments')
        ax2.set_title(f'Time-to-First-Result Distribution  (n={ttr["count"]},  '
                      f'mean={ttr["avg_days"]}d)')

        # Mean line
        mean_r = ttr['avg_days']
        # Find which bin the mean falls in for visual reference
        ax2.axvline(x=_val_to_bin_pos(mean_r, bin_edges_r), color=C_ACCENT,
                    linestyle='--', linewidth=2, label=f'Mean: {mean_r}d')
        ax2.legend(loc='upper right', fontsize=10)

    plt.tight_layout(h_pad=3)
    path = output_dir / 'fig2_time_distributions.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def _val_to_bin_pos(val, bin_edges):
    """Map a continuous value to the bar-chart x position."""
    for i in range(len(bin_edges) - 1):
        if val < bin_edges[i + 1]:
            # Interpolate within the bin
            frac = (val - bin_edges[i]) / (bin_edges[i + 1] - bin_edges[i])
            return i + frac
    return len(bin_edges) - 2


# ────────────────────────────────────────────────
# Figure 3 – Contributor Breadth
# ────────────────────────────────────────────────
def create_contributor_breadth_figure(metrics: dict, output_dir: Path):
    """
    Left panel:  bar chart of contributor count distribution
    Right panel: per-person summary (issues created, claims made, results authored)
    """
    cont = metrics['metrics']['unique_contributors']
    conv = metrics['metrics']['conversion_rate']
    xp = metrics['metrics']['cross_person_claims']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5),
                                    gridspec_kw={'width_ratios': [1, 1.3]})

    # --- Left: distribution bar ---
    if cont['experiments_analyzed'] > 0:
        dist = cont['distribution']
        x_vals = sorted(int(k) for k in dist.keys())
        y_vals = [dist[str(k)] if isinstance(dist, dict) and str(k) in dist
                  else dist.get(k, 0) for k in x_vals]

        bar_colors = [C_UNCLAIMED if x == 1 else C_INFERRED for x in x_vals]
        bars = ax1.bar(x_vals, y_vals, color=bar_colors, edgecolor='white',
                       linewidth=1.5, width=0.6)

        for bar, val in zip(bars, y_vals):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                     str(val), ha='center', va='bottom', fontsize=12, fontweight='bold')

        ax1.set_xlabel('Unique Contributors per Experiment')
        ax1.set_ylabel('Number of Experiments')
        ax1.set_xticks(x_vals)
        ax1.set_title(f'Contributor Breadth\n(avg {cont["avg_contributors"]} per experiment)')

        single_pct = cont['single_contributor_count'] / cont['experiments_analyzed'] * 100
        multi_pct = cont['multi_contributor_count'] / cont['experiments_analyzed'] * 100
        ax1.annotate(f'{single_pct:.0f}% single person', xy=(1, y_vals[0]),
                     xytext=(1.6, y_vals[0] * 0.7), fontsize=10,
                     arrowprops=dict(arrowstyle='->', color='#555'),
                     bbox=dict(boxstyle='round,pad=0.3', fc='#ffffcc', alpha=0.9))

        single_patch = mpatches.Patch(color=C_UNCLAIMED, label='Single contributor')
        multi_patch = mpatches.Patch(color=C_INFERRED, label='Multiple contributors')
        ax1.legend(handles=[single_patch, multi_patch], loc='upper right', fontsize=9)

    # --- Right: per-person activity summary ---
    # Count per-person roles
    person_roles = defaultdict(lambda: {'issues_created': 0, 'times_claimed': 0, 'self_claimed': 0, 'cross_claimed': 0})

    # From cross-person details
    for cp in xp.get('cross_person_details', []):
        creator = _normalize_name(cp.get('issue_created_by'))
        claimer = _normalize_name(cp.get('claimed_by'))
        if creator:
            person_roles[creator]['issues_created'] += 1
        if claimer:
            person_roles[claimer]['cross_claimed'] += 1
            person_roles[claimer]['times_claimed'] += 1

    # From self-claiming details
    for sc in xp.get('self_claim_details', []):
        person = _normalize_name(sc.get('person'))
        if person:
            person_roles[person]['self_claimed'] += 1
            person_roles[person]['times_claimed'] += 1

    # Sort by total activity
    people = sorted(person_roles.keys(),
                    key=lambda p: -(person_roles[p]['times_claimed'] + person_roles[p]['issues_created']))

    if people:
        y_pos = np.arange(len(people))
        iss_created = [person_roles[p]['issues_created'] for p in people]
        self_c = [person_roles[p]['self_claimed'] for p in people]
        cross_c = [person_roles[p]['cross_claimed'] for p in people]

        ax2.barh(y_pos, self_c, height=0.5, color=C_SELF, edgecolor='white',
                 linewidth=1, label='Self-claimed')
        ax2.barh(y_pos, cross_c, height=0.5, left=self_c, color=C_CROSS,
                 edgecolor='white', linewidth=1, label='Claimed by another')
        ax2.barh(y_pos, iss_created, height=0.5,
                 left=[s + c for s, c in zip(self_c, cross_c)],
                 color=C_EXPLICIT, edgecolor='white', linewidth=1,
                 label='Issues created (claimed by others)')

        ax2.set_yticks(y_pos)
        ax2.set_yticklabels([_abbrev(p) for p in people], fontsize=10)
        ax2.set_xlabel('Count')
        ax2.set_title('Per-Researcher Activity')
        ax2.legend(loc='lower right', fontsize=8, framealpha=0.9)
        ax2.invert_yaxis()

    plt.tight_layout()
    path = output_dir / 'fig3_contributor_breadth.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


# ────────────────────────────────────────────────
# Figure 4 – Idea Exchange
# ────────────────────────────────────────────────
def create_idea_exchange_figure(metrics: dict, output_dir: Path):
    """
    Left panel:  directed network graph (creator → claimer)
    Right panel: heatmap matrix (rows = creators, cols = claimers)
    """
    xp = metrics['metrics']['cross_person_claims']

    if not xp.get('exchange_pairs'):
        print("  Skipping idea exchange figure (no exchange pairs)")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7),
                                    gridspec_kw={'width_ratios': [1.2, 1]})

    # --- Left: directed network ---
    G = nx.DiGraph()

    for pair in xp['exchange_pairs']:
        src = _normalize_name(pair['from'])
        dst = _normalize_name(pair['to'])
        G.add_edge(src, dst, weight=pair['count'])

    # Also add self-claimers as isolated context
    self_counts = Counter()
    for claim in xp.get('self_claim_details', []):
        p = _normalize_name(claim.get('person'))
        if p:
            self_counts[p] += 1
            if p not in G:
                G.add_node(p)

    pos = nx.spring_layout(G, k=2.5, iterations=80, seed=42)

    # Node sizing: out-degree (ideas given) + in-degree (ideas received) + self-claims
    node_sizes = []
    node_colors = []
    for node in G.nodes():
        out_d = G.out_degree(node, weight='weight')
        in_d = G.in_degree(node, weight='weight')
        sc = self_counts.get(node, 0)
        node_sizes.append(400 + (out_d + in_d + sc) * 80)

        # Color: net creator = green, net claimer = purple
        if out_d > in_d:
            node_colors.append(C_INFERRED)
        elif in_d > out_d:
            node_colors.append(C_CROSS)
        else:
            node_colors.append(C_EXPLICIT)

    nx.draw_networkx_nodes(G, pos, ax=ax1, node_size=node_sizes,
                           node_color=node_colors, edgecolors='#2c3e50',
                           linewidths=1.5, alpha=0.85)

    # Edges: width ∝ count
    edge_weights = [G[u][v]['weight'] for u, v in G.edges()]
    max_w = max(edge_weights) if edge_weights else 1
    widths = [1.5 + (w / max_w) * 4.5 for w in edge_weights]

    nx.draw_networkx_edges(G, pos, ax=ax1, width=widths, alpha=0.55,
                           edge_color='#555', arrows=True, arrowsize=18,
                           connectionstyle='arc3,rad=0.15',
                           min_source_margin=15, min_target_margin=15)

    # Labels (abbreviations)
    labels = {n: _abbrev(n) for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, ax=ax1, font_size=10,
                            font_weight='bold')

    # Edge labels
    edge_labels = {(u, v): str(d['weight']) for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels, ax=ax1, font_size=9,
                                 font_color='#333', bbox=dict(alpha=0))

    ax1.set_title('Idea Exchange Network\n(arrow: creator → person claiming)')
    creator_patch = mpatches.Patch(color=C_INFERRED, label='Net idea creator')
    claimer_patch = mpatches.Patch(color=C_CROSS, label='Net idea recipient')
    ax1.legend(handles=[creator_patch, claimer_patch], loc='lower left', fontsize=9)
    ax1.axis('off')

    # --- Right: heatmap ---
    all_people = sorted(set(
        [_normalize_name(p['from']) for p in xp['exchange_pairs']] +
        [_normalize_name(p['to']) for p in xp['exchange_pairs']]
    ))
    n = len(all_people)
    matrix = np.zeros((n, n))
    for pair in xp['exchange_pairs']:
        i = all_people.index(_normalize_name(pair['from']))
        j = all_people.index(_normalize_name(pair['to']))
        matrix[i, j] = pair['count']

    abbrevs = [_abbrev(p) for p in all_people]

    im = ax2.imshow(matrix, cmap='Purples', aspect='auto', vmin=0)
    ax2.set_xticks(range(n))
    ax2.set_yticks(range(n))
    ax2.set_xticklabels(abbrevs, fontsize=10, fontweight='bold')
    ax2.set_yticklabels(abbrevs, fontsize=10, fontweight='bold')

    # Annotations in cells
    for i in range(n):
        for j in range(n):
            val = int(matrix[i, j])
            if val > 0:
                ax2.text(j, i, str(val), ha='center', va='center',
                         fontsize=12, fontweight='bold',
                         color='white' if val >= matrix.max() * 0.6 else 'black')

    ax2.set_xlabel('Claimed By  →', fontweight='bold')
    ax2.set_ylabel('← Issue Creator', fontweight='bold')
    ax2.set_title('Handoff Matrix\n(row creates issue, column claims it)')

    cbar = plt.colorbar(im, ax=ax2, shrink=0.7, pad=0.04)
    cbar.set_label('Count', fontsize=10)

    # Full-name legend under heatmap
    legend_lines = [f"{_abbrev(p)} = {p}" for p in all_people]
    ax2.text(0.5, -0.18, '   |   '.join(legend_lines),
             transform=ax2.transAxes, fontsize=8, ha='center', va='top',
             style='italic', color='#555')

    plt.tight_layout()
    path = output_dir / 'fig4_idea_exchange.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


# ────────────────────────────────────────────────
# Figure 5 – Issue → Experiment → Result Funnel
# ────────────────────────────────────────────────
def create_funnel_figure(metrics: dict, output_dir: Path):
    """
    Left panel:  funnel bar chart showing attrition at each stage
    Right panel: stage-to-stage conversion rates with annotations
    """
    conv = metrics['metrics']['conversion_rate']
    ttr = metrics['metrics']['time_to_first_result']

    total_issues = conv['total_issues']
    total_claimed = conv['total_claimed']
    with_results = ttr['count']
    total_linked_res = sum(d['total_linked_res'] for d in ttr['details'])

    # Breakdown of claimed
    explicit = conv['explicit_claims']
    inferred = conv['inferred_claims']
    iss_act = conv['iss_with_activity']
    no_results = total_claimed - with_results

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6),
                                    gridspec_kw={'width_ratios': [1, 1]})

    # --- Left: funnel bars ---
    stages = ['All Issues\n(ISS + Experiments)', 'Claimed', 'Produced\nResults']
    values = [total_issues, total_claimed, with_results]
    colors_funnel = ['#95a5a6', C_EXPLICIT, C_CROSS]

    bars = ax1.barh(range(len(stages)), values, color=colors_funnel,
                    edgecolor='white', linewidth=2, height=0.55)

    # Value + percentage labels
    for i, (bar, val) in enumerate(zip(bars, values)):
        pct = val / total_issues * 100
        label = f'{val}  ({pct:.0f}%)' if i > 0 else str(val)
        ax1.text(val + 5, bar.get_y() + bar.get_height() / 2,
                 label, va='center', fontsize=12, fontweight='bold')

    # Arrows between stages showing attrition
    for i in range(len(stages) - 1):
        drop = values[i] - values[i + 1]
        pct_pass = values[i + 1] / values[i] * 100
        mid_y = i + 0.5
        ax1.annotate(f'→ {pct_pass:.0f}% pass',
                     xy=(min(values[i], values[i + 1]) / 2, mid_y),
                     fontsize=10, ha='center', va='center', color='#555',
                     bbox=dict(boxstyle='round,pad=0.2', fc='#ffffcc', alpha=0.9))

    ax1.set_yticks(range(len(stages)))
    ax1.set_yticklabels(stages, fontsize=11)
    ax1.set_xlabel('Count')
    ax1.set_title('Issue → Experiment → Result Funnel')
    ax1.invert_yaxis()
    ax1.set_xlim(0, total_issues * 1.2)
    ax1.spines['right'].set_visible(False)
    ax1.spines['top'].set_visible(False)

    # --- Right: detailed breakdown at each stage ---
    # Three grouped bars showing composition
    y_positions = [0, 1.2, 2.4, 3.6]
    bar_height = 0.35

    # Row 0: Unclaimed vs Claimed
    ax2.barh(y_positions[0], conv['unclaimed_iss'], height=bar_height,
             color=C_UNCLAIMED, edgecolor='white', linewidth=1)
    ax2.barh(y_positions[0], total_claimed, height=bar_height,
             left=conv['unclaimed_iss'], color=C_EXPLICIT, edgecolor='white', linewidth=1)
    ax2.text(conv['unclaimed_iss'] / 2, y_positions[0], f'{conv["unclaimed_iss"]}\nunclaimed',
             ha='center', va='center', fontsize=8, color='#555')
    ax2.text(conv['unclaimed_iss'] + total_claimed / 2, y_positions[0],
             f'{total_claimed}\nclaimed', ha='center', va='center', fontsize=8, color='white', fontweight='bold')

    # Row 1: Claim type breakdown
    left = 0
    for val, color, label in [
        (explicit, C_EXPLICIT, f'{explicit}\nexplicit'),
        (inferred, C_INFERRED, f'{inferred}\ninferred'),
        (iss_act, C_ISS_ACT, f'{iss_act}\nISS'),
    ]:
        ax2.barh(y_positions[1], val, height=bar_height, left=left,
                 color=color, edgecolor='white', linewidth=1)
        if val > 15:
            ax2.text(left + val / 2, y_positions[1], label,
                     ha='center', va='center', fontsize=8, color='white', fontweight='bold')
        left += val

    # Row 2: Results vs No Results (among claimed)
    ax2.barh(y_positions[2], no_results, height=bar_height,
             color='#d5d8dc', edgecolor='white', linewidth=1)
    ax2.barh(y_positions[2], with_results, height=bar_height,
             left=no_results, color=C_CROSS, edgecolor='white', linewidth=1)
    ax2.text(no_results / 2, y_positions[2], f'{no_results}\nno results yet',
             ha='center', va='center', fontsize=8, color='#555')
    ax2.text(no_results + with_results / 2, y_positions[2],
             f'{with_results}\nwith results', ha='center', va='center', fontsize=8,
             color='white', fontweight='bold')

    # Row 3: Result productivity
    avg_res = total_linked_res / with_results if with_results > 0 else 0
    ax2.barh(y_positions[3], total_linked_res, height=bar_height,
             color=C_CROSS, edgecolor='white', linewidth=1, alpha=0.7)
    ax2.text(total_linked_res / 2, y_positions[3],
             f'{total_linked_res} total RES nodes\n(avg {avg_res:.1f} per experiment)',
             ha='center', va='center', fontsize=8, fontweight='bold', color='white')

    row_labels = [
        'All issues',
        'Claiming method\nbreakdown',
        'Result\nproduction',
        'Total results\nproduced',
    ]
    ax2.set_yticks(y_positions)
    ax2.set_yticklabels(row_labels, fontsize=10)
    ax2.set_xlabel('Count')
    ax2.set_title('Stage-by-Stage Breakdown')
    ax2.invert_yaxis()
    ax2.spines['right'].set_visible(False)
    ax2.spines['top'].set_visible(False)

    plt.tight_layout()
    path = output_dir / 'fig5_funnel.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


# ────────────────────────────────────────────────
# Master entry point
# ────────────────────────────────────────────────
def generate_all_visualizations(metrics: dict, output_dir: Path):
    """Generate all visualization outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nGenerating visualizations...")

    create_conversion_rate_figure(metrics, output_dir)
    create_time_distributions_figure(metrics, output_dir)
    create_contributor_breadth_figure(metrics, output_dir)
    create_idea_exchange_figure(metrics, output_dir)
    create_funnel_figure(metrics, output_dir)

    print("\nVisualization generation complete!")


if __name__ == '__main__':
    import sys

    # Load metrics from file
    base_path = Path(__file__).parent.parent
    metrics_path = sys.argv[1] if len(sys.argv) > 1 else str(base_path / 'output' / 'metrics_data.json')

    print(f"Loading metrics from: {metrics_path}")
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    output_dir = base_path / 'output' / 'visualizations'
    generate_all_visualizations(metrics, output_dir)
