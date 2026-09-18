"""Selection stages must reconstruct the policy inputs used by the search."""
import json
from pathlib import Path

from scripts.search_stables_ninja_museum import rank_policies, validation_policies

DATA = Path(__file__).resolve().parents[1] / "scripts/data"


def read(suffix):
    return json.loads((DATA / f"stables_ninja_museum_{suffix}.json").read_text())


def test_final_ranking_counts_both_seats_and_preserves_ties():
    results = [dict(a={"opening": "Ninja"}, b={"opening": "Conclave"}, rate=0.0),
               dict(a={"opening": "Ninja"}, b={"opening": "Watchtower"}, rate=0.0)]
    assert rank_policies(results, both_sides=True) == [
        {"opening": "Conclave"}, {"opening": "Watchtower"}, {"opening": "Ninja"}]


def test_recorded_policy_selection_is_reproducible_from_results():
    finalists = rank_policies(read("final")["results"], both_sides=True)
    refined = rank_policies(read("refine")["results"])
    assert finalists == read("final_ranked")
    assert refined == read("refine_ranked")
    assert validation_policies(refined, finalists) == read("validation_policies")
