#!/usr/bin/env python3
"""
De-identification Module
========================
Central mapping from real researcher names to anonymized pseudonyms.
Used throughout the pipeline to ensure consistent de-identification
before sharing data publicly.

The PI (Matt Akamatsu) remains identified as the evidence bundle creator.
All other lab members are anonymized as R1, R2, R3, etc.

The actual name-to-pseudonym mapping is loaded from ``name_mapping.json``,
which is gitignored to protect researcher identities. See
``name_mapping.example.json`` for the expected format.

Author: Matt Akamatsu (with Claude)
Date: 2026-02-12
"""

import json
from pathlib import Path

_MAPPING_PATH = Path(__file__).parent / 'name_mapping.json'


def _load_mapping() -> dict:
    """Load the name-to-pseudonym mapping from the JSON file."""
    if not _MAPPING_PATH.exists():
        raise FileNotFoundError(
            f"Name mapping file not found: {_MAPPING_PATH}\n"
            f"Copy name_mapping.example.json to name_mapping.json and fill in real names."
        )
    with open(_MAPPING_PATH) as f:
        return json.load(f)


# Mapping from real names to pseudonyms
# PI stays identified; all others anonymized
NAME_TO_PSEUDONYM = _load_mapping()

# Reverse mapping for reference (pseudonym -> real name)
# NOT used in pipeline outputs; only for internal reference
_PSEUDONYM_TO_NAME = {v: k for k, v in NAME_TO_PSEUDONYM.items()
                      if v != k}  # Exclude PI (identity preserved)


def anonymize_name(name: str) -> str:
    """
    Return the anonymized pseudonym for a researcher name.

    If the name is not in the mapping, returns the original name unchanged.
    Returns None if input is None.

    Args:
        name: Real researcher name

    Returns:
        Pseudonym or original name if not in map
    """
    if name is None:
        return None
    name = name.strip()

    # Check exact match first
    if name in NAME_TO_PSEUDONYM:
        return NAME_TO_PSEUDONYM[name]

    # Try partial match on last name for variant spellings
    for full_name, pseudonym in NAME_TO_PSEUDONYM.items():
        parts = full_name.split()
        if len(parts) >= 2 and parts[-1] in name:
            return pseudonym

    return name


def _build_first_name_map() -> dict:
    """
    Build a first-name/nickname replacement map from the loaded mapping.

    Automatically derives first names and common nicknames from the
    full names in NAME_TO_PSEUDONYM. This avoids hardcoding any
    researcher names in source code.
    """
    result = {}

    for full_name, pseudonym in NAME_TO_PSEUDONYM.items():
        if full_name == pseudonym:
            continue  # Skip PI (identity preserved)

        parts = full_name.split()
        if not parts:
            continue

        first_name = parts[0]

        # Add "FirstName " and "FirstName's" patterns
        result[f"{first_name}'s"] = f"{pseudonym}'s"
        result[f"{first_name} "] = f"{pseudonym} "
        result[f"{first_name}-"] = f"{pseudonym}-"

    # Add common nickname overrides (keyed by pseudonym for safety)
    # These map short names to the same pseudonym as the full name
    _nickname_overrides = {
        'R2': ['Ben'],
        'R4': ['Abhi'],
    }
    for target_pseudonym, nicknames in _nickname_overrides.items():
        for nick in nicknames:
            result[f"{nick}'s"] = f"{target_pseudonym}'s"
            result[f"{nick} "] = f"{target_pseudonym} "
            result[f"{nick}-"] = f"{target_pseudonym}-"

    return result


def anonymize_title(title: str) -> str:
    """
    Anonymize researcher names that appear embedded within experiment titles.

    Handles cases where first names appear as part of the title text
    rather than in a structured name field.

    Args:
        title: Experiment title string

    Returns:
        Title with embedded names replaced by pseudonyms
    """
    if title is None:
        return None

    # Replace full names that might appear in titles
    for full_name, pseudonym in NAME_TO_PSEUDONYM.items():
        if full_name in title and full_name != 'Matt Akamatsu':
            title = title.replace(full_name, pseudonym)

    # Replace first names / nicknames
    first_name_map = _build_first_name_map()
    for fragment, replacement in first_name_map.items():
        if fragment in title:
            title = title.replace(fragment, replacement)

    return title


def anonymize_dict(d: dict, fields: list[str]) -> dict:
    """
    Anonymize specified fields in a dictionary.

    Creates a shallow copy of the dict with the specified fields anonymized.

    Args:
        d: Dictionary containing researcher names
        fields: List of field names to anonymize

    Returns:
        New dict with specified fields anonymized
    """
    result = dict(d)
    for field in fields:
        if field in result and result[field] is not None:
            result[field] = anonymize_name(result[field])
    return result
