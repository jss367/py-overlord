"""Exercise the complete decision with synthetic GitHub responses, without a token."""

import copy
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURE_SPEC = importlib.util.spec_from_file_location("merge_fixtures", Path(__file__).with_name("test_auto_merge.py"))
fixtures = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(fixtures)
BOT, HEAD, OLD = fixtures.BOT, fixtures.HEAD, fixtures.OLD
job, review, summary, thread, thread_page = fixtures.job, fixtures.review, fixtures.summary, fixtures.thread, fixtures.thread_page

PATH = Path(__file__).resolve().parents[1] / ".github/auto-merge/gate.py"
SPEC = importlib.util.spec_from_file_location("merge_gate", PATH)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)
REPO = "jss367/example"
WORKFLOWS = {"tests.yml": ["test"]}


def fixture():
    pr = {"number": 7, "state": "open", "draft": False, "labels": [],
          "mergeable": True, "auto_merge": None,
          "head": {"sha": HEAD, "ref": "feature", "repo": {"full_name": REPO}},
          "base": {"ref": "main", "sha": OLD}}
    run = {"id": 12, "run_number": 12, "event": "pull_request", "head_sha": HEAD,
           "head_branch": "feature", "head_repository": {"full_name": REPO},
           "pull_requests": [{"number": 7, "base": {"sha": OLD}}],
           "display_title": "Tests for pull request #7 against main",
           "created_at": "2026-10-26T16:20:00Z", "status": "completed", "conclusion": "success"}
    return {"pr": pr, "children": [[]], "reactions": [[{
        "content": "+1", "user": {"login": BOT}, "created_at": "2026-10-26T16:15:50Z"}]],
        "timeline": [[]], "reviews": [[]], "comments": [[summary()]],
        "threads": [thread_page()], "runs": [{"workflow_runs": [run]}],
        "jobs": [{"jobs": [job(1, "success", 1, name="test")]}]}


def transport(data, calls):
    def fake(path, **kwargs):
        calls.append((path, kwargs))
        if path.endswith('/merge'):
            return {"merged": True}
        if path == f"repos/{REPO}":
            return {"default_branch": "main"}
        if path == "graphql":
            if "reviewThreads" in kwargs["fields"]["query"]:
                return data["threads"]
            nodes = [{"databaseId": r.get("legacy_id", r["id"]),
                      "fullDatabaseId": r.get("graphql_id", r["id"]),
                      "updatedAt": r.get("edited_at", r["submitted_at"])}
                     for page in data["reviews"] for r in page]
            return [{"data": {"repository": {"pullRequest": {"reviews": {"nodes": nodes}}}}}]
        for suffix, key in [("/pulls/7", "pr"), ("/reactions?", "reactions"),
                            ("/timeline?", "timeline"), ("/reviews?", "reviews"),
                            ("/comments?", "comments"), ("/runs?", "runs"),
                            ("/jobs?", "jobs"), ("/pulls?", "children")]:
            if (path.endswith(suffix) if key == "pr" else suffix in path):
                return copy.deepcopy(data[key])
        raise AssertionError(path)
    return fake


def merge(data):
    calls = []
    with patch.object(gate, "api", transport(data, calls)), patch.object(gate, "dispatch") as run:
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)
        run.assert_called_once_with(REPO, "tests.yml", "main")
    return calls


def test_complete_clean_snapshot_merges_synchronously_at_exact_head():
    calls = merge(fixture())
    merges = [kwargs for path, kwargs in calls if path.endswith("/merge")]
    assert merges == [{"method": "PUT", "fields": {"sha": HEAD, "merge_method": "squash"}}]
    assert sum(path.endswith("/pulls/7") for path, _ in calls) == 3


