#!/usr/bin/env python3
"""
Diagnostic Swimmer Plot — unified x-axis (days from page creation)
with rich hover tooltips for troubleshooting claim/result timing.

Reads output/metrics_data.json and writes
output/visualizations/fig6c_swimmer_plot_diagnostic.html

Key fix vs fig6c: all markers use page_created as day 0, so claims
and results are always on the same axis.
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go


# ── colours ──────────────────────────────────────────────────────
C_CLAIM      = '#2980b9'
C_RESULT_1ST = '#e74c3c'
C_RESULT_N   = '#ef9a9a'
BAR_CROSS    = '#f3e5f5'
BAR_SELF     = '#fff3e0'
BAR_ANOMALY  = '#ffcdd2'


def _fmt_dt(val: str | None) -> str:
    """Format an ISO timestamp for display."""
    if not val:
        return '—'
    try:
        dt = datetime.fromisoformat(str(val))
        return dt.strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return str(val)[:16]


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None


def _short(title: str, maxlen: int = 50) -> str:
    return title if len(title) <= maxlen else title[:maxlen] + '…'


def _days_from(origin: datetime | None, target: str | None) -> int | None:
    """Days from origin datetime to an ISO timestamp string."""
    if not origin or not target:
        return None
    t = _parse_dt(target)
    if not t:
        return None
    return (t - origin).days


def main():
    repo = Path(__file__).resolve().parent.parent
    metrics_path = repo / 'output' / 'metrics_data.json'
    out_path = repo / 'output' / 'visualizations' / 'fig6c_swimmer_plot_diagnostic.html'
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(metrics_path) as f:
        data = json.load(f)

    ttr = data['metrics']['time_to_first_result']
    ttc = data['metrics']['time_to_claim']
    conv = data['metrics']['conversion_rate']

    # Build lookup: title → time-to-claim record
    claim_lookup: dict[str, dict] = {}
    for d in ttc['details']:
        claim_lookup[d['title']] = d

    # Build lookup: title → experiment record (from conversion_rate)
    exp_lookup: dict[str, dict] = {}
    for e in conv.get('claimed_experiment_list', []):
        exp_lookup[e['title']] = e

    # Cross-person titles
    cross_titles = {cp['title'] for cp in conv.get('cross_person_claim_list', [])}

    # ── Pre-compute page-origin days for sorting ────────────────
    enriched = []
    for det in ttr['details']:
        title = det['experiment_title']
        claim_info = claim_lookup.get(title, {})
        exp_info = exp_lookup.get(title, {})

        page_created_str = claim_info.get('page_created',
                                          exp_info.get('page_created'))
        page_dt = _parse_dt(page_created_str)

        first_res_ts = det.get('first_res_created')
        d_result_from_page = _days_from(page_dt, first_res_ts)

        enriched.append({
            'det': det,
            'd_result_from_page': d_result_from_page if d_result_from_page is not None else 0,
        })

    # Sort by days-to-first-result-from-page descending (longest at top)
    enriched.sort(key=lambda x: x['d_result_from_page'], reverse=True)
    n = len(enriched)

    fig = go.Figure()

    for i, item in enumerate(enriched):
        det = item['det']
        y_pos = n - i
        title = det['experiment_title']
        claim_info = claim_lookup.get(title, {})
        exp_info = exp_lookup.get(title, {})
        claim_type = exp_info.get('claim_type', 'unknown')
        is_cross = title in cross_titles

        page_created_str = claim_info.get('page_created',
                                          exp_info.get('page_created'))
        page_dt = _parse_dt(page_created_str)
        claimed_ts_str = claim_info.get('claimed_timestamp',
                                        exp_info.get('claimed_by_timestamp'))
        ref_ts_str = det.get('ref_timestamp')
        first_res_ts = det.get('first_res_created')
        first_res_title = det.get('first_res_title', '—')
        first_res_creator = det.get('first_res_creator', '—')
        claimer = det.get('claimed_by', '—')
        total_res = det.get('total_linked_res', 1)
        first_log = exp_info.get('first_log_entry')
        log_count = exp_info.get('log_entry_count', 0)

        # ── Unified page-origin days ────────────────────────────
        d_claim_page = _days_from(page_dt, claimed_ts_str)  # claim on page axis
        d_first_page = _days_from(page_dt, first_res_ts)    # 1st result on page axis
        d_first_ref  = det['days_to_first_result']          # original (from ref_timestamp)
        d_claim_orig = claim_info.get('days_to_claim')      # original claim days

        ref_label = 'claimed_timestamp' if claim_type == 'explicit' else 'page_created'

        # Anomaly: result still before claim even on unified axis?
        anomaly = None
        if (d_claim_page is not None and d_first_page is not None
                and d_first_page < d_claim_page):
            anomaly = 'RESULT BEFORE CLAIM'

        # ── All result days from page_created ───────────────────
        all_res = det.get('all_linked_res', [])
        res_days_page: list[int] = []
        if all_res and page_dt:
            for r in all_res:
                rd = _days_from(page_dt, r['created'])
                if rd is not None:
                    res_days_page.append(rd)
        if not res_days_page and d_first_page is not None:
            res_days_page = [d_first_page]
        elif not res_days_page:
            res_days_page = [0]

        # ── Background bar ──────────────────────────────────────
        extent_vals = list(res_days_page)
        if d_claim_page is not None:
            extent_vals.append(d_claim_page)
        last_day = max(extent_vals) if extent_vals else 0

        bar_color = BAR_ANOMALY if anomaly else (BAR_CROSS if is_cross else BAR_SELF)

        fig.add_trace(go.Bar(
            x=[last_day], y=[y_pos],
            orientation='h',
            marker=dict(color=bar_color, line=dict(width=0)),
            width=0.5,
            showlegend=False,
            hoverinfo='skip',
        ))

        # ── Claim diamond (plotted at d_claim_page) ─────────────
        if d_claim_page is not None:
            claim_hover = [
                f'<b>◆ CLAIMED</b>',
                f'<b>Title:</b> {_short(title, 70)}',
                f'<b>Claimed by:</b> {claimer}',
                f'<b>Claim type:</b> {claim_type}',
                f'<b>Claim timestamp:</b> {_fmt_dt(claimed_ts_str)}',
                f'<b>Page created:</b> {_fmt_dt(page_created_str)}',
                f'<b>Days to claim (from page):</b> {d_claim_page}',
            ]
            if claim_type == 'inferred':
                claim_hover.append(f'<b>First log entry:</b> {_fmt_dt(first_log)}')
                claim_hover.append(f'<b>Log entry count:</b> {log_count}')
                claim_hover.append(
                    '<b>Method:</b> no Claimed By:: field; '
                    'claim inferred from first experimental log entry'
                )
            if anomaly:
                claim_hover.append(f'<b>⚠️ {anomaly}</b>')
                claim_hover.append(
                    f'<b>1st result day (page):</b> {d_first_page}'
                )

            fig.add_trace(go.Scatter(
                x=[d_claim_page], y=[y_pos],
                mode='markers',
                marker=dict(symbol='diamond', size=10,
                            color='#c62828' if anomaly else C_CLAIM,
                            line=dict(width=1, color='white')),
                text='<br>'.join(claim_hover),
                hoverinfo='text',
                showlegend=False,
            ))

        # ── Result marks (plotted at res_days_page) ─────────────
        for j, rd_page in enumerate(res_days_page):
            is_first = (j == 0)
            r_info = all_res[j] if j < len(all_res) else {}
            r_title = r_info.get('title', first_res_title if is_first else '—')
            r_created = r_info.get('created', first_res_ts if is_first else '—')
            r_creator = r_info.get('creator', first_res_creator if is_first else '—')

            # Also compute days from ref_timestamp for comparison
            r_days_from_ref = _days_from(_parse_dt(ref_ts_str), r_created)

            res_hover = [
                f'<b>{"★ 1ST RESULT" if is_first else f"● RESULT {j+1}"}</b>',
                f'<b>Exp:</b> {_short(title, 70)}',
                f'<b>Res title:</b> {_short(str(r_title), 80)}',
                f'<b>Result created:</b> {_fmt_dt(r_created)}',
                f'<b>Result creator:</b> {r_creator}',
                f'<b>Days from page_created:</b> {rd_page}',
                f'<b>Days from ref_timestamp:</b> {r_days_from_ref}  '
                f'(ref = {ref_label}: {_fmt_dt(ref_ts_str)})',
                f'<b>Claim day (page):</b> {d_claim_page}',
                f'<b>Total linked RES:</b> {total_res}',
            ]
            if anomaly and is_first:
                res_hover.append(f'<b>⚠️ {anomaly}</b>')
                if claim_type == 'inferred':
                    res_hover.append(
                        '<b>Note:</b> claim inferred from first_log_entry; '
                        f'log was {_fmt_dt(first_log)}, after result'
                    )

            fig.add_trace(go.Scatter(
                x=[rd_page], y=[y_pos],
                mode='markers',
                marker=dict(
                    symbol='star' if is_first else 'circle',
                    size=11 if is_first else 7,
                    color=('#c62828' if anomaly and is_first else
                           C_RESULT_1ST if is_first else C_RESULT_N),
                    line=dict(width=1, color='white'),
                ),
                text='<br>'.join(res_hover),
                hoverinfo='text',
                showlegend=False,
            ))

    # ── Y-axis labels: experiment titles ────────────────────────
    y_labels = [_short(item['det']['experiment_title'], 45) for item in enriched]

    fig.update_layout(
        title=dict(
            text=(
                '<b>DIAGNOSTIC Swimmer Plot</b>  —  '
                'unified x-axis: days from page (issue) creation<br>'
                '<span style="font-size:11px;color:#666">'
                'All markers now use page_created as day 0. '
                'Hover for full timestamps, claim type, original ref_timestamp comparison.'
                '</span><br>'
                '<span style="font-size:11px;color:#c62828">'
                'Pink bars = result created before claim timestamp (may indicate data issue).'
                '</span>'
            ),
            font=dict(size=14),
        ),
        xaxis_title='Days from Issue (Page) Creation',
        xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.08)'),
        yaxis=dict(
            tickvals=list(range(1, n + 1)),
            ticktext=list(reversed(y_labels)),
            tickfont=dict(size=7),
            showgrid=False,
        ),
        barmode='overlay',
        template='plotly_white',
        height=max(700, n * 20),
        width=1200,
        margin=dict(l=300),
        hoverlabel=dict(
            bgcolor='white',
            font_size=11,
            font_family='monospace',
            namelength=-1,
        ),
    )

    # Legend annotation
    fig.add_annotation(
        x=0.98, y=0.92, xref='paper', yref='paper',
        text=(
            '<b>Marks:</b>  ◆ = Claimed  |  ★ = 1st Result  |  ● = Later Results<br>'
            '<b>Bars:</b>  Orange = self-claim  |  Purple = cross-person  |  '
            '<span style="color:#c62828">Pink = result before claim</span><br>'
            '<b>X-axis:</b>  all days measured from page (issue) creation date'
        ),
        showarrow=False, font=dict(size=10),
        bgcolor='rgba(255,255,255,0.92)', bordercolor='#ccc', borderwidth=1,
        align='left',
    )

    fig.write_html(str(out_path), include_plotlyjs='cdn')
    print(f'Saved diagnostic swimmer plot: {out_path}')
    print(f'  {n} experiments plotted, all on unified page-creation axis')


if __name__ == '__main__':
    main()
