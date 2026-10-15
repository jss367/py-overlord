"""Keep the separate type-rule compatibility panel reproducible and scoped."""

import hashlib
import json
from pathlib import Path


def test_compatibility_panel_preserves_matching_inputs_seeds_and_exercised_estates():
    before, after = [json.loads(Path(f"scripts/data/capitalism-inheritance-compatibility-{side}.json").read_text())
                     for side in ("before", "after")]
    assert before["simulation_fingerprint"] != after["simulation_fingerprint"]
    assert before["runner_hashes"] == after["runner_hashes"]
    assert before["python_hash_seed"] == after["python_hash_seed"] == "0"
    for path, expected in after["runner_hashes"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
    for result in (before, after):
        records = [r for row in result["comparisons"] for r in row["records"]]
        assert result["total_games"] == len(records) == 720
        assert len(result["comparisons"]) == 36
        for row in result["comparisons"]:
            assert len(row["records"]) == 20
            assert all({r["seat"] for r in row["records"] if r["seed"] == seed} == {0, 1}
                       for seed in {r["seed"] for r in row["records"]})
            if "Inheritance" in row["modifier"]:
                assert sum(r["decisions"].get("choose_action: Estate", 0) for r in row["records"]) > 0
        assert all(isinstance(r["truncated"], bool) for r in records)
    for old, new in zip(before["comparisons"], after["comparisons"]):
        assert (old["subject"], old["modifier"], old["opponent"]) == (new["subject"], new["modifier"], new["opponent"])
        assert [(r["seed"], r["seat"]) for r in old["records"]] == [(r["seed"], r["seat"]) for r in new["records"]]


def test_current_rules_guide_is_registered_and_published():
    name = "capitalism-and-inheritance-rules-and-policy-compatibility.html"
    assert (Path("dominion/reporting/curated_strategy_guides") / name).read_bytes() == (Path("reports/strategies") / name).read_bytes()
    assert name in Path("reports/strategies/index.html").read_text()
