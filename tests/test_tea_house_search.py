"""Check that search diagnostics distinguish normal endings from turn caps."""

import pytest

from scripts import search_tea_house_kind_emperor as search


@pytest.mark.parametrize("turn_limit", [101, 160])
@pytest.mark.parametrize("normal_end", [False, True])
def test_search_reports_only_unnatural_turn_limit_endings_as_truncated(
    monkeypatch, turn_limit, normal_end
):
    class EndAtLimit(search.GameState):
        def play_turn(self):
            self.turn_number = turn_limit
            if normal_end:
                self.supply["Province"] = 0

    monkeypatch.setattr(search, "GameState", EndAtLimit)

    result = search.match((search.CHAMPION, search.CHAMPION, 2, 100))

    assert result["truncated"] == (0 if normal_end else 2)
