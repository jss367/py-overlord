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


@pytest.mark.parametrize("target", ["Gold", "Crown", "Curse"])
def test_enlightenment_replaces_courier_treasure_play_in_action_phase(target):
    from dominion.prophecies.enlightenment import Enlightenment

    state, player = make_state()
    state.prophecy = Enlightenment()
    state.prophecy.is_active = True
    state.phase = "action"
    if target == "Curse":
        state.supply = {"Charlatan": 10}
    player.actions = 0
    player.highwayman_attacks = 1
    drawn = get_card("Estate")
    player.deck = [drawn, get_card("Estate")]
    chosen = get_card(target)
    player.discard = [chosen]
    play_courier(state, player)
    assert chosen in player.in_play
    assert player.hand == [drawn]
    assert player.coins == 1  # Only Courier's coin, never Gold's payload.
    assert player.actions == 1
    assert player.actions_played == 2
    assert not player.highwayman_blocked_this_turn


@pytest.mark.parametrize("phase, active", [("buy", True), ("action", False)])
def test_enlightenment_does_not_replace_treasure_outside_its_condition(phase, active):
    from dominion.prophecies.enlightenment import Enlightenment

    state, player = make_state()
    state.prophecy = Enlightenment()
    state.prophecy.is_active = active
    state.phase = phase
    player.actions = 0
    player.discard = [get_card("Gold")]
    play_courier(state, player)
    assert player.coins == 4
    assert player.actions == 0
    assert player.hand == []


def test_enlightened_courier_treasure_can_use_a_way():
    from dominion.prophecies.enlightenment import Enlightenment
    from dominion.ways.registry import get_way

    class UseOx(EnhancedStrategy):
        def choose_way(self, state, player, card, ways):
            return next((w for w in ways if w is not None), None) if card.name == "Gold" else None

    state, player = make_state(UseOx())
    state.prophecy = Enlightenment()
    state.prophecy.is_active = True
    state.phase = "action"
    state.ways = [get_way("Way of the Ox")]
    player.actions = 0
    player.discard = [get_card("Gold")]
    play_courier(state, player)
    assert player.actions == 2
    assert player.coins == 1
    assert player.hand == []
    assert player.actions_played == 2


@pytest.mark.parametrize("indirect", [False, True])
@pytest.mark.parametrize("copies", [0, 2])
def test_kiln_copies_courier_before_its_nested_treasure(indirect, copies):
    class SelectGold(EnhancedStrategy):
        def choose_courier_target(self, state, player, choices):
            return next(c for c in choices if c.name == "Gold")

    state, player = make_state(SelectGold())
    state.supply = {"Courier": copies, "Gold": 10}
    player.kiln_pending = 2
    player.discard = [get_card("Gold")]
    if indirect:
        play_courier(state, player)
    else:
        player.hand = [get_card("Courier")]
        player.ai.strategy.action_priority = [PriorityRule("Courier")]
        player.actions = 1
        state.phase = "action"
        state.handle_action_phase()
    assert state.supply["Courier"] == 0
    assert state.supply["Gold"] == 10
    assert player.kiln_pending == 0
    assert sum(c.name == "Courier" for c in player.discard) == copies
    assert player.coins == 4


def test_kiln_play_copies_previous_charge_and_arms_next_charge():
    state, player = make_state()
    state.supply = {"Kiln": 1, "Gold": 1}
    player.kiln_pending = 1
    kiln, gold = get_card("Kiln"), get_card("Gold")
    player.in_play = [kiln]
    state.play_treasure_indirectly(player, kiln)
    assert state.supply["Kiln"] == 0
    assert player.kiln_pending == 1
    player.in_play.append(gold)
    state.play_treasure_indirectly(player, gold)
    assert state.supply["Gold"] == 0
    assert player.kiln_pending == 0


@pytest.mark.parametrize("target", ["Gold", "Crown", "Curse"])
def test_champion_rewards_enlightened_courier_targets(target):
    from dominion.prophecies.enlightenment import Enlightenment

    state, player = make_state()
    state.prophecy = Enlightenment()
    state.prophecy.is_active = True
    state.phase = "action"
    if target == "Curse":
        state.supply = {"Charlatan": 10}
    player.champions_in_play = 1
    player.actions = 0
    player.discard = [get_card(target)]
    play_courier(state, player)
    # +1 Action from Enlightenment, plus Champion for both Courier and target.
    assert player.actions == 3
    assert player.coins == 1