@pytest.mark.parametrize("change", [
    "draft", "optout", "new_head", "findings", "stale_review", "human_reaction",
    "missing_ci", "pending_ci", "failed_ci", "skipped_job", "missing_job", "old_base",
    "human_changes", "human_thread", "child", "native_auto", "retargeted",
])
def test_full_gate_blocks_unsafe_evidence(change):
    data = fixture()
    if change == "draft": data["pr"]["draft"] = True
    if change == "optout": data["pr"]["labels"] = [{"name": "no-automerge"}]
    if change == "new_head": data["pr"]["head"]["sha"] = OLD
    if change == "findings": data["comments"] = [[summary(review(any_findings=True))]]
    if change == "stale_review": data["comments"] = [[summary(review(commit=OLD))]]
    if change == "human_reaction": data["reactions"][0][0]["user"]["login"] = "jss367"
    if change == "missing_ci": data["runs"] = [{"workflow_runs": []}]
    if change == "pending_ci": data["runs"][0]["workflow_runs"][0]["status"] = "in_progress"
    if change == "failed_ci": data["runs"][0]["workflow_runs"][0]["conclusion"] = "failure"
    if change == "skipped_job": data["jobs"][0]["jobs"][0]["conclusion"] = "skipped"
    if change == "missing_job": data["jobs"] = [{"jobs": []}]
    if change == "old_base": data["pr"]["base"]["sha"] = "d" * 40
    if change == "human_changes": data["reviews"] = [[{
        "user": {"login": "alice"}, "state": "CHANGES_REQUESTED", "id": 1, "submitted_at": "2026-10-26T16:00:00Z"}]]
    if change == "human_thread": data["threads"] = [thread_page(thread("alice"))]
    if change == "child": data["children"] = [[{"number": 8}]]
    if change == "native_auto": data["pr"]["auto_merge"] = {"enabled_by": {"login": "alice"}}
    if change == "retargeted": data["timeline"] = [[{
        "event": "base_ref_changed", "created_at": "2026-10-26T16:30:00Z"}]]
    calls = []
    with patch.object(gate, "api", transport(data, calls)), patch.object(gate, "dispatch"), pytest.raises(ValueError):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)
    assert not any(path.endswith("/merge") for path, _ in calls)


def test_new_objection_during_second_snapshot_prevents_merge():
    data = fixture()
    calls = []
    fake = transport(data, calls)
    count = 0

    def mutate(path, **kwargs):
        nonlocal count
        if path.endswith("/pulls/7"):
            count += 1
            if count == 2:
                data["threads"] = [thread_page(thread("alice"))]
        return fake(path, **kwargs)

    with patch.object(gate, "api", mutate), patch.object(gate, "dispatch"), pytest.raises(ValueError):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)
    assert not any(path.endswith("/merge") for path, _ in calls)


def test_head_moving_at_final_recheck_never_calls_merge():
    data = fixture()
    calls = []
    fake = transport(data, calls)
    count = 0

    def mutate(path, **kwargs):
        nonlocal count
        if path.endswith("/pulls/7"):
            count += 1
            if count == 3:
                data["pr"]["head"]["sha"] = OLD
        return fake(path, **kwargs)

    with patch.object(gate, "api", mutate), patch.object(gate, "dispatch"), pytest.raises(ValueError):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)
    assert not any(path.endswith("/merge") for path, _ in calls)


def test_legacy_auto_request_is_disabled_even_when_new_gate_blocks(monkeypatch):
    data = fixture()
    data["pr"]["auto_merge"] = {"enabled_by": {"login": "jss367"}}
    data["pr"]["draft"] = True
    monkeypatch.setenv("REPO", REPO)
    with patch.object(gate, "api", side_effect=[{"default_branch": "main"}, [[data["pr"]]]]), \
            patch.object(gate, "merge_candidate", side_effect=ValueError("draft")), \
            patch.object(gate.subprocess, "run") as run:
        gate.main()
    run.assert_called_once_with(["gh", "pr", "merge", "7", "--repo", REPO, "--disable-auto"], check=True)


