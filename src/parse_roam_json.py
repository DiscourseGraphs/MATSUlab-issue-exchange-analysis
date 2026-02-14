#!/usr/bin/env python3
"""
Parse Roam JSON Export for Block-Level Timestamps
==================================================
Extracts block-level timestamps from the full Roam JSON export to determine
when specific fields (like "Claimed By::") were populated.

Uses streaming JSON parsing to handle the large (~173MB) file efficiently.

Author: Matt Akamatsu (with Claude)
Date: 2026-01-25
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Iterator


def load_roam_json_streaming(filepath: str) -> Iterator[dict]:
    """
    Stream pages from Roam JSON export without loading entire file into memory.

    The Roam JSON export is an array of page objects at the top level.
    """
    try:
        import ijson
        with open(filepath, 'rb') as f:
            for page in ijson.items(f, 'item'):
                yield page
    except ImportError:
        # Fallback to loading entire file if ijson not available
        print("Warning: ijson not installed, loading entire file into memory")
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for page in data:
                yield page


def load_roam_json(filepath: str) -> list[dict]:
    """Load entire Roam JSON export into memory."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_page_by_title(pages: list[dict], title: str) -> Optional[dict]:
    """Find a specific page by its exact title."""
    for page in pages:
        if page.get('title') == title:
            return page
    return None


def find_page_by_title_streaming(filepath: str, title: str) -> Optional[dict]:
    """Find a page by title using streaming parser."""
    for page in load_roam_json_streaming(filepath):
        if page.get('title') == title:
            return page
    return None


def find_pages_matching_pattern(filepath: str, pattern: str) -> list[dict]:
    """Find all pages whose titles match a regex pattern."""
    compiled_pattern = re.compile(pattern)
    matching = []
    for page in load_roam_json_streaming(filepath):
        title = page.get('title', '')
        if compiled_pattern.search(title):
            matching.append(page)
    return matching


def get_block_timestamp(block: dict) -> Optional[datetime]:
    """
    Extract the creation timestamp from a block.

    Roam timestamps are Unix milliseconds in the 'create-time' field.
    """
    create_time = block.get('create-time')
    if create_time:
        try:
            return datetime.utcfromtimestamp(create_time / 1000)
        except (ValueError, TypeError, OSError):
            pass
    return None


def get_block_edit_timestamp(block: dict) -> Optional[datetime]:
    """Extract the edit timestamp from a block."""
    edit_time = block.get('edit-time')
    if edit_time:
        try:
            return datetime.utcfromtimestamp(edit_time / 1000)
        except (ValueError, TypeError, OSError):
            pass
    return None


def find_block_by_content(page: dict, content_pattern: str, recursive: bool = True) -> Optional[dict]:
    """
    Find a block containing specific content within a page.

    Args:
        page: The page dict from Roam JSON
        content_pattern: Regex pattern to match in block string
        recursive: Whether to search nested children blocks

    Returns:
        The first matching block, or None
    """
    pattern = re.compile(content_pattern, re.IGNORECASE)

    def search_blocks(blocks: list[dict]) -> Optional[dict]:
        for block in blocks:
            block_string = block.get('string', '')
            if pattern.search(block_string):
                return block
            if recursive and 'children' in block:
                result = search_blocks(block['children'])
                if result:
                    return result
        return None

    children = page.get('children', [])
    return search_blocks(children)


def find_all_blocks_by_content(page: dict, content_pattern: str, recursive: bool = True) -> list[dict]:
    """Find all blocks matching a content pattern within a page."""
    pattern = re.compile(content_pattern, re.IGNORECASE)
    matches = []

    def search_blocks(blocks: list[dict]):
        for block in blocks:
            block_string = block.get('string', '')
            if pattern.search(block_string):
                matches.append(block)
            if recursive and 'children' in block:
                search_blocks(block['children'])

    children = page.get('children', [])
    search_blocks(children)
    return matches


def extract_claimed_by_timestamp(page: dict) -> Optional[tuple[str, datetime]]:
    """
    Extract the person and timestamp from a 'Claimed By::' block.

    Returns:
        Tuple of (person_name, creation_timestamp) or None if not found
    """
    block = find_block_by_content(page, r'Claimed By::')
    if not block:
        return None

    block_string = block.get('string', '')

    # Extract person name from [[Person Name]] pattern
    match = re.search(r'Claimed By::\s*\[\[([^\]]+)\]\]', block_string)
    if match:
        person = match.group(1)
        timestamp = get_block_timestamp(block)
        return (person, timestamp) if timestamp else None

    return None