def test_urchin_reacts_to_enlightened_treasure_attack_play():
    from dominion.prophecies.enlightenment import Enlightenment

    state, player = make_state()
    state.prophecy = Enlightenment()
    state.prophecy.is_active = True
    state.phase = "action"
    state.supply = {"Mercenary": 10}
    urchin, idol = get_card("Urchin"), get_card("Idol")
    player.in_play = [urchin]
    player.discard = [idol]
    play_courier(state, player)
    assert idol in player.in_play
    assert urchin in state.trash
    assert urchin not in player.in_play
    assert state.supply["Mercenary"] == 9
    assert any(c.name == "Mercenary" for c in player.discard)
    assert player.coins == 1


def test_highwayman_blocks_first_courier_crown_without_losing_action_bookkeeping():
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Village")]
    state, player = make_state(strategy)
    state.phase = "action"
    player.highwayman_attacks = 1
    player.actions = 0
    village = get_card("Village")
    player.hand = [village]
    first, second = get_card("Crown"), get_card("Crown")
    player.discard = [first]
    player.deck = [get_card("Estate") for _ in range(5)]
    play_courier(state, player)
    assert first in player.in_play
    assert player.hand == [village]
    assert player.actions == 0
    assert player.actions_played == 2
    assert player.highwayman_blocked_this_turn
    player.discard.append(second)
    play_courier(state, player)
    assert second in player.in_play
    assert village in player.in_play
    assert player.actions_played == 6  # Two Couriers, two Crowns, two Village plays.
    assert player.coins == 2


def test_enlightenment_applies_to_courier_played_during_another_players_action_phase():
    from dominion.prophecies.enlightenment import Enlightenment

    state, owner = make_state()
    turn_player = PlayerState(DummyAI())
    state.players.insert(0, turn_player)
    state.current_player_index = 0
    state.phase = "action"
    state.prophecy = Enlightenment()
    state.prophecy.is_active = True
    owner.actions = 0
    drawn = get_card("Estate")
    owner.deck = [drawn, get_card("Estate")]
    gold, courier = get_card("Gold"), get_card("Courier")
    owner.discard = [gold]
    owner.in_play = [courier]
    state.play_action_as_owner_indirectly(owner, courier)
    assert state.current_player is turn_player
    assert owner.coins == 1
    assert owner.actions == 1
    assert owner.hand == [drawn]
    assert gold in owner.in_play


def test_highwayman_recognizes_capitalism_treasures_in_treasure_phase():
    from dominion.projects import Capitalism

    state, player = make_state()
    player.projects = [Capitalism()]
    player.highwayman_attacks = 1
    player.actions = 0
    bazaar = get_card("Bazaar")
    player.hand = [bazaar]
    state.phase = "treasure"
    state.handle_treasure_phase()
    assert bazaar in player.in_play
    assert player.highwayman_blocked_this_turn
    assert player.coins == 0
    assert player.actions == 0
    assert player.hand == []


def test_capitalism_treasure_type_ends_on_another_players_turn():
    from dominion.projects import Capitalism

    state, player = make_state()
    player.projects = [Capitalism()]
    bazaar = get_card("Bazaar")
    assert state.is_treasure(bazaar)
    state.players.append(PlayerState(DummyAI()))
    state.current_player_index = 1
    assert not state.is_treasure(bazaar)


@pytest.mark.parametrize("use_way", [False, True])
def test_enlightened_courier_treasure_keeps_action_semantics_in_buy_phase(use_way):
    from dominion.prophecies.enlightenment import Enlightenment
    from dominion.ways.registry import get_way

    class UseOx(EnhancedStrategy):
        def choose_way(self, state, player, card, ways):
            if use_way and card.name == "Gold":
                return next(w for w in ways if w is not None)
            return None

    state, player = make_state(UseOx())
    state.prophecy = Enlightenment()
    state.prophecy.is_active = True
    state.phase = "buy"
    state.ways = [get_way("Way of the Ox")]
    gold = get_card("Gold")
    player.discard = [gold]
    player.actions = 0
    tavern_plays, ally_plays = [], []
    state._call_tavern_triggers = lambda owner, event, card: tavern_plays.append((event, card))
    state.fire_ally_play_hooks = lambda owner, card: ally_plays.append(card)
    courier = play_courier(state, player)
    assert player.coins == (1 if use_way else 4)
    assert player.actions == (2 if use_way else 0)
    assert player.actions_played == 2
    assert ("action_played", gold) in tavern_plays
    assert ally_plays == [gold, courier]