def feedback(channel, *, association="OWNER", at="2026-10-26T16:16:00Z", body="Hold this merge: the safety check is missing.", kind="User"):
    entry = {"user": {"login": "alice", "type": kind},
             "author_association": association, "body": body}
    if channel == "comments":
        entry.update(created_at=at, updated_at=at)
    else:
        entry.update(id=42, state="COMMENTED", submitted_at=at)
    return entry


@pytest.mark.parametrize("channel", ["comments", "reviews"])
@pytest.mark.parametrize("association", ["OWNER", "COLLABORATOR"])
def test_trusted_top_level_feedback_in_both_snapshots_blocks(channel, association):
    data = fixture()
    data[channel][0].append(feedback(channel, association=association))
    calls = []
    with patch.object(gate, "api", transport(data, calls)), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="trusted feedback"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)
    assert not any(path.endswith("/merge") for path, _ in calls)


@pytest.mark.parametrize("channel", ["comments", "reviews"])
@pytest.mark.parametrize("at", ["2026-10-26T16:15:50Z", "2026-10-26T16:16:00Z"])
def test_trusted_feedback_at_or_after_approval_blocks(channel, at):
    data = fixture()
    data[channel][0].append(feedback(channel, at=at))
    with patch.object(gate, "api", transport(data, [])), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="trusted feedback"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)


@pytest.mark.parametrize("channel", ["comments", "reviews"])
def test_approval_strictly_newer_than_trusted_feedback_allows_merge(channel):
    data = fixture()
    data[channel][0].append(feedback(channel, at="2026-10-26T16:15:49Z"))
    assert any(path.endswith("/merge") for path, _ in merge(data))


@pytest.mark.parametrize("channel, field", [("comments", "updated_at"), ("reviews", "edited_at")])
def test_old_feedback_edited_after_approval_blocks(channel, field):
    data = fixture()
    entry = feedback(channel, at="2026-10-26T16:00:00Z")
    entry[field] = "2026-10-26T16:16:00Z"
    data[channel][0].append(entry)
    calls = []
    with patch.object(gate, "api", transport(data, calls)), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="trusted feedback"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)
    assert not any(path.endswith("/merge") for path, _ in calls)


@pytest.mark.parametrize("channel", ["comments", "reviews"])
@pytest.mark.parametrize("association, kind", [("NONE", "User"), ("CONTRIBUTOR", "User"),
                                               ("MEMBER", "User"), ("OWNER", "Bot")])
def test_only_authenticated_owner_or_collaborator_human_feedback_sets_cutoff(channel, association, kind):
    data = fixture()
    data[channel][0].append(feedback(channel, association=association, kind=kind))
    assert any(path.endswith("/merge") for path, _ in merge(data))


@pytest.mark.parametrize("body", ["LGTM", "<!-- automated-notice -->\nHold the merge", "@codex review"])
def test_human_text_cannot_exempt_feedback_as_benign_automation(body):
    data = fixture()
    data["comments"][0].append(feedback("comments", body=body))
    with patch.object(gate, "api", transport(data, [])), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="trusted feedback"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)


@pytest.mark.parametrize("channel", ["comments", "reviews"])
def test_empty_approval_or_comment_body_adds_no_feedback_cutoff(channel):
    data = fixture()
    data[channel][0].append(feedback(channel, body="  \n"))
    assert any(path.endswith("/merge") for path, _ in merge(data))


def test_unknown_trusted_author_type_fails_closed():
    data = fixture()
    data["comments"][0].append(feedback("comments", kind="Unknown"))
    with patch.object(gate, "api", transport(data, [])), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="trusted feedback author"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)


@pytest.mark.parametrize("timestamp", [None, "2026-10-26T16:00:00"])
def test_missing_or_ambiguous_issue_edit_time_fails_closed(timestamp):
    data = fixture()
    entry = feedback("comments", at="2026-10-26T16:00:00Z")
    entry["updated_at"] = timestamp
    data["comments"][0].append(entry)
    with patch.object(gate, "api", transport(data, [])), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="trusted feedback timestamp"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)


