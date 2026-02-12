#!/usr/bin/env python3
"""
Calculate Issue Metrics
========================
Computes all 5 metrics from the parsed discourse graph data:
1. Issue Conversion Rate
2. Time-to-Claim
3. Time-to-First-Result
4. Unique Contributors per Issue Chain
5. Cross-Person Claims (Idea Exchange)

Author: Matt Akamatsu (with Claude)
Date: 2026-01-25
"""

import json
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path
from typing import Optional

from parse_jsonld import analyze_graph, parse_date


def normalize_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Normalize datetime to timezone-naive for comparison.
    Converts to UTC then removes timezone info.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Convert to UTC then make naive
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
from parse_roam_json import (
    analyze_all_experiment_pages,
    analyze_iss_pages,
    load_roam_json_streaming,
    find_block_by_content,
    get_block_timestamp,
)


def merge_experiment_data(jsonld_data: dict, roam_timestamps: dict) -> list[dict]:
    """
    Merge experiment data from JSON-LD with timestamps from Roam JSON.

    Returns list of experiment dicts with combined metadata.
    """
    merged = []

    for exp in jsonld_data['experiment_pages']:
        title = exp['title']
        roam_data = roam_timestamps.get(title, {})

        # Determine if this is a claimed issue
        claimed_by = exp.get('claimed_by')
        claimed_by_timestamp = None
        claim_type = None  # 'explicit' or 'inferred'

        if roam_data.get('claimed_by'):
            person, timestamp = roam_data['claimed_by']
            claimed_by = person
            claimed_by_timestamp = timestamp
            claim_type = 'explicit'

        # Get issue created by
        issue_created_by = exp.get('issue_created_by')
        if roam_data.get('issue_created_by'):
            person, _ = roam_data['issue_created_by']
            issue_created_by = person

        # Get made_by (Made by:: / Creator:: / Created by::) - highest priority attribution
        made_by = exp.get('made_by')  # from JSON-LD content
        if roam_data.get('made_by'):
            person, _ = roam_data['made_by']
            made_by = person  # Roam data preferred (has block-level info)

        # Get author (Author::) - lowest priority fallback
        author = exp.get('author')  # from JSON-LD content
        if roam_data.get('author'):
            person, _ = roam_data['author']
            author = person

        # Infer self-claim: if no Claimed By field but has experimental log
        # with content, the page creator is effectively self-claiming
        if not claimed_by and roam_data.get('has_experimental_log', False):
            if roam_data.get('log_entry_count', 0) > 0 and exp.get('creator'):
                claimed_by = exp['creator']
                # Use first log entry as claim timestamp
                if roam_data.get('first_log_entry'):
                    claimed_by_timestamp = roam_data['first_log_entry']
                # Also infer issue_created_by as creator if not set
                if not issue_created_by:
                    issue_created_by = exp['creator']
                claim_type = 'inferred'

        # Resolve primary_contributor using priority chain:
        # Made by/Creator/Created by > Claimed By > Author > JSON-LD creator
        primary_contributor = None
        attribution_method = None
        if made_by:
            primary_contributor = made_by
            attribution_method = 'made_by'
        elif claimed_by:
            primary_contributor = claimed_by
            attribution_method = 'claimed_by'
        elif author:
            primary_contributor = author
            attribution_method = 'author'
        elif exp.get('creator'):
            primary_contributor = exp['creator']
            attribution_method = 'creator'

        # Page creation date (= Issue creation date for converted issues)
        # Use the earliest of: JSON-LD created, Roam page created, earliest block timestamp
        # This handles cases where pages were merged and the page create-time was updated
        page_created_candidates = []
        if exp.get('created'):
            jsonld_created = normalize_datetime(parse_date(exp['created']))
            if jsonld_created:
                page_created_candidates.append(jsonld_created)
        if roam_data.get('page_created'):
            roam_created = normalize_datetime(roam_data['page_created'])
            if roam_created:
                page_created_candidates.append(roam_created)
        if roam_data.get('earliest_block_timestamp'):
            earliest_block = normalize_datetime(roam_data['earliest_block_timestamp'])
            if earliest_block:
                page_created_candidates.append(earliest_block)

        page_created = min(page_created_candidates) if page_created_candidates else None

        # Normalize claimed_by_timestamp
        if claimed_by_timestamp:
            claimed_by_timestamp = normalize_datetime(claimed_by_timestamp)

        merged.append({
            'uid': exp['uid'],
            'title': title,
            'creator': exp.get('creator'),
            'page_created': page_created,
            'claimed_by': claimed_by,
            'claimed_by_timestamp': claimed_by_timestamp,
            'issue_created_by': issue_created_by,
            'made_by': made_by,
            'author': author,
            'primary_contributor': primary_contributor,
            'attribution_method': attribution_method,
            'claim_type': claim_type,  # 'explicit', 'inferred', or None
            'status': exp.get('status'),
            'has_experimental_log': roam_data.get('has_experimental_log', False),
            'first_log_entry': roam_data.get('first_log_entry'),
            'log_entry_count': roam_data.get('log_entry_count', 0),
            'is_claimed': bool(claimed_by) or roam_data.get('has_experimental_log', False),
        })

    return merged


