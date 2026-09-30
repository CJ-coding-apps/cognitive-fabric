"""Unit tests for `validate_path` containment.

The fabric `ingest-ast` tool scans a caller-supplied directory, so the path must
be confined to the session's clientProjectRoot. These tests pin the three escape
routes that a bare `path.resolve()` does not close: `..` traversal, an absolute
path, and a symlink that points outside the root.
"""

from pathlib import Path

import pytest

from cognitive_fabric.utils.path_utils import validate_path


@pytest.mark.unit
class TestValidatePathWithoutRoot:
    def test_plain_path_is_valid(self):
        assert validate_path("some/dir") is True

    def test_empty_path_is_invalid(self):
        assert validate_path("") is False

    def test_traversal_is_refused(self):
        assert validate_path("../etc") is False

    def test_must_exist_is_checked(self, tmp_path: Path):
        assert validate_path(str(tmp_path), must_exist=True) is True
        assert validate_path(str(tmp_path / "missing"), must_exist=True) is False


@pytest.mark.unit
class TestValidatePathContainment:
    def test_path_inside_root_is_valid(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        assert (
            validate_path(str(tmp_path / "src"), must_exist=True, root=str(tmp_path))
            is True
        )

    def test_root_itself_is_valid(self, tmp_path: Path):
        assert validate_path(str(tmp_path), must_exist=True, root=str(tmp_path)) is True

    def test_relative_path_resolves_against_root(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        assert validate_path("src", must_exist=True, root=str(tmp_path)) is True

    def test_traversal_escape_is_refused(self, tmp_path: Path):
        root = tmp_path / "root"
        root.mkdir()
        (tmp_path / "outside").mkdir()
        assert validate_path("../outside", root=str(root)) is False

    def test_absolute_escape_is_refused(self, tmp_path: Path):
        root = tmp_path / "root"
        root.mkdir()
        assert validate_path("/etc", root=str(root)) is False

    def test_symlink_escape_is_refused(self, tmp_path: Path):
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        link = root / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):  # pragma: no cover
            pytest.skip("symlinks not supported on this platform")
        assert validate_path(str(link), must_exist=True, root=str(root)) is False

    def test_sibling_prefix_is_refused(self, tmp_path: Path):
        """`/tmp/root-other` must not count as being inside `/tmp/root`."""
        root = tmp_path / "root"
        root.mkdir()
        sibling = tmp_path / "root-other"
        sibling.mkdir()
        assert validate_path(str(sibling), root=str(root)) is False

    def test_missing_path_inside_root_is_refused_when_it_must_exist(
        self, tmp_path: Path
    ):
        assert (
            validate_path(
                str(tmp_path / "nope"), must_exist=True, root=str(tmp_path)
            )
            is False
        )

    def test_normalisation_does_not_smuggle_a_traversal_through(
        self, tmp_path: Path
    ):
        """`src/../src` is refused on its literal parts, not silently resolved."""
        (tmp_path / "src").mkdir()
        assert validate_path(str(tmp_path / "src" / ".." / "src"), root=str(tmp_path)) is False
