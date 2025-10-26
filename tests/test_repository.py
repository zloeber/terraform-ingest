"""Tests for repository management functionality."""

from unittest.mock import Mock
from terraform_ingest.repository import RepositoryManager


class TestGetTags:
    """Test suite for semantic version tag sorting."""

    def test_get_tags_semantic_version_sorting(self):
        """Test that tags are sorted by semantic version in descending order."""
        # Create a mock repo with tags
        mock_repo = Mock()
        mock_tags = []

        # Create mock tag objects
        tag_names = ["v1.2.3", "v1.10.0", "v1.2.1", "v2.0.0", "v1.5.0"]
        for tag_name in tag_names:
            tag = Mock()
            tag.name = tag_name
            mock_tags.append(tag)

        mock_repo.tags = mock_tags

        # Create repository manager and test
        manager = RepositoryManager()
        sorted_tags = manager._get_tags(mock_repo)

        # Expected order: v2.0.0, v1.10.0, v1.5.0, v1.2.3, v1.2.1
        expected = ["v2.0.0", "v1.10.0", "v1.5.0", "v1.2.3", "v1.2.1"]
        assert sorted_tags == expected

    def test_get_tags_with_max_tags(self):
        """Test that max_tags parameter limits the number of returned tags."""
        mock_repo = Mock()
        mock_tags = []

        tag_names = ["v1.0.0", "v2.0.0", "v3.0.0", "v4.0.0", "v5.0.0"]
        for tag_name in tag_names:
            tag = Mock()
            tag.name = tag_name
            mock_tags.append(tag)

        mock_repo.tags = mock_tags

        manager = RepositoryManager()
        sorted_tags = manager._get_tags(mock_repo, max_tags=3)

        # Should return only the 3 latest versions
        expected = ["v5.0.0", "v4.0.0", "v3.0.0"]
        assert sorted_tags == expected
        assert len(sorted_tags) == 3

    def test_get_tags_mixed_valid_and_invalid_versions(self):
        """Test handling of non-semantic version tags."""
        mock_repo = Mock()
        mock_tags = []

        tag_names = ["v1.2.3", "release-2023-01-01", "v2.0.0", "stable", "v1.5.0"]
        for tag_name in tag_names:
            tag = Mock()
            tag.name = tag_name
            mock_tags.append(tag)

        mock_repo.tags = mock_tags

        manager = RepositoryManager()
        sorted_tags = manager._get_tags(mock_repo)

        # Valid versions should come first (sorted by version), then non-versions
        # sorted alphabetically in reverse
        assert sorted_tags[:3] == ["v2.0.0", "v1.5.0", "v1.2.3"]
        # Non-version tags come after, in reverse alphabetical order
        assert sorted_tags[3:] == sorted(["release-2023-01-01", "stable"], reverse=True)

    def test_get_tags_empty_repo(self):
        """Test handling of repository with no tags."""
        mock_repo = Mock()
        mock_repo.tags = []

        manager = RepositoryManager()
        sorted_tags = manager._get_tags(mock_repo)

        assert sorted_tags == []

    def test_get_tags_pre_release_versions(self):
        """Test handling of pre-release versions."""
        mock_repo = Mock()
        mock_tags = []

        tag_names = ["v1.0.0", "v1.0.0-alpha", "v1.0.0-beta", "v1.0.1"]
        for tag_name in tag_names:
            tag = Mock()
            tag.name = tag_name
            mock_tags.append(tag)

        mock_repo.tags = mock_tags

        manager = RepositoryManager()
        sorted_tags = manager._get_tags(mock_repo)

        # Pre-release versions should be sorted correctly by packaging.version
        # v1.0.1 > v1.0.0 > v1.0.0-beta > v1.0.0-alpha
        assert sorted_tags[0] == "v1.0.1"
        assert sorted_tags[1] == "v1.0.0"