def merge_iss_data(jsonld_data: dict, roam_iss_data: dict) -> list[dict]:
    """
    Merge ISS node data from JSON-LD with Roam JSON data.

    Returns list of ISS node dicts with combined metadata.
    """
    merged = []

    for iss in jsonld_data['iss_nodes']:
        title = iss['title']
        roam_data = roam_iss_data.get(title, {})

        page_created = None
        if iss.get('created'):
            page_created = normalize_datetime(parse_date(iss['created']))
        elif roam_data.get('page_created'):
            page_created = normalize_datetime(roam_data['page_created'])

        has_log = roam_data.get('has_experimental_log', False)
        first_log = normalize_datetime(roam_data.get('first_log_entry'))

        # Get made_by and author from both sources
        made_by = iss.get('made_by')
        if roam_data.get('made_by'):
            person, _ = roam_data['made_by']
            made_by = person
        author_val = iss.get('author')
        if roam_data.get('author'):
            person, _ = roam_data['author']
            author_val = person

        # Resolve primary_contributor
        primary_contributor = None
        attribution_method = None
        if made_by:
            primary_contributor = made_by
            attribution_method = 'made_by'
        elif author_val:
            primary_contributor = author_val
            attribution_method = 'author'
        elif iss.get('creator'):
            primary_contributor = iss['creator']
            attribution_method = 'creator'

        merged.append({
            'uid': iss['uid'],
            'title': title,
            'creator': iss.get('creator'),
            'page_created': page_created,
            'made_by': made_by,
            'author': author_val,
            'primary_contributor': primary_contributor,
            'attribution_method': attribution_method,
            'status': iss.get('status'),
            'has_experimental_log': has_log,
            'first_log_entry': first_log,
            'log_entry_count': roam_data.get('log_entry_count', 0),
            'is_claimed': has_log,  # ISS with experimental log = work being done
        })

    return merged


