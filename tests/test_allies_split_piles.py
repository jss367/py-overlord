"""Tests for the five Allies split piles."""

from dominion.cards.allies.augurs import AUGURS_PILE_ORDER
from dominion.cards.allies.clashes import CLASHES_PILE_ORDER
from dominion.cards.allies.forts import FORTS_PILE_ORDER
from dominion.cards.allies.odysseys import ODYSSEYS_PILE_ORDER
from dominion.cards.allies.townsfolk import TOWNSFOLK_PILE_ORDER
from dominion.cards.allies._split_base import AlliesSplitCard
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _setup_state(top_card_name: str) -> tuple[GameState, PlayerState]:
    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    top = get_card(top_card_name)
    state.setup_supply([top])
    return state, player


def test_all_split_piles_have_four_cards():
    for order in (
        AUGURS_PILE_ORDER,
        CLASHES_PILE_ORDER,
        FORTS_PILE_ORDER,
        ODYSSEYS_PILE_ORDER,
        TOWNSFOLK_PILE_ORDER,
    ):
        assert len(order) == 4
        for name in order:
            card = get_card(name)
            assert isinstance(card, AlliesSplitCard)


def test_setup_supply_creates_all_partner_piles():
    for order in (
        AUGURS_PILE_ORDER,
        CLASHES_PILE_ORDER,
        FORTS_PILE_ORDER,
        ODYSSEYS_PILE_ORDER,
        TOWNSFOLK_PILE_ORDER,
    ):
        state, _ = _setup_state(order[0])
        for name in order:
            assert name in state.supply, f"Pile {name} missing from supply for {order[0]}"
            assert state.supply[name] > 0


def test_only_top_card_buyable():
    """The first pile-member is buyable; lower ones are not until top empties."""
    for order in (
        AUGURS_PILE_ORDER,
        CLASHES_PILE_ORDER,
        FORTS_PILE_ORDER,
        ODYSSEYS_PILE_ORDER,
        TOWNSFOLK_PILE_ORDER,
    ):
        state, _ = _setup_state(order[0])
        top = get_card(order[0])
        assert top.may_be_bought(state)
        for lower in order[1:]:
            assert not get_card(lower).may_be_bought(state)


def test_top_drained_exposes_next():
    state, _ = _setup_state("Town Crier")
    state.supply["Town Crier"] = 0
    blacksmith = get_card("Blacksmith")
    assert blacksmith.may_be_bought(state)


def test_townsfolk_grant_favor():
    for name in TOWNSFOLK_PILE_ORDER:
        state, player = _setup_state("Town Crier")
        card = get_card(name)
        player.in_play.append(card)
        before = player.favors
        # Skip Elder which expects an action in hand; stub a no-op hand.
        if name == "Elder":
            card.play_effect(state)
        else:
            card.on_play(state)
        assert player.favors >= before + 1


def test_clashes_grant_favor():
    for name in CLASHES_PILE_ORDER:
        state, player = _setup_state("Battle Plan")
        card = get_card(name)
        if not card.is_action:
            # Territory is a Victory; doesn't fire on_play.
            continue
        player.in_play.append(card)
        before = player.favors
        if name == "Battle Plan":
            # +1 Card requires deck contents — skip the +1 Card draw.
            card.play_effect(state)
        else:
            card.play_effect(state)
        assert player.favors >= before + 1


def test_distant_shore_gains_two_estates_on_gain():
    state, player = _setup_state("Old Map")
    state.supply["Estate"] = 8
    distant = get_card("Distant Shore")
    state.gain_card(player, distant)
    estates_in_discard = sum(1 for c in player.discard if c.name == "Estate")
    assert estates_in_discard == 2


def test_territory_gains_gold_per_empty_pile():
    state, player = _setup_state("Battle Plan")
    state.supply["Gold"] = 5
    state.supply["Workshop"] = 0  # one empty pile
    state.supply["Smithy"] = 0  # another empty pile
    territory = get_card("Territory")
    state.gain_card(player, territory)
    golds = sum(1 for c in player.discard if c.name == "Gold")
    assert golds == state.empty_piles or golds >= 2


def test_old_map_discards_and_redraws():
    state, player = _setup_state("Old Map")
    player.deck = [get_card("Copper"), get_card("Silver"), get_card("Gold")]
    player.hand = [get_card("Estate")]

    class DiscardAI(DummyAI):
        def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
            estates = [c for c in choices if c.name == "Estate"]
            return estates[:count]

    player.ai = DiscardAI()
    old_map = get_card("Old Map")
    player.in_play.append(old_map)
    old_map.on_play(state)
    # +1 Card from stats, then discard 1, +1 Card from play_effect.
    assert any(c.name == "Estate" for c in player.discard)
    assert len(player.hand) >= 1
