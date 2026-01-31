"""
Tests for the context search module
====================================

Tests covering context/search.py - CodeSearcher class
"""

import pytest
import tempfile
from pathlib import Path

from context.search import CodeSearcher
from context.models import FileMatch
from context.constants import CODE_EXTENSIONS, SKIP_DIRS


# =============================================================================
# CodeSearcher Tests
# =============================================================================

class TestCodeSearcher:
    """Tests for CodeSearcher class."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as td:
            # Resolve to handle macOS /var -> /private/var symlink
            project_dir = Path(td).resolve()
            yield project_dir

    @pytest.fixture
    def populated_project(self, temp_project):
        """Create a project with sample code files."""
        # Create service directory
        service_dir = temp_project / "auth-service"
        service_dir.mkdir()

        # Create Python files
        (service_dir / "login.py").write_text("""
def login(username, password):
    '''Authenticate user with username and password'''
    if validate_credentials(username, password):
        return create_session(username)
    raise AuthenticationError("Invalid credentials")
""")

        (service_dir / "session.py").write_text("""
class Session:
    def __init__(self, user_id):
        self.user_id = user_id
        self.token = generate_token()

    def is_valid(self):
        return not self.is_expired()
""")

        (service_dir / "utils.py").write_text("""
def validate_credentials(username, password):
    # Check username and password
    return True

def generate_token():
    import secrets
    return secrets.token_hex(32)
""")

        # Create a nested directory
        models_dir = service_dir / "models"
        models_dir.mkdir()
        (models_dir / "user.py").write_text("""
class User:
    def __init__(self, username, email):
        self.username = username
        self.email = email
