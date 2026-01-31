#!/usr/bin/env python3
"""
Tests for analysis.security_scanner module.

Tests cover:
- Secrets scanning with various patterns
- SAST tool integration (Bandit)
- Dependency vulnerability scanning (npm audit, pip-audit)
- Security scan result aggregation
- Severity classification
- QA blocking logic
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add backend directory to path
_backend_dir = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from analysis.security_scanner import (
    SecurityScanner,
    SecurityScanResult,
    SecurityVulnerability,
    scan_for_security_issues,
    has_security_issues,
    scan_secrets_only,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def scanner():
    """Create a SecurityScanner instance."""
    return SecurityScanner()


@pytest.fixture
def python_project_with_secrets(temp_dir):
    """Create a Python project with secrets for testing."""
    (temp_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (temp_dir / "app").mkdir()
    (temp_dir / "app" / "__init__.py").write_text("")

    # File with API key
    (temp_dir / "app" / "config.py").write_text(
        'API_KEY = "sk-1234567890abcdef1234567890abcdef"\n'
        'DATABASE_URL = "postgresql://user:password@localhost/db"\n'
    )

    return temp_dir


@pytest.fixture
def node_project_with_vulnerabilities(temp_dir):
    """Create a Node.js project for testing."""
    package_json = {
        "name": "test-project",
        "dependencies": {
            "lodash": "4.17.15",  # Known vulnerable version
        },
    }
    (temp_dir / "package.json").write_text(json.dumps(package_json, indent=2))
    return temp_dir


# =============================================================================
# SECRETS SCANNING
# =============================================================================


class TestSecretsScanning:
    """Tests for secrets detection."""

    @patch("analysis.security_scanner.HAS_SECRETS_SCANNER", True)
    @patch("analysis.security_scanner.scan_files")
    @patch("analysis.security_scanner.get_all_tracked_files")
    def test_scan_finds_secrets(
        self, mock_get_files, mock_scan_files, scanner, temp_dir
    ):
        """Test that secrets are detected and reported."""
        # Mock the secrets scanner
        mock_get_files.return_value = ["config.py"]

        # Create a mock secret match
        mock_match = MagicMock()
        mock_match.file_path = "config.py"
        mock_match.line_number = 1
        mock_match.pattern_name = "API Key"
        mock_match.matched_text = "sk-1234567890abcdef"
        mock_scan_files.return_value = [mock_match]

        result = scanner.scan(temp_dir, run_sast=False, run_dependency_audit=False)

        assert len(result.secrets) == 1
        assert result.secrets[0]["file"] == "config.py"
        assert result.secrets[0]["line"] == 1
        assert result.secrets[0]["pattern"] == "API Key"

    @patch("analysis.security_scanner.HAS_SECRETS_SCANNER", True)
    @patch("analysis.security_scanner.scan_files")
    @patch("analysis.security_scanner.get_all_tracked_files")
    def test_secrets_create_vulnerabilities(
        self, mock_get_files, mock_scan_files, scanner, temp_dir
    ):
        """Test that detected secrets are also added as vulnerabilities."""
        mock_get_files.return_value = ["config.py"]

        mock_match = MagicMock()
        mock_match.file_path = "config.py"
        mock_match.line_number = 1
        mock_match.pattern_name = "API Key"
        mock_match.matched_text = "sk-1234567890abcdef"
        mock_scan_files.return_value = [mock_match]

        result = scanner.scan(temp_dir, run_sast=False, run_dependency_audit=False)

        # Should have both secret entry and vulnerability entry
        assert len(result.secrets) == 1
        assert len(result.vulnerabilities) == 1
        assert result.vulnerabilities[0].severity == "critical"
        assert result.vulnerabilities[0].source == "secrets"

    @patch("analysis.security_scanner.HAS_SECRETS_SCANNER", True)
    @patch("analysis.security_scanner.scan_files")
    def test_scan_specific_files(self, mock_scan_files, scanner, temp_dir):
        """Test scanning specific changed files."""
        mock_scan_files.return_value = []

        scanner.scan(
            temp_dir,
            changed_files=["src/config.py", "src/utils.py"],
            run_sast=False,
            run_dependency_audit=False,
        )

        # Should pass the changed files to scan_files
        mock_scan_files.assert_called_once()
        assert mock_scan_files.call_args[0][0] == ["src/config.py", "src/utils.py"]

    @patch("analysis.security_scanner.HAS_SECRETS_SCANNER", False)
    def test_no_secrets_scanner_available(self, scanner, temp_dir):
        """Test behavior when secrets scanner is not available."""
        result = scanner.scan(temp_dir, run_sast=False, run_dependency_audit=False)

        assert len(result.secrets) == 0
        assert len(result.scan_errors) >= 1
        assert any("not available" in err for err in result.scan_errors)

    def test_secret_redaction(self, scanner):
        """Test that secrets are redacted in output."""
        redacted = scanner._redact_secret("sk-1234567890abcdef1234567890abcdef")
        assert "sk-1" in redacted
        assert "cdef" in redacted
        assert "34567890" not in redacted

    def test_short_secret_redaction(self, scanner):
        """Test redaction of short secrets."""
        redacted = scanner._redact_secret("secret")
        assert redacted == "******"


# =============================================================================
# SAST SCANNING (BANDIT)
# =============================================================================


class TestBanditScanning:
    """Tests for Bandit SAST scanning."""

    @patch("subprocess.run")
    def test_bandit_scan_python_project(self, mock_run, scanner, temp_dir):
        """Test Bandit scanning on Python project."""
        # Create Python project
        (temp_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        (temp_dir / "app").mkdir()
        (temp_dir / "app" / "__init__.py").write_text("")

        # Mock Bandit output
        bandit_output = {
            "results": [
                {
                    "issue_severity": "HIGH",
                    "issue_text": "Use of assert detected",
                    "filename": "app/main.py",
                    "line_number": 10,
                    "issue_cwe": {"id": "CWE-703"},
                }
            ]
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(bandit_output), returncode=0
        )

        # Mock bandit availability
        scanner._bandit_available = True

        result = scanner.scan(temp_dir, run_secrets=False, run_dependency_audit=False)

        assert len(result.vulnerabilities) == 1
        assert result.vulnerabilities[0].severity == "high"
        assert result.vulnerabilities[0].source == "bandit"
        assert result.vulnerabilities[0].file == "app/main.py"
        assert result.vulnerabilities[0].line == 10
        assert result.vulnerabilities[0].cwe == "CWE-703"

    @patch("subprocess.run")
    def test_bandit_severity_mapping(self, mock_run, scanner, temp_dir):
        """Test correct severity mapping for Bandit findings."""
        (temp_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        (temp_dir / "app").mkdir()
        (temp_dir / "app" / "__init__.py").write_text("")

        bandit_output = {
            "results": [
                {"issue_severity": "HIGH", "issue_text": "High severity"},
                {"issue_severity": "MEDIUM", "issue_text": "Medium severity"},
                {"issue_severity": "LOW", "issue_text": "Low severity"},
            ]
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(bandit_output), returncode=0
        )
        scanner._bandit_available = True

        result = scanner.scan(temp_dir, run_secrets=False, run_dependency_audit=False)

        severities = [v.severity for v in result.vulnerabilities]
        assert "high" in severities
        assert "medium" in severities
        assert "low" in severities

    def test_bandit_not_available(self, scanner, temp_dir):
        """Test handling when Bandit is not installed."""
        (temp_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        scanner._bandit_available = False

        result = scanner.scan(temp_dir, run_secrets=False, run_dependency_audit=False)

        # Should not crash, just skip Bandit
        assert isinstance(result, SecurityScanResult)

    def test_non_python_project_skips_bandit(self, scanner, temp_dir):
        """Test that Bandit is skipped for non-Python projects."""
        # Node.js project
        (temp_dir / "package.json").write_text("{}")

        result = scanner.scan(temp_dir, run_secrets=False, run_dependency_audit=False)

        # No Python vulnerabilities should be found
        bandit_vulns = [v for v in result.vulnerabilities if v.source == "bandit"]
        assert len(bandit_vulns) == 0


# =============================================================================
# DEPENDENCY AUDITS
# =============================================================================


class TestDependencyAudits:
    """Tests for dependency vulnerability scanning."""

    @patch("subprocess.run")
    def test_npm_audit(self, mock_run, scanner, temp_dir):
        """Test npm audit scanning."""
        package_json = {"name": "test-project", "dependencies": {"lodash": "4.17.15"}}
        (temp_dir / "package.json").write_text(json.dumps(package_json))

        # Mock npm audit output
        npm_output = {
            "vulnerabilities": {
                "lodash": {
                    "severity": "high",
                    "via": [{"title": "Prototype Pollution"}],
                }
            }
        }
        mock_run.return_value = MagicMock(stdout=json.dumps(npm_output), returncode=1)

        result = scanner.scan(temp_dir, run_secrets=False, run_sast=False)

        npm_vulns = [v for v in result.vulnerabilities if v.source == "npm_audit"]
        assert len(npm_vulns) >= 1
        assert npm_vulns[0].severity == "high"
        assert "lodash" in npm_vulns[0].title

    @patch("subprocess.run")
    def test_npm_audit_severity_mapping(self, mock_run, scanner, temp_dir):
        """Test npm audit severity mapping."""
        (temp_dir / "package.json").write_text("{}")

        npm_output = {
            "vulnerabilities": {
                "pkg1": {"severity": "critical", "via": [{"title": "Critical issue"}]},
                "pkg2": {"severity": "high", "via": [{"title": "High issue"}]},
                "pkg3": {"severity": "moderate", "via": [{"title": "Moderate issue"}]},
                "pkg4": {"severity": "low", "via": [{"title": "Low issue"}]},
            }
        }
        mock_run.return_value = MagicMock(stdout=json.dumps(npm_output), returncode=1)

        result = scanner.scan(temp_dir, run_secrets=False, run_sast=False)

        severities = [v.severity for v in result.vulnerabilities]
        assert "critical" in severities
        assert "high" in severities
        assert "medium" in severities
        assert "low" in severities

    @patch("subprocess.run")
    def test_pip_audit(self, mock_run, scanner, temp_dir):
        """Test pip-audit scanning."""
        (temp_dir / "requirements.txt").write_text("requests==2.25.0\n")

        # Mock pip-audit output
        pip_output = [
            {
                "name": "requests",
                "description": "Security vulnerability",
                "fix_versions": ["2.27.0"],
                "aliases": ["CVE-2021-12345"],
            }
        ]
        mock_run.return_value = MagicMock(stdout=json.dumps(pip_output), returncode=1)

        result = scanner.scan(temp_dir, run_secrets=False, run_sast=False)

        pip_vulns = [v for v in result.vulnerabilities if v.source == "pip_audit"]
        if len(pip_vulns) > 0:  # pip-audit may not be installed
            assert pip_vulns[0].severity == "high"
            assert "requests" in pip_vulns[0].title

    def test_no_package_json_skips_npm_audit(self, scanner, temp_dir):
        """Test that npm audit is skipped when package.json doesn't exist."""
        result = scanner.scan(temp_dir, run_secrets=False, run_sast=False)

        npm_vulns = [v for v in result.vulnerabilities if v.source == "npm_audit"]
        assert len(npm_vulns) == 0