def calculate_conversion_rate(experiments: list[dict], iss_nodes: list[dict]) -> dict:
    """
    Calculate Issue Conversion Rate.

    Claimed issues =
        - Experiment pages with Claimed By:: field (converted from ISS)
        - ISS pages with experimental log entries (work done without formal conversion)

    Total issues = Claimed + Unclaimed ISS pages
    """
    # Experiment pages with Claimed By (explicit or inferred) = converted issues
    claimed_experiments = [e for e in experiments if e['claimed_by']]
    explicit_claims = [e for e in claimed_experiments if e.get('claim_type') == 'explicit']
    inferred_claims = [e for e in claimed_experiments if e.get('claim_type') == 'inferred']

    # ISS pages with experimental log = informal claiming
    iss_with_log = [i for i in iss_nodes if i['has_experimental_log']]

    # Unclaimed ISS = no experimental log
    unclaimed_iss = [i for i in iss_nodes if not i['has_experimental_log']]

    total_claimed = len(claimed_experiments) + len(iss_with_log)
    total_issues = total_claimed + len(unclaimed_iss)

    conversion_rate = (total_claimed / total_issues * 100) if total_issues > 0 else 0

    # Cross-person vs self-claims
    cross_person_claims = [
        e for e in claimed_experiments
        if e['issue_created_by'] and e['claimed_by']
        and e['issue_created_by'] != e['claimed_by']
    ]
    self_claims = [
        e for e in claimed_experiments
        if e['issue_created_by'] and e['claimed_by']
        and e['issue_created_by'] == e['claimed_by']
    ]

    return {
        'conversion_rate_percent': round(conversion_rate, 1),
        'total_claimed': total_claimed,
        'claimed_experiments': len(claimed_experiments),
        'explicit_claims': len(explicit_claims),
        'inferred_claims': len(inferred_claims),
        'iss_with_activity': len(iss_with_log),
        'unclaimed_iss': len(unclaimed_iss),
        'total_issues': total_issues,
        'cross_person_claims': len(cross_person_claims),
        'self_claims': len(self_claims),
        'unknown_claim_type': len(claimed_experiments) - len(cross_person_claims) - len(self_claims),
        'claimed_experiment_list': claimed_experiments,
        'cross_person_claim_list': cross_person_claims,
        'self_claim_list': self_claims,
    }


