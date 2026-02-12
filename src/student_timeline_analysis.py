#!/usr/bin/env python3
"""
Student Timeline Analysis

Generates visualizations showing the onboarding timeline for undergraduate researchers,
tracking key milestones from first day to first formal result (RES node).

Researchers are anonymized as A, B, C in all outputs.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import numpy as np

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# Student milestone data (anonymized in outputs)
STUDENT_DATA = {
    'A': {
        'name': 'Researcher A',  # Anonymized; not shown in plots
        'first_day': datetime(2024, 2, 23),
        'first_experiment': datetime(2024, 4, 5),
        'first_plot': datetime(2024, 6, 20),
        'first_res': datetime(2024, 6, 27),
        'pathway': 'Self-directed exploration',
    },
    'B': {
        'name': 'Researcher B',  # Anonymized
        'first_day': datetime(2024, 10, 10),
        'first_experiment': datetime(2024, 10, 15),
        'first_plot': datetime(2024, 10, 15),
        'first_res': datetime(2024, 11, 26),
        'pathway': 'Assigned entry project',
    },
    'C': {
        'name': 'Researcher C',  # Anonymized
        'first_day': datetime(2025, 6, 23),
        'first_experiment': datetime(2025, 6, 30),
        'first_plot': datetime(2025, 7, 7),
        'first_res': datetime(2025, 7, 29),
        'pathway': 'Direct assignment',
    },
}


def calculate_days(start: datetime, end: datetime) -> int:
    """Calculate days between two dates."""
    return (end - start).days


def compute_milestones(student_data: dict) -> dict:
    """Compute milestone timings in days from first day."""
    milestones = {}
    for researcher_id, data in student_data.items():
        first_day = data['first_day']
        milestones[researcher_id] = {
            'first_day': first_day.strftime('%Y-%m-%d'),
            'days_to_experiment': calculate_days(first_day, data['first_experiment']),
            'days_to_plot': calculate_days(first_day, data['first_plot']),
            'days_to_res': calculate_days(first_day, data['first_res']),
            'pathway': data['pathway'],
        }
    return milestones


def create_timeline_gantt(student_data: dict, output_path: Path):
    """
    Create a Gantt-style timeline chart showing milestones for each researcher.

    Researchers are labeled as A, B, C (anonymized).
    """
    fig, ax = plt.subplots(figsize=(12, 5))

    # Colors for each milestone type
    colors = {
        'onboarding': '#3498db',      # Blue - first day to first experiment
        'development': '#2ecc71',     # Green - first experiment to first plot
        'result': '#9b59b6',          # Purple - first plot to first RES
    }

    # Marker colors for milestones
    marker_colors = {
        'first_day': '#2c3e50',
        'first_experiment': '#e74c3c',
        'first_plot': '#f39c12',
        'first_res': '#27ae60',
    }

    researchers = ['A', 'B', 'C']
    y_positions = [2, 1, 0]  # Reverse order so A is at top

    for i, (researcher_id, y_pos) in enumerate(zip(researchers, y_positions)):
        data = student_data[researcher_id]
        first_day = data['first_day']

        # Calculate days for each milestone
        days_to_exp = calculate_days(first_day, data['first_experiment'])
        days_to_plot = calculate_days(first_day, data['first_plot'])
        days_to_res = calculate_days(first_day, data['first_res'])

        bar_height = 0.4

        # Draw bars for each phase
        # Phase 1: Onboarding (day 0 to first experiment)
        ax.barh(y_pos, days_to_exp, left=0, height=bar_height,
                color=colors['onboarding'], alpha=0.7, label='Onboarding' if i == 0 else '')

        # Phase 2: Development (first experiment to first plot)
        if days_to_plot > days_to_exp:
            ax.barh(y_pos, days_to_plot - days_to_exp, left=days_to_exp, height=bar_height,
                    color=colors['development'], alpha=0.7, label='Development' if i == 0 else '')

        # Phase 3: Result production (first plot to first RES)
        if days_to_res > days_to_plot:
            ax.barh(y_pos, days_to_res - days_to_plot, left=days_to_plot, height=bar_height,
                    color=colors['result'], alpha=0.7, label='Result production' if i == 0 else '')

        # Add milestone markers
        milestones = [
            (0, 'first_day', 'Start'),
            (days_to_exp, 'first_experiment', 'Exp'),
            (days_to_plot, 'first_plot', 'Plot'),
            (days_to_res, 'first_res', 'RES'),
        ]

        for day, milestone_type, label in milestones:
            ax.scatter(day, y_pos, color=marker_colors[milestone_type], s=100, zorder=5,
                      edgecolor='white', linewidth=1.5)
            # Add day label above marker
            ax.annotate(f'{day}d', (day, y_pos + 0.3), ha='center', va='bottom',
                       fontsize=9, fontweight='bold')

    # Formatting
    ax.set_yticks(y_positions)
    ax.set_yticklabels([f'Researcher {r}' for r in researchers], fontsize=11)
    ax.set_xlabel('Days from First Day', fontsize=11)
    ax.set_title('Undergraduate Researcher Onboarding Timeline\n(Days from lab start to key milestones)',
                 fontsize=13, fontweight='bold')

    # Set x-axis limits with some padding
    max_days = max(calculate_days(d['first_day'], d['first_res']) for d in student_data.values())
    ax.set_xlim(-5, max_days + 15)
    ax.set_ylim(-0.5, 2.5)

    # Add gridlines
    ax.xaxis.grid(True, linestyle='--', alpha=0.5)
    ax.set_axisbelow(True)

    # Create legend for phases
    phase_patches = [
        mpatches.Patch(color=colors['onboarding'], alpha=0.7, label='Onboarding'),
        mpatches.Patch(color=colors['development'], alpha=0.7, label='Development'),
        mpatches.Patch(color=colors['result'], alpha=0.7, label='Result production'),
    ]

    # Create legend for markers
    marker_legend = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=marker_colors['first_day'],
                   markersize=10, label='First day'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=marker_colors['first_experiment'],
                   markersize=10, label='First experiment'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=marker_colors['first_plot'],
                   markersize=10, label='First plot'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=marker_colors['first_res'],
                   markersize=10, label='First RES'),
    ]

    # Add both legends
    legend1 = ax.legend(handles=phase_patches, loc='upper right', title='Phases')
    ax.add_artist(legend1)
    ax.legend(handles=marker_legend, loc='lower right', title='Milestones')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"  Saved: {output_path}")


def create_pin_timeline(student_data: dict, output_path: Path):
    """
    Create a track-based timeline with separate horizontal tracks per researcher.

    Features:
    - Each researcher gets their own horizontal track
    - Progress bars show phases (Onboarding → Development → Result)
    - Pin markers at milestone points with day labels
    - Researcher badges with pathway labels
    - Smart label positioning to avoid overlaps
    """
    fig, ax = plt.subplots(figsize=(14, 8))

    # Researcher colors
    researcher_colors = {
        'A': '#3B82F6',  # Blue
        'B': '#10B981',  # Emerald/teal
        'C': '#F59E0B',  # Amber/orange
    }

    # Phase colors
    phase_colors = {
        'onboarding': '#22C55E',  # Green (Start → Exp)
        'development': '#8B5CF6',  # Purple (Exp → RES)
    }

    # Milestone markers (matplotlib marker codes)
    milestone_markers = {
        'first_day': 'o',         # Circle for start
        'first_experiment': 'p',  # Pentagon (flask-like)
        'first_plot': '^',        # Triangle up (chart)
        'first_res': 'D',         # Diamond (result)
    }

    milestone_labels_short = {
        'first_day': 'Joined Lab',
        'first_experiment': 'Exp Assigned',
        'first_plot': 'First Plot',
        'first_res': 'RES Node',
    }

    # Pathway short labels
    pathway_short = {
        'Self-directed exploration': 'Self-Directed',
        'Assigned entry project': 'Entry Project',
        'Direct assignment': 'Direct Assign',
    }

    # Track y-positions (from top to bottom: A, B, C) - increased spacing
    track_y = {'A': 3.0, 'B': 1.8, 'C': 0.6}
    bar_height = 0.18
    pin_offset = 0.4  # Height of pins above track

    researchers = ['A', 'B', 'C']

    # X-axis configuration - extended left for badges
    x_min, x_max = -35, 145
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(-0.5, 4.5)

    # Draw each researcher's track
    for researcher_id in researchers:
        data = student_data[researcher_id]
        first_day = data['first_day']
        color = researcher_colors[researcher_id]
        y = track_y[researcher_id]
        pathway = pathway_short.get(data['pathway'], data['pathway'])

        # Calculate days
        days_to_exp = calculate_days(first_day, data['first_experiment'])
        days_to_plot = calculate_days(first_day, data['first_plot'])
        days_to_res = calculate_days(first_day, data['first_res'])

        # Draw progress bars
        # Phase 1: Onboarding (0 → first_experiment) - Green
        bar1 = mpatches.FancyBboxPatch(
            (0, y - bar_height / 2), days_to_exp, bar_height,
            boxstyle=mpatches.BoxStyle("Round", pad=0.02, rounding_size=0.1),
            facecolor=phase_colors['onboarding'], edgecolor='none', alpha=0.8, zorder=2
        )
        ax.add_patch(bar1)

        # Phase 2: Development/Result (first_experiment → first_res) - Purple
        bar2 = mpatches.FancyBboxPatch(
            (days_to_exp, y - bar_height / 2), days_to_res - days_to_exp, bar_height,
            boxstyle=mpatches.BoxStyle("Round", pad=0.02, rounding_size=0.1),
            facecolor=phase_colors['development'], edgecolor='none', alpha=0.8, zorder=2
        )
        ax.add_patch(bar2)

        # Draw researcher badge (circle with letter) - positioned to left of track
        badge_x = -25
        # Use scatter for the badge circle (better aspect ratio handling)
        ax.scatter(badge_x, y, s=1200, c=color, marker='o',
                  edgecolor='white', linewidth=3, zorder=10)
        ax.text(badge_x, y, researcher_id, ha='center', va='center',
               fontsize=14, fontweight='bold', color='white', zorder=11)

        # Researcher label below badge
        ax.text(badge_x, y - 0.55, f'Researcher {researcher_id}',
               ha='center', va='top', fontsize=9, fontweight='bold', color=color)
        ax.text(badge_x, y - 0.80, pathway,
               ha='center', va='top', fontsize=8, color='#6B7280', style='italic')

        # Collect milestones with their data
        milestones = [
            (0, 'first_day', milestone_labels_short['first_day']),
            (days_to_exp, 'first_experiment', milestone_labels_short['first_experiment']),
            (days_to_plot, 'first_plot', milestone_labels_short['first_plot']),
            (days_to_res, 'first_res', milestone_labels_short['first_res']),
        ]

        # Smart label positioning - stagger if milestones are close
        # Use different heights to avoid overlaps
        label_heights = []
        height_levels = [pin_offset, pin_offset + 0.25, pin_offset + 0.5]  # Three height levels
        for i, (day, mtype, label) in enumerate(milestones):
            base_height = pin_offset
            # Check distance from all previous milestones
            for j, prev_height in enumerate(label_heights):
                prev_day = milestones[j][0]
                if abs(day - prev_day) < 20:  # Within 20 days
                    # Need to stagger - find next available height
                    if prev_height == pin_offset:
                        base_height = max(base_height, pin_offset + 0.25)
                    elif prev_height == pin_offset + 0.25:
                        base_height = max(base_height, pin_offset + 0.5)
            label_heights.append(base_height)

        # Draw milestone pins
        for i, (day, mtype, label) in enumerate(milestones):
            marker = milestone_markers[mtype]
            pin_h = label_heights[i]

            # Vertical dashed stem
            ax.plot([day, day], [y + bar_height / 2, y + pin_h],
                   color=color, linewidth=1.5, linestyle='--', alpha=0.7, zorder=3)

            # Pin head (marker)
            ax.scatter(day, y + pin_h, marker=marker, s=250, color=color,
                      edgecolor='white', linewidth=2, zorder=5)

            # Milestone label above pin
            ax.text(day, y + pin_h + 0.15, label, ha='center', va='bottom',
                   fontsize=8, color='#374151', fontweight='medium')

            # Day label below the label
            ax.text(day, y + pin_h + 0.08, f'{day}d', ha='center', va='top',
                   fontsize=9, color=color, fontweight='bold')

    # Remove spines
    for spine in ax.spines.values():
        spine.set_visible(False)

    # X-axis
    ax.set_xlabel('Days from First Day in Lab', fontsize=11, fontweight='medium')
    ax.set_xticks([0, 20, 40, 60, 80, 100, 120, 140])
    ax.tick_params(axis='x', labelsize=10, length=5)

    # Hide y-axis
    ax.set_yticks([])

    # Add subtle grid
    ax.xaxis.grid(True, linestyle='--', alpha=0.3, zorder=0)
    ax.set_axisbelow(True)

    # Title - positioned higher to avoid overlap with legend
    ax.set_title('Undergraduate Researcher Onboarding Timeline',
                fontsize=14, fontweight='bold', pad=40)

    # Top legend for milestone types - positioned below title
    legend_items = [
        mlines.Line2D([], [], color='#6B7280', marker='o', linestyle='None',
                     markersize=10, markeredgecolor='white', markeredgewidth=1.5, label='Start'),
        mlines.Line2D([], [], color='#6B7280', marker='p', linestyle='None',
                     markersize=10, markeredgecolor='white', markeredgewidth=1.5, label='Experiment'),
        mlines.Line2D([], [], color='#6B7280', marker='^', linestyle='None',
                     markersize=10, markeredgecolor='white', markeredgewidth=1.5, label='Plot'),
        mlines.Line2D([], [], color='#6B7280', marker='D', linestyle='None',
                     markersize=10, markeredgecolor='white', markeredgewidth=1.5, label='Result (RES)'),
    ]
    legend1 = ax.legend(handles=legend_items, loc='upper center', ncol=4,
                       bbox_to_anchor=(0.5, 1.02), frameon=False, fontsize=10)
    ax.add_artist(legend1)

    # Bottom legend for phase colors - single line
    ax.text(0.5, -0.10, 'Horizontal bars represent phases: ', transform=ax.transAxes,
           ha='right', va='top', fontsize=10, color='#6B7280')
    ax.text(0.50, -0.10, 'Onboarding', transform=ax.transAxes,
           ha='left', va='top', fontsize=10, color=phase_colors['onboarding'], fontweight='bold')
    ax.text(0.60, -0.10, '→', transform=ax.transAxes,
           ha='center', va='top', fontsize=10, color='#6B7280')
    ax.text(0.62, -0.10, 'Development → Result', transform=ax.transAxes,
           ha='left', va='top', fontsize=10, color=phase_colors['development'], fontweight='bold')

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12, top=0.90)  # Make room for legends
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"  Saved: {output_path}")


def create_pin_timeline_interactive(student_data: dict, output_path: Path):
    """
    Create an interactive track-based timeline using Plotly.

    Features:
    - Separate horizontal tracks per researcher
    - Progress bars showing phases
    - Hover for milestone details
    - Zoom and pan
    - Responsive design
    """
    if not PLOTLY_AVAILABLE:
        print("  Skipping interactive timeline (Plotly not installed)")
        return

    # Researcher colors
    researcher_colors = {
        'A': '#3B82F6',  # Blue
        'B': '#10B981',  # Emerald/teal
        'C': '#F59E0B',  # Amber/orange
    }

    # Phase colors
    phase_colors = {
        'onboarding': '#22C55E',  # Green
        'development': '#8B5CF6',  # Purple
    }

    # Milestone symbols (Plotly symbol names)
    milestone_symbols = {
        'first_day': 'circle',
        'first_experiment': 'pentagon',
        'first_plot': 'triangle-up',
        'first_res': 'diamond',
    }

    milestone_labels = {
        'first_day': 'Joined Lab',
        'first_experiment': 'Experiment Assigned',
        'first_plot': 'First Plot',
        'first_res': 'RES Node Created',
    }

    # Pathway short labels
    pathway_short = {
        'Self-directed exploration': 'Self-Directed',
        'Assigned entry project': 'Entry Project',
        'Direct assignment': 'Direct Assign',
    }

    # Track y-positions
    track_y = {'A': 2.5, 'B': 1.5, 'C': 0.5}
    bar_height = 0.2

    fig = go.Figure()
    researchers = ['A', 'B', 'C']

    for researcher_id in researchers:
        data = student_data[researcher_id]
        first_day = data['first_day']
        color = researcher_colors[researcher_id]
        y = track_y[researcher_id]
        pathway = pathway_short.get(data['pathway'], data['pathway'])

        # Calculate days
        days_to_exp = calculate_days(first_day, data['first_experiment'])
        days_to_plot = calculate_days(first_day, data['first_plot'])
        days_to_res = calculate_days(first_day, data['first_res'])

        # Phase 1: Onboarding bar (0 → exp)
        fig.add_trace(go.Scatter(
            x=[0, days_to_exp, days_to_exp, 0, 0],
            y=[y - bar_height, y - bar_height, y + bar_height, y + bar_height, y - bar_height],
            fill='toself',
            fillcolor=phase_colors['onboarding'],
            line=dict(width=0),
            hovertemplate=f'Researcher {researcher_id}<br>Onboarding Phase<br>Days 0-{days_to_exp}<extra></extra>',
            showlegend=False,
        ))

        # Phase 2: Development bar (exp → res)
        fig.add_trace(go.Scatter(
            x=[days_to_exp, days_to_res, days_to_res, days_to_exp, days_to_exp],
            y=[y - bar_height, y - bar_height, y + bar_height, y + bar_height, y - bar_height],
            fill='toself',
            fillcolor=phase_colors['development'],
            line=dict(width=0),
            hovertemplate=f'Researcher {researcher_id}<br>Development → Result<br>Days {days_to_exp}-{days_to_res}<extra></extra>',
            showlegend=False,
        ))

        # Milestones
        milestones = [
            (0, 'first_day'),
            (days_to_exp, 'first_experiment'),
            (days_to_plot, 'first_plot'),
            (days_to_res, 'first_res'),
        ]

        # Calculate staggered heights for close milestones
        pin_heights = []
        base_height = 0.5
        for i, (day, mtype) in enumerate(milestones):
            height = base_height
            if i > 0:
                prev_day = milestones[i - 1][0]
                if abs(day - prev_day) < 15:
                    height = base_height + 0.25 if pin_heights[-1] == base_height else base_height
            pin_heights.append(height)

        for i, (day, mtype) in enumerate(milestones):
            symbol = milestone_symbols[mtype]
            label = milestone_labels[mtype]
            pin_h = pin_heights[i]

            # Vertical dashed line (stem)
            fig.add_trace(go.Scatter(
                x=[day, day],
                y=[y + bar_height, y + pin_h],
                mode='lines',
                line=dict(color=color, width=2, dash='dash'),
                hoverinfo='skip',
                showlegend=False,
            ))

            # Pin head marker
            fig.add_trace(go.Scatter(
                x=[day],
                y=[y + pin_h],
                mode='markers+text',
                marker=dict(
                    symbol=symbol,
                    size=18,
                    color=color,
                    line=dict(color='white', width=2),
                ),
                text=[f'{label}<br><b>{day}d</b>'],
                textposition='top center',
                textfont=dict(size=10, color='#374151'),
                hovertemplate=(
                    f'<b>Researcher {researcher_id}</b><br>'
                    f'{label}<br>'
                    f'Day {day}<br>'
                    f'Pathway: {data["pathway"]}'
                    '<extra></extra>'
                ),
                showlegend=False,
            ))

        # Researcher badge annotation
        fig.add_annotation(
            x=-20, y=y,
            text=f'<b style="font-size:16px; color:{color}">{researcher_id}</b>',
            showarrow=False,
            font=dict(size=16, color=color),
            xanchor='center',
        )

        # Researcher label
        fig.add_annotation(
            x=-20, y=y - 0.35,
            text=f'Researcher {researcher_id}',
            showarrow=False,
            font=dict(size=11, color=color),
            xanchor='center',
        )

        # Pathway label
        fig.add_annotation(
            x=-20, y=y - 0.55,
            text=f'<i>{pathway}</i>',
            showarrow=False,
            font=dict(size=10, color='#6B7280'),
            xanchor='center',
        )

    # Add legend traces for milestone types
    for mtype, symbol in milestone_symbols.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=12, color='#6B7280', symbol=symbol),
            name=milestone_labels[mtype],
            showlegend=True,
        ))

    fig.update_layout(
        title=dict(
            text='Undergraduate Researcher Onboarding Timeline',
            font=dict(size=18),
            x=0.5,
        ),
        xaxis=dict(
            title='Days from First Day in Lab',
            range=[-35, 150],
            tickvals=[0, 20, 40, 60, 80, 100, 120, 140],
            gridcolor='rgba(0,0,0,0.1)',
            zeroline=False,
        ),
        yaxis=dict(
            visible=False,
            range=[-0.2, 3.5],
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            font=dict(size=11),
        ),
        height=550,
        margin=dict(l=50, r=50, t=100, b=80),
        annotations=[
            dict(
                x=0.5, y=-0.12,
                xref='paper', yref='paper',
                text='Horizontal bars: <span style="color:#22C55E;font-weight:bold">Onboarding</span> → <span style="color:#8B5CF6;font-weight:bold">Development → Result</span>',
                showarrow=False,
                font=dict(size=12),
                xanchor='center',
            ),
        ],
    )

    fig.write_html(output_path, include_plotlyjs='cdn')
    print(f"  Saved: {output_path}")


def create_comparison_bar_chart(student_data: dict, output_path: Path):
    """
    Create a grouped bar chart comparing days to each milestone across researchers.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    researchers = ['A', 'B', 'C']
    milestones = ['Days to\nFirst Experiment', 'Days to\nFirst Plot', 'Days to\nFirst RES']

    # Extract data
    data = []
    for researcher_id in researchers:
        d = student_data[researcher_id]
        first_day = d['first_day']
        data.append([
            calculate_days(first_day, d['first_experiment']),
            calculate_days(first_day, d['first_plot']),
            calculate_days(first_day, d['first_res']),
        ])

    data = np.array(data)

    x = np.arange(len(milestones))
    width = 0.25

    colors = ['#3498db', '#2ecc71', '#9b59b6']

    for i, (researcher_id, color) in enumerate(zip(researchers, colors)):
        bars = ax.bar(x + i * width, data[i], width, label=f'Researcher {researcher_id}', color=color, alpha=0.8)
        # Add value labels on bars
        for bar, val in zip(bars, data[i]):
            ax.annotate(f'{val}', (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                       ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_ylabel('Days from First Day', fontsize=11)
    ax.set_title('Comparison of Onboarding Milestones Across Researchers', fontsize=13, fontweight='bold')
    ax.set_xticks(x + width)
    ax.set_xticklabels(milestones, fontsize=10)
    ax.legend(loc='upper left')

    # Add lab average line for RES
    lab_avg_res = 88.3
    ax.axhline(y=lab_avg_res, color='red', linestyle='--', alpha=0.7, label='Lab avg (RES)')
    ax.annotate(f'Lab avg: {lab_avg_res}d', (2.5, lab_avg_res + 3), ha='right', va='bottom',
               fontsize=9, color='red')

    ax.set_ylim(0, max(data.flatten()) + 20)
    ax.yaxis.grid(True, linestyle='--', alpha=0.5)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"  Saved: {output_path}")


def save_milestones_json(student_data: dict, output_path: Path):
    """Save milestone data to JSON file."""
    milestones = compute_milestones(student_data)

    # Add summary statistics
    all_res_days = [m['days_to_res'] for m in milestones.values()]
    milestones['_summary'] = {
        'mean_days_to_res': round(sum(all_res_days) / len(all_res_days), 1),
        'min_days_to_res': min(all_res_days),
        'max_days_to_res': max(all_res_days),
        'lab_average_days_to_res': 88.3,
        'note': 'Researcher identities anonymized in visualizations',
    }

    with open(output_path, 'w') as f:
        json.dump(milestones, f, indent=2)

    print(f"  Saved: {output_path}")


def generate_student_timeline_visualizations(output_dir: Path):
    """Generate all student timeline visualizations."""
    print("\nGenerating student timeline visualizations...")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate pin-style timeline (main figure for EVD 7)
    create_pin_timeline(STUDENT_DATA, output_dir / 'fig7_student_timelines.png')

    # Generate interactive HTML version
    create_pin_timeline_interactive(STUDENT_DATA, output_dir / 'fig7_student_timelines.html')

    # Generate comparison bar chart (supplementary)
    create_comparison_bar_chart(STUDENT_DATA, output_dir / 'student_milestone_comparison.png')

    # Save JSON data
    save_milestones_json(STUDENT_DATA, output_dir.parent / 'student_milestones.json')

    print("\nStudent timeline analysis complete!")

    # Print summary
    print("\nSummary:")
    milestones = compute_milestones(STUDENT_DATA)
    for researcher_id in ['A', 'B', 'C']:
        m = milestones[researcher_id]
        print(f"  Researcher {researcher_id}: {m['days_to_experiment']}d to exp, "
              f"{m['days_to_plot']}d to plot, {m['days_to_res']}d to RES ({m['pathway']})")


if __name__ == '__main__':
    base_path = Path(__file__).parent.parent
    output_dir = base_path / 'output' / 'visualizations'
    generate_student_timeline_visualizations(output_dir)