""")

        yield temp_project, service_dir

    def test_init(self, temp_project):
        """Test CodeSearcher initialization."""
        searcher = CodeSearcher(temp_project)
        assert searcher.project_dir == temp_project.resolve()

    def test_search_empty_service(self, temp_project):
        """Test searching in non-existent service path."""
        searcher = CodeSearcher(temp_project)
        result = searcher.search_service(
            temp_project / "nonexistent",
            "nonexistent",
            ["keyword"]
        )
        assert result == []

    def test_search_basic_keyword(self, populated_project):
        """Test basic keyword search."""
        project_dir, service_dir = populated_project
        searcher = CodeSearcher(project_dir)

        results = searcher.search_service(service_dir, "auth-service", ["login"])

        assert len(results) > 0
        # login.py should match
        paths = [r.path for r in results]
        assert any("login.py" in p for p in paths)

    def test_search_multiple_keywords(self, populated_project):
        """Test search with multiple keywords."""
        project_dir, service_dir = populated_project
        searcher = CodeSearcher(project_dir)

        results = searcher.search_service(
            service_dir,
            "auth-service",
            ["username", "password"]
        )

        assert len(results) > 0
        # Should find files with both keywords
        for match in results:
            assert "username" in match.reason or "password" in match.reason

    def test_search_case_insensitive(self, populated_project):
        """Test that search is case-insensitive on content."""
        project_dir, service_dir = populated_project
        searcher = CodeSearcher(project_dir)

        # The implementation compares keyword in content_lower (lowercased content)
        # So the keyword itself needs to match as-is in the lowercased content
        # Search with lowercase keyword (finds "Session" in the code)
        results = searcher.search_service(
            service_dir,
            "auth-service",
            ["session"]
        )

        # Should find matches in files containing "Session" (class name)
        assert len(results) > 0

        # Check that it found a file with Session class
        paths = [r.path for r in results]
        assert any("session.py" in p for p in paths)

    def test_search_returns_file_matches(self, populated_project):
        """Test that search returns FileMatch objects."""
        project_dir, service_dir = populated_project
        searcher = CodeSearcher(project_dir)

        results = searcher.search_service(service_dir, "auth-service", ["user"])

        assert len(results) > 0
        for match in results:
            assert isinstance(match, FileMatch)
            assert match.service == "auth-service"
            assert match.relevance_score > 0
            assert "user" in match.reason.lower()

    def test_search_matching_lines(self, populated_project):
        """Test that matching lines are captured."""
        project_dir, service_dir = populated_project
        searcher = CodeSearcher(project_dir)

        results = searcher.search_service(service_dir, "auth-service", ["username"])

        # Find a match with matching_lines
        matches_with_lines = [r for r in results if r.matching_lines]
        assert len(matches_with_lines) > 0

        # Check line format (line_number, line_content)
        for match in matches_with_lines:
            for line_num, line_content in match.matching_lines:
                assert isinstance(line_num, int)
                assert isinstance(line_content, str)

    def test_search_relevance_scoring(self, populated_project):
        """Test that relevance scores are calculated."""
        project_dir, service_dir = populated_project
        searcher = CodeSearcher(project_dir)

        results = searcher.search_service(
            service_dir,
            "auth-service",
            ["username"]
        )

        assert len(results) > 0
        # Results should be sorted by relevance
        scores = [r.relevance_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_limits_results(self, populated_project):
        """Test that results are limited to top 20."""
        project_dir, service_dir = populated_project
        searcher = CodeSearcher(project_dir)

        # Even with broad search, should limit to 20
        results = searcher.search_service(service_dir, "auth-service", ["def"])

        assert len(results) <= 20

    def test_search_nested_directories(self, populated_project):
        """Test searching in nested directories."""
        project_dir, service_dir = populated_project
        searcher = CodeSearcher(project_dir)

        # Search for something in nested models/user.py
        results = searcher.search_service(service_dir, "auth-service", ["email"])

        assert len(results) > 0
        paths = [r.path for r in results]
        assert any("models" in p and "user.py" in p for p in paths)

    def test_no_matches(self, populated_project):
        """Test search with no matching results."""
        project_dir, service_dir = populated_project
        searcher = CodeSearcher(project_dir)

        results = searcher.search_service(
            service_dir,
            "auth-service",
            ["nonexistentkeyword123"]
        )

        assert results == []


# =============================================================================
# _iter_code_files Tests
# =============================================================================

class TestIterCodeFiles:
    """Tests for _iter_code_files method."""

    @pytest.fixture
    def mixed_project(self):
        """Create a project with various file types."""
        with tempfile.TemporaryDirectory() as td:
            project_dir = Path(td).resolve()

            # Create code files
            (project_dir / "app.py").write_text("print('hello')")
            (project_dir / "index.js").write_text("console.log('hello')")
            (project_dir / "main.ts").write_text("console.log('hello')")
            (project_dir / "component.tsx").write_text("export default function(){}")

            # Create non-code files
            (project_dir / "README.md").write_text("# README")
            (project_dir / "data.json").write_text("{}")
            (project_dir / "config.yaml").write_text("key: value")
            (project_dir / ".env").write_text("SECRET=123")

            # Create skip directories
            node_modules = project_dir / "node_modules"
            node_modules.mkdir()
            (node_modules / "package.js").write_text("module.exports = {}")

            git_dir = project_dir / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("")

            venv_dir = project_dir / ".venv"
            venv_dir.mkdir()
            (venv_dir / "lib.py").write_text("pass")

            yield project_dir

    def test_yields_code_files(self, mixed_project):
        """Test that code files are yielded."""
        searcher = CodeSearcher(mixed_project)
        files = list(searcher._iter_code_files(mixed_project))

        filenames = [f.name for f in files]
        assert "app.py" in filenames
        assert "index.js" in filenames
        assert "main.ts" in filenames
        assert "component.tsx" in filenames

    def test_skips_non_code_files(self, mixed_project):
        """Test that non-code files are skipped."""
        searcher = CodeSearcher(mixed_project)
        files = list(searcher._iter_code_files(mixed_project))

        filenames = [f.name for f in files]
        assert "README.md" not in filenames
        assert "data.json" not in filenames
        assert "config.yaml" not in filenames
        assert ".env" not in filenames

    def test_skips_node_modules(self, mixed_project):
        """Test that node_modules is skipped."""
        searcher = CodeSearcher(mixed_project)
        files = list(searcher._iter_code_files(mixed_project))

        paths = [str(f) for f in files]
        assert not any("node_modules" in p for p in paths)

    def test_skips_git_directory(self, mixed_project):
        """Test that .git directory is skipped."""
        searcher = CodeSearcher(mixed_project)
        files = list(searcher._iter_code_files(mixed_project))

        paths = [str(f) for f in files]
        assert not any(".git" in p for p in paths)

    def test_skips_venv(self, mixed_project):
        """Test that .venv directory is skipped."""
        searcher = CodeSearcher(mixed_project)
        files = list(searcher._iter_code_files(mixed_project))

        paths = [str(f) for f in files]
        assert not any(".venv" in p for p in paths)

    def test_empty_directory(self):
        """Test iteration on empty directory."""
        with tempfile.TemporaryDirectory() as td:
            project_dir = Path(td).resolve()
            searcher = CodeSearcher(project_dir)
            files = list(searcher._iter_code_files(project_dir))
            assert files == []


# =============================================================================
# Constants Tests
# =============================================================================

class TestContextConstants:
    """Tests for context constants."""

    def test_code_extensions_contains_python(self):
        """Test that Python extension is included."""
        assert ".py" in CODE_EXTENSIONS

    def test_code_extensions_contains_javascript(self):
        """Test that JavaScript extensions are included."""
        assert ".js" in CODE_EXTENSIONS
        assert ".jsx" in CODE_EXTENSIONS

    def test_code_extensions_contains_typescript(self):
        """Test that TypeScript extensions are included."""
        assert ".ts" in CODE_EXTENSIONS
        assert ".tsx" in CODE_EXTENSIONS

    def test_skip_dirs_contains_node_modules(self):
        """Test that node_modules is in skip dirs."""
        assert "node_modules" in SKIP_DIRS

    def test_skip_dirs_contains_git(self):
        """Test that .git is in skip dirs."""
        assert ".git" in SKIP_DIRS

    def test_skip_dirs_contains_venv(self):
        """Test that virtual env directories are in skip dirs."""
        assert ".venv" in SKIP_DIRS
        assert "venv" in SKIP_DIRS

    def test_skip_dirs_contains_cache(self):
        """Test that cache directories are in skip dirs."""
        assert "__pycache__" in SKIP_DIRS
        assert ".pytest_cache" in SKIP_DIRS
        assert ".cache" in SKIP_DIRS


# =============================================================================
# Integration Tests
# =============================================================================

class TestCodeSearcherIntegration:
    """Integration tests for CodeSearcher."""

    def test_full_search_workflow(self):
        """Test complete search workflow."""
        with tempfile.TemporaryDirectory() as td:
            project_dir = Path(td).resolve()

            # Create a realistic service structure
            service_dir = project_dir / "user-service"
            service_dir.mkdir()

            controllers = service_dir / "controllers"
            controllers.mkdir()
            (controllers / "user_controller.py").write_text("""
