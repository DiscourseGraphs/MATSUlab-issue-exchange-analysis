# Methods Excerpt (EVD 1)

This excerpt contains the methods sections relevant to the issue conversion rate analysis. See `data/conversion_data.json` for current data counts.

---

## 2. Node Identification

### 2.1 Experiment Pages

Experiment pages are identified by titles starting with `@` followed by a type prefix and `/` separator. Examples:

- `@analysis/Report the percentage of simulated endocytic events...`
- `@TC/Test antibody staining for Arp2/3...`
- `@cytosim/vary Arp2/3 complex periodicity...`

**Pattern:** `re.match(r'^@[a-zA-Z]+/', title)` — `src/parse_jsonld.py`, `find_experiment_pages()` (line 69)

**Domain context:** When a researcher claims an Issue, the Issue page is converted to an Experiment page. The same underlying Roam page is renamed from `[[ISS]] - <description>` to `@type/<description>`. Therefore, the page's creation date reflects when the original Issue was created, not when claiming occurred.

### 2.2 Issue (ISS) Nodes

Issue nodes are identified by `[[ISS]]` appearing in the page title.

**Pattern:** `re.search(r'\[\[ISS\]\]', title)` — `src/parse_jsonld.py`, `extract_nodes_by_type()` (line 30)

These represent Issues that remain in their original, unclaimed state (i.e., they were never converted to an Experiment page).

---

## 3. Claiming Detection

The claiming status of an experiment page is determined through a two-tier approach. Each claimed experiment is assigned a `claim_type` of either `'explicit'` or `'inferred'`.

**Implementation:** `src/calculate_metrics.py`, `merge_experiment_data()` (line 45)

### 3.1 Explicitly Claimed (`claim_type = 'explicit'`)

An experiment page is explicitly claimed if it contains a `Claimed By::` field in its content, populated with a person name in Roam's `[[Person Name]]` link format.

**Detection (JSON-LD):** Regex extraction from the page `content` field:
```
Claimed By::\s*\[([^\]]+)\]\([^)]+\)    (markdown link)
Claimed By::\s*\[\[([^\]]+)\]\]          (wiki link)
```
— `src/parse_jsonld.py`, `extract_claimed_by_from_content()` (line 87)

**Detection (Roam JSON):** Block-level search for blocks containing `Claimed By::`, extracting the person name and block `create-time`:
— `src/parse_roam_json.py`, `extract_claimed_by_timestamp()` (line 147)

The `Issue Created By::` field is extracted similarly to identify the person who originally created the issue.

When both JSON-LD and Roam JSON provide a `Claimed By` value, the Roam JSON value is preferred because it also provides the block creation timestamp (used for time-to-claiming).

**Count in current data:** 69 explicitly claimed

### 3.2 Inferred Claiming (`claim_type = 'inferred'`)

Many experiment pages (~60%) lack formal `Claimed By::` and `Issue Created By::` metadata fields. For these, claiming is inferred if:

1. The experiment page has an "Experimental Log" or "Experiment Log" section, AND
2. That section contains at least one dated child block (matching the pattern `[[<date>, <year>]]`), AND
3. The page has a known `creator` in the JSON-LD metadata

When these conditions are met:
- **Claimed By** is set to the JSON-LD `creator` field value (the person who created the page)
- **Issue Created By** is also set to the `creator` (if not already populated), since the creator of an experiment page without formal metadata is assumed to be both the issue author and the person claiming it (self-claiming)
- **Claiming timestamp** is set to the `create-time` of the earliest dated block in the experimental log

**Rationale:** Researchers sometimes begin working on an issue directly within its page (adding experimental log entries) without formally filling in the `Claimed By::` field. The presence of substantive experimental log entries indicates active work.

**Detection of experimental log:**
— `src/parse_roam_json.py`, `has_experimental_log()` (line 193) — checks for header block matching `Experiment(al)?\s+Log` with child blocks containing date patterns
— `src/parse_roam_json.py`, `get_experimental_log_entries()` (line 221) — extracts all dated entries

**Count in current data:** 56 inferred claiming

### 3.3 ISS Pages with Activity

A small number of ISS pages (pages that were never renamed to experiment format) also contain experimental log entries, indicating work was done without formal page conversion. These are counted separately in the conversion rate denominator.

**Count in current data:** 5 ISS pages with activity

### 3.4 Unclaimed Issues

ISS pages with no experimental log entries are considered unclaimed.

**Count in current data:** 315 unclaimed ISS pages

---

## 6. Metric Definitions and Calculations

### 6.1 Metric 1: Issue Conversion Rate

**Definition:** Percentage of all known issues that have been claimed and converted to active experiments.

**Formula:**

```
Total Claimed = Explicitly Claimed + Inferred Claiming + ISS Pages with Activity
Total Issues  = Total Claimed + Unclaimed ISS Pages
Conversion Rate = Total Claimed / Total Issues × 100
```

**Components:**
| Component | Definition | Count |
|-----------|-----------|-------|
| Explicitly Claimed | Experiment pages with `Claimed By::` field | 69 |
| Inferred Claiming | Experiment pages with experimental log (no `Claimed By::`) | 56 |
| ISS with Activity | ISS pages with experimental log entries | 5 |
| Unclaimed ISS | ISS pages with no experimental log | 315 |
| **Total Claimed** | | **130** |
| **Total Issues** | | **445** |

**Result:** 29.2%

**Implementation:** `src/calculate_metrics.py`, `calculate_conversion_rate()` (line 165)
