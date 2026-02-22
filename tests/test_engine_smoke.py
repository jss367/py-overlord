import random
import types

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


# ---- Stub AI ---------------------------------------------------------------


class GreedyAI:
    """
    Simple AI:
      - Action phase: never plays actions (keeps tests deterministic).
      - Treasure phase: plays all treasures.
      - Buy phase: buys the most expensive affordable Victory, else treasure, else None.
      - Watchtower: always "topdeck".
      - Trader: always reveal to convert gains.
      - Moat/Insignia/etc. hooks default to False.
    """

    def __init__(self, name="Greedy"):
        self.name = name
        self.strategy = types.SimpleNamespace(name="Greedy")

    def choose_action(self, gs, options):
        return None

    def choose_way(self, gs, action_card, options):
        return None

    def choose_treasure(self, gs, options):
        # options include [None]
        treasures = [c for c in options if c is not None]
        return treasures[0] if treasures else None

    def choose_buy(self, gs, options):
        # options include [None], events, projects; we only buy supply cards here
        cards = [
            c
            for c in options
            if c is not None and not getattr(c, "is_event", False) and not getattr(c, "is_project", False)
        ]
        if not cards:
            return None
        # prefer Province > Duchy > Estate > Gold > Silver > Copper by cost then name
        cards.sort(key=lambda c: (c.cost.coins, c.name))
        return cards[-1]

    def choose_watchtower_reaction(self, gs, player, gained_card):
        return "topdeck"

    def should_topdeck_with_royal_seal(self, gs, player, gained_card):
        return False

    def should_topdeck_with_insignia(self, gs, player, gained_card):
        return False

    def should_reveal_trader(self, gs, player, original_card, to_deck=False):
        return True

    def should_reveal_moat(self, gs, player):
        return False

    def choose_treasures_to_set_aside_with_trickster(self, gs, player, treasures, max_count):
        return []


# ---- Tests -----------------------------------------------------------------


def make_game(n_players=2, kingdom=None, seed=0):
    random.seed(seed)
    ais = [GreedyAI(f"P{i+1}") for i in range(n_players)]
    gs = GameState(players=[])  # players filled in initialize_game
    kingdom = kingdom or []
    kingdom_cards = [get_card(name) for name in kingdom] if kingdom else []
    gs.initialize_game(ais, kingdom_cards=kingdom_cards, use_shelters=False)
    return gs


def test_initialization_and_starting_hands():
    gs = make_game()
    # 2 players, each should have 5 cards in hand post-initialize
    assert len(gs.players) == 2
    assert all(len(p.hand) == 5 for p in gs.players)
    # Copper supply reduced by 7 per player from starting_supply
    # Our Copper starting_supply is 60; 2 players remove 14 for decks
    assert gs.supply["Copper"] == 60 - (7 * 2)


def test_treasure_play_and_buy_estate_when_affordable():
    gs = make_game()
    p = gs.current_player
    # Force a deterministic starting hand: 5 Coppers to guarantee 5 coins
    p.hand = [get_card("Copper") for _ in range(5)]
    p.deck = []  # empty deck to keep things simple
    gs.handle_start_phase()  # moves to action (no durations)
    gs.handle_action_phase()  # does nothing (Greedy doesn't play actions)
    gs.handle_treasure_phase()  # plays all 5 Coppers
    assert p.coins == 5
    pre_estate = gs.supply["Estate"]
    gs.handle_buy_phase()  # Greedy buys Duchy (cost 5) rather than Estate
    assert gs.supply["Duchy"] == pre_estate - 1 + (
        gs.supply["Estate"] - gs.supply["Estate"]
    )  # sanity; main check below
    assert "Duchy" in p.bought_this_turn
    # Duchy gained to discard by default
    assert any(c.name == "Duchy" for c in p.discard)


def test_gamestate_end_on_province_depletion():
    gs = make_game()
    gs.supply["Province"] = 0
    assert gs.is_game_over() is True


def test_watchtower_topdecks_gained_card():
    gs = make_game(kingdom=["Watchtower"])
    p = gs.current_player
    # Put Watchtower in hand and enough money to buy Estate
    p.hand = [get_card("Watchtower")] + [get_card("Silver")]
    p.coins = 3  # enough for Estate(2)
    gs.phase = "buy"
    pre_estate = gs.supply["Estate"]
    choice = get_card("Estate")
    # Simulate buying Estate
    gs.supply["Estate"] -= 1
    gained = gs.gain_card(p, choice)
    # Because AI always chooses 'topdeck' for Watchtower, the gained card should be in deck top, not discard
    assert p.deck and p.deck[-1].name == "Estate" or p.deck[0].name == "Estate"
    assert gs.supply["Estate"] == pre_estate - 1  # supply decremented once


def test_trader_replaces_gain_with_silver():
    gs = make_game(kingdom=["Trader"])
    p = gs.current_player
    p.hand = [get_card("Trader")]
    gs.phase = "buy"
    pre_estate = gs.supply["Estate"]
    pre_silver = gs.supply["Silver"]
    gs.supply["Estate"] -= 1
    gained = gs.gain_card(p, get_card("Estate"))
    # Trader should have replaced the gain with Silver
    assert any(c.name == "Silver" for c in p.discard + p.deck + p.hand)
    assert gs.supply["Silver"] == pre_silver - 1
    # Estate supply should be restored because original gain was replaced
    assert gs.supply["Estate"] == pre_estate


def test_scheme_topdecks_best_action_on_cleanup():
    gs = make_game(kingdom=["Scheme", "Village"])
    p = gs.current_player
    # Put Scheme and Village into in_play so cleanup tries to topdeck an action
    p.in_play = [get_card("Scheme"), get_card("Village")]
    p.hand = []
    p.duration = []
    p.multiplied_durations = []
    # Ensure discard starts empty for clarity
    p.discard = []
    gs.phase = "cleanup"
    gs.handle_cleanup_phase()
    # Village should be topdecked (end or start depending on insert) rather than discarded
    assert any(c.name == "Village" for c in p.deck)
    assert not any(c.name == "Village" for c in p.discard)
