# Methods Excerpt (EVD 6)

This excerpt contains the methods sections relevant to the time-to-result analysis. See `data/time_to_result_data.json` for current summary statistics and per-experiment timing data.

---

## 2.3 Result (RES) Nodes

Result nodes are identified by `[[RES]]` appearing in the page title. Example:

`[[RES]] - some result description - [[@analysis/experiment name]]`

RES titles frequently contain a backreference to their source experiment in `[[@type/name]]` format.

**Pattern:** `re.search(r'\[\[RES\]\]', title)` — `src/parse_jsonld.py`, `extract_nodes_by_type()` (line 30)

---

## 4. Timestamp Handling

### 4.1 Issue Creation Date

Since experiment pages are converted Issues (same Roam page, renamed), the page creation date serves as the Issue creation date. However, Roam page merges can update the page-level `create-time`, making it unreliable as a sole proxy.

To handle this, the Issue creation date is computed as the **minimum** of three candidates:

1. **JSON-LD `created`** — ISO 8601 timestamp from the JSON-LD export
2. **Roam page `create-time`** — Unix millisecond timestamp from the Roam JSON export
3. **Earliest block `create-time`** — The earliest `create-time` across all blocks on the page

The earliest block timestamp is the most robust because block timestamps are preserved even when pages are merged.

**Implementation:** `src/calculate_metrics.py`, `merge_experiment_data()` (lines 87–104)
**Earliest block scanner:** `src/parse_roam_json.py`, `get_earliest_block_timestamp()` (line 261)

### 4.2 Claiming Timestamp

For **explicitly claimed** experiments, the claiming timestamp is the `create-time` of the `Claimed By::` block in the Roam JSON export. This represents when the researcher filled in the field.

For **inferred claiming**, the claiming timestamp is the `create-time` of the earliest dated block in the experimental log section.

**Implementation:** `src/parse_roam_json.py`, `extract_claimed_by_timestamp()` (line 147)

### 4.3 Timezone Normalization

JSON-LD timestamps are in UTC (ISO 8601 with `Z` suffix). Roam JSON timestamps are Unix milliseconds (inherently UTC). All timestamps are converted to timezone-naive UTC `datetime` objects using `datetime.utcfromtimestamp()` for Roam data and `datetime.fromisoformat()` with UTC normalization for JSON-LD data.

**Implementation:** `src/calculate_metrics.py`, `normalize_datetime()` (line 25)

---

## 5. Linking Result (RES) Nodes to Experiments

RES nodes are linked to experiment pages using a three-tier matching strategy, applied in order of reliability:

### 5.1 Method 1: Relation Instances (Most Reliable)

The JSON-LD export contains `relationInstance` entries that explicitly encode typed relationships between nodes. A bidirectional map is built from experiment UIDs to linked RES node UIDs.

**Implementation:** `src/calculate_metrics.py`, `_build_relation_map()` (line 271)

### 5.2 Method 2: Backreference Matching

RES node titles frequently contain a backreference to their source experiment in the format `[[@type/experiment name]]`. For example:

```
[[RES]] - some result - [[@analysis/Report the percentage of simulated...]]
```

If Method 1 yields no matches, the experiment's full title is searched for as a `[[title]]` substring in RES node titles (case-insensitive).

### 5.3 Method 3: Full Description Matching (Fallback)

If Methods 1 and 2 yield no matches, a substring match is attempted using the experiment's description (the portion after the first `/` in the title). This match is restricted to:

- **Title only** (not content, to avoid false positives from citation references)
- **Minimum 20 characters** of the description string
- **First-slash split** only (`split('/', 1)`) to avoid breaking on names like "Arp2/3"

**Implementation (all three methods):** `src/calculate_metrics.py`, `_find_linked_res_nodes()` (line 293)

---

## 6. Metric Definitions and Calculations

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

**Implementation:** `src/calculate_metrics.py`, `calculate_time_to_first_result()` (line 371)
