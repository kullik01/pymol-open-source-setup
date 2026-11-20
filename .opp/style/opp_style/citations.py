"""Citations of planning and decision records, which no comment may make.

Comments and docstrings, in Python and C++ alike, say what the code does
and why in plain words. A record number -- an ADR, a decision, a step, a
question or a gap -- or a short record id, a capital D, Q, S or O with up
to three digits, belongs in the records, which may cite the code, not the
other way round.
"""

from __future__ import annotations

import re

PATTERNS = (
    re.compile(r"\bADRs?\s*0?\d{2,4}\b"),
    re.compile(r"\b[Dd]ecisions?\s+\d+\b"),
    re.compile(r"\b[Ss]teps?\s+\d+\b"),
    re.compile(r"\b[Qq]uestions?\s+\d+\b"),
    re.compile(r"\b[Gg]aps?\s+\d+\b"),
)
"""Citations of planning and decision records by number."""

RECORD_ID = re.compile(r"(?<![\w.#/-])([DQSO]\d{1,3})(?![\w.])")
"""A short record id: a decision, question or specification note."""

RULE = "citation"
"""The rule's short name."""


def cited(text: str, exceptions: frozenset[str], short_ids: bool = True) -> list[str]:
    """The record citations in one line of a comment or docstring.

    Args:
        text: The line's text.
        exceptions: The short ids that are no record ids, such as a colour
            standard's name.
        short_ids: Whether short record ids count; C++ comments leave them
            out, since atom and test names such as ``O1`` look the same.

    Returns:
        Each citation, in the order the patterns find them; empty when the
        line cites none.
    """
    tmp_numbers = [tmp_match.group(0) for tmp_pattern in PATTERNS for tmp_match in tmp_pattern.finditer(text)]
    tmp_ids = [
        tmp_match.group(1)
        for tmp_match in RECORD_ID.finditer(text)
        if short_ids and tmp_match.group(1) not in exceptions
    ]
    return tmp_numbers + tmp_ids


def message(citations: list[str]) -> str:
    """Say what is wrong with a line that cites records.

    Args:
        citations: The line's citations, as :func:`cited` found them.

    Returns:
        The finding's message.
    """
    return (
        f"comments and docstrings cite no planning or decision record ({', '.join(citations)}); "
        "say what the code does and why, and leave the record to docs/"
    )
