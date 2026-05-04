"""Tests for the Plunder Events (15 total; Looting tested elsewhere)."""

import random

import pytest

from dominion.cards.registry import get_card
from dominion.events.registry import EVENT_TYPES, get_event
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


class _NullAI:
    name = "null"

    def __init__(self):
        self.strategy = None

    def choose_action(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_treasure(self, *args, **kwargs):
        return None

    def choose_buy(self, *args, **kwargs):
        return None

    def choose_card_to_trash(self, state, choices):
        for c in choices:
            if c is None:
                continue
            if getattr(c, "name", "") in ("Curse", "Estate"):
                return c
        return None

    def should_topdeck_with_insignia(self, *args, **kwargs):
        return False

    def should_topdeck_with_royal_seal(self, *args, **kwargs):
        return False

    def choose_watchtower_reaction(self, *args, **kwargs):
        return None

    def should_react_with_market_square(self, *args, **kwargs):
        return False

    def should_play_guard_dog(self, *args, **kwargs):
        return False

    def should_reveal_moat(self, *args, **kwargs):
        return True


def _make_state(num_players: int = 1) -> GameState:
    state = GameState(players=[])
    state.players = [PlayerState(_NullAI()) for _ in range(num_players)]
    for p in state.players:
        p.initialize()
    state.supply = {
        "Copper": 30,
        "Silver": 30,
        "Gold": 30,
        "Curse": 10,
        "Estate": 8,
        "Duchy": 8,
        "Province": 8,
        "Village": 10,
        "Smithy": 10,
        "Witch": 10,
        "Festival": 10,
        "Market": 10,
        "Wharf": 10,
    }
    return state


def test_all_15_plunder_events_registered():
    plunder_events = {
        "Bury", "Avoid", "Deliver", "Peril", "Rush", "Foray", "Launch",
        "Mirror", "Prepare", "Scrounge", "Maelstrom", "Invasion", "Prosper",
        "Looting",
    }
    for name in plunder_events:
        evt = get_event(name)
        assert evt.name == name


def test_bury_takes_card_from_discard_to_top():
    state = _make_state()
    player = state.current_player
    player.discard = [get_card("Copper"), get_card("Gold")]
    bury = get_event("Bury")
    pre_buys = player.buys
    bury.on_buy(state, player)
    assert player.buys == pre_buys + 1
    # Gold (more expensive) should be top of deck.
    assert player.deck[-1].name == "Gold"


def test_avoid_sets_avoid_pending():
    state = _make_state()
    player = state.current_player
    avoid = get_event("Avoid")
    avoid.on_buy(state, player)
    assert player.avoid_pending == 1


def test_avoid_keeps_three_on_top_at_shuffle():
    state = _make_state()
    player = state.current_player
    avoid = get_event("Avoid")
    avoid.on_buy(state, player)
    player.deck = []
    player.discard = [
        get_card("Copper"),
        get_card("Copper"),
        get_card("Silver"),
        get_card("Gold"),
    ]
    player.shuffle_discard_into_deck()
    # Last 3 of original discard were [Copper, Silver, Gold], topped on deck.
    top_three = [c.name for c in player.deck[-3:]]
    assert "Gold" in top_three
    assert "Silver" in top_three


def test_peril_trashes_action_and_gains_loot():
    state = _make_state()
    player = state.current_player
    player.hand = [get_card("Witch")]
    pre_discard = len(player.discard)
    peril = get_event("Peril")
    peril.on_buy(state, player)
    assert any(c.name == "Witch" for c in state.trash)
    # Loot in discard.
    assert len(player.discard) > pre_discard


def test_rush_doubles_next_action():
    state = _make_state()
    player = state.current_player
    rush = get_event("Rush")
    rush.on_buy(state, player)
    assert state.rush_pending.get(id(player)) == 1


def test_foray_discards_three_distinct_and_gains_loot():
    state = _make_state()
    player = state.current_player
    player.hand = [
        get_card("Copper"),
        get_card("Silver"),
        get_card("Gold"),
    ]
    pre_discard = len(player.discard)
    foray = get_event("Foray")
    foray.on_buy(state, player)
    # Hand emptied (3 distinct discarded), Loot gained.
    assert len(player.hand) == 0
    # Loot + 3 discarded → discard grew by 4.
    assert len(player.discard) >= pre_discard + 4


def test_launch_gives_card_action_buy_once_per_turn():
    state = _make_state()
    player = state.current_player
    player.deck = [get_card("Copper")]
    launch = get_event("Launch")
    pre_actions = player.actions
    pre_buys = player.buys
    pre_hand = len(player.hand)
    launch.on_buy(state, player)
    assert player.actions == pre_actions + 1
    assert player.buys == pre_buys + 1
    assert len(player.hand) == pre_hand + 1
    # Second time should be blocked.
    assert not launch.may_be_bought(state, player)


def test_mirror_pending_set():
    state = _make_state()
    player = state.current_player
    mirror = get_event("Mirror")
    mirror.on_buy(state, player)
    assert state.mirror_pending.get(id(player)) == 1


def test_mirror_doubles_action_gain():
    state = _make_state()
    player = state.current_player
    state.mirror_pending[id(player)] = 1
    pre_villages = sum(1 for c in player.discard if c.name == "Village")
    state.supply["Village"] -= 1
    state.gain_card(player, get_card("Village"))
    post_villages = sum(1 for c in player.discard if c.name == "Village")
    # Original gain + Mirror gain = 2 villages added to discard.
    assert post_villages >= pre_villages + 2


def test_prepare_sets_aside_and_plays_next_turn():
    state = _make_state()
    player = state.current_player
    player.hand = [get_card("Silver"), get_card("Gold")]
    prep = get_event("Prepare")
    prep.on_buy(state, player)
    # Cards are now on hasty_set_aside.
    assert len(state.hasty_set_aside.get(id(player), [])) == 2
    # Next turn plays them.
    state._handle_hasty_start_of_turn(player)
    assert sum(1 for c in player.in_play if c.is_treasure) == 2


def test_scrounge_trashes_estate_and_gains_card_up_to_5():
    state = _make_state()
    player = state.current_player
    player.hand = [get_card("Estate")]
    sc = get_event("Scrounge")
    sc.on_buy(state, player)
    assert any(c.name == "Estate" for c in state.trash)
    # A card up to $5 in discard.
    assert len(player.discard) >= 1


def test_maelstrom_trashes_three_from_hand_and_attacks():
    state = _make_state(num_players=2)
    me = state.players[0]
    foe = state.players[1]
    state.current_player_index = 0
    me.hand = [get_card("Curse"), get_card("Estate"), get_card("Copper")]
    foe.hand = [get_card("Copper") for _ in range(5)]
    pre_trash = len(state.trash)
    mael = get_event("Maelstrom")
    mael.on_buy(state, me)
    # Three from me trashed.
    assert len(state.trash) >= pre_trash + 3
    # Foe trashed one.
    foe_trashed = any(t.name in {"Copper"} for t in state.trash[pre_trash + 3:])
    assert foe_trashed


def test_invasion_gains_action_duchy_loot_silvers():
    state = _make_state()
    player = state.current_player
    pre_discard = len(player.discard)
    inv = get_event("Invasion")
    inv.on_buy(state, player)
    # Should have gained: Action, Duchy, Loot, 2 Silvers = 5 cards added.
    assert len(player.discard) >= pre_discard + 5
    assert any(c.name == "Duchy" for c in player.discard)
    assert sum(1 for c in player.discard if c.name == "Silver") >= 2


def test_prosper_gains_one_of_each_loot():
    from dominion.cards.plunder import LOOT_CARD_NAMES

    state = _make_state()
    player = state.current_player
    pre_discard = len(player.discard)
    pr = get_event("Prosper")
    pr.on_buy(state, player)
    # All 15 Loots in discard (Doubloons may have added an extra Gold).
    discard_names = {c.name for c in player.discard}
    for name in LOOT_CARD_NAMES:
        assert name in discard_names


def test_launch_lockout_clears_at_turn_start():
    """Regression for PR #193 review: launch_used must reset each turn so
    Launch is once-per-turn rather than once-per-game."""
    state = _make_state(num_players=2)
    player = state.players[0]
    state.current_player_index = 0
    player.deck = [get_card("Copper")]
    launch = get_event("Launch")
    launch.on_buy(state, player)
    assert player.launch_used is True
    assert not launch.may_be_bought(state, player)
    # Cycle: end turn (player 0) → next player → back to player 0.
    state.current_player_index = 1
    state.handle_start_phase()
    state.current_player_index = 0
    state.handle_start_phase()
    # After our next turn-start, Launch should be buyable again.
    assert player.launch_used is False
    assert launch.may_be_bought(state, player)


def test_deliver_sets_aside_one_gain_and_returns_to_hand_next_turn():
    """Regression for PR #193 review: Deliver must set aside the next gained
    card (one gain) and return it to hand at start of next turn — it must
    not act as a broad topdeck redirect."""
    state = _make_state(num_players=2)
    player = state.players[0]
    state.current_player_index = 0
    deliver = get_event("Deliver")
    deliver.on_buy(state, player)
    # First gain: Silver should be set aside, not put in deck/discard.
    state.supply["Silver"] -= 1
    state.gain_card(player, get_card("Silver"))
    assert any(c.name == "Silver" for c in player.deliver_set_aside)
    assert not any(c.name == "Silver" for c in player.discard)
    assert not any(c.name == "Silver" for c in player.deck)
    # Second gain in same turn must NOT be redirected (only one Deliver buy).
    state.supply["Gold"] -= 1
    state.gain_card(player, get_card("Gold"))
    # Gold should land in discard normally (not on deliver_set_aside, not
    # forced to deck).
    assert any(c.name == "Gold" for c in player.discard)
    assert not any(c.name == "Gold" for c in player.deliver_set_aside)
    # Pending counter consumed.
    assert player.deliver_pending_count == 0
    # Cycle to next turn for player 0.
    state.current_player_index = 1
    state.handle_start_phase()
    state.current_player_index = 0
    state.handle_start_phase()
    # Set-aside Silver returned to hand.
    assert any(c.name == "Silver" for c in player.hand)
    assert player.deliver_set_aside == []
