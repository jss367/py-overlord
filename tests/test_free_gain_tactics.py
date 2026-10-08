"""Contextual free gains and joint decisions through the actual engine."""

import pytest

from dominion.ai.gain_context import FreeGainContext
from dominion.cards.gain_decisions import gain_menu
from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.phase_strategy import PhaseAwareStrategy, StrategyPhase
from tests.test_shared_card_tactics import make_state
from tests.utils import DummyAI


def test_workshop_purchase_and_free_gain_preferences_are_independent():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Village")]
    strategy.free_gain_priority = [PriorityRule("Smithy")]
    state, player = make_state(strategy)
    assert player.ai.choose_buy(state, [get_card("Village"), get_card("Smithy")]).name == "Village"
    get_card("Workshop").play_effect(state)
    assert player.discard[-1].name == "Smithy"


def test_context_reaches_strategy_and_includes_stored_ownership():
    class Strategy(EnhancedStrategy):
        def choose_free_gain(self, state, player, choices, context):
            assert context.source == "Workshop"
            assert context.destination == "discard"
            assert context.hand == tuple(player.hand)
            assert context.owned_counts["Smithy"] == 1
            assert context.endgame
            return next(c for c in choices if c.name == "Estate")

    state, player = make_state(Strategy(), ("Smithy", "Estate", "Province"))
    state.supply["Province"] = 1
    qm = get_card("Quartermaster")
    qm.set_aside = [get_card("Smithy")]
    player.duration = [qm]
    player.hand = [get_card("Copper")]
    get_card("Workshop").play_effect(state)
    assert player.discard[-1].name == "Estate"


def test_quartermaster_free_gain_context_has_storage_destination():
    class Strategy(EnhancedStrategy):
        def choose_free_gain(self, state, player, choices, context):
            assert context.source == "Quartermaster"
            assert context.destination == "quartermaster"
            return choices[0]

    state, player = make_state(Strategy())
    player.duration = [get_card("Quartermaster")]
    state._handle_quartermaster_start_of_turn(player)
    assert len(player.duration[0].set_aside) == 1


@pytest.mark.parametrize("card_name", ["Workshop", "Quartermaster", "Anvil"])
def test_failed_free_gain_conditions_respect_ownership_limit(card_name):
    strategy = EnhancedStrategy()
    strategy.free_gain_priority = [PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 1))]
    state, player = make_state(strategy, ("Smithy", "Silver"))
    qm = get_card("Quartermaster")
    qm.set_aside = [get_card("Smithy")]
    player.duration = [qm]
    if card_name == "Quartermaster":
        # Exercise the gain rather than the timing policy.
        assert player.ai.choose_quartermaster_gain(state, player, gain_menu(state, player, CardCost(4))).name == "Silver"
    else:
        player.hand = [get_card("Copper")]
        get_card(card_name).play_effect(state)
        assert player.discard[-1].name == "Silver"


def test_free_gain_inherits_active_phase_until_explicitly_separated():
    strategy = PhaseAwareStrategy()
    strategy.phase_gain_priority[StrategyPhase.ENDGAME] = [PriorityRule("Village")]
    state, player = make_state(strategy)
    get_card("Workshop").play_effect(state)
    assert player.discard[-1].name == "Village"
    strategy.free_gain_priority = [PriorityRule("Smithy")]
    get_card("Workshop").play_effect(state)
    assert player.discard[-1].name == "Smithy"


@pytest.mark.parametrize("invalid", [None, "Gold", "not a card"])
def test_workshop_invalid_selection_uses_mandatory_legal_fallback(invalid):
    class Strategy(EnhancedStrategy):
        def choose_free_gain(self, *args):
            return get_card(invalid) if invalid == "Gold" else invalid

    state, player = make_state(Strategy())
    get_card("Workshop").play_effect(state)
    assert player.discard[-1].name == "Smithy"


@pytest.mark.parametrize("card_name", ["Workshop", "Anvil", "Quartermaster"])
def test_fixed_coin_gain_menus_exclude_potions_debt_and_empty_piles(card_name):
    class Strategy(EnhancedStrategy):
        def choose_free_gain(self, state, player, choices, context):
            assert {c.name for c in choices} == {"Village"}
            return choices[0]

    state, player = make_state(Strategy(), ("Village", "Smithy", "Alchemist", "Engineer", "Horse"))
    state.supply["Smithy"] = 0
    state.non_supply_pile_names.add("Horse")
    player.hand = [get_card("Copper")]
    if card_name == "Quartermaster":
        player.duration = [get_card(card_name)]
        state._handle_quartermaster_start_of_turn(player)
        assert player.duration[0].set_aside[0].name == "Village"
    else:
        get_card(card_name).play_effect(state)
        assert player.discard[-1].name == "Village"


