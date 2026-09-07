"""Courier rules, shared target selection, and strategy forwarding."""

from types import SimpleNamespace

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.phase_strategy import PhaseAwareStrategy, StrategyPhase
from tests.utils import DummyAI


def make_state(strategy=None):
    player = PlayerState(GeneticAI(strategy or EnhancedStrategy()))
    player.deck = [get_card("Estate")]
    state = GameState([player], supply={})
    state.log_callback = lambda *args: None
    return state, player


def play_courier(state, player):
    card = get_card("Courier")
    player.in_play.append(card)
    state.play_action_indirectly(player, card)
    return card


@pytest.mark.parametrize("target, coins, actions", [
    ("Gold", 4, 0), ("Copper", 2, 0), ("Village", 1, 2),
])
@pytest.mark.parametrize("base_ai", [False, True])
def test_plays_from_existing_discard_without_spending_an_action(target, coins, actions, base_ai):
    state, player = make_state()
    if base_ai:
        player.ai = DummyAI()
    player.actions = 0
    chosen = get_card(target)
    player.discard = [chosen]
    play_courier(state, player)
    assert chosen in player.in_play
    assert chosen not in player.discard
    assert player.coins == coins
    assert player.actions == actions
    assert player.actions_played == (2 if chosen.is_action else 1)
    assert state.trash == []


@pytest.mark.parametrize("top", ["Curse", "Estate", "Copper", "Gold"])
def test_top_card_is_discarded_and_never_trashed(top):
    class Decline(EnhancedStrategy):
        def choose_courier_target(self, state, player, choices):
            return None

    state, player = make_state(Decline())
    card = get_card(top)
    player.deck = [card]
    play_courier(state, player)
    assert player.discard == [card]
    assert state.trash == []
    assert player.coins == 1


def test_can_play_the_just_discarded_treasure():
    state, player = make_state()
    gold = get_card("Gold")
    player.deck = [gold]
    play_courier(state, player)
    assert gold in player.in_play
    assert player.discard == []
    assert player.coins == 4


def test_shuffles_before_discarding_when_deck_is_empty():
    state, player = make_state()
    gold = get_card("Gold")
    player.deck = []
    player.discard = [gold]
    play_courier(state, player)
    assert player.deck == []
    assert player.discard == []
    assert gold in player.in_play
    assert player.coins == 4


def test_empty_deck_and_discard_still_give_coin():
    state, player = make_state()
    player.deck = []
    play_courier(state, player)
    assert player.coins == 1
    assert len(player.in_play) == 1


def test_discard_reaction_gain_is_available_as_target():
    state, player = make_state()
    state.supply = {"Gold": 1}
    tunnel = get_card("Tunnel")
    player.deck = [tunnel]
    play_courier(state, player)
    assert player.discard == [tunnel]
    assert state.supply["Gold"] == 0
    assert player.coins == 4
    assert any(c.name == "Gold" for c in player.in_play)


def test_discard_reaction_can_empty_discard_before_selection():
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Trail")]
    state, player = make_state(strategy)
    trail, gold = get_card("Trail"), get_card("Gold")
    player.deck = [trail]
    player.discard = [gold]
    play_courier(state, player)
    # Trail reacts, leaves discard, then draws Gold by shuffling. Courier
    # cannot replay Trail or take Gold from the now-empty discard pile.
    assert trail in player.in_play
    assert player.hand == [gold]
    assert player.discard == []
    assert player.coins == 1
    assert player.actions_played == 2


def test_strategy_override_sees_legal_menu_and_can_ignore_hand_priorities():
    class SelectGold(EnhancedStrategy):
        def choose_courier_target(self, state, player, choices):
            assert {c.name for c in choices} == {"Village", "Gold"}
            return next(c for c in choices if c.name == "Gold")

    strategy = SelectGold()
    strategy.action_priority = [PriorityRule("Village")]
    state, player = make_state(strategy)
    player.discard = [get_card("Village"), get_card("Gold"), get_card("Curse")]
    play_courier(state, player)
    assert player.coins == 4
    assert any(c.name == "Village" for c in player.discard)