def test_missing_graphql_review_edit_time_fails_closed():
    data = fixture()
    data["reviews"][0].append(feedback("reviews", at="2026-10-26T16:00:00Z"))
    data["reviews"][0][-1]["edited_at"] = None
    with patch.object(gate, "api", transport(data, [])), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="trusted feedback timestamp"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)


def test_trusted_comment_on_second_page_blocks():
    data = fixture()
    data["comments"].append([feedback("comments")])
    with patch.object(gate, "api", transport(data, [])), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="trusted feedback"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)


@pytest.mark.parametrize("channel", ["comments", "reviews"])
def test_new_trusted_feedback_during_second_snapshot_blocks(channel):
    data = fixture()
    calls = []
    fake = transport(data, calls)
    count = 0

    def mutate(path, **kwargs):
        nonlocal count
        if path.endswith("/pulls/7"):
            count += 1
            if count == 2:
                data[channel][0].append(feedback(channel))
        return fake(path, **kwargs)

    with patch.object(gate, "api", mutate), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="trusted feedback"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)
    assert not any(path.endswith("/merge") for path, _ in calls)


@pytest.mark.parametrize("rest_id, graphql_id", [
    (5949252876, "5949252876"),
    ("5949252876", 5949252876),
    (9007199254740993, "9007199254740993"),
    ("9223372036854775807", 9223372036854775807),
])
def test_full_database_ids_join_across_json_types(rest_id, graphql_id):
    data = fixture()
    entry = feedback("reviews", at="2026-10-26T16:00:00Z")
    entry.update(id=rest_id, graphql_id=graphql_id, legacy_id=None)
    data["reviews"][0].append(entry)
    calls = merge(data)
    queries = [args["fields"]["query"] for path, args in calls if path == "graphql"]
    assert any("fullDatabaseId" in query for query in queries)
    assert all("nodes{databaseId" not in query for query in queries)
    assert any(path.endswith("/merge") for path, _ in calls)


@pytest.mark.parametrize("field", ["id", "graphql_id"])
@pytest.mark.parametrize("invalid", [None, True, False, 5949252876.0, 0, -1,
                                    "", " 42", "+42", "-42", "42.0", "4e2", "٤٢", {}, []])
def test_invalid_review_database_ids_fail_closed(field, invalid):
    data = fixture()
    entry = feedback("reviews", at="2026-10-26T16:00:00Z")
    entry.update(id=5949252876, graphql_id="5949252876", legacy_id=None)
    entry[field] = invalid
    data["reviews"][0].append(entry)
    calls = []
    with patch.object(gate, "api", transport(data, calls)), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="review database ID"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)
    assert not any(path.endswith("/merge") for path, _ in calls)


def test_large_review_id_still_blocks_newer_edit():
    data = fixture()
    entry = feedback("reviews", at="2026-10-26T16:00:00Z")
    entry.update(id=5949252876, graphql_id="5949252876", legacy_id=None,
                 edited_at="2026-10-26T16:16:00Z")
    data["reviews"][0].append(entry)
    with patch.object(gate, "api", transport(data, [])), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="trusted feedback review"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)


def test_unmatched_full_review_id_does_not_use_legacy_id():
    data = fixture()
    entry = feedback("reviews", at="2026-10-26T16:00:00Z")
    entry.update(id=5949252876, graphql_id="5949252877", legacy_id=5949252876)
    data["reviews"][0].append(entry)
    with patch.object(gate, "api", transport(data, [])), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="missing trusted feedback timestamp"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)


def test_duplicate_normalized_ids_fail_closed():
    data = fixture()
    for key in [5949252876, "5949252876"]:
        entry = feedback("reviews", at="2026-10-26T16:00:00Z")
        entry.update(id=key, graphql_id=key)
        data["reviews"][0].append(entry)
    with patch.object(gate, "api", transport(data, [])), patch.object(gate, "dispatch"), \
            pytest.raises(ValueError, match="duplicate review database ID"):
        gate.merge_candidate(REPO, 7, HEAD, "main", WORKFLOWS)
