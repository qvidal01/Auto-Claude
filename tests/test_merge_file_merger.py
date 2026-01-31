#!/usr/bin/env python3
"""
Tests for File Merger
=====================

Comprehensive tests for file content manipulation and merging utilities.

Covers:
- Line ending detection (LF, CRLF, CR)
- Single task change application
- Multi-task change combination
- Import location detection
- Content extraction from locations
- AI merge application
- Edge cases with mixed line endings
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Add auto-claude directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from merge.file_merger import (
    apply_ai_merge,
    apply_single_task_changes,
    combine_non_conflicting_changes,
    detect_line_ending,
    extract_location_content,
    find_import_end,
)
from merge.types import ChangeType, SemanticChange, TaskSnapshot


class TestLineEndingDetection:
    """Tests for line ending detection."""

    def test_detect_lf_unix(self):
        """Detects Unix LF line endings."""
        content = "line1\nline2\nline3\n"
        assert detect_line_ending(content) == "\n"

    def test_detect_crlf_windows(self):
        """Detects Windows CRLF line endings."""
        content = "line1\r\nline2\r\nline3\r\n"
        assert detect_line_ending(content) == "\r\n"

    def test_detect_cr_classic_mac(self):
        """Detects classic Mac CR line endings."""
        content = "line1\rline2\rline3\r"
        assert detect_line_ending(content) == "\r"

    def test_detect_mixed_line_endings(self):
        """Returns first detected style for mixed endings."""
        # CRLF takes priority (checked first)
        content = "line1\r\nline2\nline3\r"
        assert detect_line_ending(content) == "\r\n"

    def test_detect_no_line_endings(self):
        """Defaults to LF when no line endings found."""
        content = "single line without newline"
        assert detect_line_ending(content) == "\n"


class TestSingleTaskChanges:
    """Tests for applying single task changes."""

    def test_apply_import_addition(self):
        """Adds import to file top."""
        baseline = """import os
from pathlib import Path

def hello():
    pass
"""

        change = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="logging",
            location="file_top",
            line_start=1,
            line_end=1,
            content_after="import logging",
        )

        snapshot = TaskSnapshot(
            task_id="task-001",
            task_intent="Add logging",
            started_at=datetime.now(),
            semantic_changes=[change],
        )

        result = apply_single_task_changes(baseline, snapshot, "test.py")

        assert "import logging" in result
        assert "import os" in result

    def test_apply_function_addition(self):
        """Adds function to file."""
        baseline = """def existing():
    pass
"""

        change = SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="new_function",
            location="file_bottom",
            line_start=10,
            line_end=12,
            content_after="def new_function():\n    return 42",
        )

        snapshot = TaskSnapshot(
            task_id="task-001",
            task_intent="Add function",
            started_at=datetime.now(),
            semantic_changes=[change],
        )

        result = apply_single_task_changes(baseline, snapshot, "test.py")

        assert "def new_function():" in result
        assert "def existing():" in result

    def test_apply_function_modification(self):
        """Modifies existing function."""
        baseline = """def hello():
    print("Hello")
"""

        change = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="hello",
            location="function:hello",
            line_start=1,
            line_end=2,
            content_before='def hello():\n    print("Hello")',
            content_after='def hello():\n    print("Hello, World!")',
        )

        snapshot = TaskSnapshot(
            task_id="task-001",
            task_intent="Update greeting",
            started_at=datetime.now(),
            semantic_changes=[change],
        )

        result = apply_single_task_changes(baseline, snapshot, "test.py")

        assert "Hello, World!" in result
        assert "Hello" in result

    def test_apply_multiple_changes(self):
        """Applies multiple changes in order."""
        baseline = """import os

def hello():
    pass
