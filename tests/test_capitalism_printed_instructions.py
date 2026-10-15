"""Capitalism classifies printed instructions, including choices and delays."""

import pytest

from dominion.cards.printed_coin_instructions import (
    ACTIONS_WITH_PRINTED_COINS,
    ACTIONS_WITHOUT_PRINTED_COINS,
)
from dominion.cards.registry import CARD_TYPES, get_card
from dominion.events.registry import get_event
from dominion.projects.capitalism import Capitalism
from dominion.projects.guildhall import Guildhall
from tests.test_named_card_decisions import make_state


CONDITIONAL = ["Courtier", "Minion", "Moneylender", "Spice Merchant", "Baron", "Mill", "Ironworks", "Broker", "Sycophant", "Town", "Town Crier", "Merchant", "Harbor Village", "Storyteller"]
DELAYED = ["Amulet", "Caravan Guard", "Sailor", "Secret Cave", "Swamp Hag", "Samurai"]


def test_printed_coin_metadata_covers_every_registered_action_once():
    actions = {name for name, cls in CARD_TYPES.items() if cls().is_action}
    assert not ACTIONS_WITH_PRINTED_COINS & ACTIONS_WITHOUT_PRINTED_COINS
    assert ACTIONS_WITH_PRINTED_COINS | ACTIONS_WITHOUT_PRINTED_COINS == actions
    state, player = make_state()
    player.projects = [Capitalism()]
    for name in actions:
        card = get_card(name)
        assert state.is_treasure(card) == (name in ACTIONS_WITH_PRINTED_COINS or card.is_treasure), name
        # The printed instruction does not change when executable stats change.
        card.stats.coins = 0 if name in ACTIONS_WITH_PRINTED_COINS else 9
        assert state.is_treasure(card) == (name in ACTIONS_WITH_PRINTED_COINS or card.is_treasure), name


@pytest.mark.parametrize("name", CONDITIONAL + DELAYED)
def test_conditional_and_future_coins_are_live_everywhere_on_actual_owners_turn(name):
    state, owner = make_state()
    other = state.players[1]
    owner.projects = [Capitalism()]
    card = get_card(name)
    assert card.stats.coins == (1 if name == "Storyteller" else 0)
    assert state.is_treasure(card)
    other.hand = [card]
    state.current_player_index = 1
    state.reaction_turn_player_index = 0
    assert state.is_treasure(card)
    state.reaction_turn_player_index = None
    assert not state.is_treasure(card)


@pytest.mark.parametrize("name", ["Baker", "Butcher", "Candlestick Maker", "Villain", "Inventor", "Highway", "Carpenter", "Modify", "Teacher", "Coppersmith", "Bandit Camp", "Captain", "Throne Room"])
def test_coffers_costs_tokens_and_playing_other_cards_do_not_qualify(name):
    state, player = make_state()
    player.projects = [Capitalism()]
    assert not state.is_treasure(get_card(name))


@pytest.mark.parametrize("name", ["Minion", "Moneylender", "Sailor"])
def test_buy_phase_plays_the_physical_conditional_or_duration_action(name):
    state, player = make_state(kingdom=(name,))
    player.projects = [Capitalism()]
    card = get_card(name)
    player.hand = [card]
    player.ai.choose_treasure = lambda state, choices: next((c for c in choices if c is card), None)
    state.phase = "buy"
    state.handle_treasure_phase()
    assert card not in player.hand and card in player.in_play
    assert player.actions_played == 1
    assert (card in player.duration) == (name == "Sailor")
    assert player.actions == (1 if name in {"Minion", "Sailor"} else 0)


@pytest.mark.parametrize("name", ["Courtier", "Minion", "Sailor"])
def test_gain_and_reveal_bonuses_use_the_same_live_classification(name):
    state, player = make_state(kingdom=(name,))
    player.projects = [Capitalism(), Guildhall()]
    gained = state.gain_from_supply(player, name)
    assert gained in player.discard
    assert player.coin_tokens == 1
    assert state.live_type_count(gained) == len(gained.types) + 1


def test_bandit_can_trash_opponents_conditional_coin_action():
    state, player = make_state(kingdom=("Bandit", "Moneylender"))
    player.projects = [Capitalism()]
    other = state.players[1]
    physical = get_card("Moneylender")
    other.deck = [physical, get_card("Estate")]
    get_card("Bandit").play_effect(state)
    assert physical in state.trash
    assert physical not in other.all_cards()


@pytest.mark.parametrize("handler", ["Stables", "Spice Merchant", "Counterfeit"])
def test_treasure_menus_offer_physical_conditional_coin_actions(handler):
    state, player = make_state(kingdom=(handler, "Minion"))
    player.projects = [Capitalism()]
    target = get_card("Minion")
    player.hand = [target]
    player.deck = [get_card("Copper") for _ in range(4)]
    menus = []
    hook = {"Stables": "choose_treasure_to_discard_for_stables", "Spice Merchant": "choose_treasure_to_trash_for_spice_merchant", "Counterfeit": "should_replay_treasure_with_counterfeit"}[handler]
    def pick(*args):
        menus.append(args[-1])
        return target
    setattr(player.ai, hook, pick)
    get_card(handler).play_effect(state)
    assert menus and target in menus[0]
    assert target not in player.hand
    assert target in (player.discard if handler == "Stables" else state.trash)


def test_inheritance_estate_is_command_action_victory_everywhere_and_never_inherits_coins():
    state, owner = make_state(kingdom=("Moneylender",))
    owner.ai.choose_card_to_inherit = lambda *_: get_card("Moneylender")
    get_event("Inheritance").on_buy(state, owner)
    owner.projects = [Capitalism()]
    other = state.players[1]
    estate = get_card("Estate")
    other.hand = [estate]
    assert state.is_action(estate) and state.is_command(estate)
    assert state.live_type_count(estate) == 3
    assert not state.is_treasure(estate)
    state.current_player_index = 1
    state.reaction_turn_player_index = 0
    assert state.is_action(estate) and state.is_command(estate)
    state.reaction_turn_player_index = None
    assert not state.is_action(estate) and not state.is_command(estate)
    assert state.live_type_count(estate) == 1


def test_storyteller_initial_coin_and_nested_conditional_treasure_play():
    state, player = make_state(kingdom=("Storyteller", "Minion"))
    player.projects = [Capitalism()]
    storyteller, minion = get_card("Storyteller"), get_card("Minion")
    player.in_play = [storyteller]
    player.hand = [minion]
    player.deck = [get_card("Copper") for _ in range(6)]
    player.ai.choose_treasures_to_play_for_storyteller = lambda s, p, choices: [minion]
    player.ai.choose_minion_mode = lambda *_: "coins"
    state.play_action_indirectly(player, storyteller)
    assert minion in player.in_play
    assert player.actions_played == 2
    assert player.coins == 0
    assert len(player.hand) == 3  # Storyteller's initial coin plus Minion's two.
