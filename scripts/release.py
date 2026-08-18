#!/usr/bin/env python3
"""Release helper for pyatmo.

Finalizes ``CHANGELOG.md`` for a release: renames the ``[unreleased]`` section to
the new version with a date, resets a fresh empty ``[unreleased]`` scaffold,
maintains the bottom compare links, and can extract release notes for a version.

Version numbers come from git tags (``setuptools_scm``); this script only decides
the next number from a ``--bump`` type and rewrites the changelog. It never tags
or pushes -- that is done by the CI workflow (or a maintainer for a local run).

Usage:
    release.py --bump {patch,minor,major} [--dry-run]
    release.py --notes X.Y.Z
    release.py --check-ancestry ANCESTOR DESCENDANT
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import os
from pathlib import Path
import re
import subprocess
import sys

REPO_DEFAULT = "jabesq-org/pyatmo"
CHANGELOG = Path(__file__).resolve().parents[1] / "CHANGELOG.md"

_BUMP_PARTS = ("patch", "minor", "major")
_SECTION_RE = re.compile(r"^## \[", re.MULTILINE)
_SUBSECTION_RE = re.compile(r"^### .+$", re.MULTILINE)
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _line_end(text: str, pos: int) -> int:
    """Return the offset of the newline at/after ``pos``, or end of text."""
    nl = text.find("\n", pos)
    return len(text) if nl == -1 else nl


class ReleaseError(Exception):
    """Raised when a release cannot proceed (e.g. empty changelog)."""


def bump_version(current: str, part: str) -> str:
    """Return the next version after bumping ``part`` of ``current``.

    ``current`` may carry a leading ``v``. ``part`` is patch/minor/major.
    """
    if part not in _BUMP_PARTS:
        msg = f"unknown bump part {part!r}; expected one of {_BUMP_PARTS}"
        raise ValueError(msg)

    stripped = current.removeprefix("v")
    if not _VERSION_RE.match(stripped):
        msg = f"expected an X.Y.Z version tag, got {current!r}"
        raise ReleaseError(msg)
    major, minor, patch = (int(x) for x in stripped.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _split_sections(text: str) -> list[tuple[str, int, int]]:
    """Return (header_line, start, end) for each ``## [...]`` section.

    ``start`` is the offset of the ``##`` header, ``end`` the offset of the next
    header (or the start of the link section / EOF).
    """
    matches = list(_SECTION_RE.finditer(text))
    sections: list[tuple[str, int, int]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        header = text[start : _line_end(text, start)]
        sections.append((header, start, end))
    return sections


def _section_body(text: str, label: str) -> str | None:
    """Return the raw body (text after the header line) of section ``label``."""
    for header, start, end in _split_sections(text):
        if header.strip() == f"## [{label}]" or header.strip().startswith(
            f"## [{label}] "
        ):
            line_end = _line_end(text, start)
            header_end = min(line_end + 1, len(text))
            return text[header_end:end]
    return None


def has_unreleased_entries(text: str) -> bool:
    """Return whether ``[unreleased]`` contains at least one real bullet."""
    body = _section_body(text, "unreleased")
    if body is None:
        return False
    return any(line.startswith("- ") and line[2:].strip() for line in body.splitlines())


def strip_empty_subsections(body: str) -> str:
    """Drop ``### `` subsections whose only bullet is a ``-`` placeholder/blank."""
    matches = list(_SUBSECTION_RE.finditer(body))
    if not matches:
        return body
    kept = [body[: matches[0].start()]]
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunk = body[start:end]
        content = chunk[chunk.index("\n") + 1 :] if "\n" in chunk else ""
        if any(
            line.startswith("- ") and line[2:].strip() for line in content.splitlines()
        ):
            kept.append(chunk)
    return "".join(kept)


def extract_notes(text: str, version: str) -> str:
    """Return the changelog body for ``version`` (without the header), trimmed."""
    body = _section_body(text, version)
    if body is None:
        msg = f"no changelog section found for version {version}"
        raise ReleaseError(msg)
    return body.strip()


