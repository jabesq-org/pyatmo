"""Tests for the release helper script (scripts/release.py)."""

import importlib.util
from pathlib import Path

import pytest

# Load scripts/release.py as a module (it lives outside the package).
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release.py"
_spec = importlib.util.spec_from_file_location("release", _SCRIPT)
release = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release)


REPO = "jabesq-org/pyatmo"

SAMPLE = """\
# Changelog

All notable changes to this project will be documented in this file.

## [unreleased]

### Added

- A shiny new feature (#123)

### Fixed

- A nasty bug (#124)

### Removed

-

## [9.4.0]

### Added

- Older thing

[9.4.0]: https://github.com/jabesq-org/pyatmo/compare/v9.3.0...v9.4.0
"""

EMPTY_UNRELEASED = """\
# Changelog

## [unreleased]

## [9.4.0]

### Added

- Older thing

[9.4.0]: https://github.com/jabesq-org/pyatmo/compare/v9.3.0...v9.4.0
"""


class TestBumpVersion:
    def test_patch(self):
        assert release.bump_version("9.4.0", "patch") == "9.4.1"

    def test_minor(self):
        assert release.bump_version("9.4.2", "minor") == "9.5.0"

    def test_major(self):
        assert release.bump_version("9.4.2", "major") == "10.0.0"

    def test_strips_leading_v(self):
        assert release.bump_version("v9.4.0", "minor") == "9.5.0"

    def test_rejects_unknown_part(self):
        with pytest.raises(ValueError, match="patch"):
            release.bump_version("9.4.0", "sideways")

    def test_rejects_two_component_tag(self):
        with pytest.raises(release.ReleaseError, match=r"9\.4"):
            release.bump_version("9.4", "patch")

    def test_rejects_non_numeric_tag(self):
        with pytest.raises(release.ReleaseError):
            release.bump_version("9.4.x", "patch")


class TestParsingRobustness:
    def test_header_as_last_line_without_newline(self):
        # A header with no trailing newline must not raise; body is empty.
        text = "# Changelog\n\n## [9.4.0]"
        assert release.extract_notes(text, "9.4.0") == ""

    def test_extract_notes_last_section_no_trailing_newline(self):
        text = "# C\n\n## [9.4.0]\n\n### Added\n\n- old"
        assert release.extract_notes(text, "9.4.0") == "### Added\n\n- old"


class TestUnreleasedGuard:
    def test_detects_entries(self):
        assert release.has_unreleased_entries(SAMPLE) is True

    def test_empty_section_has_no_entries(self):
        assert release.has_unreleased_entries(EMPTY_UNRELEASED) is False


class TestFinalizeChangelog:
    def test_renames_unreleased_with_date(self):
        out = release.finalize_changelog(
            SAMPLE, "9.5.0", "2026-07-20", "9.4.0", repo=REPO
        )
        assert "## [9.5.0] - 2026-07-20" in out

    def test_keeps_fresh_empty_unreleased_on_top(self):
        out = release.finalize_changelog(
            SAMPLE, "9.5.0", "2026-07-20", "9.4.0", repo=REPO
        )
        # unreleased header still present and appears before the new version
        assert out.index("## [unreleased]") < out.index("## [9.5.0]")
        # the released entries moved under the version, not under unreleased
        assert release.has_unreleased_entries(out) is False

    def test_moves_entries_under_new_version(self):
        out = release.finalize_changelog(
            SAMPLE, "9.5.0", "2026-07-20", "9.4.0", repo=REPO
        )
        notes = release.extract_notes(out, "9.5.0")
        assert "A shiny new feature (#123)" in notes
        assert "A nasty bug (#124)" in notes

    def test_adds_compare_link_for_new_version(self):
        out = release.finalize_changelog(
            SAMPLE, "9.5.0", "2026-07-20", "9.4.0", repo=REPO
        )
        assert (
            "[9.5.0]: https://github.com/jabesq-org/pyatmo/compare/v9.4.0...v9.5.0"
            in out
        )

    def test_new_link_inserted_above_previous(self):
        out = release.finalize_changelog(
            SAMPLE, "9.5.0", "2026-07-20", "9.4.0", repo=REPO
        )
        assert out.index("[9.5.0]:") < out.index("[9.4.0]:")

    def test_does_not_maintain_unreleased_link(self):
        out = release.finalize_changelog(
            SAMPLE, "9.5.0", "2026-07-20", "9.4.0", repo=REPO
        )
        assert "[unreleased]: " not in out
        assert "...HEAD" not in out

    def test_removes_lingering_unreleased_link(self):
        legacy = SAMPLE.replace(
            "[9.4.0]: https://github.com/jabesq-org/pyatmo/compare/v9.3.0...v9.4.0",
            "[unreleased]: https://github.com/jabesq-org/pyatmo/compare/v9.4.0...HEAD\n"
            "[9.4.0]: https://github.com/jabesq-org/pyatmo/compare/v9.3.0...v9.4.0",
        )
        out = release.finalize_changelog(
            legacy, "9.5.0", "2026-07-20", "9.4.0", repo=REPO
        )
        assert "[unreleased]: " not in out
        assert "[9.5.0]:" in out

    def test_guard_raises_on_empty_unreleased(self):
        with pytest.raises(release.ReleaseError):
            release.finalize_changelog(
                EMPTY_UNRELEASED, "9.5.0", "2026-07-20", "9.4.0", repo=REPO
            )

    def test_is_deterministic(self):
        a = release.finalize_changelog(
            SAMPLE, "9.5.0", "2026-07-20", "9.4.0", repo=REPO
        )
        b = release.finalize_changelog(
            SAMPLE, "9.5.0", "2026-07-20", "9.4.0", repo=REPO
        )
        assert a == b


class TestStripEmptySubsections:
    def test_drops_placeholder_only_subsection(self):
        body = "\n### Added\n\n- real (#1)\n\n### Removed\n\n-\n"
        out = release.strip_empty_subsections(body)
        assert "### Added" in out
        assert "### Removed" not in out
        assert "- real (#1)" in out

    def test_keeps_subsections_with_entries(self):
        body = "\n### Added\n\n- one\n\n### Fixed\n\n- two\n"
        out = release.strip_empty_subsections(body)
        assert "### Added" in out
        assert "### Fixed" in out

    def test_drops_blank_subsection(self):
        body = "\n### Changed\n\n\n"
        assert "### Changed" not in release.strip_empty_subsections(body)


class TestFinalizeStripsEmptySections:
    def test_empty_removed_not_in_notes(self):
        out = release.finalize_changelog(
            SAMPLE, "9.5.0", "2026-07-20", "9.4.0", repo=REPO
        )
        notes = release.extract_notes(out, "9.5.0")
        assert "### Removed" not in notes
        assert "### Added" in notes
        assert "A nasty bug (#124)" in notes


class TestExtractNotes:
    def test_extracts_requested_section_only(self):
        notes = release.extract_notes(SAMPLE, "9.4.0")
        assert "Older thing" in notes
        assert "A shiny new feature" not in notes

    def test_missing_version_raises(self):
        with pytest.raises(release.ReleaseError):
            release.extract_notes(SAMPLE, "1.2.3")
