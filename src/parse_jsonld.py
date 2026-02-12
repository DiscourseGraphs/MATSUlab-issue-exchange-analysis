#!/usr/bin/env python3
"""
Parse JSON-LD Export from Discourse Graph
==========================================
Extracts discourse nodes, experiment pages, and relationships from the
JSON-LD export of the Akamatsu Lab discourse graph.

Author: Matt Akamatsu (with Claude)
Date: 2026-01-25
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


def load_jsonld(filepath: str) -> dict:
    """Load and parse the JSON-LD file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_graph_nodes(data: dict) -> list[dict]:
    """Extract the @graph array from JSON-LD data."""
    return data.get('@graph', [])


def extract_nodes_by_type(graph: list[dict], node_type: str) -> list[dict]:
    """
    Filter nodes by their discourse type.

    Args:
        graph: The @graph array from JSON-LD
        node_type: Type to filter by (e.g., 'ISS', 'RES', 'CLM', 'HYP', 'CON', 'EVD', 'QUE')

    Returns:
        List of nodes matching the type
    """
    # Node types are indicated by @type field pointing to schema nodes
    # e.g., "pages:p4ijlwP1p" for Issue, "pages:lxCvhQ034" for Result

    # Map of label to node type patterns
    type_patterns = {
        'ISS': r'\[\[ISS\]\]',
        'RES': r'\[\[RES\]\]',
        'CLM': r'\[\[CLM\]\]',
        'HYP': r'\[\[HYP\]\]',
        'CON': r'\[\[CON\]\]',
        'EVD': r'\[\[EVD\]\]',
        'QUE': r'\[\[QUE\]\]',
    }

    if node_type not in type_patterns:
        return []

    pattern = type_patterns[node_type]
    matching_nodes = []

    for node in graph:
        title = node.get('title', '')
        if re.search(pattern, title):
            matching_nodes.append(node)

    return matching_nodes


def find_experiment_pages(graph: list[dict]) -> list[dict]:
    """
    Find all pages matching the @type/name experiment convention.

    Experiment pages have titles starting with @ followed by type and description.
    Examples: @analysis/..., @TC/..., @cytosim/..., @pythonSim/...
    """
    experiment_pages = []

    for node in graph:
        title = node.get('title', '')
        # Match titles starting with @ followed by type/description
        if re.match(r'^@[a-zA-Z]+/', title):
            experiment_pages.append(node)

    return experiment_pages


def extract_claimed_by_from_content(content: str) -> Optional[str]:
    """
    Extract the 'Claimed By' person from the content field.

    Looks for patterns like:
    - Claimed By:: [Person Name](url)
    - Claimed By:: [[Person Name]]
    """
    if not content:
        return None

    # Pattern for markdown link: [Name](url)
    match = re.search(r'Claimed By::\s*\[([^\]]+)\]\([^)]+\)', content)
    if match:
        return match.group(1).strip()

    # Pattern for wiki link: [[Name]]
    match = re.search(r'Claimed By::\s*\[\[([^\]]+)\]\]', content)
    if match:
        return match.group(1).strip()

    return None


def extract_issue_created_by_from_content(content: str) -> Optional[str]:
    """
    Extract the 'Issue Created By' person from the content field.

    Looks for patterns like:
    - Issue Created By:: [Person Name](url)
    - Issue Created By:: [[Person Name]]
    """
    if not content:
        return None

    # Pattern for markdown link: [Name](url)
    match = re.search(r'Issue Created By::\s*\[([^\]]+)\]\([^)]+\)', content)
    if match:
        return match.group(1).strip()

    # Pattern for wiki link: [[Name]]
    match = re.search(r'Issue Created By::\s*\[\[([^\]]+)\]\]', content)
    if match:
        return match.group(1).strip()

    return None


