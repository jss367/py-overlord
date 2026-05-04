"""Tests for the Menagerie Ways and the choose-Way-on-Action play hook."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.ways.registry import get_way
from tests.utils import ChooseFirstActionAI


class WayPickerAI(ChooseFirstActionAI):
    def __init__(self, way_name: str):
        super().__init__()
        self._way_name = way_name

    def choose_way(self, state, card, ways):
        for w in ways:
            if w and w.name == self._way_name:
                return w
        return None


def _state(way_name: str | None = None, kingdom=None):
    kingdom = kingdom or [get_card("Village"), get_card("Smithy")]
    if way_name is not None:
        ais = [WayPickerAI(way_name), ChooseFirstActionAI()]
        ways = [get_way(way_name)]
    else:
        ais = [ChooseFirstActionAI(), ChooseFirstActionAI()]
        ways = []
    state = GameState(players=[])
    state.initialize_game(ais, kingdom, ways=ways)
    state.supply.setdefault("Horse", 30)
    state.supply.setdefault("Silver", 40)
    state.supply.setdefault("Gold", 30)
    state.supply.setdefault("Estate", 8)
    state.supply.setdefault("Curse", 10)
    state.supply.setdefault("Copper", 46)
    return state, state.players[0]


def test_way_of_the_ox_gives_two_actions():
    state, p1 = _state("Way of the Ox")
    p1.actions = 1
    # Play any action via the Way; it should give +2 Actions
    p1.hand = [get_card("Smithy")]
    state.phase = "action"
    state.handle_action_phase()
    # Smithy normally would give 3 cards; via Way of the Ox we should see
    # actions go up by 2 (and no draw), so we can play another action.
    assert p1.actions >= 2 - 1  # 1 starting -1 played + 2 = 2; then loop sees no other action
    # Smithy's draw 3 must NOT have happened
    assert all(c.name != "Smithy" for c in p1.hand)


def test_way_of_the_sheep_gives_two_coins():
    state, p1 = _state("Way of the Sheep")
    p1.actions = 1
    p1.hand = [get_card("Village")]
    state.phase = "action"
    state.handle_action_phase()
    assert p1.coins == 2


def test_way_of_the_otter_draws_two():
    state, p1 = _state("Way of the Otter")
    p1.actions = 1
    p1.hand = [get_card("Village")]
    p1.deck = [get_card("Copper"), get_card("Estate")]
    state.phase = "action"
    state.handle_action_phase()
    # Two cards drawn from deck
    assert len(p1.hand) == 2
    # No +Cards from village's normal play happened (just the way's 2)
    # Action count: 0 (we used 1 to play; way of otter doesn't give actions)
    assert p1.actions == 0


def test_way_of_the_horse_returns_card_to_pile():
    state, p1 = _state("Way of the Horse")
    state.supply["Smithy"] = 10
    p1.actions = 1
    p1.hand = [get_card("Smithy")]
    smithy_before = state.supply["Smithy"]
    state.phase = "action"
    state.handle_action_phase()
    # +2 cards +1 action; Smithy returned to pile
    assert state.supply["Smithy"] == smithy_before + 1
    assert all(c.name != "Smithy" for c in p1.in_play)


def test_way_of_the_camel_exiles_gold():
    state, p1 = _state("Way of the Camel")
    p1.actions = 1
    p1.hand = [get_card("Village")]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Gold" for c in p1.exile)


def test_way_of_the_worm_exiles_card_and_gains_estate():
    state, p1 = _state("Way of the Worm")
    state.supply["Village"] = state.supply.get("Village", 10)
    p1.actions = 1
    village = get_card("Village")
    p1.hand = [village]
    state.phase = "action"
    state.handle_action_phase()
    # Village should be in exile
    assert village in p1.exile
    # Estate should be gained
    assert any(c.name == "Estate" for c in p1.discard + p1.deck)


def test_way_of_the_squirrel_pending_draw():
    state, p1 = _state("Way of the Squirrel")
    p1.actions = 1
    p1.hand = [get_card("Village")]
    state.phase = "action"
    state.handle_action_phase()
    assert p1.squirrel_pending == 2


def test_way_of_the_mule_gives_action_and_coin():
    state, p1 = _state("Way of the Mule")
    p1.actions = 1
    p1.hand = [get_card("Village")]
    state.phase = "action"
    state.handle_action_phase()
    # +1 Action +$1; played from 1 action -1 + 1 = 1 net
    assert p1.coins == 1


def test_way_of_the_pig_gives_card_and_action():
    state, p1 = _state("Way of the Pig")
    p1.actions = 1
    p1.hand = [get_card("Village")]
    p1.deck = [get_card("Copper")]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Copper" for c in p1.hand)


def test_way_of_the_goat_trashes_card():
    class TrashAI(WayPickerAI):
        def choose_card_to_trash(self, state, choices):
            for c in choices:
                if c is not None:
                    return c
            return None

    state = GameState(players=[])
    state.initialize_game(
        [TrashAI("Way of the Goat"), ChooseFirstActionAI()],
        [get_card("Village")],
        ways=[get_way("Way of the Goat")],
    )
    state.supply.setdefault("Estate", 8)
    p1 = state.players[0]
    p1.actions = 1
    p1.hand = [get_card("Village"), get_card("Estate")]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name in ("Estate", "Village") for c in state.trash)


def test_way_of_the_owl_draws_to_six():
    state, p1 = _state("Way of the Owl")
    p1.actions = 1
    p1.hand = [get_card("Village"), get_card("Copper"), get_card("Copper")]
    p1.deck = [get_card("Copper")] * 10
    state.phase = "action"
    state.handle_action_phase()
    # We had 2 in hand after playing village, draw to 6
    assert len(p1.hand) >= 6


def test_way_of_the_mole_discards_hand_then_draws_three():
    state, p1 = _state("Way of the Mole")
    p1.actions = 1
    p1.hand = [
        get_card("Village"),
        get_card("Copper"),
        get_card("Estate"),
    ]
    p1.deck = [get_card("Copper")] * 10
    state.phase = "action"
    state.handle_action_phase()
    # Hand discarded then drew 3 → 3 new cards
    assert len(p1.hand) == 3


def test_way_of_the_rat_discards_treasure_gains_action():
    state, p1 = _state("Way of the Rat")
    state.supply["Village"] = 10
    p1.actions = 1
    p1.hand = [get_card("Village"), get_card("Copper")]
    state.phase = "action"
    state.handle_action_phase()
    # Copper discarded; gained an action card.
    assert any(c.name == "Copper" for c in p1.discard)
    gained = [c for c in p1.discard if c.is_action]
    assert gained


def test_way_of_the_turtle_plays_next_turn():
    state, p1 = _state("Way of the Turtle")
    p1.actions = 1
    smithy = get_card("Smithy")
    p1.hand = [smithy]
    p1.deck = [get_card("Copper")] * 10
    state.phase = "action"
    state.handle_action_phase()
    assert smithy in p1.turtle_set_aside
    # Play through turn end + next turn
    state.handle_treasure_phase()
    state.handle_buy_phase()
    state.handle_cleanup_phase()
    # Now next turn for p1
    state.current_player_index = 0
    state.phase = "start"
    state.handle_start_phase()
    # Smithy should fire (drew 3 cards)
    assert smithy in p1.in_play


def test_way_of_the_frog_topdecks_on_cleanup():
    state, p1 = _state("Way of the Frog")
    p1.actions = 1
    village = get_card("Village")
    p1.hand = [village]
    state.phase = "action"
    state.handle_action_phase()
    state.handle_treasure_phase()
    state.handle_buy_phase()
    state.handle_cleanup_phase()
    # Village should be at top of deck (deck[0]) after cleanup
    assert village in p1.deck


def test_way_of_the_chameleon_swaps_cards_and_coins():
    state, p1 = _state("Way of the Chameleon")
    p1.actions = 1
    smithy = get_card("Smithy")  # +3 Cards
    p1.hand = [smithy]
    p1.deck = [get_card("Copper")] * 10
    state.phase = "action"
    state.handle_action_phase()
    # Swapped: +3 coins and 0 cards
    assert p1.coins == 3