def extract_issue_created_by_timestamp(page: dict) -> Optional[tuple[str, datetime]]:
    """
    Extract the person and timestamp from an 'Issue Created By::' block.

    Returns:
        Tuple of (person_name, creation_timestamp) or None if not found
    """
    block = find_block_by_content(page, r'Issue Created By::')
    if not block:
        return None

    block_string = block.get('string', '')

    # Extract person name from [[Person Name]] pattern
    match = re.search(r'Issue Created By::\s*\[\[([^\]]+)\]\]', block_string)
    if match:
        person = match.group(1)
        timestamp = get_block_timestamp(block)
        return (person, timestamp) if timestamp else None

    return None


def extract_made_by_timestamp(page: dict) -> Optional[tuple[str, datetime]]:
    """
    Extract the person and timestamp from a 'Made by::', 'Creator::',
    or 'Created by::' block (highest priority attribution fields).

    Uses negative lookbehind to avoid matching 'Issue Created By::'.

    Returns:
        Tuple of (person_name, creation_timestamp) or None if not found
    """
    # Try Made by:: and Creator:: first
    for pattern in [r'Made [Bb]y::', r'Creator::']:
        block = find_block_by_content(page, pattern)
        if block:
            block_string = block.get('string', '')
            match = re.search(rf'(?:Made [Bb]y|Creator)::\s*\[\[([^\]]+)\]\]', block_string)
            if match:
                person = match.group(1)
                timestamp = get_block_timestamp(block)
                return (person, timestamp) if timestamp else (person, None)

    # Try Created by:: with care to avoid matching "Issue Created By::"
    # find_block_by_content uses case-insensitive search, so we search for
    # "Created by::" then verify it's not preceded by "Issue "
    block = find_block_by_content(page, r'Created [Bb]y::')
    if block:
        block_string = block.get('string', '')
        # Make sure this isn't "Issue Created By::"
        if not re.search(r'Issue Created [Bb]y::', block_string, re.IGNORECASE):
            match = re.search(r'Created [Bb]y::\s*\[\[([^\]]+)\]\]', block_string)
            if match:
                person = match.group(1)
                timestamp = get_block_timestamp(block)
                return (person, timestamp) if timestamp else (person, None)

    return None


def extract_author_from_page(page: dict) -> Optional[tuple[str, datetime]]:
    """
    Extract the person and timestamp from an 'Author::' block
    (lowest priority fallback attribution).

    Returns:
        Tuple of (person_name, creation_timestamp) or None if not found
    """
    block = find_block_by_content(page, r'Author::')
    if not block:
        return None

    block_string = block.get('string', '')

    # Extract person name from [[Person Name]] pattern
    match = re.search(r'Author::\s*\[\[([^\]]+)\]\]', block_string)
    if match:
        person = match.group(1)
        timestamp = get_block_timestamp(block)
        return (person, timestamp) if timestamp else (person, None)

    return None


def has_experimental_log(page: dict) -> bool:
    """
    Check if a page has experimental log entries.

    Looks for:
    - 'Experimental Log' or 'Experiment Log' header
    - Date entries like [[October 31st, 2024]] as children
    """
    # Look for experimental log header
    log_block = find_block_by_content(page, r'Experiment(al)?\s+Log')
    if not log_block:
        return False

    # Check if it has date entries as children
    children = log_block.get('children', [])
    if not children:
        return False

    # Look for date patterns in children
    date_pattern = re.compile(r'\[\[.+\d{1,2}(st|nd|rd|th),?\s+\d{4}\]\]')
    for child in children:
        child_string = child.get('string', '')
        if date_pattern.search(child_string):
            return True

    return False


def get_experimental_log_entries(page: dict) -> list[dict]:
    """
    Get all experimental log date entries from a page.

    Returns list of dicts with: date_string, timestamp, content
    """
    entries = []

    log_block = find_block_by_content(page, r'Experiment(al)?\s+Log')
    if not log_block:
        return entries

    children = log_block.get('children', [])
    date_pattern = re.compile(r'\[\[([^\]]+\d{4})\]\]')

    for child in children:
        child_string = child.get('string', '')
        match = date_pattern.search(child_string)
        if match:
            entries.append({
                'date_string': match.group(1),
                'timestamp': get_block_timestamp(child),
                'block_uid': child.get('uid'),
                'has_children': len(child.get('children', [])) > 0,
            })

    return entries


def get_page_creation_time(page: dict) -> Optional[datetime]:
    """Get the creation timestamp of a page."""
    create_time = page.get('create-time')
    if create_time:
        try:
            return datetime.utcfromtimestamp(create_time / 1000)
        except (ValueError, TypeError, OSError):
            pass
    return None


