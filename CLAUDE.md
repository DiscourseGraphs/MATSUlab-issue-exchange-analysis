# Node Metrics Project

## Project Overview
This repository contains analysis tools for tracking research lab metrics from a Roam Research-based discourse graph system. The primary focus is on quantifying researcher contributions, onboarding timelines, and knowledge graph structure.

## Key Data Sources
- **Roam Research exports**: Daily notes, experiment pages, result (RES) pages
- **Discourse graph nodes**: ISS (Issues), RES (Results), EVD (Evidence), QUE (Questions), HYP (Hypotheses), CLM (Claims), CON (Conclusions)
- **metrics_data.json**: Pre-extracted metrics about issues, issue claiming, and researcher activity

## Evidence Bundles (EVD)
Evidence bundles are stored in `output/evidence_bundles/` with JSON-LD + RO-Crate metadata format:
- `evd7-student-onboarding/`: Undergraduate researcher onboarding timeline analysis

## Student Timeline Analysis (EVD 7)

### Researchers Tracked (Anonymized)
| ID | Start Date | Days to Exp | Days to Plot | Days to RES | Pathway |
|----|------------|-------------|--------------|-------------|---------|
| A  | Feb 23, 2024 | 42 | 118 | 125 | Self-directed exploration |
| B  | Oct 10, 2024 | 5 | 5 | 47 | Assigned entry project |
| C  | Jun 23, 2025 | 7 | 14 | 36 | Direct assignment |

### Key Files
- `src/student_timeline_analysis.py`: Generates timeline visualizations
- `output/visualizations/fig7_student_timelines.png`: Static matplotlib figure
- `output/visualizations/fig7_student_timelines_app.html`: **Polished interactive HTML/JS app** (matches target design)
- `output/visualizations/fig7_student_timelines.html`: Plotly-based interactive version
- `output/student_milestones.json`: Extracted milestone data

### Visualization Design Notes
The target design (`target_plot.png`) features:
1. **Single consolidated timeline** - All researchers share one x-axis at bottom
2. **Vertical pins** rising at different heights per researcher to avoid overlap
3. **Circular icons** with symbols inside (play=start, flask=experiment, chart=plot, checkmark=result)
4. **Thin progress bars at bottom** showing each researcher's timeline span (color-coded by researcher)
5. **Summary cards** with insights about each pathway
6. **Interactive zoom toggle** for first 50 days
7. Clean typography, whitespace, and modern styling

**Important**: The polished design requires HTML/JS (`fig7_student_timelines_app.html`), not matplotlib. Matplotlib has limitations for achieving this level of visual polish.

### Result Statement (EVD 7)
> All three undergraduate researchers generated an original result from their analysis projects within ~4 months of joining the lab, with two creating a result within ~1 month

## Code Patterns

### Visualization Functions
```python
# In src/student_timeline_analysis.py
generate_student_timeline_visualizations(output_dir)  # Main entry point
create_pin_timeline()           # Matplotlib static PNG
create_pin_timeline_interactive()  # Plotly HTML
create_comparison_bar_chart()   # Bar chart comparing milestones
```

### Researcher Colors (Consistent Across Visualizations)
```python
researcher_colors = {
    'A': '#3B82F6',  # Blue
    'B': '#10B981',  # Emerald/teal
    'C': '#F59E0B',  # Amber/orange
}
```

### Phase Colors
```python
phase_colors = {
    'onboarding': '#22C55E',  # Green (Start → Exp)
    'development': '#8B5CF6',  # Purple (Exp → RES)
}
```

## Running the Analysis
```bash
python src/student_timeline_analysis.py
```

Outputs:
- `output/visualizations/fig7_student_timelines.png`
- `output/visualizations/fig7_student_timelines.html`
- `output/visualizations/student_milestone_comparison.png`
- `output/student_milestones.json`
