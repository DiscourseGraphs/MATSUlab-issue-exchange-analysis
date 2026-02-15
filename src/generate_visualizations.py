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
# Helper: collect all issue creation dates
# ────────────────────────────────────────────────
def _collect_issue_dates(metrics: dict):
    """
    Collect creation dates for all 445 issues (claimed experiments + ISS nodes).

    Returns list of dicts with keys: date, claimed (bool), claim_type, creator.
    """
    from datetime import datetime as dt

    issues = []

    # 1. Claimed experiments (from claimed_experiment_list)
    for exp in metrics['metrics']['conversion_rate'].get('claimed_experiment_list', []):
        page_created = exp.get('page_created')
        if page_created is None:
            continue
        if isinstance(page_created, str):
            try:
                page_created = dt.fromisoformat(page_created)
            except (ValueError, TypeError):
                continue
        issues.append({
            'date': page_created,
            'claimed': True,
            'claim_type': exp.get('claim_type', 'unknown'),
            'creator': exp.get('creator') or exp.get('issue_created_by'),
        })

    # 2. ISS nodes (from iss_node_list — includes unclaimed + ISS with activity)
    for iss in metrics.get('iss_node_list', []):
        page_created = iss.get('page_created')
        if page_created is None:
            continue
        if isinstance(page_created, str):
            try:
                page_created = dt.fromisoformat(page_created)
            except (ValueError, TypeError):
                continue
        is_claimed = iss.get('is_claimed', False)
        issues.append({
            'date': page_created,
            'claimed': is_claimed,
            'claim_type': 'iss_activity' if is_claimed else 'unclaimed',
            'creator': iss.get('creator') or iss.get('primary_contributor'),
        })

    issues.sort(key=lambda x: x['date'])
    return issues


def _collect_discourse_node_dates(metrics: dict):
    """
    Collect creation dates for all discourse nodes by type.

    Returns dict: {node_type: [{'date': datetime, 'creator': str}, ...]}
    """
    from datetime import datetime as dt
    from parse_jsonld import parse_date

    result = {}
    graph_growth = metrics.get('graph_growth', {})

    for node_type, nodes in graph_growth.get('nodes_by_type', {}).items():
        dated = []
        for n in nodes:
            created = n.get('created')
            if created is None:
                continue
            if isinstance(created, str):
                try:
                    d = dt.fromisoformat(created.replace('Z', '+00:00'))
                    d = d.replace(tzinfo=None)  # make naive for comparison
                except (ValueError, TypeError):
                    continue
            else:
                d = created
            dated.append({'date': d, 'creator': n.get('creator')})
        dated.sort(key=lambda x: x['date'])
        result[node_type] = dated

    return result


