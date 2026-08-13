"""Tests for the release helper script (scripts/release.py)."""

import importlib.util
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

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


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """Build a throwaway git repo with one commit and chdir into it.

    Ancestry is a property of real git history, so these tests build history
    rather than mocking subprocess.
    """

    def run(*args):
        subprocess.run(  # noqa: S603 - trusted, hardcoded "git" for a test fixture
            ["git", *args],  # noqa: S607 - git resolved via PATH is fine here
            cwd=tmp_path,
            check=True,
            stdout=subprocess.DEVNULL,
        )

    def commit(name, text):
        (tmp_path / name).write_text(text)
        run("add", name)
        run("commit", "-m", f"add {name}")

    # Isolate from the developer's global/system git config (core.hooksPath,
    # commit.gpgsign, merge.ff, core.excludesFile, includeIf, ...). Per-repo
    # `git config` overrides can't cover all of these; only excluding the
    # config files entirely is categorically hermetic.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    run("init", "-b", "main")
    run("config", "user.email", "test@example.com")
    run("config", "user.name", "Test")
    commit("one.txt", "one\n")
    monkeypatch.chdir(tmp_path)
    return SimpleNamespace(run=run, commit=commit)


class TestIsAncestor:
    def test_parent_is_ancestor_of_child(self, git_repo):
        git_repo.commit("two.txt", "two\n")
        assert release.is_ancestor("HEAD~1", "HEAD") is True

    def test_child_is_not_ancestor_of_parent(self, git_repo):
        git_repo.commit("two.txt", "two\n")
        assert release.is_ancestor("HEAD", "HEAD~1") is False

    def test_diverged_branch_is_not_ancestor(self, git_repo):
        git_repo.run("switch", "-c", "side")
        git_repo.commit("side.txt", "side\n")
        git_repo.run("switch", "main")
        git_repo.commit("main.txt", "main\n")
        assert release.is_ancestor("side", "main") is False

    def test_true_merge_makes_branch_an_ancestor(self, git_repo):
        git_repo.run("switch", "-c", "side")
        git_repo.commit("side.txt", "side\n")
        git_repo.run("switch", "main")
        git_repo.commit("main.txt", "main\n")
        git_repo.run("merge", "--no-ff", "-m", "merge side", "side")
        assert release.is_ancestor("side", "main") is True

    def test_squashed_merge_does_not_make_branch_an_ancestor(self, git_repo):
        """The actual bug: a squashed mergeback strands the merged branch."""
        git_repo.run("switch", "-c", "side")
        git_repo.commit("side.txt", "side\n")
        git_repo.run("switch", "main")
        git_repo.commit("main.txt", "main\n")
        git_repo.run("merge", "--squash", "side")
        git_repo.run("commit", "-m", "squashed side")
        assert release.is_ancestor("side", "main") is False

    @pytest.mark.usefixtures("git_repo")
    def test_unknown_ref_raises(self):
        with pytest.raises(release.ReleaseError, match="git merge-base failed"):
            release.is_ancestor("no-such-ref", "HEAD")

    def test_shallow_clone_raises(self, git_repo, tmp_path_factory, monkeypatch):
        """A depth-1 clone severs the merge commit's parents.

        ``side`` really is an ancestor of ``main`` (a true merge, as in the test
        above), but in a shallow clone git can no longer see far enough back to
        tell, and answers "not reachable" instead of raising. A silent false
        negative here would let the release gate wave through exactly the drift
        it exists to catch, so this must raise rather than return ``False``.
        """
        git_repo.run("switch", "-c", "side")
        git_repo.commit("side.txt", "side\n")
        git_repo.run("switch", "main")
        git_repo.commit("main.txt", "main\n")
        git_repo.run("merge", "--no-ff", "-m", "merge side", "side")

        origin = Path.cwd()
        clone_dir = tmp_path_factory.mktemp("shallow-clone")
        subprocess.run(  # noqa: S603 - trusted, hardcoded "git" for a test fixture
            [  # noqa: S607 - git resolved via PATH is fine here
                "git",
                "clone",
                "--depth",
                "1",
                "--no-single-branch",
                f"file://{origin}",
                str(clone_dir),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        monkeypatch.chdir(clone_dir)

        with pytest.raises(release.ReleaseError, match="shallow"):
            release.is_ancestor("origin/side", "origin/main")


class TestCheckAncestryCommand:
    def test_exits_zero_when_reachable(self, git_repo, capsys, monkeypatch):
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        git_repo.commit("two.txt", "two\n")
        assert release.main(["--check-ancestry", "HEAD~1", "HEAD"]) == 0
        captured = capsys.readouterr()
        assert "HEAD~1 is an ancestor of HEAD" in captured.out
        assert captured.err == ""

    def test_exits_one_when_not_reachable(self, git_repo, capsys, monkeypatch):
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        git_repo.run("switch", "-c", "side")
        git_repo.commit("side.txt", "side\n")
        git_repo.run("switch", "main")
        git_repo.commit("main.txt", "main\n")
        assert release.main(["--check-ancestry", "side", "main"]) == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "::error::side is not an ancestor of main" in captured.err
        assert "Merge side into main" in captured.err
        assert "See docs/release-process.md for recovery steps." in captured.err

    @pytest.mark.usefixtures("git_repo")
    def test_reports_release_errors_as_annotations(self, capsys, monkeypatch):
        """A real bad ref must fail loudly, not crash with a traceback."""
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        assert release.main(["--check-ancestry", "no-such-ref", "HEAD"]) == 1
        captured = capsys.readouterr()
        assert "::error::git merge-base failed" in captured.err
        assert captured.out == ""

    @pytest.mark.usefixtures("git_repo")
    def test_requires_exactly_two_refs(self):
        with pytest.raises(SystemExit) as exc:
            release.main(["--check-ancestry", "HEAD"])
        assert exc.value.code == 2

    @pytest.mark.usefixtures("git_repo")
    def test_is_mutually_exclusive_with_bump(self):
        with pytest.raises(SystemExit) as exc:
            release.main(["--check-ancestry", "HEAD~1", "HEAD", "--bump", "patch"])
        assert exc.value.code == 2

    @pytest.mark.usefixtures("git_repo")
    def test_is_mutually_exclusive_with_notes(self):
        with pytest.raises(SystemExit) as exc:
            release.main(["--check-ancestry", "HEAD~1", "HEAD", "--notes", "1.2.3"])
        assert exc.value.code == 2

    @pytest.mark.usefixtures("git_repo")
    def test_dry_run_only_applies_to_bump(self):
        with pytest.raises(SystemExit) as exc:
            release.main(["--check-ancestry", "HEAD~1", "HEAD", "--dry-run"])
        assert exc.value.code == 2


class TestMainRequiresACommand:
    @pytest.mark.usefixtures("git_repo")
    def test_bare_invocation_exits_two(self):
        with pytest.raises(SystemExit) as exc:
            release.main([])
        assert exc.value.code == 2


class TestBumpCommandErrorPath:
    def test_empty_unreleased_reports_plain_error_via_main(
        self, tmp_path, monkeypatch, capsys
    ):
        """Assert ``main()`` catches the empty-``[unreleased]`` ``ReleaseError``.

        ``_cmd_bump`` has no local try/except; ``main()`` must catch the
        ``ReleaseError`` from ``finalize_changelog``'s empty-``[unreleased]``
        guard and report it via ``_fail``, exactly as documented in
        docs/release-process.md.
        """
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(EMPTY_UNRELEASED, encoding="utf-8")
        monkeypatch.setattr(release, "CHANGELOG", changelog)

        assert release.main(["--bump", "minor", "--dry-run"]) == 1
        captured = capsys.readouterr()
        assert (
            captured.err
            == "error: the [unreleased] section has no entries; nothing to release\n"
        )
        assert captured.out == ""


class TestFail:
    def test_plain_prefix_without_github_actions(self, capsys, monkeypatch):
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        assert release._fail("boom") == 1  # noqa: SLF001 - testing the private reporter
        captured = capsys.readouterr()
        assert captured.err == "error: boom\n"
        assert captured.out == ""

    def test_annotation_prefix_with_github_actions(self, capsys, monkeypatch):
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        assert release._fail("boom") == 1  # noqa: SLF001 - testing the private reporter
        captured = capsys.readouterr()
        assert captured.err == "::error::boom\n"

    def test_multiline_message_is_percent_encoded(self, capsys, monkeypatch):
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        release._fail("line one\nline two")  # noqa: SLF001 - testing the private reporter
        captured = capsys.readouterr()
        assert captured.err == "::error::line one%0Aline two\n"

    def test_percent_sign_does_not_corrupt_newline_encoding(self, capsys, monkeypatch):
        # "%" must be encoded first, or an already-produced "%0D" would be
        # re-escaped into "%250D". A message with both a literal "%" and a CR
        # pins the order: "%" becomes "%25" and "\r" becomes "%0D", and the two
        # do not interfere with each other.
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        release._fail("100% done\rretry")  # noqa: SLF001 - testing the private reporter
        captured = capsys.readouterr()
        assert captured.err == "::error::100%25 done%0Dretry\n"