def extract_made_by_from_content(content: str) -> Optional[str]:
    """
    Extract the 'Made by', 'Creator', or 'Created by' person from content.

    These fields indicate who actually performed the work (highest priority
    attribution). 'Created by' uses a negative lookbehind to avoid matching
    'Issue Created By'.

    Priority: Made by > Creator > Created by

    Looks for patterns like:
    - Made by:: [Person Name](url)  or  Made by:: [[Person Name]]
    - Creator:: [Person Name](url)  or  Creator:: [[Person Name]]
    - Created by:: [Person Name](url)  or  Created by:: [[Person Name]]
    """
    if not content:
        return None

    # Try Made by:: and Creator:: first
    for field in [r'Made [Bb]y', r'Creator']:
        # Markdown link
        match = re.search(rf'{field}::\s*\[([^\]]+)\]\([^)]+\)', content)
        if match:
            return match.group(1).strip()
        # Wiki link
        match = re.search(rf'{field}::\s*\[\[([^\]]+)\]\]', content)
        if match:
            return match.group(1).strip()

    # Try Created by:: with negative lookbehind to avoid "Issue Created By::"
    # Markdown link
    match = re.search(r'(?<![Ii]ssue )Created [Bb]y::\s*\[([^\]]+)\]\([^)]+\)', content)
    if match:
        return match.group(1).strip()
    # Wiki link
    match = re.search(r'(?<![Ii]ssue )Created [Bb]y::\s*\[\[([^\]]+)\]\]', content)
    if match:
        return match.group(1).strip()

    return None


def extract_author_from_content(content: str) -> Optional[str]:
    """
    Extract the 'Author' person from content (lowest priority fallback).

    The Author field often represents the page creator (frequently the PI),
    not necessarily the person who did the work.

    Looks for patterns like:
    - Author:: [Person Name](url)
    - Author:: [[Person Name]]
    """
    if not content:
        return None

    # Markdown link
    match = re.search(r'Author::\s*\[([^\]]+)\]\([^)]+\)', content)
    if match:
        return match.group(1).strip()

    # Wiki link
    match = re.search(r'Author::\s*\[\[([^\]]+)\]\]', content)
    if match:
        return match.group(1).strip()

    return None


def extract_status_from_content(content: str) -> Optional[str]:
    """Extract the Status field from content."""
    if not content:
        return None

    match = re.search(r'Status::\s*([^\n]+)', content)
    if match:
        return match.group(1).strip()

    return None


def extract_node_metadata(node: dict) -> dict:
    """
    Extract key metadata from a node.

    Returns dict with: uid, title, creator, created, modified,
    claimed_by, issue_created_by, made_by, author, status, node_type
    """
    content = node.get('content', '')
    title = node.get('title', '')

    # Determine node type from title
    node_type = None
    if title.startswith('@'):
        node_type = 'experiment'
    elif '[[ISS]]' in title:
        node_type = 'ISS'
    elif '[[RES]]' in title:
        node_type = 'RES'
    elif '[[CLM]]' in title:
        node_type = 'CLM'
    elif '[[HYP]]' in title:
        node_type = 'HYP'
    elif '[[CON]]' in title:
        node_type = 'CON'
    elif '[[EVD]]' in title:
        node_type = 'EVD'
    elif '[[QUE]]' in title:
        node_type = 'QUE'

    # Extract UID from @id (e.g., "pages:Y9EBEzQnB" -> "Y9EBEzQnB")
    node_id = node.get('@id', '')
    uid = node_id.replace('pages:', '') if node_id.startswith('pages:') else node_id

    return {
        'uid': uid,
        'title': title,
        'creator': node.get('creator'),
        'created': node.get('created'),
        'modified': node.get('modified'),
        'claimed_by': extract_claimed_by_from_content(content),
        'issue_created_by': extract_issue_created_by_from_content(content),
        'made_by': extract_made_by_from_content(content),
        'author': extract_author_from_content(content),
        'status': extract_status_from_content(content),
        'node_type': node_type,
        'content': content,
    }


def get_relation_definitions(graph: list[dict]) -> list[dict]:
    """Extract relation definitions from the graph."""
    relations = []
    for node in graph:
        if node.get('@type') == 'relationDef':
            relations.append({
                'id': node.get('@id'),
                'label': node.get('label'),
                'domain': node.get('domain'),
                'range': node.get('range'),
                'inverse_of': node.get('inverseOf'),
            })
    return relations


def get_relation_instances(graph: list[dict]) -> list[dict]:
    """Extract relation instances from the graph."""
    instances = []
    for node in graph:
        if node.get('@type') == 'relationInstance':
            instances.append({
                'id': node.get('@id'),
                'source': node.get('source'),
                'destination': node.get('destination'),
                'predicate': node.get('predicate'),
            })
    return instances