# ────────────────────────────────────────────────
# Figure 0 – Issue Creation Timeline
# ────────────────────────────────────────────────
def _compute_issue_timeline_data(metrics: dict):
    """
    Shared computation for issue timeline figures.
    Returns dict with all_issue_dates, cum_total, cum_claimed,
    pct_of_discourse, pct_of_all_pages, and helper counts.
    """
    from datetime import datetime as dt

    issues = _collect_issue_dates(metrics)
    if not issues:
        return None

    discourse_nodes = _collect_discourse_node_dates(metrics)

    dates_claimed = [i['date'] for i in issues if i['claimed']]
    dates_unclaimed = [i['date'] for i in issues if not i['claimed']]
    all_issue_dates = sorted([i['date'] for i in issues])

    # All discourse node dates (typed nodes only)
    all_discourse_dates = sorted(
        d['date']
        for nodes in discourse_nodes.values()
        for d in nodes
    )

    # All content page dates = discourse nodes + experiment pages
    all_content_dates = list(all_discourse_dates)
    for exp in metrics['metrics']['conversion_rate'].get('claimed_experiment_list', []):
        pc = exp.get('page_created')
        if pc:
            if isinstance(pc, str):
                try:
                    pc = dt.fromisoformat(pc)
                except (ValueError, TypeError):
                    continue
            all_content_dates.append(pc)
    all_content_dates.sort()

    # Also add experiment pages to discourse dates for the "discourse" denominator
    # (since experiments are part of the graph, even if not typed as ISS/RES/etc.)
    all_discourse_plus_exp = list(all_discourse_dates)
    for exp in metrics['metrics']['conversion_rate'].get('claimed_experiment_list', []):
        pc = exp.get('page_created')
        if pc:
            if isinstance(pc, str):
                try:
                    pc = dt.fromisoformat(pc)
                except (ValueError, TypeError):
                    continue
            all_discourse_plus_exp.append(pc)
    all_discourse_plus_exp.sort()

    # Cumulative counts
    cum_total = []
    cum_claimed = []
    claimed_set = sorted(dates_claimed)
    ci = 0
    for i, d in enumerate(all_issue_dates):
        while ci < len(claimed_set) and claimed_set[ci] <= d:
            ci += 1
        cum_total.append(i + 1)
        cum_claimed.append(ci)

    # % of discourse nodes (typed nodes + experiments)
    pct_of_discourse = []
    disc_idx = 0
    for idx, d in enumerate(all_issue_dates):
        while disc_idx < len(all_discourse_plus_exp) and all_discourse_plus_exp[disc_idx] <= d:
            disc_idx += 1
        total_disc = max(disc_idx, 1)
        pct_of_discourse.append(cum_total[idx] / total_disc * 100)

    # % of all content pages (total_content_nodes is final count; approximate growth
    # using all_content_dates which tracks typed+experiment pages we know about)
    pct_of_all_pages = []
    total_content_final = metrics.get('graph_growth', {}).get('total_content_nodes', 0)
    content_idx = 0
    for idx, d in enumerate(all_issue_dates):
        while content_idx < len(all_content_dates) and all_content_dates[content_idx] <= d:
            content_idx += 1
        # Use tracked content pages as lower bound, scale by ratio to known total
        tracked_total = max(content_idx, 1)
        pct_of_all_pages.append(cum_total[idx] / total_content_final * 100
                                if total_content_final > 0
                                else 0)

    return {
        'all_issue_dates': all_issue_dates,
        'cum_total': cum_total,
        'cum_claimed': cum_claimed,
        'dates_claimed': dates_claimed,
        'dates_unclaimed': dates_unclaimed,
        'pct_of_discourse': pct_of_discourse,
        'pct_of_all_pages': pct_of_all_pages,
        'total_content_final': total_content_final,
    }


def create_issue_timeline_figure(metrics: dict, output_dir: Path):
    """
    Standalone figure: cumulative issue count (claimed vs unclaimed)
    with right axis showing % of discourse nodes (max 100%).
    """
    import matplotlib.dates as mdates

    data = _compute_issue_timeline_data(metrics)
    if data is None:
        print("  Skipping fig0: no issue dates available")
        return

    all_issue_dates = data['all_issue_dates']
    cum_total = data['cum_total']
    cum_claimed = data['cum_claimed']
    dates_claimed = data['dates_claimed']
    dates_unclaimed = data['dates_unclaimed']
    pct_of_discourse = data['pct_of_discourse']

    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Fill between for claimed/unclaimed
    ax1.fill_between(all_issue_dates, 0, cum_claimed, step='post',
                     alpha=0.4, color=C_EXPLICIT,
                     label=f'Claimed issues ({len(dates_claimed)})')
    ax1.fill_between(all_issue_dates, cum_claimed, cum_total, step='post',
                     alpha=0.3, color=C_UNCLAIMED,
                     label=f'Unclaimed issues ({len(dates_unclaimed)})')
    ax1.step(all_issue_dates, cum_total, where='post', color='#2c3e50',
             linewidth=1.5, label=f'Total issues ({len(all_issue_dates)})')

    ax1.set_xlabel('Date')
    ax1.set_ylabel('Cumulative Issue Count')
    ax1.set_ylim(0, len(all_issue_dates) * 1.1)

    # Right axis: % of discourse nodes, max 100%
    ax2 = ax1.twinx()
    ax2.plot(all_issue_dates, pct_of_discourse, '--', color=C_ACCENT,
             linewidth=1.2, alpha=0.8, label='% of discourse nodes')
    ax2.set_ylabel('Issues as % of Discourse Nodes', color=C_ACCENT)
    ax2.set_ylim(0, 100)
    ax2.tick_params(axis='y', labelcolor=C_ACCENT)

    # Remove gridlines
    ax1.grid(False)
    ax2.grid(False)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left',
               fontsize=9, framealpha=0.9)

    ax1.set_title('Figure 0. Issue Creation Timeline — MATSUlab Discourse Graph',
                  fontsize=13, fontweight='bold', pad=12)

    # Format x-axis
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    path = output_dir / 'fig0_issue_timeline.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def create_issue_pct_figure(metrics: dict, output_dir: Path):
    """
    Separate figure: issues as % of discourse nodes vs % of all content pages.
    """
    import matplotlib.dates as mdates

    data = _compute_issue_timeline_data(metrics)
    if data is None:
        print("  Skipping fig0_pct: no issue dates available")
        return

    all_issue_dates = data['all_issue_dates']
    pct_of_discourse = data['pct_of_discourse']
    pct_of_all_pages = data['pct_of_all_pages']

    fig, ax = plt.subplots(figsize=(12, 4.5))

    ax.plot(all_issue_dates, pct_of_discourse, '-', color=C_ACCENT,
            linewidth=1.5, label='% of discourse nodes')
    ax.plot(all_issue_dates, pct_of_all_pages, '-', color='#8e44ad',
            linewidth=1.5, label=f'% of all content pages (n={data["total_content_final"]})')

    ax.set_xlabel('Date')
    ax.set_ylabel('Issues as % of Total')
    ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
    ax.grid(False)

    ax.set_title('Figure 0d. Issues as Fraction of Discourse Graph — MATSUlab',
                 fontsize=12, fontweight='bold', pad=12)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    path = output_dir / 'fig0d_issue_pct.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