def _latest_tag() -> str:
    """Return the latest ``v*`` git tag by version order."""
    out = subprocess.run(
        ["git", "tag", "--list", "v*", "--sort=-v:refname"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    tags = [line.strip() for line in out.splitlines() if line.strip()]
    if not tags:
        msg = "no v* git tags found"
        raise ReleaseError(msg)
    return tags[0]


def _is_shallow() -> bool:
    """Return whether the current repository is a shallow clone."""
    out = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return out == "true"


def is_ancestor(ancestor: str, descendant: str) -> bool:
    """Return whether ``ancestor`` is reachable from ``descendant``.

    Raises ``ReleaseError`` when git cannot answer -- a bad ref, or a shallow
    clone whose graft boundary hides the merge that would prove reachability.
    """
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        check=False,
        capture_output=True,
        text=True,
    )
    # 0 = reachable, 1 = not reachable; anything else is a git failure (bad ref,
    # not a repository) and must not be read as "not reachable".
    if result.returncode not in (0, 1):
        msg = f"git merge-base failed: {result.stderr.strip()}"
        raise ReleaseError(msg)
    if result.returncode == 1 and _is_shallow():
        msg = "cannot determine ancestry in a shallow clone; fetch full history"
        raise ReleaseError(msg)
    return result.returncode == 0


def finalize_changelog(
    text: str,
    version: str,
    date: str,
    prev: str,
    repo: str = REPO_DEFAULT,
) -> str:
    """Return ``text`` finalized for ``version``.

    Renames ``## [unreleased]`` to ``## [version] - date``, inserts a fresh empty
    ``## [unreleased]`` on top, and adds the ``vprev...vversion`` compare link.
    ``prev`` is the previous released version (the latest git tag), which is the
    authoritative compare base even if the changelog on this branch lags behind.
    """
    if not has_unreleased_entries(text):
        msg = "the [unreleased] section has no entries; nothing to release"
        raise ReleaseError(msg)

    # Locate the unreleased section and strip its empty subsections.
    start = end = header_end = None
    for header, sec_start, sec_end in _split_sections(text):
        if header.strip() == "## [unreleased]":
            start, end = sec_start, sec_end
            header_end = min(_line_end(text, sec_start) + 1, len(text))
            break
    if start is None:
        msg = "could not find the [unreleased] section"
        raise ReleaseError(msg)

    cleaned = strip_empty_subsections(text[header_end:end])

    # Rename the section to the new version and add a fresh empty unreleased.
    replacement = f"## [unreleased]\n\n## [{version}] - {date}\n{cleaned}"
    new_text = text[:start] + replacement + text[end:]

    # Drop any lingering ``[unreleased]`` reference link. It is intentionally not
    # maintained -- it was a perpetual merge-conflict source between development
    # and master. Removing it here keeps finalize idempotent on old changelogs.
    new_text = re.sub(r"(?m)^\[unreleased\]: .*\n?", "", new_text)

    # Insert the versioned compare link above the previous one.
    base = f"https://github.com/{repo}/compare"
    link = f"[{version}]: {base}/v{prev}...v{version}"
    new_text, count = re.subn(
        r"(?m)^(\[\d+\.\d+\.\d+\]: )",
        f"{link}\n\\1",
        new_text,
        count=1,
    )
    if count == 0:  # no existing version links; append at end
        new_text = f"{new_text.rstrip()}\n{link}\n"
    return new_text


def _emit_output(version: str, notes: str) -> None:
    """Write step outputs when running inside GitHub Actions."""
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if not gh_output:
        return
    with Path(gh_output).open("a", encoding="utf-8") as fh:
        fh.write(f"version={version}\n")
        delimiter = "NOTES_EOF"
        fh.write(f"notes<<{delimiter}\n{notes}\n{delimiter}\n")


def _fail(msg: str) -> int:
    """Report a fatal error on stderr and return the process exit code.

    Emits a GitHub Actions annotation under CI and a plain message otherwise. A
    workflow command must be one line, so newlines are percent-encoded -- git can
    produce multi-line stderr (e.g. the "dubious ownership" hint), and without
    this only its first line would reach the annotation.
    """
    if os.environ.get("GITHUB_ACTIONS"):
        encoded = msg.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::error::{encoded}", file=sys.stderr)
    else:
        print(f"error: {msg}", file=sys.stderr)
    return 1


def _cmd_bump(args: argparse.Namespace) -> int:
    text = CHANGELOG.read_text(encoding="utf-8")
    current = _latest_tag()
    prev = current.removeprefix("v")
    version = bump_version(current, args.bump)
    date = datetime.datetime.now(tz=datetime.UTC).strftime("%Y-%m-%d")

    new_text = finalize_changelog(text, version, date, prev)
    notes = extract_notes(new_text, version)

    if args.dry_run:
        print(f"Next version: {version} (from {current})")
        print("\n--- release notes ---")
        print(notes)
        print("\n--- changelog changes ---")
        _print_diff(text, new_text)
        return 0

    CHANGELOG.write_text(new_text, encoding="utf-8")
    _emit_output(version, notes)
    print(f"Finalized CHANGELOG.md for {version}")
    return 0


def _cmd_notes(args: argparse.Namespace) -> int:
    text = CHANGELOG.read_text(encoding="utf-8")
    print(extract_notes(text, args.notes))
    return 0


def _cmd_check_ancestry(args: argparse.Namespace) -> int:
    """Fail unless ANCESTOR is reachable from DESCENDANT.

    Guards a release against a squashed mergeback. A squash leaves ``master``
    unreachable from ``development``, which pins the release PR's merge base
    before the previous release: both sides then insert a section at the same
    ``[unreleased]`` anchor and ``CHANGELOG.md`` conflicts every time. It also
    strands the release tags, so setuptools_scm versions development builds from
    a stale tag.
    """
    ancestor, descendant = args.check_ancestry
    if is_ancestor(ancestor, descendant):
        print(f"{ancestor} is an ancestor of {descendant}")
        return 0
    return _fail(
        f"{ancestor} is not an ancestor of {descendant}. The last mergeback was "
        f"squashed or rebased, or {ancestor} has commits that never came back. Merge "
        f"{ancestor} into {descendant} with a real merge commit (not a squash or "
        f"rebase) before releasing. See docs/release-process.md for recovery steps."
    )


def _print_diff(before: str, after: str) -> None:
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile="CHANGELOG.md",
        tofile="CHANGELOG.md (new)",
    )
    sys.stdout.writelines(diff)


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the requested subcommand."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bump", choices=_BUMP_PARTS, help="version part to bump")
    group.add_argument("--notes", metavar="X.Y.Z", help="print notes for a version")
    group.add_argument(
        "--check-ancestry",
        nargs=2,
        metavar=("ANCESTOR", "DESCENDANT"),
        help="exit non-zero unless ANCESTOR is reachable from DESCENDANT",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="preview only; write nothing and touch no git state",
    )
    args = parser.parse_args(argv)

    if args.dry_run and not args.bump:
        parser.error("--dry-run only applies to --bump")

    try:
        if args.check_ancestry:
            return _cmd_check_ancestry(args)
        if args.notes:
            return _cmd_notes(args)
        if args.bump:
            return _cmd_bump(args)
    except ReleaseError as err:
        return _fail(str(err))
    # Unreachable while the argument group is required=True; parser.error() raises
    # SystemExit, and the return only satisfies the "all paths return" check.
    parser.error("no command given")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
