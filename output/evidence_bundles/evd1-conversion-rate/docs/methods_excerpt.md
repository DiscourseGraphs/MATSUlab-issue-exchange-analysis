# Methods Excerpt (EVD 1)

This excerpt contains the methods sections relevant to the issue conversion rate analysis. For the complete methods document, see `output/methods.md`.

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

### 2.3 Result (RES) Nodes

Result nodes are identified by `[[RES]]` appearing in the page title. Example:

`[[RES]] - some result description - [[@analysis/experiment name]]`

RES titles frequently contain a backreference to their source experiment in `[[@type/name]]` format.

**Pattern:** `re.search(r'\[\[RES\]\]', title)` — `src/parse_jsonld.py`, `extract_nodes_by_type()` (line 30)

---


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

### 6.2 Metric 2: Time-to-Claiming

**Definition:** Duration (in days) from when an Issue was created to when it was claimed.

**Formula:**

```
Time-to-Claiming = Claiming Timestamp − Issue Creation Date
```

Where:
- **Claiming Timestamp** = `create-time` of the `Claimed By::` block (explicitly claimed) or earliest experimental log entry (inferred)
- **Issue Creation Date** = minimum of (JSON-LD `created`, Roam page `create-time`, earliest block `create-time`) — see Section 4.1

**Inclusion criteria:** Only experiments with both a known claiming timestamp and a known issue creation date are included. This yields 125 experiments (out of 130 claimed).

**Results:**
| Statistic | Value |
|-----------|-------|
| Average | 53.5 days |
| Median | 0 days |
| Min | 0 days |
| Max | 483 days |

The high frequency of 0-day values reflects cases where an issue was created and immediately claimed (same day).

**Implementation:** `src/calculate_metrics.py`, `calculate_time_to_claim()` (line 221)

### 6.3 Metric 3: Time-to-First-Result

**Definition:** Duration (in days) from when an experiment was claimed to when the first linked Result (RES) node was created.

**Formula:**

```
Time-to-First-Result = Earliest Linked RES Creation Date − Reference Timestamp
```

Where:
- **Reference Timestamp** =
  - For explicitly claimed: `Claimed By::` block `create-time`
  - For inferred claiming: Issue creation date (page_created), since there is no formal claiming event
- **Earliest Linked RES** = the RES node with the earliest `created` date among those linked to the experiment (see Section 5 for linking methods)

**Inclusion criteria:** Only claimed experiments that have at least one linked RES node with a parseable creation date. This yields 50 experiments.

**Results:**
| Statistic | Value |
|-----------|-------|
| Average | 88.3 days |
| Min | −1 days |
| Max | 754 days |

The single −1 day case represents a RES node created approximately 6 minutes before the `Claimed By::` block was populated — likely filled in during the same session.

**Implementation:** `src/calculate_metrics.py`, `calculate_time_to_first_result()` (line 371)

### 6.4 Metric 4: Unique Contributors per Issue Chain

**Definition:** Count of distinct researchers involved in the full Issue → Experiment → Result chain for each claimed experiment.

**Contributors include:**
- `Issue Created By::` person
- `Claimed By::` person
- Page `creator` (from JSON-LD)
- `creator` of each linked RES node

**Results:**
| Contributors | Experiments |
|-------------|-------------|
| 1 | 90 |
| 2 | 29 |
| 3 | 3 |
| **Average** | **1.29** |

**Implementation:** `src/calculate_metrics.py`, `calculate_unique_contributors()` (line 446)

### 6.5 Metric 5: Cross-Person Claiming (Idea Exchange)

**Definition:** Cases where the person who claimed an issue (`Claimed By::`) is different from the person who created the issue (`Issue Created By::`). This is the key metric demonstrating transfer of ideas between researchers.

**Formula:**

```
Idea Exchange Rate = Cross-Person Claiming / (Cross-Person Claiming + Self-Claiming) × 100
```

Only experiments where both `Issue Created By` and `Claimed By` are known are included in the denominator. Experiments with unknown issue creators are excluded from the rate calculation.

**Results:**
| Metric | Value |
|--------|-------|
| Cross-Person Claiming | 19 |
| Self-Claiming | 106 |
| Idea Exchange Rate | 15.2% |

**Implementation:** `src/calculate_metrics.py`, `calculate_cross_person_claims()` (line 524)

---


---