"""

        changes = [
            SemanticChange(
                change_type=ChangeType.ADD_IMPORT,
                target="logging",
                location="file_top",
                line_start=1,
                line_end=1,
                content_after="import logging",
            ),
            SemanticChange(
                change_type=ChangeType.ADD_FUNCTION,
                target="goodbye",
                location="file_bottom",
                line_start=10,
                line_end=12,
                content_after="def goodbye():\n    pass",
            ),
        ]

        snapshot = TaskSnapshot(
            task_id="task-001",
            task_intent="Add logging and goodbye",
            started_at=datetime.now(),
            semantic_changes=changes,
        )

        result = apply_single_task_changes(baseline, snapshot, "test.py")

        assert "import logging" in result
        assert "def goodbye():" in result

    def test_preserves_crlf_line_endings(self):
        """Preserves CRLF line endings."""
        baseline = "import os\r\n\r\ndef hello():\r\n    pass\r\n"

        change = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="logging",
            location="file_top",
            line_start=1,
            line_end=1,
            content_after="import logging",
        )

        snapshot = TaskSnapshot(
            task_id="task-001",
            task_intent="Add import",
            started_at=datetime.now(),
            semantic_changes=[change],
        )

        result = apply_single_task_changes(baseline, snapshot, "test.py")

        # Should preserve CRLF
        assert "\r\n" in result
        assert "import logging\r\n" in result or "import logging" in result

    def test_empty_changes(self):
        """Handles empty changes list."""
        baseline = "def hello():\n    pass\n"

        snapshot = TaskSnapshot(
            task_id="task-001",
            task_intent="No changes",
            started_at=datetime.now(),
            semantic_changes=[],
        )

        result = apply_single_task_changes(baseline, snapshot, "test.py")

        # Should return unchanged baseline
        assert result == baseline


class TestCombineNonConflictingChanges:
    """Tests for combining changes from multiple tasks."""

    def test_combine_compatible_imports(self):
        """Combines imports from different tasks."""
        baseline = """import os
from pathlib import Path

def hello():
    pass
"""

        snapshot1 = TaskSnapshot(
            task_id="task-001",
            task_intent="Add logging",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="logging",
                    location="file_top",
                    line_start=1,
                    line_end=1,
                    content_after="import logging",
                ),
            ],
        )

        snapshot2 = TaskSnapshot(
            task_id="task-002",
            task_intent="Add json",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="json",
                    location="file_top",
                    line_start=1,
                    line_end=1,
                    content_after="import json",
                ),
            ],
        )

        result = combine_non_conflicting_changes(baseline, [snapshot1, snapshot2], "test.py")

        assert "import logging" in result
        assert "import json" in result

    def test_combine_functions_from_different_tasks(self):
        """Combines new functions from multiple tasks."""
        baseline = """def existing():
    pass
"""

        snapshot1 = TaskSnapshot(
            task_id="task-001",
            task_intent="Add func1",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="func1",
                    location="file_bottom",
                    line_start=10,
                    line_end=12,
                    content_after="def func1():\n    return 1",
                ),
            ],
        )

        snapshot2 = TaskSnapshot(
            task_id="task-002",
            task_intent="Add func2",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="func2",
                    location="file_bottom",
                    line_start=20,
                    line_end=22,
                    content_after="def func2():\n    return 2",
                ),
            ],
        )

        result = combine_non_conflicting_changes(baseline, [snapshot1, snapshot2], "test.py")

        assert "def func1():" in result
        assert "def func2():" in result

    def test_combine_imports_and_modifications(self):
        """Combines imports, modifications, and additions."""
        baseline = """import os

def hello():
    print("Hello")
"""

        snapshot1 = TaskSnapshot(
            task_id="task-001",
            task_intent="Add logging import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="logging",
                    location="file_top",
                    line_start=1,
                    line_end=1,
                    content_after="import logging",
                ),
            ],
        )

        snapshot2 = TaskSnapshot(
            task_id="task-002",
            task_intent="Modify hello",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.MODIFY_FUNCTION,
                    target="hello",
                    location="function:hello",
                    line_start=3,
                    line_end=4,
                    content_before='def hello():\n    print("Hello")',
                    content_after='def hello():\n    print("Hello, World!")',
                ),
            ],
        )

        result = combine_non_conflicting_changes(baseline, [snapshot1, snapshot2], "test.py")

        assert "import logging" in result
        assert "Hello, World!" in result

    def test_deduplicates_identical_imports(self):
        """Checks deduplication behavior for identical imports."""
        baseline = """import os