def find_linked_results(graph: list[dict], experiment_title: str) -> list[dict]:
    """
    Find RES nodes that are linked to an experiment.

    A RES node is linked if:
    - Its title contains the experiment title/name
    - It is referenced within the experiment page content
    """
    linked_results = []
    res_nodes = extract_nodes_by_type(graph, 'RES')

    # Normalize experiment title for matching
    exp_name = experiment_title.replace('@', '').split('/')[-1].lower()

    for res in res_nodes:
        res_title = res.get('title', '').lower()
        res_content = res.get('content', '').lower()

        # Check if experiment is mentioned in RES node
        if exp_name in res_title or exp_name in res_content:
            linked_results.append(extract_node_metadata(res))

    return linked_results


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse ISO date string to datetime object."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None


def analyze_graph(filepath: str) -> dict:
    """
    Perform full analysis of the JSON-LD graph.

    Returns a dict with:
    - experiment_pages: List of experiment pages with metadata
    - iss_nodes: List of ISS (Issue) nodes
    - res_nodes: List of RES (Result) nodes
    - all_nodes_by_type: Dict mapping node type to list of nodes
    - relations: List of relation definitions
    """
    data = load_jsonld(filepath)
    graph = get_graph_nodes(data)

    # Filter out schema definitions (nodeSchema, relationDef)
    content_nodes = [
        n for n in graph
        if n.get('@type') not in ('nodeSchema', 'relationDef', 'relationInstance')
    ]

    # Extract experiment pages
    experiment_pages = []
    for node in find_experiment_pages(content_nodes):
        metadata = extract_node_metadata(node)
        experiment_pages.append(metadata)

    # Extract ISS nodes
    iss_nodes = []
    for node in extract_nodes_by_type(content_nodes, 'ISS'):
        metadata = extract_node_metadata(node)
        iss_nodes.append(metadata)

    # Extract RES nodes
    res_nodes = []
    for node in extract_nodes_by_type(content_nodes, 'RES'):
        metadata = extract_node_metadata(node)
        res_nodes.append(metadata)

    # Extract all node types
    all_nodes_by_type = {}
    for node_type in ['ISS', 'RES', 'CLM', 'HYP', 'CON', 'EVD', 'QUE']:
        nodes = extract_nodes_by_type(content_nodes, node_type)
        all_nodes_by_type[node_type] = [extract_node_metadata(n) for n in nodes]

    # Get relations
    relations = get_relation_definitions(graph)
    relation_instances = get_relation_instances(graph)

    return {
        'experiment_pages': experiment_pages,
        'iss_nodes': iss_nodes,
        'res_nodes': res_nodes,
        'all_nodes_by_type': all_nodes_by_type,
        'relations': relations,
        'relation_instances': relation_instances,
        'total_content_nodes': len(content_nodes),
    }


if __name__ == '__main__':
    import sys

    # Default path
    default_path = Path(__file__).parent.parent / 'graph raw data' / 'akamatsulab_discourse-graph-json-LD_202601242232.json'
    filepath = sys.argv[1] if len(sys.argv) > 1 else str(default_path)

    print(f"Parsing JSON-LD file: {filepath}")
    result = analyze_graph(filepath)

    print(f"\nTotal content nodes: {result['total_content_nodes']}")
    print(f"Experiment pages: {len(result['experiment_pages'])}")
    print(f"ISS nodes: {len(result['iss_nodes'])}")
    print(f"RES nodes: {len(result['res_nodes'])}")

    print("\nNode counts by type:")
    for node_type, nodes in result['all_nodes_by_type'].items():
        print(f"  {node_type}: {len(nodes)}")

    # Show experiment pages with Claimed By
    claimed_experiments = [p for p in result['experiment_pages'] if p['claimed_by']]
    print(f"\nExperiment pages with 'Claimed By': {len(claimed_experiments)}")
    for exp in claimed_experiments[:5]:
        print(f"  - {exp['title'][:60]}...")
        print(f"    Issue Created By: {exp['issue_created_by']}")
        print(f"    Claimed By: {exp['claimed_by']}")