def get_earliest_block_timestamp(page: dict) -> Optional[datetime]:
    """
    Find the earliest block creation timestamp across all blocks in a page.

    This is a more robust proxy for page origin date than the page-level
    create-time, since page merges can update the page create-time while
    block timestamps preserve the original creation dates.
    """
    earliest = None

    def scan_blocks(blocks: list[dict]):
        nonlocal earliest
        for block in blocks:
            create_time = block.get('create-time')
            if create_time:
                try:
                    ts = datetime.utcfromtimestamp(create_time / 1000)
                    if earliest is None or ts < earliest:
                        earliest = ts
                except (ValueError, TypeError, OSError):
                    pass
            if 'children' in block:
                scan_blocks(block['children'])

    children = page.get('children', [])
    scan_blocks(children)
    return earliest


def extract_timestamps_for_experiments(filepath: str, experiment_titles: list[str]) -> dict:
    """
    Extract timestamps for a list of experiment page titles.

    Returns dict mapping title to:
    - page_created: Page creation timestamp
    - claimed_by: (person, timestamp) tuple
    - issue_created_by: (person, timestamp) tuple
    - has_experimental_log: bool
    - first_log_entry: timestamp of first log entry
    """
    results = {}

    for page in load_roam_json_streaming(filepath):
        title = page.get('title', '')
        if title not in experiment_titles:
            continue

        page_created = get_page_creation_time(page)
        claimed_by = extract_claimed_by_timestamp(page)
        issue_created_by = extract_issue_created_by_timestamp(page)
        has_log = has_experimental_log(page)
        log_entries = get_experimental_log_entries(page)

        first_log_entry = None
        if log_entries:
            timestamps = [e['timestamp'] for e in log_entries if e['timestamp']]
            if timestamps:
                first_log_entry = min(timestamps)

        results[title] = {
            'page_created': page_created,
            'claimed_by': claimed_by,
            'issue_created_by': issue_created_by,
            'has_experimental_log': has_log,
            'first_log_entry': first_log_entry,
            'log_entry_count': len(log_entries),
        }

        # Early exit if we've found all requested titles
        if len(results) == len(experiment_titles):
            break

    return results


def validate_roam_export(filepath: str, jsonld_data: dict, min_match_rate: float = 0.5) -> dict:
    """
    Validate that a Roam JSON export comes from the same graph as the JSON-LD export.

    Compares experiment page titles and ISS node titles between the two exports.
    If the match rate is below min_match_rate, the Roam export is likely from a
    different Roam graph.

    Args:
        filepath: Path to the Roam JSON export
        jsonld_data: Parsed JSON-LD data (from analyze_graph())
        min_match_rate: Minimum fraction of JSON-LD titles that must be found
                        in the Roam export (default 0.5 = 50%)

    Returns:
        Dict with validation results including match counts and pass/fail status.

    Raises:
        ValueError: If match rate is below min_match_rate
    """
    jsonld_exp_titles = {e['title'] for e in jsonld_data.get('experiment_pages', [])}
    jsonld_iss_titles = {i['title'] for i in jsonld_data.get('iss_nodes', [])}

    roam_exp_titles = set()
    roam_iss_titles = set()
    total_roam_pages = 0

    for page in load_roam_json_streaming(filepath):
        title = page.get('title', '')
        total_roam_pages += 1
        if title.startswith('@'):
            roam_exp_titles.add(title)
        if '[[ISS]]' in title:
            roam_iss_titles.add(title)

    exp_matched = len(jsonld_exp_titles & roam_exp_titles)
    iss_matched = len(jsonld_iss_titles & roam_iss_titles)
    total_jsonld = len(jsonld_exp_titles) + len(jsonld_iss_titles)
    total_matched = exp_matched + iss_matched
    match_rate = total_matched / total_jsonld if total_jsonld > 0 else 0

    result = {
        'total_roam_pages': total_roam_pages,
        'jsonld_experiment_pages': len(jsonld_exp_titles),
        'roam_experiment_pages': len(roam_exp_titles),
        'experiment_matches': exp_matched,
        'jsonld_iss_nodes': len(jsonld_iss_titles),
        'roam_iss_nodes': len(roam_iss_titles),
        'iss_matches': iss_matched,
        'match_rate': round(match_rate, 3),
        'passed': match_rate >= min_match_rate,
    }

    if not result['passed']:
        raise ValueError(
            f"Roam export validation failed: only {match_rate:.1%} of JSON-LD titles "
            f"found in Roam export ({total_matched}/{total_jsonld}). "
            f"The Roam export ({total_roam_pages} pages, {len(roam_exp_titles)} @ pages) "
            f"appears to be from a different Roam graph than the JSON-LD export "
            f"({len(jsonld_exp_titles)} experiment pages, {len(jsonld_iss_titles)} ISS nodes). "
            f"Please re-export the whole-graph JSON from the correct Roam database."
        )

    return result


