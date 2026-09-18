"""Keep readable custom policies aligned with configured gameplay decisions."""

import pytest

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.reporting.strategy_instructions import decision_instructions
from dominion.reporting.strategy_pages import (
    RenderedStrategy, missing_decision_descriptions, render_strategy_page,
)
from dominion.strategy.strategies.stables_ninja_museum import (
    StablesNinjaMuseum, create_ninja_watchtower_figurine_money,
)


def page_for(strategy):
    return render_strategy_page(RenderedStrategy(
        display_name="Ninja, Watchtower and Figurine", slug="example",
        strategy=strategy, source_path="example.py", factory_name="create_example",
        references={},
    ))


def test_selected_policy_has_readable_instructions_before_static_details():
    strategy = create_ninja_watchtower_figurine_money()
    page = page_for(strategy)
    gain = page.split('class="section section-gain"', 1)[1].split('</section>', 1)[0]
    # The published policy leaves ``watchtowers`` at 0, so the opening buy is
    # the only Watchtower and no replacement rule appears.
    assert "Your first Ninja." in gain
    assert "Figurine while you own fewer than 3 copies" in gain
    assert "Province when 4 or fewer Colonies remain, or from your turn 22" in gain
    assert "For Museum" in gain
    assert gain.index("Figurine while") < gain.index('class="technical-details"')
    assert "No list condition" not in gain.split('class="technical-details"', 1)[0]
    assert "See the source for details" not in page
    assert 'href="#instructions-gain"' in page
    assert 'id="instructions-gain"' in page
    assert "def choose_gain" in page
    assert "Trash a gained Curse, except keep your first Curse" in page
    assert missing_decision_descriptions(strategy) == []


@pytest.mark.parametrize("cap", [1, 3, 5])
def test_configured_figurine_limit_matches_real_purchase_decisions(cap):
    strategy = create_ninja_watchtower_figurine_money()
    strategy.params["figurines"] = cap
    instructions = decision_instructions(strategy, "choose_gain")
    assert any(f"Figurine while you own fewer than {cap} " in step for step in instructions.steps)
    player = PlayerState(ai=None, turns_taken=3)
    state = GameState(players=[player], supply={"Colony": 8, "Province": 8})
    # Silver, not Gold: the published policy sets ``money``, which puts Gold
    # above Figurine outright, so a Figurine/Gold pair cannot show the cap.
    choices = [get_card("Figurine"), get_card("Silver")]
    player.deck = [get_card("Figurine") for _ in range(cap - 1)]
    assert strategy.choose_gain(state, player, choices).name == "Figurine"
    player.deck.append(get_card("Figurine"))
    assert strategy.choose_gain(state, player, choices).name == "Silver"


def test_configured_scoring_thresholds_match_real_purchase_decisions():
    strategy = create_ninja_watchtower_figurine_money()
    strategy.params.update(province_at=3, green_turn=12)
    instructions = decision_instructions(strategy, "choose_gain")
    assert "Province when 3 or fewer Colonies remain, or from your turn 12." in instructions.steps
    player = PlayerState(ai=None, turns_taken=11)
    state = GameState(players=[player], supply={"Colony": 4, "Province": 8})
    choices = [get_card("Province"), get_card("Platinum")]
    assert strategy.choose_gain(state, player, choices).name == "Platinum"
    player.turns_taken = 12
    assert strategy.choose_gain(state, player, choices).name == "Province"
    player.turns_taken = 11
    state.supply["Colony"] = 3
    assert strategy.choose_gain(state, player, choices).name == "Province"


def test_alternate_configuration_changes_instructions_and_escapes_text():
    strategy = StablesNinjaMuseum(
        money=True, credit=True, museum=False, ninja_first=True,
        curse_silver=True, keep_copper=1, opening="<special & opening>",
    )
    gain = decision_instructions(strategy, "choose_gain")
    assert "try Stables if available" in gain.introduction
    assert "use Credit" in gain.introduction
    assert not any("For Museum" in step for step in gain.steps)
    assert gain.steps.index("Gold while you own fewer than 1 copy.") < gain.steps.index("Stables while you own fewer than 4 copies.")
    assert decision_instructions(strategy, "choose_action").steps[1] == "Ninja."
    trash = decision_instructions(strategy, "choose_trash")
    assert "Rocks, then Silver" in trash.steps[1]
    assert "Copper while you own more than 1 copy." in trash.steps
    page = page_for(strategy)
    assert "&lt;special &amp; opening&gt;" in page
    assert "<special & opening>" not in page


def test_inherited_hook_keeps_instructions_but_an_override_does_not():
    class Inherited(StablesNinjaMuseum):
        pass

    class Changed(Inherited):
        def choose_gain(self, state, player, choices):
            return None

    class Documented(Changed):
        def choose_gain(self, state, player, choices):
            """Always decline the offered gain."""
            return None

    assert decision_instructions(Inherited(), "choose_gain") is not None
    assert decision_instructions(Changed(), "choose_gain") is None
    assert missing_decision_descriptions(Changed()) == ["choose_gain"]
    assert "Readable instructions are missing" in page_for(Changed())
    assert missing_decision_descriptions(Documented()) == []
    assert "Always decline the offered gain." in page_for(Documented())
