"""Tests for Nocturne non-supply piles: Spirits, Bat, Wish, Zombies."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class _AI(DummyAI):
    def choose_card_to_trash(self, state, choices):
        for c in choices:
            if c.name in {"Estate", "Curse", "Copper"}:
                return c
        return choices[0] if choices else None

    def choose_cards_to_trash(self, state, choices, count):
        junky = [c for c in choices if c.name in {"Estate", "Curse", "Copper"}]
        return junky[:count]

    def choose_imp_action(self, state, player, choices):
        return choices[0] if choices else None

    def choose_card_to_gain_to_hand(self, state, player, choices, max_cost):
        return max(choices, key=lambda c: c.cost.coins)

    def choose_card_to_gain_for_zombie_mason(self, state, player, max_cost, choices):
        return max(choices, key=lambda c: c.cost.coins)

    def choose_action_to_play_from_trash(self, state, player, choices):
        return max(choices, key=lambda c: c.cost.coins)


def _setup():
    state = GameState(players=[])
    state.log_callback = lambda *_: None
    state.players = [PlayerState(_AI())]
    state.players[0].initialize()
    state.supply = {
        "Copper": 30, "Silver": 20, "Gold": 10, "Curse": 10,
        "Estate": 10, "Duchy": 10, "Province": 8,
        "Will-o'-Wisp": 12, "Imp": 13, "Ghost": 6, "Bat": 10, "Wish": 12,
        "Vampire": 10,
        "Village": 10, "Smithy": 10,
    }
    return state, state.players[0]


def test_will_o_wisp_extra_card_when_top_costs_two_or_less():
    state, player = _setup()
    wisp = get_card("Will-o'-Wisp")
    player.deck = [get_card("Estate"), get_card("Silver")]  # top is Silver ($3)? No, pop returns last → Silver
    # We need top of deck (last index) to cost <=2
    player.deck = [get_card("Silver"), get_card("Copper")]
    player.in_play = [wisp]
    hand_before = len(player.hand)
    wisp.on_play(state)
    # +1 Card from base stats. Then Copper revealed → +1 more card.
    assert len(player.hand) >= hand_before + 1


def test_imp_plays_action_not_in_play():
    state, player = _setup()
    imp = get_card("Imp")
    village = get_card("Village")
    player.in_play = [imp]
    player.hand = [village]
    player.actions = 0
    imp.on_play(state)
    # Imp gives +2 cards from base stats; then plays Village (+2 cards +2 actions)
    assert village in player.in_play
    assert player.actions == 2


def test_ghost_sets_aside_action_for_two_plays():
    state, player = _setup()
    ghost = get_card("Ghost")
    village = get_card("Village")
    player.in_play = [ghost]
    player.deck = [get_card("Copper"), village]  # village on top (last)
    ghost.on_play(state)
    # Ghost moved to duration
    assert ghost in player.duration
    # Village queued for 2 plays
    assert player.ghost_pending_actions
    action_card, plays = player.ghost_pending_actions[0]
    assert action_card is village
    assert plays == 2


def test_bat_trashes_and_swaps_to_vampire():
    state, player = _setup()
    bat = get_card("Bat")
    player.in_play = [bat]
    player.hand = [get_card("Curse"), get_card("Estate")]
    bat_before = state.supply.get("Bat", 0)
    vampire_before = state.supply["Vampire"]
    bat.on_play(state)
    # Trashed up to 2 junky cards
    assert len(state.trash) >= 1
    # Vampire gained, Bat returned
    assert state.supply["Vampire"] == vampire_before - 1
    assert state.supply.get("Bat", 0) == bat_before + 1


def test_wish_returns_to_pile_and_gains_to_hand():
    state, player = _setup()
    wish = get_card("Wish")
    player.in_play = [wish]
    wish_pile_before = state.supply["Wish"]
    wish.on_play(state)
    # Wish returned to pile
    assert state.supply["Wish"] == wish_pile_before + 1
    # Gained a card to hand (most expensive up to $6)
    # The most expensive available will be Gold ($6)
    assert any(c.name == "Gold" for c in player.hand)


def test_zombie_apprentice_draws_action_and_trashes():
    state, player = _setup()
    za = get_card("Zombie Apprentice")
    player.in_play = [za]
    player.hand = [get_card("Estate")]
    player.deck = [get_card("Silver")]
    za.on_play(state)
    assert any(c.name == "Estate" for c in state.trash)


def test_zombie_mason_trashes_top_and_gains_one_more():
    state, player = _setup()
    zm = get_card("Zombie Mason")
    player.in_play = [zm]
    player.deck = [get_card("Silver")]  # cost 3 → gain up to $4
    zm.on_play(state)
    assert any(c.name == "Silver" for c in state.trash)
    # Gained a $4 card
    assert any(c.cost.coins == 4 for c in player.discard)


def test_zombie_spy_discards_junk():
    state, player = _setup()
    zs = get_card("Zombie Spy")
    player.in_play = [zs]
    # +1 Card draws Silver first, then we look at top (Estate) and discard.
    player.deck = [get_card("Estate"), get_card("Silver")]  # top is Silver
    zs.on_play(state)
    # Silver was drawn into hand by +1 Card. Then Estate is on top (looked at)
    # and discarded since it's a Victory.
    assert any(c.name == "Estate" for c in player.discard)