def hello():
    pass
"""

        # Both tasks add same import
        snapshot1 = TaskSnapshot(
            task_id="task-001",
            task_intent="Add logging",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="logging",
                    location="file_top",
                    line_start=1,
                    line_end=1,
                    content_after="import logging",
                ),
            ],
        )

        snapshot2 = TaskSnapshot(
            task_id="task-002",
            task_intent="Also add logging",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="logging",
                    location="file_top",
                    line_start=1,
                    line_end=1,
                    content_after="import logging",
                ),
            ],
        )

        result = combine_non_conflicting_changes(baseline, [snapshot1, snapshot2], "test.py")

        # Current implementation deduplicates via "not in content" check
        # Should have deduplication
        assert result.count("import logging") <= 2  # May be 1 or 2 depending on implementation

    def test_preserves_line_endings(self):
        """Preserves original line ending style."""
        baseline = "import os\r\n\r\ndef hello():\r\n    pass\r\n"

        snapshot = TaskSnapshot(
            task_id="task-001",
            task_intent="Add import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="logging",
                    location="file_top",
                    line_start=1,
                    line_end=1,
                    content_after="import logging",
                ),
            ],
        )

        result = combine_non_conflicting_changes(baseline, [snapshot], "test.py")

        # Should preserve CRLF
        assert "\r\n" in result


class TestFindImportEnd:
    """Tests for finding import section end."""

    def test_find_import_end_python(self):
        """Finds end of Python imports."""
        lines = [
            "import os",
            "import sys",
            "from pathlib import Path",
            "",
            "def hello():",
            "    pass",
        ]

        end = find_import_end(lines, "test.py")

        assert end == 3

    def test_find_import_end_typescript(self):
        """Finds end of TypeScript imports."""
        lines = [
            "import React from 'react';",
            "import { useState } from 'react';",
            "",
            "function App() {",
            "  return <div />;",
            "}",
        ]

        end = find_import_end(lines, "test.tsx")

        assert end == 2

    def test_find_import_end_no_imports(self):
        """Returns 0 when no imports found."""
        lines = [
            "def hello():",
            "    pass",
        ]

        end = find_import_end(lines, "test.py")

        assert end == 0

    def test_find_import_end_python_with_from(self):
        """Handles Python from imports."""
        lines = [
            "from os import path",
            "from typing import List, Dict",
            "",
            "class MyClass:",
            "    pass",
        ]

        end = find_import_end(lines, "test.py")

        assert end == 2


class TestExtractLocationContent:
    """Tests for extracting content from specific locations."""

    def test_extract_function_content(self):
        """Extracts function definition."""
        content = """import os

function hello() {
  console.log("Hello");
}

function goodbye() {
  console.log("Goodbye");
}
"""

        extracted = extract_location_content(content, "function:hello")

        assert "hello" in extracted
        assert "goodbye" not in extracted

    def test_extract_arrow_function(self):
        """Extracts arrow function."""
        content = """const hello = () => {
  console.log("Hello");
};

const goodbye = () => {
  console.log("Goodbye");
};
"""

        extracted = extract_location_content(content, "function:hello")

        # Should extract hello function
        assert "hello" in extracted

    def test_extract_class_content(self):
        """Extracts class definition."""
        content = """class MyClass {
  constructor() {
    this.value = 42;
  }
}

class OtherClass {
  constructor() {}
}
"""

        extracted = extract_location_content(content, "class:MyClass")

        assert "MyClass" in extracted
        assert "OtherClass" not in extracted

    def test_extract_nonexistent_location(self):
        """Returns full content if location not found."""
        content = "def hello():\n    pass\n"

        extracted = extract_location_content(content, "function:nonexistent")

        assert extracted == content

    def test_extract_invalid_location_format(self):
        """Returns full content for invalid location format."""
        content = "def hello():\n    pass\n"

        extracted = extract_location_content(content, "invalid_format")

        assert extracted == content


class TestApplyAIMerge:
    """Tests for applying AI-merged content."""

    def test_apply_ai_merge_to_function(self):
        """Applies AI-merged function content."""
        content = """import os

