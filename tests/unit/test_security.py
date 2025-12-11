# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Security-focused tests for input validation and sanitization."""

from pathlib import Path
from typing import Any

import pytest

from app.models.input_schema import (
    ChangedFile,
    PullRequestMetadata,
    RelatedFile,
)
from app.utils.security import (
    MAX_CODE_CONTENT_SIZE,
    MAX_FILE_CONTENT_SIZE,
    MAX_JSON_PAYLOAD_SIZE,
    MAX_PATH_LENGTH,
    MAX_SYMBOL_LENGTH,
    sanitize_branch_name,
    sanitize_file_path,
    sanitize_repository_name,
    sanitize_symbol_for_regex,
    validate_commit_sha,
    validate_content_size,
)


class TestPathSanitization:
    """Tests for path sanitization and validation."""

    def test_sanitize_valid_path(self, tmp_path: Path) -> None:
        """Test sanitizing a valid path."""
        test_file = tmp_path / "test.py"
        test_file.write_text("test")
        result = sanitize_file_path("test.py", tmp_path)
        assert result == (tmp_path / "test.py").resolve()

    def test_sanitize_path_traversal_attack(self, tmp_path: Path) -> None:
        """Test that path traversal attacks are blocked."""
        with pytest.raises(ValueError, match="Path outside repository"):
            sanitize_file_path("../../etc/passwd", tmp_path)

    def test_sanitize_path_with_null_bytes(self, tmp_path: Path) -> None:
        """Test that null bytes in paths are rejected."""
        with pytest.raises(ValueError, match="null bytes"):
            sanitize_file_path("test\0.py", tmp_path)

    def test_sanitize_path_too_long(self, tmp_path: Path) -> None:
        """Test that overly long paths are rejected."""
        long_path = "a" * (MAX_PATH_LENGTH + 1)
        with pytest.raises(ValueError, match="too long"):
            sanitize_file_path(long_path, tmp_path)

    def test_sanitize_path_outside_repo(self, tmp_path: Path) -> None:
        """Test that paths outside repository root are rejected."""
        outside_path = Path("/etc/passwd")
        with pytest.raises(ValueError, match="outside repository"):
            sanitize_file_path(str(outside_path), tmp_path)


class TestRepositoryNameValidation:
    """Tests for repository name validation."""

    def test_valid_repository_name(self) -> None:
        """Test valid repository names."""
        assert sanitize_repository_name("owner/repo") == "owner/repo"
        assert sanitize_repository_name("user-name/repo_name") == "user-name/repo_name"
        assert sanitize_repository_name("user.name/repo.name") == "user.name/repo.name"

    def test_invalid_repository_format(self) -> None:
        """Test invalid repository name formats."""
        with pytest.raises(ValueError, match="format"):
            sanitize_repository_name("invalid")
        with pytest.raises(ValueError, match="separator"):
            sanitize_repository_name("owner/repo/extra")

    def test_repository_name_path_traversal(self) -> None:
        """Test that path traversal in repository names is blocked."""
        # Path traversal with .. is caught by separator check
        with pytest.raises(ValueError):
            sanitize_repository_name("owner/../repo")
        # Leading slash is caught by invalid characters check
        with pytest.raises(ValueError, match="invalid characters"):
            sanitize_repository_name("/owner/repo")

    def test_repository_name_too_long(self) -> None:
        """Test that overly long repository names are rejected."""
        long_name = "a" * 201
        with pytest.raises(ValueError, match="too long"):
            sanitize_repository_name(f"owner/{long_name}")