class UserController:
    def get_user(self, user_id):
        return self.user_repository.find(user_id)

    def create_user(self, data):
        user = User(**data)
        return self.user_repository.save(user)
""")

            models = service_dir / "models"
            models.mkdir()
            (models / "user.py").write_text("""
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
""")

            repos = service_dir / "repositories"
            repos.mkdir()
            (repos / "user_repository.py").write_text("""
class UserRepository:
    def find(self, user_id):
        return self.db.query(User).filter(id=user_id).first()

    def save(self, user):
        self.db.add(user)
        self.db.commit()
        return user
""")

            # Search for user-related files
            searcher = CodeSearcher(project_dir)
            results = searcher.search_service(service_dir, "user-service", ["user"])

            # Should find all three files
            assert len(results) >= 3

            # Check that results include expected files
            paths = [r.path for r in results]
            assert any("user_controller.py" in p for p in paths)
            assert any("user.py" in p for p in paths)
            assert any("user_repository.py" in p for p in paths)

            # Controller should have higher score (more user mentions)
            controller_match = next(r for r in results if "controller" in r.path)
            assert controller_match.relevance_score > 0

    def test_search_with_special_characters_in_content(self):
        """Test searching files with special characters."""
        with tempfile.TemporaryDirectory() as td:
            project_dir = Path(td).resolve()
            service_dir = project_dir / "service"
            service_dir.mkdir()

            (service_dir / "special.py").write_text("""
# Special chars: áéíóú ñ 中文 emoji 🎉
def process_unicode():
    return "Hello, 世界"
""")

            searcher = CodeSearcher(project_dir)
            results = searcher.search_service(service_dir, "service", ["unicode"])

            assert len(results) > 0
            assert any("special.py" in r.path for r in results)