def calculate_time_to_claim(experiments: list[dict]) -> dict:
    """
    Calculate Time-to-Claim metric.

    Time-to-Claim = Claimed By timestamp - Page creation timestamp
    (Page creation = Issue creation since it's the same page that got renamed)
    """
    times_to_claim = []

    for exp in experiments:
        if not exp['claimed_by']:
            continue
        if not exp['page_created']:
            continue
        if not exp['claimed_by_timestamp']:
            continue

        days = (exp['claimed_by_timestamp'] - exp['page_created']).days
        times_to_claim.append({
            'title': exp['title'],
            'issue_created_by': exp['issue_created_by'],
            'claimed_by': exp['claimed_by'],
            'page_created': exp['page_created'],
            'claimed_timestamp': exp['claimed_by_timestamp'],
            'days_to_claim': days,
        })

    if not times_to_claim:
        return {
            'count': 0,
            'avg_days': None,
            'min_days': None,
            'max_days': None,
            'median_days': None,
            'details': [],
        }

    days_list = [t['days_to_claim'] for t in times_to_claim]
    days_list_sorted = sorted(days_list)

    return {
        'count': len(times_to_claim),
        'avg_days': round(sum(days_list) / len(days_list), 1),
        'min_days': min(days_list),
        'max_days': max(days_list),
        'median_days': days_list_sorted[len(days_list_sorted) // 2],
        'details': sorted(times_to_claim, key=lambda x: x['days_to_claim']),
    }


def _build_relation_map(relation_instances: list[dict], res_uid_set: set) -> dict:
    """
    Build a mapping from experiment UIDs to linked RES node UIDs using relation instances.

    Returns dict mapping source UID -> set of destination UIDs that are RES nodes,
    and destination UID -> set of source UIDs that are RES nodes.
    """
    exp_to_res = {}
    for rel in relation_instances:
        src = rel.get('source', '').replace('pages:', '')
        dst = rel.get('destination', '').replace('pages:', '')

        # If destination is a RES node, map source -> destination
        if dst in res_uid_set:
            exp_to_res.setdefault(src, set()).add(dst)
        # If source is a RES node, map destination -> source
        if src in res_uid_set:
            exp_to_res.setdefault(dst, set()).add(src)

    return exp_to_res


def _find_linked_res_nodes(
    exp: dict,
    res_nodes: list[dict],
    res_by_uid: dict,
    relation_map: dict,
) -> list[dict]:
    """
    Find RES nodes linked to an experiment, using relation instances first
    and falling back to full title matching.
    """
    linked_res = []
    seen_uids = set()

    # Helper to resolve primary_contributor for a RES node
    def _res_primary_contributor(res):
        made_by = res.get('made_by')
        author = res.get('author')
        creator = res.get('creator')
        if made_by:
            return made_by, 'made_by'
        elif author:
            return author, 'author'
        elif creator:
            return creator, 'creator'
        return None, None

    # Method 1: Use relation instances (most reliable)
    exp_uid = exp.get('uid', '')
    if exp_uid in relation_map:
        for res_uid in relation_map[exp_uid]:
            if res_uid in res_by_uid and res_uid not in seen_uids:
                res = res_by_uid[res_uid]
                res_created = normalize_datetime(parse_date(res.get('created')))
                if res_created:
                    pc, pc_method = _res_primary_contributor(res)
                    linked_res.append({
                        'uid': res['uid'],
                        'title': res['title'],
                        'created': res_created,
                        'creator': res.get('creator'),
                        'made_by': res.get('made_by'),
                        'author': res.get('author'),
                        'primary_contributor': pc,
                        'attribution_method': pc_method,
                    })
                    seen_uids.add(res_uid)

    # Method 2: Match [[@experiment/...]] backreference in RES title
    # RES nodes often end with - [[@type/experiment name]] referencing their source experiment
    if not linked_res:
        exp_title = exp['title']  # e.g. "@analysis/Report the percentage..."
        # Look for [[exp_title]] in RES node titles (case-insensitive)
        exp_ref = f'[[{exp_title}]]'.lower()
        for res in res_nodes:
            if res['uid'] in seen_uids:
                continue
            res_title = res.get('title', '').lower()
            if exp_ref in res_title:
                res_created = normalize_datetime(parse_date(res.get('created')))
                if res_created:
                    pc, pc_method = _res_primary_contributor(res)
                    linked_res.append({
                        'uid': res['uid'],
                        'title': res['title'],
                        'created': res_created,
                        'creator': res.get('creator'),
                        'made_by': res.get('made_by'),
                        'author': res.get('author'),
                        'primary_contributor': pc,
                        'attribution_method': pc_method,
                    })
                    seen_uids.add(res['uid'])

    # Method 3: Fall back to full description matching in title only
    if not linked_res:
        exp_name = exp['title'].replace('@', '').lower()
        # Split only on the first '/' to separate type prefix from description
        # (avoids breaking on names like "Arp2/3")
        exp_short_name = exp_name.split('/', 1)[-1] if '/' in exp_name else exp_name

        # Require full short name match (no truncation), title only to avoid citation false positives
        if len(exp_short_name) >= 20:
            for res in res_nodes:
                if res['uid'] in seen_uids:
                    continue
                res_title = res.get('title', '').lower()

                if exp_short_name in res_title:
                    res_created = normalize_datetime(parse_date(res.get('created')))
                    if res_created:
                        pc, pc_method = _res_primary_contributor(res)
                        linked_res.append({
                            'uid': res['uid'],
                            'title': res['title'],
                            'created': res_created,
                            'creator': res.get('creator'),
                            'made_by': res.get('made_by'),
                            'author': res.get('author'),
                            'primary_contributor': pc,
                            'attribution_method': pc_method,
                        })
                        seen_uids.add(res['uid'])

    return linked_res


def calculate_time_to_first_result(
    experiments: list[dict],
    res_nodes: list[dict],
    relation_instances: list[dict] = None,
) -> dict:
    """
    Calculate Time-to-First-Result metric.

    Time-to-First-Result = First RES node creation - Claim timestamp
    (or page creation if claim timestamp not available)

    Uses relation instances from JSON-LD for reliable linking,
    with fallback to full title matching.
    """
    # Build lookup structures
    res_uid_set = {r['uid'] for r in res_nodes}
    res_by_uid = {r['uid']: r for r in res_nodes}
    relation_map = _build_relation_map(relation_instances or [], res_uid_set)

    results = []

    for exp in experiments:
        if not exp['is_claimed']:
            continue

        # Get the reference timestamp
        # For explicit claims: use claim timestamp (when Claimed By was filled in)
        # For inferred claims: use page creation (no formal claim event)
        if exp.get('claim_type') == 'explicit' and exp.get('claimed_by_timestamp'):
            ref_timestamp = exp['claimed_by_timestamp']
        else:
            ref_timestamp = exp.get('page_created')
        if not ref_timestamp:
            continue

        linked_res = _find_linked_res_nodes(exp, res_nodes, res_by_uid, relation_map)

        if not linked_res:
            continue

        # Find earliest RES node
        earliest_res = min(linked_res, key=lambda x: x['created'])
        days_to_result = (earliest_res['created'] - ref_timestamp).days

        results.append({
            'experiment_title': exp['title'],
            'claimed_by': exp['claimed_by'],
            'ref_timestamp': ref_timestamp,
            'first_res_title': earliest_res['title'],
            'first_res_created': earliest_res['created'],
            'first_res_creator': earliest_res['creator'],
            'first_res_primary_contributor': earliest_res.get('primary_contributor') or earliest_res.get('creator'),
            'days_to_first_result': days_to_result,
            'total_linked_res': len(linked_res),
        })

    if not results:
        return {
            'count': 0,
            'avg_days': None,
            'min_days': None,
            'max_days': None,
            'details': [],
        }

    days_list = [r['days_to_first_result'] for r in results]

    return {
        'count': len(results),
        'avg_days': round(sum(days_list) / len(days_list), 1),
        'min_days': min(days_list),
        'max_days': max(days_list),
        'details': sorted(results, key=lambda x: x['days_to_first_result']),
    }


def calculate_unique_contributors(
    experiments: list[dict],
    res_nodes: list[dict],
    relation_instances: list[dict] = None,
) -> dict:
    """
    Calculate Unique Contributors per Issue Chain.

    Contributors include:
    - Issue creator (Issue Created By)
    - Claimer (Claimed By)
    - RES node creators
    """
    # Build lookup structures for RES matching
    res_uid_set = {r['uid'] for r in res_nodes}
    res_by_uid = {r['uid']: r for r in res_nodes}
    relation_map = _build_relation_map(relation_instances or [], res_uid_set)

    contributor_data = []

    for exp in experiments:
        if not exp['is_claimed']:
            continue

        contributors = set()

        # Add issue creator
        if exp.get('issue_created_by'):
            contributors.add(exp['issue_created_by'])

        # Add claimer
        if exp.get('claimed_by'):
            contributors.add(exp['claimed_by'])

        # Add page creator (if different)
        if exp.get('creator'):
            contributors.add(exp['creator'])

        # Add primary_contributor (may differ from creator/claimer)
        if exp.get('primary_contributor'):
            contributors.add(exp['primary_contributor'])

        # Find linked RES nodes and their creators/primary_contributors
        linked_res = _find_linked_res_nodes(exp, res_nodes, res_by_uid, relation_map)
        for res in linked_res:
            if res.get('creator'):
                contributors.add(res['creator'])
            if res.get('primary_contributor'):
                contributors.add(res['primary_contributor'])

        contributor_data.append({
            'title': exp['title'],
            'contributors': list(contributors),
            'count': len(contributors),
            'issue_created_by': exp.get('issue_created_by'),
            'claimed_by': exp.get('claimed_by'),
        })

    if not contributor_data:
        return {
            'experiments_analyzed': 0,
            'avg_contributors': None,
            'distribution': {},
            'multi_contributor_count': 0,
            'single_contributor_count': 0,
            'details': [],
        }

    counts = [c['count'] for c in contributor_data]
    distribution = Counter(counts)

    multi = sum(1 for c in counts if c > 1)
    single = sum(1 for c in counts if c == 1)

    return {
        'experiments_analyzed': len(contributor_data),
        'avg_contributors': round(sum(counts) / len(counts), 2),
        'distribution': dict(sorted(distribution.items())),
        'multi_contributor_count': multi,
        'single_contributor_count': single,
        'details': sorted(contributor_data, key=lambda x: -x['count']),
    }


def calculate_cross_person_claims(experiments: list[dict]) -> dict:
    """
    Identify Cross-Person Claims (Idea Exchange).

    Cross-person claim = Issue Created By != Claimed By
    These demonstrate transfer of ideas from one researcher to another.
    """
    cross_person = []
    self_claims = []
    unknown = []

    for exp in experiments:
        if not exp.get('claimed_by'):
            continue

        issue_creator = exp.get('issue_created_by')
        claimer = exp.get('claimed_by')

        if not issue_creator:
            unknown.append({
                'title': exp['title'],
                'claimed_by': claimer,
                'issue_created_by': None,
            })
        elif issue_creator != claimer:
            cross_person.append({
                'title': exp['title'],
                'issue_created_by': issue_creator,
                'claimed_by': claimer,
                'page_created': exp.get('page_created'),
                'claimed_timestamp': exp.get('claimed_by_timestamp'),
            })
        else:
            self_claims.append({
                'title': exp['title'],
                'person': claimer,
                'page_created': exp.get('page_created'),
            })

    # Analyze idea exchange patterns
    exchange_pairs = Counter()
    for claim in cross_person:
        pair = (claim['issue_created_by'], claim['claimed_by'])
        exchange_pairs[pair] += 1

    return {
        'cross_person_count': len(cross_person),
        'self_claim_count': len(self_claims),
        'unknown_count': len(unknown),
        'total_claimed': len(cross_person) + len(self_claims) + len(unknown),
        'idea_exchange_rate': round(
            len(cross_person) / (len(cross_person) + len(self_claims)) * 100, 1
        ) if (len(cross_person) + len(self_claims)) > 0 else 0,
        'exchange_pairs': [
            {'from': pair[0], 'to': pair[1], 'count': count}
            for pair, count in exchange_pairs.most_common()
        ],
        'cross_person_details': cross_person,
        'self_claim_details': self_claims,
    }


def calculate_all_metrics(
    jsonld_path: str,
    roam_json_path: str,
) -> dict:
    """
    Calculate all 5 metrics from the discourse graph data.

    Args:
        jsonld_path: Path to JSON-LD export
        roam_json_path: Path to Roam JSON export

    Returns:
        Dict with all calculated metrics
    """
    print("Loading JSON-LD data...")
    jsonld_data = analyze_graph(jsonld_path)

    print("Analyzing experiment pages in Roam JSON...")
    roam_exp_data = analyze_all_experiment_pages(roam_json_path)

    print("Analyzing ISS pages in Roam JSON...")
    roam_iss_data = analyze_iss_pages(roam_json_path)

    print("Merging data...")
    experiments = merge_experiment_data(jsonld_data, roam_exp_data)
    iss_nodes = merge_iss_data(jsonld_data, roam_iss_data)
    res_nodes = jsonld_data['res_nodes']

    print("Calculating metrics...")

    # Get relation instances for linking experiments to RES nodes
    relation_instances = jsonld_data.get('relation_instances', [])

    # Metric 1: Conversion Rate
    conversion = calculate_conversion_rate(experiments, iss_nodes)

    # Metric 2: Time-to-Claim
    time_to_claim = calculate_time_to_claim(experiments)

    # Metric 3: Time-to-First-Result
    time_to_result = calculate_time_to_first_result(experiments, res_nodes, relation_instances)

    # Metric 4: Unique Contributors
    contributors = calculate_unique_contributors(experiments, res_nodes, relation_instances)

    # Metric 5: Cross-Person Claims
    cross_person = calculate_cross_person_claims(experiments)

    return {
        'generated': datetime.now().isoformat(),
        'data_sources': {
            'jsonld': jsonld_path,
            'roam_json': roam_json_path,
        },
        'summary': {
            'total_experiment_pages': len(experiments),
            'total_iss_nodes': len(iss_nodes),
            'total_res_nodes': len(res_nodes),
        },
        'metrics': {
            'conversion_rate': conversion,
            'time_to_claim': time_to_claim,
            'time_to_first_result': time_to_result,
            'unique_contributors': contributors,
            'cross_person_claims': cross_person,
        },
    }


def print_metrics_summary(metrics: dict):
    """Print a human-readable summary of the metrics."""
    print("\n" + "=" * 80)
    print("DISCOURSE GRAPH ISSUE METRICS SUMMARY")
    print("=" * 80)
    print(f"\nGenerated: {metrics['generated']}")

    summary = metrics['summary']
    print(f"\nData Overview:")
    print(f"  Experiment pages: {summary['total_experiment_pages']}")
    print(f"  ISS nodes: {summary['total_iss_nodes']}")
    print(f"  RES nodes: {summary['total_res_nodes']}")

    m = metrics['metrics']

    # Metric 1
    conv = m['conversion_rate']
    print(f"\n--- METRIC 1: Issue Conversion Rate ---")
    print(f"  Conversion rate: {conv['conversion_rate_percent']}%")
    print(f"  Total claimed: {conv['total_claimed']} ({conv['explicit_claims']} explicit + {conv['inferred_claims']} inferred + {conv['iss_with_activity']} ISS with activity)")
    print(f"  Unclaimed ISS: {conv['unclaimed_iss']}")
    print(f"  Cross-person claims: {conv['cross_person_claims']}")
    print(f"  Self-claims: {conv['self_claims']}")

    # Metric 2
    ttc = m['time_to_claim']
    print(f"\n--- METRIC 2: Time-to-Claim ---")
    if ttc['count'] > 0:
        print(f"  Experiments with data: {ttc['count']}")
        print(f"  Average: {ttc['avg_days']} days")
        print(f"  Range: {ttc['min_days']} - {ttc['max_days']} days")
        print(f"  Median: {ttc['median_days']} days")
    else:
        print("  No data available")

    # Metric 3
    ttr = m['time_to_first_result']
    print(f"\n--- METRIC 3: Time-to-First-Result ---")
    if ttr['count'] > 0:
        print(f"  Experiments with results: {ttr['count']}")
        print(f"  Average: {ttr['avg_days']} days")
        print(f"  Range: {ttr['min_days']} - {ttr['max_days']} days")
    else:
        print("  No data available")

    # Metric 4
    cont = m['unique_contributors']
    print(f"\n--- METRIC 4: Unique Contributors ---")
    if cont['experiments_analyzed'] > 0:
        print(f"  Experiments analyzed: {cont['experiments_analyzed']}")
        print(f"  Average contributors per experiment: {cont['avg_contributors']}")
        print(f"  Multi-contributor experiments: {cont['multi_contributor_count']}")
        print(f"  Single-contributor experiments: {cont['single_contributor_count']}")
        print(f"  Distribution: {cont['distribution']}")
    else:
        print("  No data available")

    # Metric 5
    xp = m['cross_person_claims']
    print(f"\n--- METRIC 5: Cross-Person Claims (Idea Exchange) ---")
    print(f"  Cross-person claims: {xp['cross_person_count']}")
    print(f"  Self-claims: {xp['self_claim_count']}")
    print(f"  Idea exchange rate: {xp['idea_exchange_rate']}%")
    if xp['exchange_pairs']:
        print("  Exchange pairs:")
        for pair in xp['exchange_pairs'][:5]:
            print(f"    {pair['from']} -> {pair['to']}: {pair['count']} claims")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    import sys

    # Default paths
    base_path = Path(__file__).parent.parent
    default_jsonld = base_path / 'graph raw data' / 'akamatsulab_discourse-graph-json-LD_202601242232.json'
    default_roam = base_path / 'graph raw data' / 'akamatsulab-whole-graph-json-2026-01-24-23-44-15.json'

    jsonld_path = sys.argv[1] if len(sys.argv) > 1 else str(default_jsonld)
    roam_path = sys.argv[2] if len(sys.argv) > 2 else str(default_roam)

    metrics = calculate_all_metrics(jsonld_path, roam_path)
    print_metrics_summary(metrics)

    # Save to file
    output_path = base_path / 'output' / 'metrics_data.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert datetime objects for JSON serialization
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(output_path, 'w') as f:
        json.dump(metrics, f, indent=2, default=json_serializer)

    print(f"\nMetrics saved to: {output_path}")