@pytest.mark.parametrize("card_name", ["Workshop", "Remodel", "Anvil", "Quartermaster"])
def test_empty_gain_menus_and_mandatory_remodel_trash(card_name):
    state, player = make_state(names=("Province",))
    player.hand = [get_card("Copper")]
    if card_name == "Quartermaster":
        player.duration = [get_card(card_name)]
        state._handle_quartermaster_start_of_turn(player)
    else:
        get_card(card_name).play_effect(state)
    assert state.supply["Province"] == 10
    assert len(state.trash) == (card_name == "Remodel")
    assert player.discard == []


def test_baseline_avoids_excess_terminal_copies():
    state, player = make_state(names=("Smithy", "Silver"))
    player.deck += [get_card("Smithy") for _ in range(4)]
    get_card("Workshop").play_effect(state)
    assert player.discard[-1].name == "Silver"


def test_remodel_baseline_compares_pairs_and_preserves_gold_when_curse_present():
    state, player = make_state(names=("Province", "Chapel", "Silver"))
    curse, gold = get_card("Curse"), get_card("Gold")
    player.hand = [gold, curse]
    get_card("Remodel").play_effect(state)
    assert curse in state.trash
    assert gold in player.hand
    assert player.discard[-1].name == "Chapel"


def test_remodel_endgame_upgrades_gold_to_province():
    state, player = make_state(names=("Province", "Estate", "Silver"))
    state.supply["Province"] = 1
    gold, copper = get_card("Gold"), get_card("Copper")
    player.hand = [copper, gold]
    get_card("Remodel").play_effect(state)
    assert gold in state.trash
    assert player.discard[-1].name == "Province"


def test_remodel_pair_override_has_legal_menus_and_sacrifice_context():
    class Strategy(EnhancedStrategy):
        def choose_remodel_option(self, state, player, options):
            trash, gains = next((c, gains) for c, gains in options if c.name == "Estate")
            assert {c.name for c in gains} == {"Smithy", "Village"}
            return trash, get_card("Gold")  # Invalid gain must fall back after trash.

        def choose_free_gain(self, state, player, choices, context):
            assert context.sacrificed.name == "Estate"
            assert context.sacrificed not in context.hand
            assert context.owned_counts.get("Estate", 0) == 0
            return next(c for c in choices if c.name == "Village")

    state, player = make_state(Strategy())
    player.hand = [get_card("Estate"), get_card("Copper")]
    get_card("Remodel").play_effect(state)
    assert state.trash[-1].name == "Estate"
    assert player.discard[-1].name == "Village"


@pytest.mark.parametrize("invalid", [None, (None, None), ("bogus", "bogus")])
def test_remodel_invalid_pair_uses_shared_baseline(invalid):
    class Strategy(EnhancedStrategy):
        def choose_remodel_option(self, *args):
            return invalid

    state, player = make_state(Strategy())
    player.hand = [get_card("Estate")]
    get_card("Remodel").play_effect(state)
    assert state.trash[-1].name == "Estate"
    assert player.discard[-1].name == "Smithy"


@pytest.mark.parametrize("trashed, allowed, forbidden", [
    ("Alchemist", "Philosopher's Stone", "Overlord"),
    ("Overlord", "Engineer", "Alchemist"),
    ("Copper", "Estate", "Engineer"),
])
def test_remodel_componentwise_potion_and_debt_limits(trashed, allowed, forbidden):
    class Strategy(EnhancedStrategy):
        def choose_remodel_option(self, state, player, options):
            card, choices = options[0]
            names = {c.name for c in choices}
            assert allowed in names
            assert forbidden not in names
            return card, next(c for c in choices if c.name == allowed)

    state, player = make_state(Strategy(), (allowed, forbidden))
    player.hand = [get_card(trashed)]
    get_card("Remodel").play_effect(state)
    assert player.discard[-1].name == allowed
    assert player.debt == 0  # Gaining a debt card incurs no debt.


def test_remodel_uses_modified_costs_for_both_trash_and_gain():
    class Strategy(EnhancedStrategy):
        def choose_remodel_option(self, state, player, options):
            assert {c.name for c in options[0][1]} == {"Village"}
            return options[0][0], options[0][1][0]

    state, player = make_state(Strategy(), ("Village", "Gold"))
    player.in_play = [get_card("Quarry")]
    player.hand = [get_card("Smithy")]
    get_card("Remodel").play_effect(state)
    assert player.discard[-1].name == "Village"
    player.in_play = []
    player.cost_reduction = 1
    player.hand = [get_card("Copper")]
    get_card("Remodel").play_effect(state)
    assert player.discard[-1].name == "Village"