@pytest.mark.parametrize("result", [None, "Gold", "Province"])
def test_decline_and_invalid_targets_do_not_play_a_card(result):
    class Select(EnhancedStrategy):
        def choose_courier_target(self, state, player, choices):
            # Even a fresh copy of an offered card is not the offered instance.
            return get_card(result) if result else None

    state, player = make_state(Select())
    player.discard = [get_card("Gold")]
    play_courier(state, player)
    assert len(player.in_play) == 1
    assert player.coins == 1
    assert [c.name for c in player.discard] == ["Gold", "Estate"]


@pytest.mark.parametrize("reverse", [False, True])
def test_default_supports_actions_needed_in_hand(reverse):
    state, player = make_state()
    player.actions = 0
    player.hand = [get_card("Smithy")]
    player.discard = [get_card("Village"), get_card("Gold")][::(-1 if reverse else 1)]
    play_courier(state, player)
    assert player.actions == 2
    assert any(c.name == "Village" for c in player.in_play)


def test_default_prefers_draw_when_actions_are_sufficient():
    state, player = make_state()
    player.deck = [get_card("Copper") for _ in range(5)]
    player.discard = [get_card("Smithy"), get_card("Gold")]
    play_courier(state, player)
    assert len(player.hand) == 3
    assert player.coins == 1


def test_default_chains_courier_then_plays_payload():
    state, player = make_state()
    player.deck = [get_card("Estate") for _ in range(3)]
    second, gold = get_card("Courier"), get_card("Gold")
    player.discard = [gold, second]
    play_courier(state, player)
    assert second in player.in_play and gold in player.in_play
    assert player.coins == 5
    assert player.actions_played == 2


def test_default_avoids_chaining_when_it_would_shuffle_away_gold():
    state, player = make_state()
    second, gold = get_card("Courier"), get_card("Gold")
    player.discard = [second, gold]
    play_courier(state, player)
    assert gold in player.in_play
    assert second in player.discard
    assert player.coins == 4


@pytest.mark.parametrize("kind, target", [("action", "Village"), ("treasure", "Silver")])
def test_uses_explicit_priorities(kind, target):
    strategy = EnhancedStrategy()
    setattr(strategy, f"{kind}_priority", [PriorityRule(target)])
    state, player = make_state(strategy)
    card = get_card(target)
    player.discard = [get_card("Gold"), card]
    play_courier(state, player)
    assert card in player.in_play


def test_failed_conditional_preferences_allow_declining_harmful_play():
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Rats", lambda *_: False)]
    state, player = make_state(strategy)
    rats = get_card("Rats")
    player.hand = [get_card("Gold")]
    player.discard = [rats]
    play_courier(state, player)
    assert rats in player.discard
    assert state.trash == []


def test_phase_preferences_are_forwarded_and_fallback_works():
    strategy = PhaseAwareStrategy()
    strategy.phase_action_priority[StrategyPhase.ENDGAME] = [PriorityRule("Village")]
    state, player = make_state(strategy)
    village = get_card("Village")
    player.discard = [get_card("Gold"), village]
    play_courier(state, player)
    assert village in player.in_play
    # No applicable preference for this menu: use the shared default.
    choices = [get_card("Gold"), get_card("Silver")]
    assert player.ai.choose_courier_target(state, player, choices) is choices[0]


def test_strategy_without_new_hook_inherits_default():
    state, player = make_state(SimpleNamespace())
    player.discard = [get_card("Gold")]
    play_courier(state, player)
    assert player.coins == 4


def test_treasure_play_honors_highwayman():
    state, player = make_state()
    player.highwayman_attacks = 1
    gold = get_card("Gold")
    player.discard = [gold]
    play_courier(state, player)
    assert gold in player.in_play
    assert player.coins == 1
    assert player.highwayman_blocked_this_turn


def test_treasure_play_fires_hooks_without_action_bookkeeping():
    state, player = make_state()
    gold = get_card("Gold")
    player.discard = [gold]
    seen = []
    state.fire_ally_play_hooks = lambda owner, card: seen.append(card)
    courier = play_courier(state, player)
    assert seen == [gold, courier]
    assert player.actions_played == 1


def test_charlatan_curse_is_a_legal_treasure():
    state, player = make_state()
    state.supply = {"Charlatan": 10}
    curse = get_card("Curse")
    player.deck = [curse]
    play_courier(state, player)
    assert curse in player.in_play
    assert player.coins == 2
    assert state.trash == []