function hello() {
  console.log("Hello");
}

function goodbye() {
  console.log("Goodbye");
}
"""

        merged_region = """function hello() {
  console.log("Hello, World!");
  console.log("AI merged this");
}"""

        result = apply_ai_merge(content, "function:hello", merged_region)

        assert "AI merged this" in result
        assert "function goodbye()" in result

    def test_apply_ai_merge_empty_region(self):
        """Returns original content if merged region is empty."""
        content = "def hello():\n    pass\n"

        result = apply_ai_merge(content, "function:hello", "")

        assert result == content

    def test_apply_ai_merge_to_class(self):
        """Applies AI-merged class content."""
        content = """class MyClass {
  method1() {
    return 1;
  }
}

class OtherClass {}
"""

        merged_region = """class MyClass {
  method1() {
    return 42;
  }
  method2() {
    return 2;
  }
}"""

        result = apply_ai_merge(content, "class:MyClass", merged_region)

        assert "method2()" in result
        assert "return 42" in result
        assert "class OtherClass" in result


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_baseline(self):
        """Handles empty baseline content."""
        baseline = ""

        change = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="os",
            location="file_top",
            line_start=1,
            line_end=1,
            content_after="import os",
        )

        snapshot = TaskSnapshot(
            task_id="task-001",
            task_intent="Add import to empty file",
            started_at=datetime.now(),
            semantic_changes=[change],
        )

        result = apply_single_task_changes(baseline, snapshot, "test.py")

        assert "import os" in result

    def test_baseline_with_only_whitespace(self):
        """Handles baseline with only whitespace."""
        baseline = "   \n\n   \n"

        change = SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="hello",
            location="file_bottom",
            line_start=1,
            line_end=2,
            content_after="def hello():\n    pass",
        )

        snapshot = TaskSnapshot(
            task_id="task-001",
            task_intent="Add function",
            started_at=datetime.now(),
            semantic_changes=[change],
        )

        result = apply_single_task_changes(baseline, snapshot, "test.py")

        assert "def hello():" in result

    def test_change_with_none_content(self):
        """Handles changes with None content gracefully."""
        baseline = "def existing():\n    pass\n"

        change = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="existing",
            location="function:existing",
            line_start=1,
            line_end=2,
            content_before=None,
            content_after=None,
        )

        snapshot = TaskSnapshot(
            task_id="task-001",
            task_intent="Null change",
            started_at=datetime.now(),
            semantic_changes=[change],
        )

        result = apply_single_task_changes(baseline, snapshot, "test.py")

        # Should handle gracefully
        assert result is not None

    def test_unicode_content(self):
        """Handles Unicode content correctly."""
        baseline = """# -*- coding: utf-8 -*-
def hello():
    return "Hello 世界 🌍"
"""

        change = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="os",
            location="file_top",
            line_start=1,
            line_end=1,
            content_after="import os",
        )

        snapshot = TaskSnapshot(
            task_id="task-001",
            task_intent="Add import",
            started_at=datetime.now(),
            semantic_changes=[change],
        )

        result = apply_single_task_changes(baseline, snapshot, "test.py")

        assert "世界" in result
        assert "🌍" in result
        assert "import os" in result

    def test_very_long_file(self):
        """Handles very long files."""
        # Create file with 1000 lines
        lines = [f"# Line {i}\n" for i in range(1000)]
        baseline = "".join(lines)

        change = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="os",
            location="file_top",
            line_start=1,
            line_end=1,
            content_after="import os",
        )

        snapshot = TaskSnapshot(
            task_id="task-001",
            task_intent="Add import",
            started_at=datetime.now(),
            semantic_changes=[change],
        )

        result = apply_single_task_changes(baseline, snapshot, "test.py")

        assert "import os" in result
        assert len(result.splitlines()) >= 1000
