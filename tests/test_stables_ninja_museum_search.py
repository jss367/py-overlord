"""Selection stages must reconstruct the policy inputs used by the search."""
import json
from pathlib import Path

from scripts.search_stables_ninja_museum import (
    normalize, rank_policies, spec_key, validation_policies)

DATA = Path(__file__).resolve().parents[1] / "scripts/data"


def read(suffix):
    return json.loads((DATA / f"stables_ninja_museum_{suffix}.json").read_text())


def test_final_ranking_counts_both_seats_and_preserves_ties():
    results = [dict(a={"opening": "Ninja"}, b={"opening": "Conclave"}, rate=0.0),
               dict(a={"opening": "Ninja"}, b={"opening": "Watchtower"}, rate=0.0)]
    # Ranking returns policies with the class defaults filled in, so compare on
    # the field under test.
    assert [spec["opening"] for spec in rank_policies(results, both_sides=True)] == [
        "Conclave", "Watchtower", "Ninja"]


def test_ranking_merges_specs_that_only_differ_by_a_spelled_out_default():
    """Otherwise one policy enters a round robin twice and meets itself."""
    explicit = {"opening": "Ninja", "ninjas": 1}
    implicit = {"opening": "Ninja"}
    assert spec_key(explicit) == spec_key(implicit)
    results = [dict(a=explicit, b={"opening": "Conclave"}, rate=1.0),
               dict(a=implicit, b={"opening": "Conclave"}, rate=1.0)]
    ranked = rank_policies(results, both_sides=True)
    assert len(ranked) == 2
    assert normalize(explicit) in ranked


def test_recorded_policy_selection_is_reproducible_from_results():
    finalists = rank_policies(read("final")["results"], both_sides=True)
    refined = rank_policies(read("refine")["results"])
    assert finalists == read("final_ranked")
    assert refined == read("refine_ranked")
    assert validation_policies(refined, finalists) == read("validation_policies")
