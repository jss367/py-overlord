# Synchronous merge policy

Default-branch lookup must succeed and produce a valid nonempty branch before
checkout selects the gate that executes with a write token. A Codex-authored
structured `codex-review-state:v1` summary must name the full current head SHA,
complete without findings, and have a strictly newer Codex thumbs-up reaction.
Human comments/reactions cannot substitute for Codex review. This deliberately
narrows the previous py-overlord approval policy; it does not add trusted actors.

The PR must be open, ready, mergeable, target the default branch, lack
`no-automerge`, and have no open child PRs targeting its source branch in this
repository. Standing change requests and unresolved human review threads (even
outdated ones) block. Only threads containing verified Codex comments exclusively
are governed by Codex's structured findings state. All inline comments/replies are
REST-paginated independently of the thread query; human replies remove that
exemption even when Codex authored the thread root.
A base retarget invalidates prior approval.

Every nonempty top-level comment, inline comment/reply or review body from a GitHub-authenticated
`OWNER` or `COLLABORATOR` human must strictly predate Codex's approval reaction.
Comment creation/edit times and review submission/edit times count; REST reviews
are joined to GraphQL `updatedAt` by `fullDatabaseId` to detect edited review
bodies. Full decimal IDs are normalized without floating-point conversion so
REST integers and GraphQL BigInt strings match beyond the 32-bit range; invalid,
missing, duplicate or unmatched IDs fail closed.
Missing or ambiguous timestamps fail closed, and a same-second tie blocks.
This intentionally treats even positive feedback and automation notices posted
through a human account as requiring a fresh clean review/approval. There are no
text-marker exemptions. GitHub `Bot` identities and other author associations do
not set this cutoff; standing change requests and unresolved threads still block
independently. A new reaction alone cannot replace the exact-head clean summary.

`required-ci.json` lists actual workflow filenames and mandatory job names.
The latest PR run must test the exact head and current base revision, match the
PR, source repository/branch and target name, and complete successfully. Every
mandatory job's latest execution must pass; absent, pending, skipped, cancelled,
failed and newer unsuccessful reruns block. No protection-setting lookup is used.

Some fork Actions responses omit `pull_requests` or its tested-base SHA. Those
runs are unsupported for automatic merging: source branch, head SHA, title and
success alone do not establish the PR/base revision actually tested. The gate
continues to reject them; there is no empty-association fallback. Fork runs with
an explicit matching PR and tested-base association can pass the same gates.
The maintainer must handle unsupported cases manually after checking evidence.

Every authoritative evidence request is repeated and compared before a final
PR/child recheck and REST squash merge with an atomic SHA precondition. GitHub
cannot atomically condition a merge on labels, base, reviews or child PRs, so a
small race for those mutable states remains. API errors fail closed. Legacy
native auto-merge requests are disabled before evaluation, including on drafts
and opted-out PRs; this workflow never arms a deferred merge request.

Any merge-write exception, malformed response or unconfirmed result fails the
entire job and stops processing subsequent PRs. The write is not retried and the
failure is not logged as an ordinary gate rejection: GitHub may have merged
before the client lost the response. Operator recovery must check the PR's
actual merge state/commit, dispatch the configured test-only workflows if it
merged, and only then decide whether to rerun the gate. Ordinary pre-write gate
rejections remain nonfatal and cannot issue a merge write.

`GITHUB_TOKEN` merges do not start push workflows. After merging, the gate
explicitly dispatches only the test/lint workflows listed in `required-ci.json`
on the default branch. A dispatch failure fails the gate job and needs operator
attention; it cannot undo an already completed merge. No deployment or release
workflow is dispatched. Branches are retained to avoid destructive stack cleanup.

Regression tests feed synthetic paginated GitHub responses to the jq parsers and
Python orchestrator. Run `python -m pytest -q tests/test_auto_merge*.py` with jq and PyYAML
installed. Keep the CI run names synchronized with `ci_run.jq` and `gate.py`.
