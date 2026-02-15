#!/usr/bin/env python3
"""
Experiment Lifecycle Visualizations (Fig 6 Series)
====================================================
Visualizes the progression from issue creation to claiming to result production:

Fig 6a: Time-to-Result Histogram (log-scale bins with rug plot)
Fig 6b: CDF of time-to-first-result (static + interactive Plotly)
Fig 6c: Swimmer plot — experiment lifecycle lanes (interactive Plotly)
Fig 6d: Raincloud plot — time-to-claim vs time-to-result
Fig 6e: Result yield bubble chart (static + interactive)
Fig 6f: Kaplan-Meier survival curve (time until first result)
Fig 6g: Result cascade — timing of all results for multi-result experiments

Author: Matt Akamatsu (with Claude)
Date: 2026-02-14
"""

from datetime import datetime
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns

from anonymize import anonymize_name

# --- Shared palette (matching generate_visualizations.py) ---
C_EXPLICIT  = '#2980b9'    # blue
C_INFERRED  = '#27ae60'    # green
C_CROSS     = '#8e44ad'    # purple
C_SELF      = '#e67e22'    # orange
C_ACCENT    = '#e74c3c'    # red for mean lines
C_MEDIAN    = '#2ecc71'    # green for median
C_UNCLAIMED = '#bdc3c7'    # light grey

# Researcher color palette for multi-researcher views
RESEARCHER_COLORS = [
    '#1E88E5', '#43A047', '#FB8C00', '#8E24AA',
    '#E53935', '#00ACC1', '#6D4C41', '#D81B60',
    '#FDD835', '#546E7A', '#7CB342',
]


def _abbrev(name: str) -> str:
    if name is None:
        return '?'
    anon = anonymize_name(name)
    return anon if anon else '?'


def _get_researcher_color_map(names: list[str]) -> dict:
    """Build a consistent name → color mapping."""
    unique = sorted(set(n for n in names if n))
    cmap = {}
    for i, name in enumerate(unique):
        cmap[name] = RESEARCHER_COLORS[i % len(RESEARCHER_COLORS)]
    return cmap


# ─────────────────────────────────────────────────────────────
# Fig 6a — Time-to-Result Histogram
# ─────────────────────────────────────────────────────────────
def create_time_to_result_histogram(metrics: dict, output_dir: Path):
    """
    Log-scale-binned histogram of days-to-first-result (n=50)
    with rug plot, quartile markers, and callouts.
    """
    ttr = metrics['metrics']['time_to_first_result']
    if ttr['count'] == 0:
        return

    details = ttr['details']
    days = [d['days_to_first_result'] for d in details]

    # Separate negatives (RES predates formal claim)
    neg_days = [d for d in days if d < 0]
    pos_days = [d for d in days if d >= 0]

    # Custom bins on the positive side
    bin_edges = [0, 1, 8, 31, 91, 181, 366, max(max(pos_days), 366) + 1]
    bin_labels = ['0\n(same day)', '1–7', '8–30', '31–90', '91–180', '181–365', '366+']

    counts = []
    for i in range(len(bin_edges) - 1):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        if i == 0:
            c = sum(1 for d in pos_days if d == 0)
        else:
            c = sum(1 for d in pos_days if lo <= d < hi)
        counts.append(c)

    fig, ax = plt.subplots(figsize=(11, 5.5))

    x_pos = np.arange(len(bin_labels))
    bars = ax.bar(x_pos, counts, color=C_CROSS, edgecolor='white',
                  linewidth=1.2, width=0.7, alpha=0.85, zorder=3)

    # Value labels on bars
    for bar, val in zip(bars, counts):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                    str(val), ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax.set_xticks(x_pos)
    ax.set_xticklabels(bin_labels, fontsize=10)
    ax.set_xlabel('Days from Claiming to First Result', fontsize=12)
    ax.set_ylabel('Number of Experiments', fontsize=12)

    # Compute stats
    q25 = int(np.percentile(pos_days, 25))
    q50 = int(np.percentile(pos_days, 50))
    q75 = int(np.percentile(pos_days, 75))
    mean_d = round(np.mean(pos_days), 1)

    ax.set_title(
        f'Time-to-First-Result Distribution  (n={len(pos_days)},  '
        f'median={q50}d,  mean={mean_d}d,  IQR={q25}–{q75}d)',
        fontsize=13, fontweight='bold',
    )

    # Rug plot along the bottom
    rug_y = -0.6
    for d in pos_days:
        # Map day value to bar position
        bpos = _day_to_bar_pos(d, bin_edges)
        ax.plot(bpos, rug_y, '|', color=C_CROSS, markersize=8, alpha=0.6,
                markeredgewidth=1.5, zorder=5, clip_on=False)

    # Same-day callout
    zero_count = counts[0]
    if zero_count > 0:
        zero_pct = zero_count / len(pos_days) * 100
        ax.annotate(
            f'{zero_count} experiments ({zero_pct:.0f}%)\nproduced a result\non the same day',
            xy=(0, zero_count), xytext=(2.0, zero_count * 0.92),
            fontsize=9.5, ha='center',
            arrowprops=dict(arrowstyle='->', color='#555', lw=1.2),
            bbox=dict(boxstyle='round,pad=0.3', fc='#ffffcc', alpha=0.9),
        )

    # Negative-value callout
    if neg_days:
        ax.annotate(
            f'{len(neg_days)} experiment(s) have negative\ntime (result predates formal claim)',
            xy=(0, 0), xytext=(4.5, max(counts) * 0.65),
            fontsize=9, ha='center', color='#666',
            bbox=dict(boxstyle='round,pad=0.3', fc='#f0f0f0', alpha=0.9),
        )

    ax.set_ylim(bottom=-1.5)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    path = output_dir / 'fig6a_time_to_result_histogram.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def _day_to_bar_pos(day_val: int, bin_edges: list) -> float:
    """Map a day value to the approximate bar x-position (0-indexed)."""
    for i in range(len(bin_edges) - 1):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        if i == 0 and day_val == 0:
            return 0.0
        elif lo <= day_val < hi:
            frac = (day_val - lo) / (hi - lo) if hi > lo else 0
            return i + frac * 0.6 - 0.3  # jitter within bar
    return len(bin_edges) - 2


