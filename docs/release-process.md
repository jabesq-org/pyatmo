# Release process

Releases are cut from `development` into `master` by two GitHub Actions
workflows. Nothing is published by hand.

## Branch topology

    development ──┬─────────────────────────────┬──── (ongoing work)
                  │                             │
                  │ release/vX.Y.Z              │ mergeback/vX.Y.Z
                  ▼                             ▲
    master ───────┴── merge commit, tagged vX.Y.Z ──┘

- `development` is the integration branch. Feature PRs target it and are
  **squashed**.
- `master` only ever receives release merges. No hotfixes land on it directly.
- Every release ends with a mergeback PR that returns the release commit to
  `development`. That PR must be merged as a **merge commit** — never squashed,
  never rebased. See [The merge-method rule](#the-merge-method-rule).

## Cutting a release

1. Land everything you want in the release on `development`, each PR adding its
   entry under `## [unreleased]` in `CHANGELOG.md`.
2. Run the **Release · prepare** workflow from the Actions tab, choosing
   `patch`, `minor`, or `major`.

   It refuses to proceed unless `master` is an ancestor of `development` and the
   `Python package` workflow is green on the `development` head.

   It then rewrites `CHANGELOG.md` via `scripts/release.py --bump`: `[unreleased]`
   becomes `[X.Y.Z] - <date>`, a fresh empty `[unreleased]` goes on top, and a
   compare link is added. It pushes `release/vX.Y.Z` and opens a PR into `master`.
3. Review and merge the release PR. **Merge commit**, not squash.
4. **Release · publish** then runs automatically: it tags the merge commit
   `vX.Y.Z`, creates the GitHub Release from the changelog section, and opens the
   mergeback PR into `development`.

   The tag push triggers **Publish 📦 to PyPI** (`publish-to-pypi.yml`).
5. Approve the mergeback PR. With *Allow auto-merge* enabled it merges itself as a
   merge commit. If auto-merge is off, the workflow logs a warning and you must
   merge it manually — **as a merge commit**.

## The merge-method rule

Feature PRs are squashed. **Mergeback PRs must not be** — and must not be
rebase-merged either.

Both a squash and a rebase produce commits with a single parent, so the release
commits on `master` never become reachable from `development`. Two things then
break:

1. `merge-base(development, master)` stays pinned *before* the last release. The
   next release PR therefore diffs across all accumulated release history, and
   both sides insert a new section at the same `## [unreleased]` anchor — so
   `CHANGELOG.md` conflicts, and the conflicted region grows every release.
2. Release tags live only on `master`. `setuptools_scm` derives the version from
   the nearest *reachable* tag, so builds off `development` get versioned from a
   stale tag (at one point `v9.2.3-97-g…` while the real version was 9.8.0).

`release-prepare.yml` gates on this, so drift blocks the *next* release rather
than silently corrupting it.

## Recovering from drift

If **Release · prepare** fails with:

```
::error::origin/master is not an ancestor of HEAD. The last mergeback was squashed or rebased, ...
```

then a mergeback did not produce a merge commit. Check it:

```bash
git fetch origin
python3 scripts/release.py --check-ancestry origin/master origin/development
git describe --tags origin/development   # should report the latest release
```

Fix it by merging `master` into `development` with a real merge commit — via a PR,
since `development` is protected. No history rewriting and no force pushes are
needed. If a mergeback PR is still open, merging it with *Create a merge commit*
is enough on its own.

If `development` picked up new `## [unreleased]` entries after the squashed
mergeback, this merge will conflict in `CHANGELOG.md` at the `## [unreleased]`
anchor. Resolve it by keeping both sides: the released version section coming
in from `master`, and the entries already on `development` staying under
`## [unreleased]`.

To confirm a mergeback really produced a merge commit, count its parents:

```bash
git rev-list --parents -n1 <mergeback-merge-sha> | wc -w
```

Three means a merge commit (the commit plus two parents). Two means it was
squashed or rebased.

## Local dry run

`scripts/release.py` never tags or pushes. To preview what a release would do to
the changelog:

```bash
uv run python scripts/release.py --bump minor --dry-run
```

Right after a release the `[unreleased]` section is an empty scaffold, so this
reports `error: the [unreleased] section has no entries; nothing to release` and
exits 1. That is the guard doing its job, not a broken script — the same guard
stops **Release · prepare** from cutting an empty release.

To print the notes for an already-released version:

```bash
uv run python scripts/release.py --notes 9.8.0
```
