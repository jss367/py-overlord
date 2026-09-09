"""Card-interaction tests for the Albuquerque board (``boards/albuquerque.txt``)."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class _RemakeAI(DummyAI):
    """Trash Coppers first; gain the first offered card (the engine's own order)."""

    def choose_card_to_trash(self, state, choices):
        for card in choices:
            if card.name == "Copper":
                return card
        return None

    def choose_buy(self, state, choices):
        for card in choices:
            if card is not None:
                return card
        return None


def _state(ai):
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.setup_supply([get_card("Remake"), get_card("Bridge"), get_card("Peasant")])
    state.log_callback = lambda *_: None
    player.hand = []
    player.deck = []
    player.discard = []
    return state, player


def test_remake_uses_modified_costs_under_bridge():
    state, player = _state(_RemakeAI())
    player.cost_reduction = 1  # a Bridge is in play
    player.hand = [get_card("Copper"), get_card("Copper")]
    remake = get_card("Remake")
    player.in_play.append(remake)
    remake.play_effect(state)

    assert [c.name for c in state.trash] == ["Copper", "Copper"]
    # Copper costs $0 under Bridge, so "exactly $1 more" is a printed-$2 card.
    gained = sorted(c.name for c in player.discard)
    assert len(gained) == 2
    assert all(get_card(n).cost.coins == 2 for n in gained), gained


def test_remake_without_bridge_cannot_upgrade_copper():
    state, player = _state(_RemakeAI())
    player.hand = [get_card("Copper")]
    remake = get_card("Remake")
    player.in_play.append(remake)
    remake.play_effect(state)

    assert [c.name for c in state.trash] == ["Copper"]
    assert player.discard == []


class _DeclineAI(DummyAI):
    def choose_action(self, state, choices):
        return None


def test_kings_court_may_decline_to_play_anything():
    state, player = _state(_DeclineAI())
    player.hand = [get_card("Bridge")]
    kc = get_card("King's Court")
    player.in_play.append(kc)
    kc.play_effect(state)

    assert [c.name for c in player.hand] == ["Bridge"]
    assert player.coins == 0 and player.buys == 1


def test_treasure_value_in_deck_condition():
    from dominion.strategy.enhanced_strategy import PriorityRule

    state, player = _state(DummyAI())
    player.deck = [get_card("Copper") for _ in range(3)] + [get_card("Silver"), get_card("Estate")]
    assert PriorityRule.treasure_value_in_deck(">", 4)(state, player)
    assert not PriorityRule.treasure_value_in_deck(">", 5)(state, player)


def test_deck_group_diff_condition():
    from dominion.strategy.enhanced_strategy import PriorityRule

    state, player = _state(DummyAI())
    player.deck = [get_card("Bridge"), get_card("Bridge"), get_card("Wharf"), get_card("Wandering Minstrel")]
    cond = PriorityRule.deck_group_diff(["Bridge", "Wharf"], ["Wandering Minstrel"], ">", 1)
    assert cond(state, player)
    assert "deck_group_diff" in cond._source
    player.deck.append(get_card("Wandering Minstrel"))
    assert not cond(state, player)


class _DeclineGainAI(_RemakeAI):
    def choose_buy(self, state, choices):
        return None


def test_remake_forced_gain_prefers_non_victory():
    state, player = _state(_DeclineGainAI())
    player.cost_reduction = 1
    player.hand = [get_card("Copper")]
    remake = get_card("Remake")
    player.in_play.append(remake)
    remake.play_effect(state)

    assert len(player.discard) == 1
    assert not player.discard[0].is_victory


def test_not_combinator():
    from dominion.strategy.enhanced_strategy import PriorityRule

    state, player = _state(DummyAI())
    cond = PriorityRule.not_(PriorityRule.card_in_play("Bridge"))
    assert cond(state, player)
    player.in_play.append(get_card("Bridge"))
    assert not cond(state, player)
    assert cond._source.startswith("PriorityRule.not_(")


def test_engine_drains_a_low_pile_when_ahead_with_two_piles_empty():
    from dominion.game.game_state import GameState
    from dominion.game.player_state import PlayerState
    from dominion.strategy.strategies.albuquerque_seeds import AlbuquerqueChapelBridgeEngine

    strategy = AlbuquerqueChapelBridgeEngine()
    me, opp = PlayerState(DummyAI()), PlayerState(DummyAI())
    state = GameState(players=[me, opp])
    state.setup_supply([get_card("Bridge"), get_card("Wandering Minstrel"), get_card("Chapel")])
    state.log_callback = lambda *_: None
    for p in (me, opp):
        p.hand, p.deck, p.discard = [], [], []
    me.deck = [get_card("Province")]
    state.supply["Estate"] = 0
    state.supply["Duchy"] = 0
    state.supply["Bridge"] = 3
    choices = [get_card("Bridge"), get_card("Wandering Minstrel"), get_card("Silver"), None]

    assert state.empty_piles >= 2
    assert strategy.choose_gain(state, me, choices).name == "Bridge"

    # Not ahead: no pile-out (with six Bridges the normal list declines them too).
    opp.deck = [get_card("Province"), get_card("Province")]
    me.deck += [get_card("Bridge") for _ in range(6)]
    pick = strategy.choose_gain(state, me, choices)
    assert pick is None or pick.name != "Bridge"