# ─────────────────────────────────────────────────────────────
# Fig 6b — CDF
# ─────────────────────────────────────────────────────────────
def create_time_to_result_cdf(metrics: dict, output_dir: Path):
    """
    Empirical CDF of time-to-first-result with quartile annotations.
    Static matplotlib version.
    """
    ttr = metrics['metrics']['time_to_first_result']
    if ttr['count'] == 0:
        return

    details = ttr['details']
    days = sorted([d['days_to_first_result'] for d in details])
    n = len(days)
    ecdf_y = np.arange(1, n + 1) / n

    fig, ax = plt.subplots(figsize=(10, 6))

    # Step function
    ax.step(days, ecdf_y, where='post', color=C_CROSS, linewidth=2.5, zorder=4)
    ax.fill_between(days, ecdf_y, step='post', alpha=0.1, color=C_CROSS, zorder=2)

    # Color dots by claim type (self vs cross)
    for i, det in enumerate(sorted(details, key=lambda x: x['days_to_first_result'])):
        d_val = det['days_to_first_result']
        # Determine if cross-person: check if experiment_title is in cross_person list
        claimer = _abbrev(det.get('claimed_by', ''))
        # We'll mark based on whether first_res_creator differs from claimed_by
        is_cross = (det.get('first_res_primary_contributor', '') !=
                    det.get('claimed_by', '') and
                    det.get('first_res_primary_contributor', ''))
        color = C_CROSS if is_cross else C_SELF
        ax.scatter(d_val, (i + 1) / n, color=color, s=25, zorder=5,
                   edgecolors='white', linewidths=0.5)

    # Quartile drop-lines
    for frac, label_prefix in [(0.25, '25%'), (0.50, '50%'), (0.75, '75%')]:
        idx = int(np.ceil(frac * n)) - 1
        q_day = days[idx]
        ax.axhline(y=frac, color='grey', linestyle=':', linewidth=0.8, alpha=0.5)
        ax.plot([q_day, q_day], [0, frac], color='grey', linestyle=':', linewidth=0.8, alpha=0.5)
        ax.annotate(
            f'{label_prefix} by day {q_day}',
            xy=(q_day, frac), xytext=(q_day + 30, frac + 0.05),
            fontsize=9, color='#444',
            arrowprops=dict(arrowstyle='->', color='#888', lw=0.8),
        )

    # Legend
    handles = [
        mpatches.Patch(color=C_SELF, label='Self-claimed'),
        mpatches.Patch(color=C_CROSS, label='Cross-person'),
    ]
    ax.legend(handles=handles, loc='lower right', fontsize=10)

    ax.set_xlabel('Days from Claiming to First Result', fontsize=12)
    ax.set_ylabel('Cumulative Fraction of Experiments', fontsize=12)
    ax.set_title(f'CDF: Time to First Result  (n={n})', fontsize=13, fontweight='bold')
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlim(min(days) - 10, max(days) + 30)
    ax.grid(axis='both', alpha=0.3)

    # Stats inset
    mean_d = round(np.mean(days), 1)
    median_d = int(np.median(days))
    stats_text = f'n = {n}\nMedian = {median_d}d\nMean = {mean_d}d'
    ax.text(0.98, 0.3, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.4', fc='white', alpha=0.9, ec='#ccc'))

    plt.tight_layout()
    path = output_dir / 'fig6b_time_to_result_cdf.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def create_time_to_result_cdf_interactive(metrics: dict, output_dir: Path):
    """Interactive Plotly CDF with hover showing experiment details."""
    import plotly.graph_objects as go

    ttr = metrics['metrics']['time_to_first_result']
    if ttr['count'] == 0:
        return

    details = sorted(ttr['details'], key=lambda x: x['days_to_first_result'])
    n = len(details)
    days = [d['days_to_first_result'] for d in details]
    ecdf_y = [(i + 1) / n for i in range(n)]

    hover_texts = []
    for det in details:
        title = det['experiment_title'][:60]
        claimer = _abbrev(det.get('claimed_by', ''))
        d = det['days_to_first_result']
        total = det.get('total_linked_res', 1)
        hover_texts.append(
            f"<b>{title}</b><br>"
            f"Days to result: {d}<br>"
            f"Claimed by: {claimer}<br>"
            f"Total results: {total}"
        )

    fig = go.Figure()

    # CDF step line
    fig.add_trace(go.Scatter(
        x=days, y=ecdf_y,
        mode='lines+markers',
        line=dict(shape='hv', color=C_CROSS, width=2),
        marker=dict(size=6, color=C_CROSS),
        text=hover_texts,
        hoverinfo='text',
        name='CDF',
    ))

    # Quartile annotations
    for frac in [0.25, 0.50, 0.75]:
        idx = int(np.ceil(frac * n)) - 1
        q_day = days[idx]
        fig.add_hline(y=frac, line_dash='dot', line_color='grey', opacity=0.4)
        fig.add_annotation(
            x=q_day, y=frac,
            text=f'{int(frac*100)}% by day {q_day}',
            showarrow=True, arrowhead=2,
            font=dict(size=11),
        )

    fig.update_layout(
        title=f'CDF: Time to First Result (n={n})',
        xaxis_title='Days from Claiming to First Result',
        yaxis_title='Cumulative Fraction',
        yaxis=dict(range=[-0.02, 1.05]),
        template='plotly_white',
        width=900, height=550,
        # Add log-scale toggle via updatemenus
        updatemenus=[dict(
            type='buttons',
            direction='left',
            x=0.0, y=1.12,
            buttons=[
                dict(label='Linear', method='relayout',
                     args=[{'xaxis.type': 'linear'}]),
                dict(label='Log', method='relayout',
                     args=[{'xaxis.type': 'log'}]),
            ],
        )],
    )

    path = output_dir / 'fig6b_time_to_result_cdf.html'
    fig.write_html(str(path), include_plotlyjs='cdn')
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────
# Fig 6c — Swimmer Plot
# ─────────────────────────────────────────────────────────────
def create_swimmer_plot(metrics: dict, output_dir: Path):
    """
    Interactive Plotly swimmer plot: one horizontal lane per experiment
    showing creation → claiming → all results.

    All markers are plotted on a unified x-axis: days from page (issue) creation.
    """
    import plotly.graph_objects as go

    ttr = metrics['metrics']['time_to_first_result']
    if ttr['count'] == 0:
        return

    # Build lookup: title → full claim record (need page_created + claimed_timestamp)
    ttc = metrics['metrics']['time_to_claim']
    claim_detail_lookup = {}
    for d in ttc['details']:
        claim_detail_lookup[d['title']] = d

    # Cross-person info
    conv = metrics['metrics']['conversion_rate']
    cross_titles = set()
    for cp in conv.get('cross_person_claim_list', []):
        cross_titles.add(cp['title'])

    # Pre-compute page-origin days for each experiment, for sorting
    enriched = []
    for det in ttr['details']:
        title = det['experiment_title']
        claim_rec = claim_detail_lookup.get(title, {})
        page_created_str = claim_rec.get('page_created')
        first_res_str = det.get('first_res_created')
        page_dt = _parse_dt(page_created_str)
        d_result_page = _days_from_origin(page_dt, first_res_str)
        enriched.append({
            'det': det,
            'd_result_page': d_result_page if d_result_page is not None else 0,
        })

    # Sort by days-to-first-result from page creation (longest at top)
    enriched.sort(key=lambda x: x['d_result_page'], reverse=True)
    n = len(enriched)

    fig = go.Figure()

    for i, item in enumerate(enriched):
        det = item['det']
        y_pos = n - i
        exp_label = f'Experiment {i + 1}'
        title = det['experiment_title']
        claimer = _abbrev(det.get('claimed_by', ''))
        total_res = det.get('total_linked_res', 1)
        is_cross = title in cross_titles

        claim_rec = claim_detail_lookup.get(title, {})
        page_created_str = claim_rec.get('page_created')
        claimed_ts_str = claim_rec.get('claimed_timestamp')
        page_dt = _parse_dt(page_created_str)

        # Unified page-origin days
        d_claim_page = _days_from_origin(page_dt, claimed_ts_str)

        # All result days from page_created
        all_res = det.get('all_linked_res', [])
        res_days_page = _compute_res_days_from_page(all_res, page_dt,
                                                     item['d_result_page'])

        # Bar extent
        extent_vals = list(res_days_page)
        if d_claim_page is not None:
            extent_vals.append(d_claim_page)
        last_day = max(extent_vals) if extent_vals else 0

        # Background bar
        bar_color = '#f3e5f5' if is_cross else '#fff3e0'
        fig.add_trace(go.Bar(
            x=[last_day], y=[y_pos],
            orientation='h',
            marker=dict(color=bar_color, line=dict(width=0)),
            width=0.5,
            showlegend=False,
            hoverinfo='skip',
        ))

        # Claiming mark (diamond)
        if d_claim_page is not None and d_claim_page > 0:
            fig.add_trace(go.Scatter(
                x=[d_claim_page], y=[y_pos],
                mode='markers',
                marker=dict(symbol='diamond', size=9, color=C_EXPLICIT,
                            line=dict(width=1, color='white')),
                text=f"<b>Claimed</b><br>{exp_label}<br>Day {d_claim_page}",
                hoverinfo='text',
                showlegend=False,
            ))

        # Result marks
        for j, rd_page in enumerate(res_days_page):
            is_first = (j == 0)
            fig.add_trace(go.Scatter(
                x=[rd_page], y=[y_pos],
                mode='markers',
                marker=dict(
                    symbol='star' if is_first else 'circle',
                    size=10 if is_first else 6,
                    color=C_ACCENT if is_first else '#ef9a9a',
                    line=dict(width=1, color='white'),
                ),
                text=(
                    f"<b>{'1st Result' if is_first else f'Result {j+1}'}</b><br>"
                    f"{exp_label}<br>"
                    f"Day {rd_page}<br>"
                    f"Total: {total_res} results"
                ),
                hoverinfo='text',
                showlegend=False,
            ))

    # Y-axis labels: anonymous "Experiment N"
    labels = [f'Experiment {i + 1}' for i in range(n)]

    fig.update_layout(
        title=f'Experiment Lifecycle Swimmer Plot  (n={n}, sorted by time to first result)',
        xaxis_title='Days from Issue Creation',
        xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.08)'),
        yaxis=dict(
            tickvals=list(range(1, n + 1)),
            ticktext=list(reversed(labels)),
            tickfont=dict(size=8),
            showgrid=False,
        ),
        barmode='overlay',
        template='plotly_white',
        height=max(600, n * 18),
        width=1000,
        margin=dict(l=120),
    )

    # Add legend annotation inside the plot area (below top lanes)
    fig.add_annotation(
        x=0.98, y=0.88, xref='paper', yref='paper',
        text='<b>Marks:</b>  ◆ = Claimed  |  ★ = 1st Result  |  ● = Subsequent Results',
        showarrow=False, font=dict(size=11),
        bgcolor='rgba(255,255,255,0.85)', bordercolor='#ccc', borderwidth=1,
    )

    path = output_dir / 'fig6c_swimmer_plot.html'
    fig.write_html(str(path), include_plotlyjs='cdn')
    print(f"  Saved: {path}")

    # Also generate static PNG (linear and log-scale)
    _create_swimmer_plot_static(metrics, output_dir)
    _create_swimmer_plot_static(metrics, output_dir, log_scale=True)