def test_enlightened_courier_treasure_keeps_tiara_replay_in_buy_phase():
    from dominion.prophecies.enlightenment import Enlightenment

    state, player = make_state()
    state.prophecy = Enlightenment()
    state.prophecy.is_active = True
    state.phase = "buy"
    gold = get_card("Gold")
    player.in_play = [get_card("Tiara")]
    player.discard = [gold]
    plays = []
    state.fire_ally_play_hooks = lambda owner, card: plays.append(card)
    play_courier(state, player)
    assert player.coins == 7
    assert player.actions_played == 3
    assert plays.count(gold) == 2
    assert player.tiara_replay_used


def test_enlightened_courier_treasure_keeps_corsair_trigger_in_buy_phase():
    from dominion.prophecies.enlightenment import Enlightenment

    state, player = make_state()
    opponent = PlayerState(DummyAI())
    state.players.append(opponent)
    corsair = get_card("Corsair")
    state.current_player_index = 1
    corsair.on_play(state)
    state.current_player_index = 0
    state.prophecy = Enlightenment()
    state.prophecy.is_active = True
    state.phase = "buy"
    gold = get_card("Gold")
    player.discard = [gold]
    play_courier(state, player)
    assert player.coins == 4
    assert player.actions_played == 2
    assert gold in state.trash
    assert gold not in player.in_play


def test_courier_offers_inherited_estate_and_restores_its_identity():
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Estate")]
    state, player = make_state(strategy)
    player.inherited_action_name = "Village"
    player.actions = 0
    estate, gold = get_card("Estate"), get_card("Gold")
    player.discard = [estate, gold]
    player.deck = [get_card("Copper") for _ in range(5)]
    play_courier(state, player)
    assert estate in player.in_play
    assert gold in player.discard
    assert player.actions == 2
    assert len(player.hand) == 1
    assert estate.name == "Estate"
    assert estate.is_victory and not estate.is_action
    assert estate.stats.actions == 0


def test_courier_inheritance_overlay_is_restored_after_failed_play():
    class FailOnVillage(EnhancedStrategy):
        def choose_way(self, state, player, card, ways):
            if card.name == "Village":
                raise RuntimeError("test play failed")
            return None

    from dominion.ways.registry import get_way

    state, player = make_state(FailOnVillage())
    player.ai.strategy.action_priority = [PriorityRule("Estate")]
    player.inherited_action_name = "Village"
    estate = get_card("Estate")
    player.discard = [estate]
    player.deck = [get_card("Copper")]
    state.ways = [get_way("Way of the Ox")]
    with pytest.raises(RuntimeError, match="test play failed"):
        play_courier(state, player)
    assert estate.name == "Estate"
    assert estate.is_victory and not estate.is_action


@pytest.mark.parametrize("target", ["Gold", "Crown"])
def test_highwayman_suppression_preserves_prophecy_and_ally_play_triggers(target):
    from dominion.prophecies.good_harvest import GoodHarvest

    state, player = make_state()
    state.phase = "buy"
    state.prophecy = GoodHarvest()
    state.prophecy.is_active = True
    player.highwayman_attacks = 1
    card = get_card(target)
    player.discard = [card]
    seen = []
    state.fire_ally_play_hooks = lambda owner, played: seen.append(played)
    courier = play_courier(state, player)
    assert player.highwayman_blocked_this_turn
    assert player.coins == 2  # Courier and Good Harvest, no Treasure payload.
    assert player.buys == 2
    assert seen == [card, courier]


def test_highwayman_suppression_still_allows_tiara_replay():
    state, player = make_state()
    gold = get_card("Gold")
    player.in_play = [get_card("Tiara")]
    player.discard = [gold]
    player.highwayman_attacks = 1
    plays = []
    state.fire_ally_play_hooks = lambda owner, card: plays.append(card)
    play_courier(state, player)
    assert player.coins == 4  # First Gold suppressed; Tiara replay produces $3.
    assert plays.count(gold) == 2
    assert player.tiara_replay_used


def test_highwayman_suppression_still_triggers_corsair():
    state, player = make_state()
    opponent = PlayerState(DummyAI())
    state.players.append(opponent)
    state.current_player_index = 1
    get_card("Corsair").on_play(state)
    state.current_player_index = 0
    gold = get_card("Gold")
    player.discard = [gold]
    player.highwayman_attacks = 1
    play_courier(state, player)
    assert player.coins == 1
    assert gold in state.trash
    assert gold not in player.in_play


def test_highwayman_suppression_still_triggers_inspiring():
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Village")]
    state, player = make_state(strategy)
    state.pile_traits = {"Gold": "Inspiring"}
    village = get_card("Village")
    player.hand = [village]
    player.discard = [get_card("Gold")]
    player.highwayman_attacks = 1
    player.actions = 0
    play_courier(state, player)
    assert village in player.in_play
    assert player.actions == 2
    assert player.coins == 1