def analyze_all_experiment_pages(filepath: str) -> dict:
    """
    Analyze all experiment pages (titles starting with @) in the Roam export.

    Returns dict with analysis results for each experiment page.
    """
    results = {}

    for page in load_roam_json_streaming(filepath):
        title = page.get('title', '')

        # Only process experiment pages (start with @)
        if not title.startswith('@'):
            continue

        page_created = get_page_creation_time(page)
        earliest_block = get_earliest_block_timestamp(page)
        claimed_by = extract_claimed_by_timestamp(page)
        issue_created_by = extract_issue_created_by_timestamp(page)
        made_by = extract_made_by_timestamp(page)
        author = extract_author_from_page(page)
        has_log = has_experimental_log(page)
        log_entries = get_experimental_log_entries(page)

        first_log_entry = None
        if log_entries:
            timestamps = [e['timestamp'] for e in log_entries if e['timestamp']]
            if timestamps:
                first_log_entry = min(timestamps)

        results[title] = {
            'page_created': page_created,
            'earliest_block_timestamp': earliest_block,
            'claimed_by': claimed_by,
            'issue_created_by': issue_created_by,
            'made_by': made_by,
            'author': author,
            'has_experimental_log': has_log,
            'first_log_entry': first_log_entry,
            'log_entry_count': len(log_entries),
        }

    return results


def analyze_iss_pages(filepath: str) -> dict:
    """
    Analyze all ISS (Issue) pages in the Roam export.

    Returns dict with analysis results for each ISS page.
    """
    results = {}

    for page in load_roam_json_streaming(filepath):
        title = page.get('title', '')

        # Only process ISS pages
        if '[[ISS]]' not in title:
            continue

        page_created = get_page_creation_time(page)
        made_by = extract_made_by_timestamp(page)
        author = extract_author_from_page(page)
        has_log = has_experimental_log(page)
        log_entries = get_experimental_log_entries(page)

        first_log_entry = None
        if log_entries:
            timestamps = [e['timestamp'] for e in log_entries if e['timestamp']]
            if timestamps:
                first_log_entry = min(timestamps)

        results[title] = {
            'page_created': page_created,
            'made_by': made_by,
            'author': author,
            'has_experimental_log': has_log,
            'first_log_entry': first_log_entry,
            'log_entry_count': len(log_entries),
        }

    return results


if __name__ == '__main__':
    import sys

    # Default path
    default_path = Path(__file__).parent.parent / 'graph raw data' / 'akamatsulab-whole-graph-json-2026-01-24-23-44-15.json'
    filepath = sys.argv[1] if len(sys.argv) > 1 else str(default_path)

    print(f"Parsing Roam JSON file: {filepath}")
    print("This may take a moment due to file size...")

    # Analyze experiment pages
    print("\nAnalyzing experiment pages...")
    exp_results = analyze_all_experiment_pages(filepath)
    print(f"Found {len(exp_results)} experiment pages")

    # Count pages with Claimed By
    claimed_count = sum(1 for r in exp_results.values() if r['claimed_by'])
    print(f"Pages with 'Claimed By': {claimed_count}")

    # Count pages with experimental log
    log_count = sum(1 for r in exp_results.values() if r['has_experimental_log'])
    print(f"Pages with experimental log: {log_count}")

    # Show some examples
    print("\nExample experiment pages with 'Claimed By':")
    for title, data in list(exp_results.items())[:3]:
        if data['claimed_by']:
            person, timestamp = data['claimed_by']
            print(f"  - {title[:60]}...")
            print(f"    Claimed By: {person} at {timestamp}")
            if data['page_created']:
                days_to_claim = (timestamp - data['page_created']).days
                print(f"    Days to claim: {days_to_claim}")

    # Analyze ISS pages
    print("\nAnalyzing ISS pages...")
    iss_results = analyze_iss_pages(filepath)
    print(f"Found {len(iss_results)} ISS pages")

    # Count ISS pages with experimental log (claimed without formal claiming)
    iss_with_log = sum(1 for r in iss_results.values() if r['has_experimental_log'])
    print(f"ISS pages with experimental log: {iss_with_log}")
