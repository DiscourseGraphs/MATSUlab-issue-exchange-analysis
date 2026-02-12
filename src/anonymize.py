#!/usr/bin/env python3
"""
De-identification Module
========================
Central mapping from real researcher names to anonymized pseudonyms.
Used throughout the pipeline to ensure consistent de-identification
before sharing data publicly.

The PI (Matt Akamatsu) remains identified as the evidence bundle creator.
All other lab members are anonymized as R1, R2, R3, etc.

Author: Matt Akamatsu (with Claude)
Date: 2026-02-12
"""

# Mapping from real names to pseudonyms
# PI stays identified; all others anonymized
NAME_TO_PSEUDONYM = {
    'Matt Akamatsu': 'Matt Akamatsu',  # PI stays identified
    'R1': 'R1',
    'R2': 'R2',
    'R3': 'R3',
    'R4': 'R4',
    'R5': 'R5',
    'R5': 'R5',  # Same person as R5
    'R6': 'R6',
    'R7': 'R7',
    'R8': 'R8',
    'R9': 'R9',
    'R10': 'R10',
    'R11': 'R11',
}

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
        name: Real researcher name (e.g., 'R3')

    Returns:
        Pseudonym (e.g., 'R3') or original name if not in map
    """
    if name is None:
        return None
    name = name.strip()

    # Check exact match first
    if name in NAME_TO_PSEUDONYM:
        return NAME_TO_PSEUDONYM[name]

    # Try normalizing R5_surname variants
    if 'R5_surname' in name:
        return NAME_TO_PSEUDONYM.get('R5', name)

    return name


def anonymize_title(title: str) -> str:
    """
    Anonymize researcher names that appear embedded within experiment titles.

    Handles cases like "R1's updates to the pipeline..." or
    "R4 -Run image analysis pipeline..." where first names appear
    as part of the title text rather than in a structured name field.

    Args:
        title: Experiment title string

    Returns:
        Title with embedded first names replaced by pseudonyms
    """
    if title is None:
        return None

    # Map first names / nicknames to their full-name pseudonyms
    FIRST_NAME_MAP = {
        "R1's": f"{NAME_TO_PSEUDONYM['R1']}'s",
        "R1 ": f"{NAME_TO_PSEUDONYM['R1']} ",
        "R4 ": f"{NAME_TO_PSEUDONYM['R4']} ",
        "R4-": f"{NAME_TO_PSEUDONYM['R4']}-",
        "R3's": f"{NAME_TO_PSEUDONYM['R3']}'s",
        "R3 ": f"{NAME_TO_PSEUDONYM['R3']} ",
        "R11's": f"{NAME_TO_PSEUDONYM['R11']}'s",
        "R11 ": f"{NAME_TO_PSEUDONYM['R11']} ",
        "R2 ": f"{NAME_TO_PSEUDONYM['R2']} ",
        "R2's": f"{NAME_TO_PSEUDONYM['R2']}'s",
        "R2's": f"{NAME_TO_PSEUDONYM['R2']}'s",
        "R6's": f"{NAME_TO_PSEUDONYM['R6']}'s",
        "R6 ": f"{NAME_TO_PSEUDONYM['R6']} ",
        "R5's": f"{NAME_TO_PSEUDONYM['R5']}'s",
        "R5 ": f"{NAME_TO_PSEUDONYM['R5']} ",
        "R7's": f"{NAME_TO_PSEUDONYM['R7']}'s",
        "R7 ": f"{NAME_TO_PSEUDONYM['R7']} ",
        "R8's": f"{NAME_TO_PSEUDONYM['R8']}'s",
        "R9's": f"{NAME_TO_PSEUDONYM['R9']}'s",
        "R9 ": f"{NAME_TO_PSEUDONYM['R9']} ",
        "R10's": f"{NAME_TO_PSEUDONYM['R10']}'s",
        "R10 ": f"{NAME_TO_PSEUDONYM['R10']} ",
    }

    # Also replace full names that might appear in titles
    for full_name, pseudonym in NAME_TO_PSEUDONYM.items():
        if full_name in title and full_name != 'Matt Akamatsu':
            title = title.replace(full_name, pseudonym)

    # Replace first names / nicknames
    for fragment, replacement in FIRST_NAME_MAP.items():
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