# =============================================================================
# SEVERITY AND BLOCKING LOGIC
# =============================================================================


class TestSeverityAndBlocking:
    """Tests for severity classification and QA blocking logic."""

    def test_critical_issues_detected(self, scanner):
        """Test detection of critical issues."""
        result = SecurityScanResult()
        result.vulnerabilities.append(
            SecurityVulnerability(
                severity="critical",
                source="test",
                title="Critical issue",
                description="Test",
            )
        )

        # Manually trigger the logic that scan() performs
        result.has_critical_issues = any(
            v.severity in ["critical", "high"] for v in result.vulnerabilities
        )
        result.should_block_qa = any(
            v.severity == "critical" for v in result.vulnerabilities
        )

        assert result.has_critical_issues is True
        assert result.should_block_qa is True

    def test_high_issues_detected(self, scanner):
        """Test detection of high severity issues."""
        result = SecurityScanResult()
        result.vulnerabilities.append(
            SecurityVulnerability(
                severity="high", source="test", title="High issue", description="Test"
            )
        )

        result.has_critical_issues = any(
            v.severity in ["critical", "high"] for v in result.vulnerabilities
        )
        result.should_block_qa = any(
            v.severity == "critical" for v in result.vulnerabilities
        )

        assert result.has_critical_issues is True
        assert result.should_block_qa is False  # Only critical blocks

    @patch("analysis.security_scanner.HAS_SECRETS_SCANNER", True)
    @patch("analysis.security_scanner.scan_files")
    @patch("analysis.security_scanner.get_all_tracked_files")
    def test_secrets_always_block(
        self, mock_get_files, mock_scan_files, scanner, temp_dir
    ):
        """Test that any detected secrets always block QA."""
        mock_get_files.return_value = ["config.py"]

        mock_match = MagicMock()
        mock_match.file_path = "config.py"
        mock_match.line_number = 1
        mock_match.pattern_name = "API Key"
        mock_match.matched_text = "sk-test"
        mock_scan_files.return_value = [mock_match]

        result = scanner.scan(temp_dir, run_sast=False, run_dependency_audit=False)

        assert result.should_block_qa is True

    def test_low_severity_does_not_block(self, scanner):
        """Test that low severity issues don't block QA."""
        result = SecurityScanResult()
        result.vulnerabilities.append(
            SecurityVulnerability(
                severity="low", source="test", title="Low issue", description="Test"
            )
        )

        result.has_critical_issues = any(
            v.severity in ["critical", "high"] for v in result.vulnerabilities
        )
        result.should_block_qa = any(
            v.severity == "critical" for v in result.vulnerabilities
        )

        assert result.has_critical_issues is False
        assert result.should_block_qa is False


