"""Synchronous merge gate. Only default-branch code runs with the write token."""

import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlencode

GATE = Path(__file__).resolve().parent
BOT = "chatgpt-codex-connector[bot]"
THREAD_QUERY = """query($owner:String!,$name:String!,$number:Int!,$endCursor:String){
 repository(owner:$owner,name:$name){pullRequest(number:$number){
 reviewThreads(first:100,after:$endCursor){pageInfo{hasNextPage endCursor}
 nodes{isResolved isOutdated path line comments(first:1){nodes{author{login}}}}}}}}"""


def api(path, *, method="GET", fields=None, pages=False):
    cmd = ["gh", "api", path, "--method", method]
    if pages:
        cmd += ["--paginate", "--slurp"]
    for key, value in (fields or {}).items():
        cmd += ["-F" if isinstance(value, int) else "-f", f"{key}={value}"]
    return json.loads(subprocess.check_output(cmd, text=True))


def verdict(program, data, **args):
    cmd = ["jq", "-r"]
    for key, value in args.items():
        cmd += ["--arg" if isinstance(value, str) else "--argjson",
                key, value if isinstance(value, str) else json.dumps(value)]
    cmd += ["-f", str(GATE / program)]
    return subprocess.check_output(cmd, input=json.dumps(data), text=True).strip()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def children(repo, pr):
    if pr["head"]["repo"]["full_name"] != repo:
        return []
    return api(f"repos/{repo}/pulls?" + urlencode({
        "state": "open", "base": pr["head"]["ref"], "per_page": 100}), pages=True)


def snapshot(repo, number, head, default, workflows):
    """Fetch all authoritative evidence; missing data/errors cannot authorize a merge."""
    root = f"repos/{repo}"
    pr = api(f"{root}/pulls/{number}")
    require(verdict("live.jq", pr, head=head, default=default) == "ok", "PR state blocks")
    require(pr.get("mergeable") is True, "mergeability unknown or conflicting")
    require(pr.get("auto_merge") is None, "native auto-merge still armed")
    child_pages = children(repo, pr)
    require(not any(child_pages), "open child PRs target this branch")
    reactions = api(f"{root}/issues/{number}/reactions?per_page=100", pages=True)
    thumbs = max((r["created_at"] for page in reactions for r in page
                  if r["content"] == "+1" and r["user"]["login"] == BOT), default="")
    require(bool(thumbs), "no Codex approval reaction")
    timeline = api(f"{root}/issues/{number}/timeline?per_page=100", pages=True)
    retargeted = max((e["created_at"] for page in timeline for e in page
                      if e.get("event") == "base_ref_changed"), default="")
    require(thumbs > retargeted, "approval predates base change")
    reviews = api(f"{root}/pulls/{number}/reviews?per_page=100", pages=True)
    require(all(thumbs > r["submitted_at"] for page in reviews for r in page
                if r["user"]["login"] == BOT), "approval predates Codex findings")
    require(verdict("reviews.jq", reviews) == "ok", "standing change request")
    comments = api(f"{root}/issues/{number}/comments?per_page=100", pages=True)
    require(verdict("codex_state.jq", comments, bot=BOT, head=head, thumbs=thumbs) == "ok",
            "no clean exact-head structured Codex review")
    threads = api("graphql", method="POST", fields={"owner": repo.split("/")[0],
                  "name": repo.split("/")[1], "number": number, "query": THREAD_QUERY}, pages=True)
    require(verdict("threads.jq", threads, author="chatgpt-codex-connector") == "ok",
            "unresolved review threads")
    evidence = []
    for workflow, required_jobs in workflows.items():
        runs = api(f"{root}/actions/workflows/{workflow}/runs?" + urlencode({
            "event": "pull_request", "head_sha": head, "per_page": 100}), pages=True)
        run = json.loads(verdict("ci_run.jq", runs, head=head,
                    source_repo=pr["head"]["repo"]["full_name"], source_branch=pr["head"]["ref"],
                    retargeted=retargeted, number=number,
                    target_title=f"Tests for pull request #{number} against {default}"))
        require(run is not None and run["status"] == "completed" and run["conclusion"] == "success",
                f"{workflow}: latest exact-head CI missing or not successful")
        require(any(p.get("number") == number and p.get("base", {}).get("sha") == pr["base"]["sha"]
                    for p in run["pull_requests"]), "CI tested another base revision")
        jobs = api(f"{root}/actions/runs/{run['id']}/jobs?filter=all&per_page=100", pages=True)
        require(verdict("ci_jobs.jq", jobs, required=required_jobs) == "true",
                f"{workflow}: required jobs missing or not successful")
        evidence.append((runs, jobs))
    # Comparing complete fetched evidence also detects reruns, edited summaries,
    # newly added objections, retargeting and children during the first pass.
    return pr, child_pages, reactions, timeline, reviews, comments, threads, evidence


def dispatch(repo, workflow, default):
    done = subprocess.run(["gh", "workflow", "run", workflow, "--repo", repo, "--ref", default], check=False)
    if done.returncode:
        raise RuntimeError(f"Merged, but postmerge tests failed to dispatch: {workflow}")


def merge_candidate(repo, number, head, default, workflows):
    before = snapshot(repo, number, head, default, workflows)
    after = snapshot(repo, number, head, default, workflows)
    require(before == after, "merge evidence changed during evaluation")
    require(api(f"repos/{repo}")["default_branch"] == default, "default branch changed")
    live = api(f"repos/{repo}/pulls/{number}")
    require(live == after[0] and not any(children(repo, live)), "final PR or child state changed")
    # REST's sha precondition is atomic. Unlike gh pr merge, this cannot
    # silently queue/arm an auto-merge request when checks are pending.
    result = api(f"repos/{repo}/pulls/{number}/merge", method="PUT",
                 fields={"sha": head, "merge_method": "squash"})
    require(result.get("merged") is True, "GitHub did not merge")
    # GITHUB_TOKEN push events do not start workflows. Explicit dispatch starts
    # only these test/lint workflows; there is no deploy/release dispatch here.
    for workflow in workflows:
        dispatch(repo, workflow, default)


def main():
    repo = os.environ["REPO"]
    workflows = json.loads((GATE / "required-ci.json").read_text())
    default = api(f"repos/{repo}")["default_branch"]
    pulls = api(f"repos/{repo}/pulls?state=open&per_page=100", pages=True)
    for page in pulls:
        for pr in page:
            number = pr["number"]
            # Remove legacy deferred requests even for PRs that now fail gates.
            # No repository/branch protection settings are read or changed.
            if pr.get("auto_merge") is not None:
                subprocess.run(["gh", "pr", "merge", str(number), "--repo", repo, "--disable-auto"], check=True)
            try:
                merge_candidate(repo, number, pr["head"]["sha"], default, workflows)
            except (ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
                print(f"PR #{number}: stopped: {error}", flush=True)


if __name__ == "__main__":
    main()