def _create_swimmer_plot_static(metrics: dict, output_dir: Path, log_scale: bool = False):
    """Static matplotlib swimmer plot for evidence bundles.

    All markers use page_created (issue creation) as day 0.
    """
    ttr = metrics['metrics']['time_to_first_result']
    if ttr['count'] == 0:
        return

    # Build lookup: title → full claim record
    ttc = metrics['metrics']['time_to_claim']
    claim_detail_lookup = {d['title']: d for d in ttc['details']}

    conv = metrics['metrics']['conversion_rate']
    cross_titles = set(cp['title'] for cp in conv.get('cross_person_claim_list', []))

    # Pre-compute page-origin days and sort
    enriched = []
    for det in ttr['details']:
        title = det['experiment_title']
        claim_rec = claim_detail_lookup.get(title, {})
        page_dt = _parse_dt(claim_rec.get('page_created'))
        first_res_str = det.get('first_res_created')
        d_result_page = _days_from_origin(page_dt, first_res_str)
        enriched.append({
            'det': det,
            'page_dt': page_dt,
            'claim_rec': claim_rec,
            'd_result_page': d_result_page if d_result_page is not None else 0,
        })

    enriched.sort(key=lambda x: x['d_result_page'], reverse=True)
    n = len(enriched)

    fig, ax = plt.subplots(figsize=(12, max(8, n * 0.22)))

    # For log scale, shift 0 values to 0.5 so they're visible
    def _log_safe(val):
        return max(val, 0.5) if log_scale else val

    for i, item in enumerate(enriched):
        det = item['det']
        page_dt = item['page_dt']
        claim_rec = item['claim_rec']
        y_pos = n - i - 1
        title = det['experiment_title']
        is_cross = title in cross_titles
        total_res = det.get('total_linked_res', 1)

        # Unified page-origin days
        d_claim_page = _days_from_origin(page_dt, claim_rec.get('claimed_timestamp'))

        # All result days from page_created
        all_res = det.get('all_linked_res', [])
        res_days_page = _compute_res_days_from_page(all_res, page_dt,
                                                     item['d_result_page'])

        # Bar extent
        extent_vals = list(res_days_page)
        if d_claim_page is not None:
            extent_vals.append(d_claim_page)
        last_day = max(extent_vals) if extent_vals else 0

        # Thin bar
        bar_color = '#e1bee7' if is_cross else '#ffe0b2'
        if log_scale:
            bar_start = _log_safe(0)
            bar_end = _log_safe(last_day)
            ax.barh(y_pos, bar_end - bar_start, left=bar_start, height=0.4,
                    color=bar_color, alpha=0.5, zorder=1)
        else:
            ax.barh(y_pos, last_day, height=0.4, color=bar_color, alpha=0.5, zorder=1)

        # Issue creation at 0
        ax.plot(_log_safe(0), y_pos, 'o', color=C_UNCLAIMED, markersize=4, zorder=3)

        # Claiming diamond
        if d_claim_page is not None and d_claim_page > 0:
            ax.plot(_log_safe(d_claim_page), y_pos, 'D', color=C_EXPLICIT, markersize=5, zorder=4)

        # Result marks
        for j, rd_page in enumerate(res_days_page):
            if j == 0:
                ax.plot(_log_safe(rd_page), y_pos, '*', color=C_ACCENT, markersize=8, zorder=5)
            else:
                ax.plot(_log_safe(rd_page), y_pos, 'o', color='#ef9a9a', markersize=3, zorder=4)

        # Right annotation: total results
        ax.text(_log_safe(last_day) * (1.05 if log_scale else 1) + (0 if log_scale else 5),
                y_pos, f'{total_res}', fontsize=7, va='center', color='#666')

    # Y-axis labels: anonymous "Experiment N"
    labels = [f'Exp {i + 1}' for i in range(n)]
    ax.set_yticks(range(n))
    ax.set_yticklabels(list(reversed(labels)), fontsize=7)

    if log_scale:
        ax.set_xscale('log')
        ax.set_xlim(0.4, None)
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(
            lambda x, _: f'{int(x)}' if x >= 1 else '0'))
        ax.set_xlabel('Days from Issue Creation (log scale)', fontsize=11)
        ax.set_title(f'Experiment Lifecycle Swimmer Plot — log scale  (n={n})',
                     fontsize=13, fontweight='bold')
    else:
        ax.set_xlabel('Days from Issue Creation', fontsize=11)
        ax.set_title(f'Experiment Lifecycle Swimmer Plot  (n={n})',
                     fontsize=13, fontweight='bold')

    # Legend — inside the plot
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=C_UNCLAIMED, markersize=6, label='Issue Created'),
        plt.Line2D([0], [0], marker='D', color='w', markerfacecolor=C_EXPLICIT, markersize=6, label='Claimed'),
        plt.Line2D([0], [0], marker='*', color='w', markerfacecolor=C_ACCENT, markersize=8, label='1st Result'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#ef9a9a', markersize=5, label='Subsequent Results'),
    ]
    ax.legend(handles=legend_elements, loc='right', bbox_to_anchor=(1.0, 0.85),
              fontsize=8, framealpha=0.9)

    # Minimal grid: vertical only, no horizontal
    ax.grid(axis='x', alpha=0.2)
    ax.grid(axis='y', visible=False)
    plt.tight_layout()
    suffix = '_log' if log_scale else ''
    path = output_dir / f'fig6c_swimmer_plot{suffix}.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def _parse_dt(val) -> datetime | None:
    """Parse a datetime from string or return as-is if already datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None


def _days_from_origin(origin: datetime | None, target) -> int | None:
    """Days from origin datetime to a target (str or datetime)."""
    if origin is None:
        return None
    t = _parse_dt(target)
    if t is None:
        return None
    return (t - origin).days


def _compute_res_days_from_page(
    all_res: list, page_dt: datetime | None, fallback_first: int
) -> list[int]:
    """Compute days for all results relative to page_created (unified origin)."""
    if not all_res or page_dt is None:
        return [fallback_first]
    res_days = []
    for r in all_res:
        rd = _days_from_origin(page_dt, r.get('created'))
        if rd is not None:
            res_days.append(rd)
    return res_days if res_days else [fallback_first]


# ─────────────────────────────────────────────────────────────
# Fig 6d — Raincloud Plot
# ─────────────────────────────────────────────────────────────
def create_raincloud_plot(metrics: dict, output_dir: Path):
    """
    Two-row raincloud: time-to-claim (top) vs time-to-first-result (bottom).
    Each row: half-violin + box + jitter strip.
    """
    ttc = metrics['metrics']['time_to_claim']
    ttr = metrics['metrics']['time_to_first_result']

    days_claim = [d['days_to_claim'] for d in ttc['details']]
    days_result = [d['days_to_first_result'] for d in ttr['details']]

    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    datasets = [
        (days_claim, 'Time to Claiming', C_EXPLICIT, ttc['count'], axes[0]),
        (days_result, 'Time to First Result', C_CROSS, ttr['count'], axes[1]),
    ]

    for data, label, color, n, ax in datasets:
        data_arr = np.array(data, dtype=float)

        # Add a small offset for log display (0 → 0.5)
        data_log = np.where(data_arr <= 0, 0.5, data_arr)

        # Half-violin (upper)
        parts = ax.violinplot(data_log, positions=[0.5], vert=False,
                              showmedians=False, showextrema=False)
        for pc in parts['bodies']:
            # Clip to upper half
            m = np.mean(pc.get_paths()[0].vertices[:, 1])
            pc.get_paths()[0].vertices[:, 1] = np.clip(
                pc.get_paths()[0].vertices[:, 1], m, None)
            pc.set_facecolor(color)
            pc.set_alpha(0.4)

        # Box plot (at center)
        bp = ax.boxplot(data_log, positions=[0.3], vert=False, widths=0.15,
                        patch_artist=True, showfliers=False,
                        boxprops=dict(facecolor=color, alpha=0.6),
                        medianprops=dict(color='white', linewidth=2),
                        whiskerprops=dict(color=color),
                        capprops=dict(color=color))

        # Jitter strip (lower half)
        jitter_y = np.random.uniform(-0.05, 0.15, size=len(data_log))
        ax.scatter(data_log, jitter_y, s=15, color=color, alpha=0.5,
                   edgecolors='white', linewidths=0.3, zorder=4)

        # Stats annotation
        med = np.median(data_arr)
        mean = np.mean(data_arr)
        ax.text(0.98, 0.85, f'{label}\nn={n}  median={med:.0f}d  mean={mean:.1f}d',
                transform=ax.transAxes, fontsize=10, ha='right', va='top',
                bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.9, ec='#ccc'))

        ax.set_xscale('log')
        ax.set_xlim(0.3, 1000)
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(
            lambda x, _: f'{int(x)}' if x >= 1 else '0'))
        ax.set_yticks([])
        ax.grid(axis='x', alpha=0.3)

    axes[1].set_xlabel('Days (log scale)', fontsize=12)
    fig.suptitle('Raincloud: Time-to-Claim vs Time-to-First-Result',
                 fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout()
    path = output_dir / 'fig6d_raincloud.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────
# Fig 6e — Result Yield Bubble Chart
# ─────────────────────────────────────────────────────────────
def create_result_yield_bubble(metrics: dict, output_dir: Path):
    """
    Scatter/bubble: x = days-to-first-result, y = total results,
    bubble size = total results, color = researcher.
    """
    ttr = metrics['metrics']['time_to_first_result']
    if ttr['count'] == 0:
        return

    details = ttr['details']
    days = [d['days_to_first_result'] for d in details]
    total_res = [d['total_linked_res'] for d in details]
    claimers = [_abbrev(d.get('claimed_by', '')) for d in details]

    cmap = _get_researcher_color_map(claimers)
    colors = [cmap.get(c, '#999') for c in claimers]

    fig, ax = plt.subplots(figsize=(11, 7))

    # Bubble sizes (sqrt scale for area perception)
    sizes = [max(np.sqrt(r) * 60, 30) for r in total_res]

    scatter = ax.scatter(days, total_res, s=sizes, c=colors, alpha=0.7,
                         edgecolors='white', linewidths=1, zorder=4)

    # Label top experiments
    for det in sorted(details, key=lambda x: x['total_linked_res'], reverse=True)[:3]:
        d = det['days_to_first_result']
        r = det['total_linked_res']
        title = det['experiment_title'][:45] + '...'
        ax.annotate(
            f'{r} results\n{title}',
            xy=(d, r), xytext=(d + 50, r + 2),
            fontsize=7.5, ha='left',
            arrowprops=dict(arrowstyle='->', color='#888', lw=0.8),
            bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.85, ec='#ccc'),
        )

    # Reference lines
    ax.axhline(y=1, color='grey', linestyle=':', alpha=0.4, linewidth=0.8)
    median_days = int(np.median(days))
    ax.axvline(x=median_days, color=C_MEDIAN, linestyle='--', alpha=0.5, linewidth=1,
               label=f'Median: {median_days}d')

    # Legend for researchers
    unique_claimers = sorted(cmap.keys())
    handles = [mpatches.Patch(color=cmap[c], label=c) for c in unique_claimers]
    ax.legend(handles=handles, loc='upper right', fontsize=8, framealpha=0.9,
              title='Researcher', title_fontsize=9)

    ax.set_xlabel('Days to First Result', fontsize=12)
    ax.set_ylabel('Total Results Produced', fontsize=12)
    ax.set_title(f'Result Yield per Experiment  (n={len(details)})', fontsize=13, fontweight='bold')
    ax.set_yscale('symlog', linthresh=5)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    path = output_dir / 'fig6e_result_yield.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def create_result_yield_bubble_interactive(metrics: dict, output_dir: Path):
    """Interactive Plotly version of the result yield bubble chart."""
    import plotly.graph_objects as go

    ttr = metrics['metrics']['time_to_first_result']
    if ttr['count'] == 0:
        return

    details = ttr['details']
    claimers = [_abbrev(d.get('claimed_by', '')) for d in details]
    cmap = _get_researcher_color_map(claimers)

    # Group by researcher for legend
    by_researcher = defaultdict(list)
    for det in details:
        c = _abbrev(det.get('claimed_by', ''))
        by_researcher[c].append(det)

    fig = go.Figure()
    for researcher in sorted(by_researcher.keys()):
        exps = by_researcher[researcher]
        fig.add_trace(go.Scatter(
            x=[e['days_to_first_result'] for e in exps],
            y=[e['total_linked_res'] for e in exps],
            mode='markers',
            marker=dict(
                size=[max(np.sqrt(e['total_linked_res']) * 12, 8) for e in exps],
                color=cmap.get(researcher, '#999'),
                line=dict(width=1, color='white'),
                opacity=0.75,
            ),
            name=researcher,
            text=[
                f"<b>{e['experiment_title'][:55]}</b><br>"
                f"Days to 1st result: {e['days_to_first_result']}<br>"
                f"Total results: {e['total_linked_res']}<br>"
                f"Claimed by: {_abbrev(e.get('claimed_by', ''))}"
                for e in exps
            ],
            hoverinfo='text',
        ))

    fig.update_layout(
        title=f'Result Yield per Experiment (n={len(details)})',
        xaxis_title='Days to First Result',
        yaxis_title='Total Results Produced',
        yaxis_type='log',
        template='plotly_white',
        width=950, height=600,
    )

    path = output_dir / 'fig6e_result_yield.html'
    fig.write_html(str(path), include_plotlyjs='cdn')
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────
# Fig 6f — Kaplan-Meier Survival Curve
# ─────────────────────────────────────────────────────────────
def create_survival_curve(metrics: dict, output_dir: Path):
    """
    Kaplan-Meier survival curve treating 'first result produced' as the event.
    The 80 experiments without results are right-censored.
    Stratified by self-claimed vs cross-person.
    """
    ttr = metrics['metrics']['time_to_first_result']
    conv = metrics['metrics']['conversion_rate']

    # Get all claimed experiments
    all_claimed = conv.get('claimed_experiment_list', [])
    if not all_claimed:
        print("  Skipping fig6f: no claimed_experiment_list available")
        return

    # Determine data export date (for censoring)
    generated = metrics.get('generated', '')
    if isinstance(generated, str):
        try:
            export_date = datetime.fromisoformat(generated)
        except ValueError:
            export_date = datetime.now()
    else:
        export_date = generated if generated else datetime.now()

    # Build title → first result days lookup
    result_lookup = {}
    for det in ttr['details']:
        result_lookup[det['experiment_title']] = det['days_to_first_result']

    # Build cross-person set
    cross_titles = set(cp['title'] for cp in conv.get('cross_person_claim_list', []))

    # Build event data: (time, event_occurred, is_cross)
    events = []
    for exp in all_claimed:
        title = exp['title']
        is_cross = title in cross_titles

        if title in result_lookup:
            # Event occurred
            t = result_lookup[title]
            events.append((max(t, 0), True, is_cross))
        else:
            # Censored: time from claim to export date
            claimed_ts = exp.get('claimed_by_timestamp') or exp.get('page_created', '')
            if claimed_ts:
                try:
                    if isinstance(claimed_ts, str):
                        claim_dt = datetime.fromisoformat(claimed_ts)
                    else:
                        claim_dt = claimed_ts
                    t = (export_date - claim_dt).days
                    events.append((max(t, 0), False, is_cross))
                except (ValueError, TypeError):
                    pass

    if not events:
        return

    # Compute KM curve for all, self, and cross
    def kaplan_meier(event_list):
        """Compute KM survival curve. Returns (times, survival_probs)."""
        if not event_list:
            return [], []
        event_list = sorted(event_list, key=lambda x: x[0])
        n_at_risk = len(event_list)
        times = [0]
        surv = [1.0]

        i = 0
        while i < len(event_list):
            t_i = event_list[i][0]
            # Count events and censorings at time t_i
            d_i = 0  # events (deaths)
            c_i = 0  # censorings
            while i < len(event_list) and event_list[i][0] == t_i:
                if event_list[i][1]:
                    d_i += 1
                else:
                    c_i += 1
                i += 1

            if d_i > 0:
                surv_step = surv[-1] * (1 - d_i / n_at_risk)
                times.append(t_i)
                surv.append(surv_step)

            n_at_risk -= (d_i + c_i)
            if n_at_risk <= 0:
                break

        return times, surv

    # All experiments
    all_events = [(t, e, c) for t, e, c in events]
    self_events = [(t, e) for t, e, c in events if not c]
    cross_events = [(t, e) for t, e, c in events if c]

    all_km_t, all_km_s = kaplan_meier([(t, e) for t, e, c in all_events])
    self_km_t, self_km_s = kaplan_meier(self_events)
    cross_km_t, cross_km_s = kaplan_meier(cross_events)

    fig, ax = plt.subplots(figsize=(11, 6.5))

    # Plot KM curves
    ax.step(all_km_t, all_km_s, where='post', color='#333', linewidth=2.5,
            label=f'All experiments (n={len(all_events)})', zorder=4)

    if self_km_t:
        ax.step(self_km_t, self_km_s, where='post', color=C_SELF, linewidth=2,
                linestyle='-', label=f'Self-claimed (n={len(self_events)})', zorder=3)
    if cross_km_t:
        ax.step(cross_km_t, cross_km_s, where='post', color=C_CROSS, linewidth=2,
                linestyle='-', label=f'Cross-person (n={len(cross_events)})', zorder=3)

    # Censoring tick marks on the 'all' curve
    censor_times = sorted([t for t, e, c in events if not e])
    for ct in censor_times:
        # Find survival probability at censoring time
        surv_at_t = 1.0
        for j in range(len(all_km_t)):
            if all_km_t[j] <= ct:
                surv_at_t = all_km_s[j]
            else:
                break
        ax.plot(ct, surv_at_t, '|', color='#999', markersize=5, markeredgewidth=0.8,
                alpha=0.4, zorder=2)

    # Median survival line
    median_surv = None
    for j in range(len(all_km_s)):
        if all_km_s[j] <= 0.5:
            median_surv = all_km_t[j]
            break

    if median_surv:
        ax.axhline(y=0.5, color='grey', linestyle=':', alpha=0.4)
        ax.axvline(x=median_surv, color='grey', linestyle=':', alpha=0.4)
        ax.annotate(
            f'Median: {median_surv} days',
            xy=(median_surv, 0.5), xytext=(median_surv + 40, 0.55),
            fontsize=10,
            arrowprops=dict(arrowstyle='->', color='#888', lw=1),
            bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.9, ec='#ccc'),
        )

    # Stats
    n_events = sum(1 for _, e, _ in events if e)
    n_censored = sum(1 for _, e, _ in events if not e)
    ax.text(0.98, 0.95,
            f'Events: {n_events}\nCensored: {n_censored}\nTotal: {len(events)}',
            transform=ax.transAxes, fontsize=10, ha='right', va='top',
            bbox=dict(boxstyle='round,pad=0.4', fc='white', alpha=0.9, ec='#ccc'))

    ax.set_xlabel('Days from Claiming', fontsize=12)
    ax.set_ylabel('Survival Probability (no result yet)', fontsize=12)
    ax.set_title('Kaplan-Meier: Time Until First Result Production', fontsize=13, fontweight='bold')
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlim(-10, max(t for t, _, _ in events) + 20)
    ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    path = output_dir / 'fig6f_survival_curve.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────
# Fig 6g — Result Cascade
# ─────────────────────────────────────────────────────────────
def create_result_cascade(metrics: dict, output_dir: Path):
    """
    For experiments with 2+ results: timing of every result relative
    to the first result (time=0). Reveals cadence — bursts vs steady.
    """
    ttr = metrics['metrics']['time_to_first_result']
    if ttr['count'] == 0:
        return

    # Build claim lookup to get page_created
    ttc = metrics['metrics']['time_to_claim']
    claim_detail_lookup = {d['title']: d for d in ttc['details']}

    # Filter to experiments with 2+ results that have all_linked_res data
    multi_res = []
    for det in ttr['details']:
        all_res = det.get('all_linked_res', [])
        if len(all_res) >= 2:
            claim_rec = claim_detail_lookup.get(det['experiment_title'], {})
            page_dt = _parse_dt(claim_rec.get('page_created'))
            first_res_str = det.get('first_res_created')
            d_fallback = _days_from_origin(page_dt, first_res_str) or 0
            res_days = _compute_res_days_from_page(all_res, page_dt, d_fallback)
            # Make relative to first result
            first_day = min(res_days) if res_days else 0
            rel_days = sorted([d - first_day for d in res_days])
            multi_res.append({
                'title': det['experiment_title'],
                'claimer': _abbrev(det.get('claimed_by', '')),
                'total': det['total_linked_res'],
                'rel_days': rel_days,
                'first_result_day': det['days_to_first_result'],
            })

    if not multi_res:
        print("  Skipping fig6g: no multi-result experiments with all_linked_res data")
        return

    # Sort by total results (most at top)
    multi_res.sort(key=lambda x: x['total'], reverse=True)
    n = len(multi_res)

    fig, ax = plt.subplots(figsize=(12, max(5, n * 0.35)))

    claimers = [m['claimer'] for m in multi_res]
    cmap = _get_researcher_color_map(claimers)

    for i, exp in enumerate(multi_res):
        y_pos = n - i - 1
        color = cmap.get(exp['claimer'], '#999')

        # Thin connecting line
        if exp['rel_days']:
            ax.plot([exp['rel_days'][0], exp['rel_days'][-1]], [y_pos, y_pos],
                    '-', color=color, linewidth=1, alpha=0.4, zorder=1)

        # Result dots
        for j, rd in enumerate(exp['rel_days']):
            if j == 0:
                ax.plot(rd, y_pos, 'o', color=color, markersize=7,
                        markeredgecolor='white', markeredgewidth=0.8, zorder=4)
            else:
                ax.plot(rd, y_pos, 'o', color=color, markersize=4,
                        markeredgecolor='white', markeredgewidth=0.3, zorder=3,
                        alpha=0.7)

        # Right annotation
        ax.text(max(exp['rel_days']) + 5, y_pos,
                f"{exp['total']} results", fontsize=7, va='center', color='#666')

    # Y-axis labels
    labels = [f"{m['claimer']} | {m['title'][:40]}" for m in multi_res]
    ax.set_yticks(range(n))
    ax.set_yticklabels(list(reversed(labels)), fontsize=7)
    ax.set_xlabel('Days from First Result', fontsize=11)
    ax.set_title(
        f'Result Cascade: Timing of All Results  ({n} experiments with 2+ results)',
        fontsize=13, fontweight='bold',
    )

    # Legend
    unique_claimers = sorted(cmap.keys())
    handles = [mpatches.Patch(color=cmap[c], label=c) for c in unique_claimers]
    ax.legend(handles=handles, loc='lower right', fontsize=8, framealpha=0.9,
              title='Researcher', title_fontsize=9)

    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    path = output_dir / 'fig6g_result_cascade.png'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")

    # Interactive version
    _create_result_cascade_interactive(multi_res, cmap, output_dir)


def _create_result_cascade_interactive(multi_res: list, cmap: dict, output_dir: Path):
    """Interactive Plotly version of the result cascade."""
    import plotly.graph_objects as go

    n = len(multi_res)
    fig = go.Figure()

    for i, exp in enumerate(multi_res):
        y_pos = n - i - 1
        color = cmap.get(exp['claimer'], '#999')
        title_short = exp['title'][:55]

        # Connecting line
        if len(exp['rel_days']) > 1:
            fig.add_trace(go.Scatter(
                x=[exp['rel_days'][0], exp['rel_days'][-1]],
                y=[y_pos, y_pos],
                mode='lines',
                line=dict(color=color, width=1),
                opacity=0.3,
                showlegend=False,
                hoverinfo='skip',
            ))

        # Dots
        fig.add_trace(go.Scatter(
            x=exp['rel_days'],
            y=[y_pos] * len(exp['rel_days']),
            mode='markers',
            marker=dict(
                size=[8] + [5] * (len(exp['rel_days']) - 1),
                color=color,
                line=dict(width=1, color='white'),
            ),
            text=[
                f"<b>{title_short}</b><br>"
                f"Result {j+1} of {exp['total']}<br>"
                f"Day {rd} after 1st result"
                for j, rd in enumerate(exp['rel_days'])
            ],
            hoverinfo='text',
            showlegend=False,
        ))

    labels = [f"{m['claimer']} | {m['title'][:40]}" for m in multi_res]
    fig.update_layout(
        title=f'Result Cascade ({n} experiments with 2+ results)',
        xaxis_title='Days from First Result',
        yaxis=dict(
            tickvals=list(range(n)),
            ticktext=list(reversed(labels)),
            tickfont=dict(size=8),
        ),
        template='plotly_white',
        height=max(500, n * 25),
        width=1000,
        margin=dict(l=280),
    )

    path = output_dir / 'fig6g_result_cascade.html'
    fig.write_html(str(path), include_plotlyjs='cdn')
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────
def generate_experiment_lifecycle_visualizations(metrics: dict, output_dir: Path):
    """Generate all Fig 6 experiment lifecycle visualizations."""
    print("\n--- Fig 6: Experiment Lifecycle Visualizations ---")

    create_time_to_result_histogram(metrics, output_dir)        # 6a
    create_time_to_result_cdf(metrics, output_dir)              # 6b (static)
    create_time_to_result_cdf_interactive(metrics, output_dir)  # 6b (interactive)
    create_swimmer_plot(metrics, output_dir)                     # 6c (interactive + static)
    create_raincloud_plot(metrics, output_dir)                   # 6d
    create_result_yield_bubble(metrics, output_dir)              # 6e (static)
    create_result_yield_bubble_interactive(metrics, output_dir)  # 6e (interactive)
    create_survival_curve(metrics, output_dir)                   # 6f
    create_result_cascade(metrics, output_dir)                   # 6g (static + interactive)

    print("--- Fig 6 complete ---\n")