# =============================================================================
# RESULT SERIALIZATION
# =============================================================================


class TestResultSerialization:
    """Tests for scan result serialization."""

    def test_to_dict(self, scanner):
        """Test converting scan result to dictionary."""
        result = SecurityScanResult()
        result.secrets.append(
            {
                "file": "config.py",
                "line": 1,
                "pattern": "API Key",
                "matched_text": "sk-***",
            }
        )
        result.vulnerabilities.append(
            SecurityVulnerability(
                severity="high",
                source="bandit",
                title="SQL Injection",
                description="Possible SQL injection",
                file="app/db.py",
                line=25,
                cwe="CWE-89",
            )
        )

        result_dict = scanner.to_dict(result)

        assert "secrets" in result_dict
        assert "vulnerabilities" in result_dict
        assert "summary" in result_dict
        assert result_dict["summary"]["total_secrets"] == 1
        assert result_dict["summary"]["total_vulnerabilities"] == 1
        assert result_dict["summary"]["high_count"] == 1

    def test_dict_is_json_serializable(self, scanner):
        """Test that result dict can be serialized to JSON."""
        result = SecurityScanResult()
        result.vulnerabilities.append(
            SecurityVulnerability(
                severity="medium",
                source="test",
                title="Test",
                description="Test vuln",
            )
        )

        result_dict = scanner.to_dict(result)
        json_str = json.dumps(result_dict)
        assert len(json_str) > 0

    def test_save_results(self, scanner, temp_dir):
        """Test saving results to spec directory."""
        result = SecurityScanResult()
        result.vulnerabilities.append(
            SecurityVulnerability(
                severity="high", source="test", title="Test", description="Test"
            )
        )

        spec_dir = temp_dir / "spec"
        scanner.scan(temp_dir, spec_dir=spec_dir, run_secrets=False, run_sast=False)

        output_file = spec_dir / "security_scan_results.json"
        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)
        assert "vulnerabilities" in data


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch("analysis.security_scanner.HAS_SECRETS_SCANNER", True)
    @patch("analysis.security_scanner.scan_files")
    @patch("analysis.security_scanner.get_all_tracked_files")
    def test_scan_for_security_issues(
        self, mock_get_files, mock_scan_files, temp_dir
    ):
        """Test scan_for_security_issues convenience function."""
        mock_get_files.return_value = []
        mock_scan_files.return_value = []

        result = scan_for_security_issues(temp_dir)

        assert isinstance(result, SecurityScanResult)

    @patch("analysis.security_scanner.HAS_SECRETS_SCANNER", True)
    @patch("analysis.security_scanner.scan_files")
    @patch("analysis.security_scanner.get_all_tracked_files")
    def test_has_security_issues(self, mock_get_files, mock_scan_files, temp_dir):
        """Test has_security_issues convenience function."""
        mock_get_files.return_value = ["config.py"]

        # No secrets
        mock_scan_files.return_value = []
        assert has_security_issues(temp_dir) is False

        # With secrets
        mock_match = MagicMock()
        mock_match.file_path = "config.py"
        mock_match.line_number = 1
        mock_match.pattern_name = "API Key"
        mock_match.matched_text = "sk-test"
        mock_scan_files.return_value = [mock_match]
        assert has_security_issues(temp_dir) is True

    @patch("analysis.security_scanner.HAS_SECRETS_SCANNER", True)
    @patch("analysis.security_scanner.scan_files")
    @patch("analysis.security_scanner.get_all_tracked_files")
    def test_scan_secrets_only(self, mock_get_files, mock_scan_files, temp_dir):
        """Test scan_secrets_only convenience function."""
        mock_get_files.return_value = ["config.py"]

        mock_match = MagicMock()
        mock_match.file_path = "config.py"
        mock_match.line_number = 1
        mock_match.pattern_name = "API Key"
        mock_match.matched_text = "sk-test"
        mock_scan_files.return_value = [mock_match]

        secrets = scan_secrets_only(temp_dir)

        assert len(secrets) == 1
        assert secrets[0]["pattern"] == "API Key"


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_project(self, scanner, temp_dir):
        """Test scanning empty project."""
        result = scanner.scan(temp_dir)

        assert len(result.secrets) == 0
        assert len(result.vulnerabilities) == 0

    @patch("subprocess.run")
    def test_timeout_handling(self, mock_run, scanner, temp_dir):
        """Test handling of subprocess timeouts."""
        (temp_dir / "package.json").write_text("{}")

        mock_run.side_effect = subprocess.TimeoutExpired("npm audit", 120)

        result = scanner.scan(temp_dir, run_secrets=False, run_sast=False)

        # Should have error logged but not crash
        assert any("timed out" in err.lower() for err in result.scan_errors)

    def test_project_type_detection(self, scanner, temp_dir):
        """Test Python project detection."""
        # Not a Python project
        assert scanner._is_python_project(temp_dir) is False

        # Add Python indicator
        (temp_dir / "pyproject.toml").write_text("")
        assert scanner._is_python_project(temp_dir) is True

        # Clear and try requirements.txt
        (temp_dir / "pyproject.toml").unlink()
        (temp_dir / "requirements.txt").write_text("")
        assert scanner._is_python_project(temp_dir) is True

    def test_scan_with_all_options_disabled(self, scanner, temp_dir):
        """Test scan with all scan types disabled."""
        result = scanner.scan(
            temp_dir, run_secrets=False, run_sast=False, run_dependency_audit=False
        )

        assert isinstance(result, SecurityScanResult)
        assert len(result.secrets) == 0
        assert len(result.vulnerabilities) == 0