# ────────────────────────────────────────────────
# Figure 0 – Interactive (Plotly)
# ────────────────────────────────────────────────
def create_issue_timeline_interactive(metrics: dict, output_dir: Path):
    """Plotly interactive version of the issue creation timeline."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    issues = _collect_issue_dates(metrics)
    if not issues:
        print("  Skipping fig0 interactive: no issue dates available")
        return

    discourse_nodes = _collect_discourse_node_dates(metrics)

    all_issue_dates = sorted([i['date'] for i in issues])
    claimed_dates = sorted([i['date'] for i in issues if i['claimed']])
    unclaimed_dates = sorted([i['date'] for i in issues if not i['claimed']])

    # Cumulative totals
    cum_total = list(range(1, len(all_issue_dates) + 1))

    # Cumulative claimed count at each point
    cum_claimed = []
    ci = 0
    for d in all_issue_dates:
        while ci < len(claimed_dates) and claimed_dates[ci] <= d:
            ci += 1
        cum_claimed.append(ci)

    # Discourse node cumulative (for percentage)
    all_disc_dates = sorted(
        d['date']
        for nodes in discourse_nodes.values()
        for d in nodes
    )
    # Include experiment pages
    from datetime import datetime as dt
    for exp in metrics['metrics']['conversion_rate'].get('claimed_experiment_list', []):
        pc = exp.get('page_created')
        if pc:
            if isinstance(pc, str):
                try:
                    pc = dt.fromisoformat(pc)
                except (ValueError, TypeError):
                    continue
            all_disc_dates.append(pc)
    all_disc_dates.sort()

    pct_discourse = []
    pct_all_content = []
    total_content = metrics.get('graph_growth', {}).get('total_content_nodes', 0)
    di = 0
    for idx, d in enumerate(all_issue_dates):
        while di < len(all_disc_dates) and all_disc_dates[di] <= d:
            di += 1
        disc_count = max(di, 1)
        pct_discourse.append(cum_total[idx] / disc_count * 100)
        if total_content > 0:
            pct_all_content.append(cum_total[idx] / total_content * 100)
        else:
            pct_all_content.append(0)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Claimed area
    fig.add_trace(go.Scatter(
        x=all_issue_dates, y=cum_claimed,
        fill='tozeroy', name=f'Claimed ({len(claimed_dates)})',
        line=dict(color=C_EXPLICIT, width=0), fillcolor='rgba(41, 128, 185, 0.4)',
        hovertemplate='%{x|%b %d, %Y}<br>Claimed: %{y}<extra></extra>'
    ), secondary_y=False)

    # Total area (fill between claimed and total = unclaimed)
    fig.add_trace(go.Scatter(
        x=all_issue_dates, y=cum_total,
        fill='tonexty', name=f'Unclaimed ({len(unclaimed_dates)})',
        line=dict(color='#2c3e50', width=1.5), fillcolor='rgba(189, 195, 199, 0.3)',
        hovertemplate='%{x|%b %d, %Y}<br>Total: %{y}<extra></extra>'
    ), secondary_y=False)

    # % of discourse nodes
    fig.add_trace(go.Scatter(
        x=all_issue_dates, y=pct_discourse,
        name='% of discourse nodes',
        line=dict(color=C_ACCENT, width=1.5, dash='dash'),
        hovertemplate='%{x|%b %d, %Y}<br>%{y:.1f}% of discourse nodes<extra></extra>'
    ), secondary_y=True)

    # % of all content pages (hidden by default, toggle)
    fig.add_trace(go.Scatter(
        x=all_issue_dates, y=pct_all_content,
        name='% of all content pages',
        line=dict(color='#9b59b6', width=1.5, dash='dot'),
        visible='legendonly',
        hovertemplate='%{x|%b %d, %Y}<br>%{y:.1f}% of all pages<extra></extra>'
    ), secondary_y=True)

    fig.update_layout(
        title='Figure 0. Issue Creation Timeline — MATSUlab Discourse Graph',
        xaxis_title='Date',
        yaxis_title='Cumulative Issue Count',
        yaxis2_title='Issues as % of Nodes',
        hovermode='x unified',
        template='plotly_white',
        legend=dict(x=0.02, y=0.98),
        width=1000, height=550,
    )

    path = output_dir / 'fig0_issue_timeline.html'
    fig.write_html(str(path), include_plotlyjs='cdn')
    print(f"  Saved: {path}")


# ────────────────────────────────────────────────
# Figure 0b – Creator Attribution Heatmap
# ────────────────────────────────────────────────
def create_issue_creator_heatmap(metrics: dict, output_dir: Path):
    """
    Static heatmap: months × anonymized researchers, cell intensity = issue count.
    """
    import pandas as pd

    issues = _collect_issue_dates(metrics)
    if not issues:
        print("  Skipping fig0b: no issue dates available")
        return

    # Build (month, researcher) pairs
    records = []
    for iss in issues:
        creator = iss.get('creator')
        anon = _normalize_name(creator) if creator else 'Unknown'
        if not anon:
            anon = 'Unknown'
        month_str = iss['date'].strftime('%Y-%m')
        records.append({'month': month_str, 'researcher': anon})

    df = pd.DataFrame(records)
    pivot = df.groupby(['researcher', 'month']).size().unstack(fill_value=0)

    # Sort researchers by total issues (descending)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]

    # Sort months chronologically
    pivot = pivot[sorted(pivot.columns)]

    fig, ax = plt.subplots(figsize=(max(14, len(pivot.columns) * 0.5), max(5, len(pivot) * 0.5)))
    cmap = sns.color_palette("YlOrRd", as_cmap=True)

    sns.heatmap(pivot, ax=ax, cmap=cmap, linewidths=0.5, linecolor='white',
                annot=True, fmt='d', annot_kws={'size': 7},
                cbar_kws={'label': 'Issues Created', 'shrink': 0.7})

    ax.set_xlabel('Month')
    ax.set_ylabel('Researcher')
    ax.set_title('Figure 0b. Issue Creator Attribution — MATSUlab Discourse Graph',
                 fontsize=12, fontweight='bold', pad=12)

    # Rotate x labels
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
    plt.setp(ax.yaxis.get_majorticklabels(), fontsize=9)

    plt.tight_layout()
    path = output_dir / 'fig0b_creator_heatmap.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def create_issue_creator_heatmap_interactive(metrics: dict, output_dir: Path):
    """
    Interactive heatmap with node-type toggles.
    Checkbox toggles for ISS, RES, CLM, HYP, CON, EVD, QUE, plus "All".
    Default = issues only.
    """
    import plotly.graph_objects as go
    import pandas as pd
    from datetime import datetime as dt

    issues = _collect_issue_dates(metrics)
    discourse_nodes = _collect_discourse_node_dates(metrics)

    if not issues and not discourse_nodes:
        print("  Skipping fig0b interactive: no data available")
        return

    # Collect all data by node type
    # "Issues" = claimed experiments + ISS nodes
    all_data = {}

    # Issues (special: combined from experiment list + ISS list)
    issue_records = []
    for iss in issues:
        creator = iss.get('creator')
        anon = _normalize_name(creator) if creator else 'Unknown'
        if not anon:
            anon = 'Unknown'
        month_str = iss['date'].strftime('%Y-%m')
        issue_records.append({'month': month_str, 'researcher': anon})
    all_data['Issues'] = issue_records

    # Discourse node types
    for node_type, nodes in discourse_nodes.items():
        records = []
        for n in nodes:
            creator = n.get('creator')
            anon = _normalize_name(creator) if creator else 'Unknown'
            if not anon:
                anon = 'Unknown'
            month_str = n['date'].strftime('%Y-%m')
            records.append({'month': month_str, 'researcher': anon})
        all_data[node_type] = records

    # Get all researchers and months across all types
    all_researchers = set()
    all_months = set()
    for records in all_data.values():
        for r in records:
            all_researchers.add(r['researcher'])
            all_months.add(r['month'])

    researchers_sorted = sorted(all_researchers)
    months_sorted = sorted(all_months)

    # Build pivot tables for each type
    pivots = {}
    for type_name, records in all_data.items():
        if not records:
            pivots[type_name] = pd.DataFrame(0, index=researchers_sorted, columns=months_sorted)
            continue
        df = pd.DataFrame(records)
        pivot = df.groupby(['researcher', 'month']).size().unstack(fill_value=0)
        pivot = pivot.reindex(index=researchers_sorted, columns=months_sorted, fill_value=0)
        pivots[type_name] = pivot

    # Sort researchers by total issues (descending)
    issue_totals = pivots['Issues'].sum(axis=1).sort_values(ascending=False)
    researchers_sorted = list(issue_totals.index)
    for k in pivots:
        pivots[k] = pivots[k].loc[researchers_sorted]

    # Build Plotly figure with one trace per type
    fig = go.Figure()

    type_names = list(pivots.keys())
    for i, type_name in enumerate(type_names):
        pivot = pivots[type_name]
        visible = True if type_name == 'Issues' else False
        fig.add_trace(go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale='YlOrRd',
            name=type_name,
            visible=visible,
            hovertemplate='%{y}<br>%{x}<br>Count: %{z}<extra>' + type_name + '</extra>',
            colorbar=dict(title='Count'),
        ))

    # Add buttons for each type
    buttons = []
    for i, type_name in enumerate(type_names):
        visibility = [False] * len(type_names)
        visibility[i] = True
        buttons.append(dict(
            label=type_name,
            method='update',
            args=[{'visible': visibility}],
        ))

    # "All" button (sum all types)
    all_pivot = sum(pivots[t] for t in type_names)
    fig.add_trace(go.Heatmap(
        z=all_pivot.values,
        x=all_pivot.columns.tolist(),
        y=all_pivot.index.tolist(),
        colorscale='YlOrRd',
        name='All',
        visible=False,
        hovertemplate='%{y}<br>%{x}<br>Count: %{z}<extra>All types</extra>',
        colorbar=dict(title='Count'),
    ))
    all_visibility = [False] * len(type_names) + [True]
    buttons.append(dict(
        label='All',
        method='update',
        args=[{'visible': all_visibility}],
    ))

    # Update previous buttons to account for the extra "All" trace
    for i in range(len(type_names)):
        buttons[i]['args'][0]['visible'] = buttons[i]['args'][0]['visible'] + [False]

    fig.update_layout(
        title='Figure 0b. Creator Attribution Heatmap — MATSUlab Discourse Graph',
        xaxis_title='Month',
        yaxis_title='Researcher',
        updatemenus=[dict(
            type='buttons',
            direction='right',
            active=0,
            x=0.0,
            y=1.15,
            buttons=buttons,
            showactive=True,
        )],
        yaxis=dict(autorange='reversed'),
        template='plotly_white',
        width=max(900, len(months_sorted) * 28),
        height=max(500, len(researchers_sorted) * 35),
    )

    path = output_dir / 'fig0b_creator_heatmap.html'
    fig.write_html(str(path), include_plotlyjs='cdn')
    print(f"  Saved: {path}")


# ────────────────────────────────────────────────
# Figure 0c – Discourse Node Composition Stacked Area
# ────────────────────────────────────────────────
def create_discourse_growth_figure(metrics: dict, output_dir: Path):
    """
    Stacked area chart showing growth of all discourse node types over time.
    """
    import matplotlib.dates as mdates
    from datetime import datetime as dt

    discourse_nodes = _collect_discourse_node_dates(metrics)
    if not discourse_nodes:
        print("  Skipping fig0c: no discourse node dates available")
        return

    # Also include experiment pages in the total
    exp_dates = []
    for exp in metrics['metrics']['conversion_rate'].get('claimed_experiment_list', []):
        pc = exp.get('page_created')
        if pc:
            if isinstance(pc, str):
                try:
                    pc = dt.fromisoformat(pc)
                except (ValueError, TypeError):
                    continue
            exp_dates.append(pc)
    exp_dates.sort()

    # Collect all dates to build a common timeline
    all_dates = set()
    for nodes in discourse_nodes.values():
        for n in nodes:
            all_dates.add(n['date'])
    for d in exp_dates:
        all_dates.add(d)
    timeline = sorted(all_dates)

    if not timeline:
        print("  Skipping fig0c: no dates available")
        return

    # Merge HYP + CON into a single HYP category
    hyp_nodes = discourse_nodes.get('HYP', []) + discourse_nodes.get('CON', [])
    hyp_nodes.sort(key=lambda n: n['date'])
    discourse_nodes['HYP'] = hyp_nodes
    if 'CON' in discourse_nodes:
        del discourse_nodes['CON']

    # Node type colors — palette E (high-contrast greens, warm/cool separation)
    type_colors = {
        'QUE': '#DAA520',     # goldenrod
        'EVD': '#E8254B',     # crimson red
        'CLM': '#8FBF40',     # bright lime-green
        'HYP': '#1B5E20',     # deep forest green
        'ISS': '#1E88E5',     # bright blue
        'Experiments': '#9E9E9E', # true grey
        'RES': '#C62828',     # deep red crown
    }

    # Display names for legend (HYP includes merged CON)
    display_names = {
        'QUE': 'QUE', 'EVD': 'EVD', 'CLM': 'CLM',
        'HYP': 'HYP+CON', 'ISS': 'ISS',
        'Experiments': 'Experiments', 'RES': 'RES',
    }

    # Stacking order (bottom to top): questions → evidence → claims →
    # hypotheses+conclusions → issues → experiments → results
    type_names = ['QUE', 'EVD', 'CLM', 'HYP', 'ISS', 'Experiments', 'RES']
    type_cum = {t: [] for t in type_names}

    for d in timeline:
        for t in type_names:
            if t == 'Experiments':
                count = sum(1 for ed in exp_dates if ed <= d)
            else:
                nodes = discourse_nodes.get(t, [])
                count = sum(1 for n in nodes if n['date'] <= d)
            type_cum[t].append(count)

    # Stack them for area chart
    fig, ax = plt.subplots(figsize=(12, 6))

    y_stack = np.zeros(len(timeline))
    for t in type_names:
        y_vals = np.array(type_cum[t])
        dn = display_names[t]
        ax.fill_between(timeline, y_stack, y_stack + y_vals,
                        alpha=0.85, label=f'{dn} ({y_vals[-1]})',
                        color=type_colors.get(t, '#95a5a6'))
        y_stack += y_vals

    ax.set_xlabel('Date')
    ax.set_ylabel('Cumulative Node Count')
    ax.set_title('Figure 0c. Discourse Graph Growth by Node Type — MATSUlab',
                 fontsize=12, fontweight='bold', pad=12)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    ax.legend(loc='upper left', fontsize=9, ncol=2, framealpha=0.9)

    plt.tight_layout()
    path = output_dir / 'fig0c_discourse_growth.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


# ────────────────────────────────────────────────
# Figure 0 – Animated GIF
# ────────────────────────────────────────────────
def create_issue_timeline_gif(metrics: dict, output_dir: Path):
    """
    Animated GIF showing cumulative issue creation month by month.
    """
    import matplotlib.dates as mdates
    from datetime import datetime as dt
    from io import BytesIO

    try:
        from PIL import Image
    except ImportError:
        print("  Skipping fig0 GIF: pillow not installed (pip install pillow)")
        return

    issues = _collect_issue_dates(metrics)
    if not issues:
        print("  Skipping fig0 GIF: no issue dates available")
        return

    all_issue_dates = sorted([i['date'] for i in issues])
    claimed_dates = sorted([i['date'] for i in issues if i['claimed']])
    unclaimed_dates = sorted([i['date'] for i in issues if not i['claimed']])

    # Group into months
    from collections import OrderedDict
    months = OrderedDict()
    for d in all_issue_dates:
        key = d.strftime('%Y-%m')
        if key not in months:
            months[key] = {'date': d.replace(day=1), 'claimed': 0, 'unclaimed': 0, 'total': 0}

    for d in claimed_dates:
        key = d.strftime('%Y-%m')
        months[key]['claimed'] += 1
    for d in unclaimed_dates:
        key = d.strftime('%Y-%m')
        months[key]['unclaimed'] += 1
    for key in months:
        months[key]['total'] = months[key]['claimed'] + months[key]['unclaimed']

    month_keys = list(months.keys())
    total_issues = len(all_issue_dates)
    total_claimed = len(claimed_dates)

    # Generate frames
    frames = []
    cum_claimed = 0
    cum_unclaimed = 0
    frame_dates = []
    frame_cum_claimed = []
    frame_cum_total = []

    for i, key in enumerate(month_keys):
        cum_claimed += months[key]['claimed']
        cum_unclaimed += months[key]['unclaimed']
        cum_total = cum_claimed + cum_unclaimed
        frame_dates.append(months[key]['date'])
        frame_cum_claimed.append(cum_claimed)
        frame_cum_total.append(cum_total)

        fig, ax = plt.subplots(figsize=(10, 5.5))

        # Fill areas
        if len(frame_dates) > 1:
            ax.fill_between(frame_dates, 0, frame_cum_claimed, step='post',
                           alpha=0.4, color=C_EXPLICIT)
            ax.fill_between(frame_dates, frame_cum_claimed, frame_cum_total, step='post',
                           alpha=0.3, color=C_UNCLAIMED)
            ax.step(frame_dates, frame_cum_total, where='post', color='#2c3e50', linewidth=1.5)
        else:
            ax.bar(frame_dates, frame_cum_claimed, width=20, color=C_EXPLICIT, alpha=0.4)
            ax.bar(frame_dates, [cum_unclaimed], bottom=frame_cum_claimed, width=20,
                   color=C_UNCLAIMED, alpha=0.3)

        ax.set_xlim(all_issue_dates[0], all_issue_dates[-1])
        ax.set_ylim(0, total_issues * 1.15)
        ax.set_xlabel('Date')
        ax.set_ylabel('Cumulative Issues')
        ax.set_title('Issue Creation Timeline — MATSUlab Discourse Graph',
                     fontsize=12, fontweight='bold')

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        # Counter box
        ax.text(0.98, 0.95, f'{cum_total} issues\n{cum_claimed} claimed',
                transform=ax.transAxes, fontsize=14, fontweight='bold',
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                         edgecolor='#2c3e50', alpha=0.9))

        # Month label
        ax.text(0.02, 0.95, key,
                transform=ax.transAxes, fontsize=12, fontweight='bold',
                verticalalignment='top', color='#7f8c8d')

        plt.tight_layout()

        # Render to PIL Image
        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close(fig)
        buf.seek(0)
        img = Image.open(buf).copy()
        buf.close()
        frames.append(img)

    if not frames:
        print("  Skipping fig0 GIF: no frames generated")
        return

    # Duplicate last frame a few times to pause at end
    for _ in range(5):
        frames.append(frames[-1].copy())

    # Save GIF
    path = output_dir / 'fig0_issue_timeline_animated.gif'
    frames[0].save(
        str(path),
        save_all=True,
        append_images=frames[1:],
        duration=200,  # 200ms per frame
        loop=0,
    )
    print(f"  Saved: {path}")


# ────────────────────────────────────────────────
# Master entry point
# ────────────────────────────────────────────────
def generate_all_visualizations(metrics: dict, output_dir: Path):
    """Generate all visualization outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nGenerating visualizations...")

    # Figure 0: Issue creation timeline (introductory panel for EVD1)
    create_issue_timeline_figure(metrics, output_dir)
    create_issue_pct_figure(metrics, output_dir)
    create_issue_timeline_interactive(metrics, output_dir)
    create_issue_creator_heatmap(metrics, output_dir)
    create_issue_creator_heatmap_interactive(metrics, output_dir)
    create_discourse_growth_figure(metrics, output_dir)
    create_issue_timeline_gif(metrics, output_dir)

    # Figures 1-5: existing metrics visualizations
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
