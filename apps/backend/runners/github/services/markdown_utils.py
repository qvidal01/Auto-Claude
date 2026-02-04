"""
Markdown Parsing Utilities for PR Reviews
==========================================

Shared utilities for parsing markdown output from AI reviewers.
"""

from __future__ import annotations

import hashlib
import logging
import re

try:
    from ..models import PRReviewFinding, ReviewCategory, ReviewSeverity
    from .category_utils import map_category
except (ImportError, ValueError, SystemError):
    from models import PRReviewFinding, ReviewCategory, ReviewSeverity
    from services.category_utils import map_category


logger = logging.getLogger(__name__)


def parse_markdown_findings(
    output: str, context_name: str = "Review"
) -> list[PRReviewFinding]:
    """Parse findings from markdown output when JSON extraction fails.

    This handles cases where the AI outputs findings in markdown format
    after structured output validation fails. Extracts findings from patterns like:
    - **CRITICAL - Code Duplication**
    - ### Critical Issues (Must Fix)
    - 1. **HIGH - Race condition in auth.ts:45**

    Args:
        output: Markdown text output to parse
        context_name: Name of the context (e.g., "ParallelOrchestrator", "ParallelFollowup")

    Returns:
        List of PRReviewFinding instances extracted from markdown
    """
    findings: list[PRReviewFinding] = []

    # Normalize line endings
    output = output.replace("\r\n", "\n")

    # Pattern: **SEVERITY - Title** or **SEVERITY: Title** or numbered lists
    numbered_pattern = r"(?:\d+\.\s*)?\*\*(\w+)\s*[-:–]\s*([^*]+)\*\*"

    # Track positions to avoid duplicates
    found_titles: set[str] = set()

    # Find all severity-title matches
    for match in re.finditer(numbered_pattern, output, re.IGNORECASE):
        severity_str = match.group(1).strip().upper()
        title = match.group(2).strip()

        # Skip if already found this title (avoid duplicates)
        title_key = title.lower()[:50]
        if title_key in found_titles:
            continue
        found_titles.add(title_key)

        # Map severity string to enum
        severity_map = {
            "CRITICAL": ReviewSeverity.CRITICAL,
            "HIGH": ReviewSeverity.HIGH,
            "MEDIUM": ReviewSeverity.MEDIUM,
            "MED": ReviewSeverity.MEDIUM,
            "LOW": ReviewSeverity.LOW,
            "SUGGESTION": ReviewSeverity.LOW,
        }
        severity = severity_map.get(severity_str, ReviewSeverity.MEDIUM)

        # Try to extract file and line from title or nearby text
        file_line_match = re.search(
            r"[`(]?([a-zA-Z0-9_./\-]+\.(?:ts|tsx|js|jsx|py|go|rs|java|rb|c|cpp|h|hpp|swift|kt|scala|php|vue|svelte)):(\d+)[`)]?",
            title + output[match.end() : match.end() + 200],
        )

        file_path = "unknown"
        line_num = 0
        if file_line_match:
            file_path = file_line_match.group(1)
            line_num = int(file_line_match.group(2))

        # Extract description - text following the title until next heading or finding
        desc_start = match.end()
        desc_end_patterns = [
            r"\n\s*\*\*\w+\s*[-:–]",  # Next finding
            r"\n\s*#{1,3}\s",  # Next heading
            r"\n\s*\d+\.\s*\*\*",  # Next numbered item
            r"\n\s*---",  # Horizontal rule
        ]
        desc_end = len(output)
        for pattern in desc_end_patterns:
            end_match = re.search(pattern, output[desc_start:])
            if end_match:
                desc_end = min(desc_end, desc_start + end_match.start())

        description = output[desc_start:desc_end].strip()
        description = re.sub(r"^\s*[-*]\s*", "", description, flags=re.MULTILINE)
        description = description[:500]  # Limit length

        # Infer category from title/description
        category_keywords = {
            "security": [
                "security",
                "injection",
                "xss",
                "auth",
                "credential",
                "secret",
            ],
            "redundancy": [
                "duplication",
                "redundant",
                "duplicate",
                "similar",
                "copy",
            ],
            "performance": ["performance", "slow", "optimize", "memory", "leak"],
            "logic": ["logic", "race", "condition", "edge case", "bug", "error"],
            "quality": ["quality", "maintainability", "readability", "complexity"],
            "test": ["test", "coverage", "assertion"],
            "docs": ["doc", "comment", "readme"],
            "regression": ["regression", "broke", "revert"],
            "incomplete_fix": ["incomplete", "partial", "still"],
        }

        category = ReviewCategory.QUALITY  # Default
        title_desc_lower = (title + " " + description).lower()
        for cat, keywords in category_keywords.items():
            if any(kw in title_desc_lower for kw in keywords):
                category = map_category(cat)
                break

        # Generate finding ID
        finding_id = hashlib.md5(
            f"{file_path}:{line_num}:{title[:50]}".encode(),
            usedforsecurity=False,
        ).hexdigest()[:12]

        finding = PRReviewFinding(
            id=finding_id,
            file=file_path,
            line=line_num,
            title=title[:80],
            description=description if description else title,
            category=category,
            severity=severity,
            suggested_fix="",
            evidence=None,
        )
        findings.append(finding)

    if findings:
        logger.info(
            f"[{context_name}] Extracted {len(findings)} findings from markdown output"
        )

    return findings