@pytest.mark.parametrize("treasure, gained", [("Copper", True), ("Gold", False)])
def test_anvil_baseline_accounts_for_lost_treasure_income(treasure, gained):
    state, player = make_state(names=("Silver",))
    player.hand = [get_card(treasure)]
    get_card("Anvil").play_effect(state)
    assert (state.supply["Silver"] == 9) == gained
    assert bool(player.hand) != gained


def test_anvil_declines_junk_even_when_discarding_copper():
    state, player = make_state(names=("Curse",))
    player.hand = [get_card("Copper")]
    get_card("Anvil").play_effect(state)
    assert len(player.hand) == 1
    assert not player.discard


def test_anvil_combined_override_can_choose_both_cards():
    class Strategy(EnhancedStrategy):
        def choose_anvil_option(self, state, player, treasures, choices):
            return next(c for c in treasures if c.name == "Gold"), get_card("Village")

    state, player = make_state(Strategy())
    copper, gold = get_card("Copper"), get_card("Gold")
    player.hand = [copper, gold]
    get_card("Anvil").play_effect(state)
    assert player.hand == [copper]
    assert len(player.discard) == 2
    assert player.discard[0] is gold
    assert player.discard[-1].name == "Village"


@pytest.mark.parametrize("pair", [None, (None, None), (get_card("Copper"), get_card("Gold"))])
def test_anvil_invalid_or_declined_pair_preserves_hand(pair):
    class Strategy(EnhancedStrategy):
        def choose_anvil_option(self, *args):
            return pair

    state, player = make_state(Strategy())
    player.hand = [get_card("Copper")]
    get_card("Anvil").play_effect(state)
    assert len(player.hand) == 1
    assert not player.discard


@pytest.mark.parametrize("source", ["Workshop", "Remodel", "Anvil"])
def test_free_gains_keep_watchtower_reaction_path(source):
    strategy = EnhancedStrategy()
    strategy.free_gain_priority = [PriorityRule("Smithy")]
    state, player = make_state(strategy, ("Smithy",))
    player.hand = [get_card("Watchtower"), get_card("Estate"), get_card("Copper")]
    get_card(source).play_effect(state)
    assert player.deck[-1].name == "Smithy"
    assert not any(c.name == "Smithy" for c in player.discard)


def test_remodel_rebuilds_gain_menu_after_trash_reaction():
    class Strategy(EnhancedStrategy):
        def choose_remodel_option(self, state, player, options):
            return player.hand[0], get_card("Village")

    state, player = make_state(Strategy())
    copper = get_card("Copper")
    player.cost_reduction = 1
    player.hand = [copper]
    original = state.trash_card

    def trash_and_empty_pile(owner, card):
        original(owner, card)
        state.supply["Village"] = 0
        owner.cost_reduction = 2

    state.trash_card = trash_and_empty_pile
    get_card("Remodel").play_effect(state)
    assert player.discard[-1].name == "Smithy"
    assert state.supply["Village"] == 0


def test_quartermaster_collects_one_useful_card_without_waiting_for_two():
    state, player = make_state(names=("Silver",))
    qm = get_card("Quartermaster")
    qm.set_aside = [get_card("Silver")]
    player.duration = [qm]
    state._handle_quartermaster_start_of_turn(player)
    assert player.hand[-1].name == "Silver"
    assert not qm.set_aside


def test_quartermaster_selects_hand_support_over_higher_printed_cost():
    state, player = make_state()
    player.hand = [get_card("Smithy")]
    qm = get_card("Quartermaster")
    smithy, village = get_card("Smithy"), get_card("Village")
    qm.set_aside = [smithy, village]
    player.duration = [qm]
    state._handle_quartermaster_start_of_turn(player)
    assert player.hand[-1] is village
    assert qm.set_aside == [smithy]


def test_quartermaster_endgame_gains_points_already_owned_on_mat():
    state, player = make_state(names=("Estate", "Province"))
    state.supply["Province"] = 1
    qm = get_card("Quartermaster")
    silver = get_card("Silver")
    qm.set_aside = [silver]
    player.duration = [qm]
    state._handle_quartermaster_start_of_turn(player)
    assert not player.hand
    assert [c.name for c in qm.set_aside] == ["Silver", "Estate"]
    assert player.get_victory_points() == 1


def test_quartermaster_takes_dead_card_to_avoid_gaining_curse():
    state, player = make_state(names=("Curse",))
    qm = get_card("Quartermaster")
    qm.set_aside = [get_card("Estate")]
    player.duration = [qm]
    state._handle_quartermaster_start_of_turn(player)
    assert player.hand[-1].name == "Estate"
    assert state.supply["Curse"] == 10


