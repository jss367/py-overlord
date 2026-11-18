"""Check real YAML run names against the exact-head CI selector contract."""

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("workflow_fixtures", Path(__file__).with_name("test_auto_merge.py"))
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)
REQUIRED = json.loads((ROOT / ".github/auto-merge/required-ci.json").read_text())


@pytest.mark.parametrize("workflow", REQUIRED)
def test_required_workflow_yaml_title_is_accepted_by_ci_selector(workflow):
    document = yaml.safe_load((ROOT / ".github/workflows" / workflow).read_text())
    title = document["run-name"].replace("${{ github.event.pull_request.number }}", "7").replace(
        "${{ github.event.pull_request.base.ref }}", "main")
    run = fixtures.run(3)
    run["display_title"] = title
    # An unquoted # is a YAML comment: the actual API title is truncated, and
    # the exact-head gate must reject it even though the job itself passed.
    selected = fixtures.ci_run(run)
    assert selected is not None, f"{workflow}: parsed YAML run-name {title!r} cannot pass the merge gate"
    assert selected["id"] == run["id"]