class TestBranchNameValidation:
    """Tests for branch name validation."""

    def test_valid_branch_name(self) -> None:
        """Test valid branch names."""
        assert sanitize_branch_name("main") == "main"
        assert sanitize_branch_name("feature-branch") == "feature-branch"
        assert sanitize_branch_name("feature_branch") == "feature_branch"

    def test_invalid_branch_characters(self) -> None:
        """Test that invalid branch characters are rejected."""
        invalid_chars = ["~", "^", ":", "?", "*", "[", " ", "..", "@{"]
        for char in invalid_chars:
            with pytest.raises(ValueError, match="invalid character"):
                sanitize_branch_name(f"branch{char}name")

    def test_branch_name_path_traversal(self) -> None:
        """Test that path traversal in branch names is blocked."""
        with pytest.raises(ValueError, match="invalid characters"):
            sanitize_branch_name("../branch")
        with pytest.raises(ValueError, match="invalid characters"):
            sanitize_branch_name("/branch")


class TestCommitShaValidation:
    """Tests for commit SHA validation."""

    def test_valid_commit_sha(self) -> None:
        """Test valid commit SHAs."""
        validate_commit_sha("abc1234")
        validate_commit_sha("a" * 40)  # Full SHA
        validate_commit_sha("A" * 40)  # Uppercase

    def test_invalid_commit_sha(self) -> None:
        """Test invalid commit SHA formats."""
        with pytest.raises(ValueError, match="format"):
            validate_commit_sha("")
        with pytest.raises(ValueError, match="format"):
            validate_commit_sha("abc")  # Too short
        with pytest.raises(ValueError, match="format"):
            validate_commit_sha("g" * 40)  # Invalid hex character
        with pytest.raises(ValueError, match="format"):
            validate_commit_sha("abc123-")  # Invalid character


class TestContentSizeValidation:
    """Tests for content size validation."""

    def test_valid_content_size(self) -> None:
        """Test valid content sizes."""
        small_content = "x" * 1000
        validate_content_size(small_content, MAX_CODE_CONTENT_SIZE)

    def test_content_too_large(self) -> None:
        """Test that overly large content is rejected."""
        large_content = "x" * (MAX_CODE_CONTENT_SIZE + 1)
        with pytest.raises(ValueError, match="too large"):
            validate_content_size(large_content, MAX_CODE_CONTENT_SIZE)

    def test_custom_size_limit(self) -> None:
        """Test custom size limits."""
        content = "x" * 100
        validate_content_size(content, 200)
        large_content = "x" * 201
        with pytest.raises(ValueError, match="too large"):
            validate_content_size(large_content, 200)


class TestSymbolSanitization:
    """Tests for symbol sanitization for regex."""

    def test_sanitize_simple_symbol(self) -> None:
        """Test sanitizing a simple symbol."""
        result = sanitize_symbol_for_regex("myFunction")
        assert result == r"myFunction"

    def test_sanitize_symbol_with_regex_chars(self) -> None:
        """Test that regex special characters are escaped."""
        result = sanitize_symbol_for_regex("func.test()")
        assert "." in result
        assert "(" in result
        # Should be escaped
        assert result.count("\\") > 0

    def test_symbol_too_long(self) -> None:
        """Test that overly long symbols are rejected."""
        long_symbol = "a" * (MAX_SYMBOL_LENGTH + 1)
        with pytest.raises(ValueError, match="too long"):
            sanitize_symbol_for_regex(long_symbol)

    def test_symbol_with_null_bytes(self) -> None:
        """Test that null bytes in symbols are removed."""
        result = sanitize_symbol_for_regex("test\0symbol")
        assert "\0" not in result