def test_throne_room_quartermaster_repeats_each_turn_with_one_shared_pile():
    class Strategy(EnhancedStrategy):
        def choose_quartermaster_option(self, state, player, mat, candidates):
            return ("take", mat[0]) if mat else ("gain", candidates[0])

    state, player = make_state(Strategy(), ("Silver",))
    qm, throne = get_card("Quartermaster"), get_card("Throne Room")
    player.hand = [qm]
    player.in_play = [throne]
    throne.on_play(state)
    assert player.duration == [qm, qm]
    assert len([c for c in player.all_cards() if c.name == "Quartermaster"]) == 1
    player.deck = []
    state.handle_cleanup_phase()
    assert player.in_play.count(qm) == 1
    assert throne in player.in_play
    for _ in range(2):
        state.handle_start_phase()
        assert player.duration == [qm, qm]
        assert not qm.set_aside
    assert [c.name for c in player.hand] == ["Silver", "Silver"]
    assert state.supply["Silver"] == 8
    import copy
    clone = copy.deepcopy(state)
    assert clone.current_player.duration[0] is clone.current_player.duration[1]


def test_base_ai_uses_same_free_gain_baseline():
    state, player = make_state()
    player.ai = DummyAI()
    get_card("Workshop").play_effect(state)
    assert player.discard[-1].name == "Smithy"


def test_context_snapshot_does_not_change_when_hand_changes():
    state, player = make_state()
    copper = get_card("Copper")
    player.hand = [copper]
    context = FreeGainContext.build(state, player, "Workshop")
    player.hand.clear()
    assert context.hand == (copper,)


def test_quartermaster_played_at_start_of_turn_waits_until_following_turn():
    state, player = make_state(names=("Silver",))
    qm = get_card("Quartermaster")
    state.patient_mat[id(player)] = [qm]
    state.handle_start_phase()
    assert player.duration == [qm]
    assert not qm.set_aside
    assert state.supply["Silver"] == 10
    state.handle_start_phase()
    assert qm.set_aside[0].name == "Silver"
    assert state.supply["Silver"] == 9


def test_anvil_all_failed_priorities_decline_optional_exchange():
    strategy = EnhancedStrategy()
    strategy.free_gain_priority = [PriorityRule("Silver", lambda *_: False)]
    state, player = make_state(strategy, ("Silver",))
    player.hand = [get_card("Copper")]
    get_card("Anvil").play_effect(state)
    assert len(player.hand) == 1
    assert state.supply["Silver"] == 10


def test_mandatory_free_gain_still_selects_when_every_condition_fails():
    strategy = EnhancedStrategy()
    strategy.free_gain_priority = [PriorityRule("Smithy", lambda *_: False)]
    state, player = make_state(strategy, ("Smithy",))
    get_card("Workshop").play_effect(state)
    assert player.discard[-1].name == "Smithy"


def test_remodel_with_empty_hand_does_nothing():
    state, player = make_state()
    get_card("Remodel").play_effect(state)
    assert not state.trash
    assert not player.discard


@pytest.mark.parametrize("source", ["Workshop", "Remodel", "Anvil"])
def test_free_gain_trail_reaction_plays_gained_card(source):
    strategy = EnhancedStrategy()
    strategy.free_gain_priority = [PriorityRule("Trail")]
    strategy.action_priority = [PriorityRule("Trail")]
    state, player = make_state(strategy, ("Trail",))
    player.hand = [get_card("Estate"), get_card("Copper")]
    get_card(source).play_effect(state)
    assert any(c.name == "Trail" for c in player.in_play)
    assert len(player.deck) == 9
    assert state.supply["Trail"] == 9


def test_remodel_checks_trash_cost_after_trash_reactions():
    class Strategy(EnhancedStrategy):
        def choose_remodel_option(self, state, player, options):
            return player.hand[0], get_card("Gold")

    state, player = make_state(Strategy(), ("Gold", "Village"))
    # A reaction changing costs invalidates the pre-trash plan. Changing
    # Smithy from $4 to $0 lowers its replacement limit from $6 to $2.
    smithy = get_card("Smithy")
    player.hand = [smithy]
    original = state.trash_card

    def trash_and_change_cost(owner, card):
        original(owner, card)
        card.cost.coins = 0

    state.trash_card = trash_and_change_cost
    get_card("Remodel").play_effect(state)
    assert not player.discard
    assert smithy in state.trash
    assert state.supply["Gold"] == 10