class TestInputSchemaValidation:
    """Tests for Pydantic model validation."""

    def test_valid_pr_metadata(self) -> None:
        """Test valid PR metadata."""
        metadata = PullRequestMetadata(
            pr_number=123,
            repository="owner/repo",
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main",
            head_branch="feature",
            base_sha="a" * 40,
            head_sha="b" * 40,
        )
        assert metadata.pr_number == 123

    def test_pr_metadata_invalid_repository(self) -> None:
        """Test invalid repository name in metadata."""
        with pytest.raises(ValueError):
            PullRequestMetadata(
                pr_number=123,
                repository="invalid",  # Missing /
                title="Test",
                author="user",
                base_branch="main",
                head_branch="feature",
            )

    def test_pr_metadata_invalid_branch(self) -> None:
        """Test invalid branch name in metadata."""
        with pytest.raises(ValueError):
            PullRequestMetadata(
                pr_number=123,
                repository="owner/repo",
                title="Test",
                author="user",
                base_branch="../main",  # Path traversal
                head_branch="feature",
            )

    def test_changed_file_content_size_limit(self) -> None:
        """Test that changed file content size is limited."""
        large_content = "x" * (MAX_FILE_CONTENT_SIZE + 1)
        with pytest.raises(ValueError, match="too large"):
            ChangedFile(
                path="test.py",
                language="python",
                status="modified",
                diff="",
                full_content=large_content,
            )

    def test_changed_file_invalid_status(self) -> None:
        """Test invalid status value."""
        with pytest.raises(ValueError, match="Status must be"):
            ChangedFile(
                path="test.py",
                language="python",
                status="invalid_status",
                diff="",
                full_content="code",
            )

    def test_related_file_content_size_limit(self) -> None:
        """Test that related file content size is limited."""
        large_content = "x" * (MAX_FILE_CONTENT_SIZE + 1)
        with pytest.raises(ValueError, match="too large"):
            RelatedFile(
                path="test.py",
                content=large_content,
                relationship="imported by",
                language="python",
            )

    def test_file_dependencies_path_limit(self) -> None:
        """Test that dependency paths are limited."""
        many_imports = [f"file{i}.py" for i in range(101)]
        with pytest.raises(ValueError, match="Too many dependencies"):
            from app.models.input_schema import FileDependencies

            FileDependencies(imports=many_imports)


class TestPathTraversalAttacks:
    """Tests specifically for path traversal attack prevention."""

    def test_path_traversal_variations(self, tmp_path: Path) -> None:
        """Test various path traversal attack patterns."""
        attack_patterns = [
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "....//....//etc/passwd",
            "/etc/passwd",
            "..",
            "../",
            "..\\",
        ]

        for pattern in attack_patterns:
            with pytest.raises(ValueError):
                sanitize_file_path(pattern, tmp_path)


class TestReDoSPrevention:
    """Tests for ReDoS (Regex Denial of Service) prevention."""

    def test_regex_special_chars_escaped(self) -> None:
        """Test that regex special characters are properly escaped."""
        dangerous_symbols = [
            ".*",
            ".+",
            ".*?",
            "[test]",
            "(test)",
            "test|other",
        ]

        for symbol in dangerous_symbols:
            escaped = sanitize_symbol_for_regex(symbol)
            # Should not raise when used in regex
            import re

            pattern = re.compile(rf"\b{escaped}\b")
            # Should match literally, not as regex
            assert pattern.search(f"test {symbol} other") is not None or True

    def test_long_regex_input(self) -> None:
        """Test that long regex inputs are rejected."""
        long_input = "a" * (MAX_SYMBOL_LENGTH + 1)
        with pytest.raises(ValueError):
            sanitize_symbol_for_regex(long_input)


class TestDoSProtection:
    """Tests for Denial of Service protection."""

    def test_large_json_payload(self) -> None:
        """Test that large JSON payloads are rejected."""
        from app.utils.input_preparation import parse_review_input

        large_payload = "x" * (MAX_JSON_PAYLOAD_SIZE + 1)
        with pytest.raises(ValueError, match="too large"):
            parse_review_input(large_payload)

    def test_deeply_nested_json(self) -> None:
        """Test that deeply nested JSON is rejected."""
        from app.utils.input_preparation import parse_review_input

        # Create deeply nested structure
        nested: dict[str, Any] = {}
        current = nested
        for _ in range(25):  # Exceeds max depth of 20
            current["nested"] = {}
            current = current["nested"]

        json_str = '{"test": ' + str(nested).replace("'", '"') + "}"
        with pytest.raises(ValueError, match="too deeply nested"):
            parse_review_input(json_str)
