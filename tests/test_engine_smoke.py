import random
import sys
import types
from types import SimpleNamespace

# ---- Minimal fake "dominion" API for the engine to call --------------------


class Cost:
    def __init__(self, coins=0, potions=0, debt=0):
        self.coins = coins
        self.potions = potions
        self.debt = debt


class Stats:
    def __init__(self, cards=0, actions=0):
        self.cards = cards
        self.actions = actions


class FakeCard:
    """
    Minimal card stub that covers what GameState/PlayerState read/call.
    """

    is_action = False
    is_treasure = False
    is_victory = False
    is_event = False
    is_project = False
    duration_persistent = False
    partner_card_name = None

    def __init__(
        self,
        name,
        cost,
        *,
        treasure_coins=0,
        victory_points=0,
        is_action=False,
        is_treasure=False,
        is_victory=False,
        is_duration=False,
        split_partner=None,
    ):
        self.name = name
        self.cost = Cost(**cost) if isinstance(cost, dict) else cost
        self._treasure_coins = treasure_coins
        self._victory_points = victory_points
        self.is_action = is_action
        self.is_treasure = is_treasure
        self.is_victory = is_victory
        self.is_duration = is_duration
        self.stats = Stats(cards=0, actions=0)  # for Scheme heuristic
        if split_partner:

            # flag that engine checks
            self.__class__ = type("SplitPileCard", (self.__class__, SplitPileMixin), {})
            self.partner_card_name = split_partner

    # --- Hooks the engine might call
    def starting_supply(self, gs):
        # generous piles so tests don't run out
        if self.name in {"Estate", "Duchy", "Province"}:
            return 12
        if self.name in {"Silver"}:
            return 40
        if self.name in {"Gold"}:
            return 30
        if self.name in {"Curse"}:
            return 30
        if self.name in {"Copper"}:
            return 60
        return 10

    def may_be_bought(self, gs, player=None):
        return True

    def get_victory_points(self, player_state):
        return self._victory_points

    def on_play(self, gs):
        # Treasures add coins; actions do nothing by default
        if self.is_treasure:
            p = gs.current_player
            p.coins += self._treasure_coins

    def on_buy(self, *args, **kwargs):
        pass

    def on_gain(self, gs, player):
        pass

    def on_trash(self, gs, player):
        pass

    def __repr__(self):
        return f"<Card {self.name}>"


class SplitPileMixin:
    pass


# Registry
_REGISTRY = {}


def reg(card: FakeCard):
    _REGISTRY[card.name] = card


def get_card(name):
    # Return a fresh instance with same attributes (engine mutates instances)
    base = _REGISTRY[name]
    return FakeCard(
        base.name,
        {"coins": base.cost.coins, "potions": base.cost.potions, "debt": base.cost.debt},
        treasure_coins=base._treasure_coins,
        victory_points=base._victory_points,
        is_action=base.is_action,
        is_treasure=base.is_treasure,
        is_victory=base.is_victory,
        is_duration=getattr(base, "is_duration", False),
        split_partner=getattr(base, "partner_card_name", None),
    )


def get_all_card_names():
    return list(_REGISTRY.keys())


# Basic cards
reg(FakeCard("Copper", {"coins": 0}, treasure_coins=1, is_treasure=True))
reg(FakeCard("Silver", {"coins": 3}, treasure_coins=2, is_treasure=True))
reg(FakeCard("Gold", {"coins": 6}, treasure_coins=3, is_treasure=True))
reg(FakeCard("Estate", {"coins": 2}, victory_points=1, is_victory=True))
reg(FakeCard("Duchy", {"coins": 5}, victory_points=3, is_victory=True))
reg(FakeCard("Province", {"coins": 8}, victory_points=6, is_victory=True))
reg(FakeCard("Curse", {"coins": 0}, victory_points=-1))

# Reaction/utility cards we need for tests
# Watchtower: we only need it recognizable by name; reaction is driven via AI hook.
reg(FakeCard("Watchtower", {"coins": 3}, is_action=True))
# Trader: recognizable by name; exchange is implemented in engine via name check and AI hook.
reg(FakeCard("Trader", {"coins": 4}, is_action=True))
# Scheme: recognizable by name for cleanup topdeck heuristic.
reg(FakeCard("Scheme", {"coins": 3}, is_action=True))
# A cheap action to be topdecked by Scheme
act = FakeCard("Village", {"coins": 3}, is_action=True)
act.stats = Stats(cards=1, actions=2)
reg(act)

# ---- Install fakes into the import paths your engine expects ----------------
# We simulate the package layout the engine imports from.

dominion = types.ModuleType("dominion")
cards_pkg = types.ModuleType("dominion.cards")
base_card_mod = types.ModuleType("dominion.cards.base_card")
registry_mod = types.ModuleType("dominion.cards.registry")
split_mod = types.ModuleType("dominion.cards.split_pile")
game_pkg = types.ModuleType("dominion.game")

base_card_mod.Card = FakeCard
registry_mod.get_card = get_card
registry_mod.get_all_card_names = get_all_card_names
split_mod.SplitPileMixin = SplitPileMixin

sys.modules["dominion"] = dominion
sys.modules["dominion.cards"] = cards_pkg
sys.modules["dominion.cards.base_card"] = base_card_mod
sys.modules["dominion.cards.registry"] = registry_mod
sys.modules["dominion.cards.split_pile"] = split_mod
sys.modules["dominion.game"] = game_pkg

from dominion.game.game_state import GameState  # your source file

# Now import the engine code under test
from dominion.game.player_state import PlayerState  # your source file

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
    gs.initialize_game(ais, kingdom_cards=kingdom, use_shelters=False)
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
    gs = make_game()
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
    gs = make_game()
    p = gs.current_player
    p.hand = [get_card("Trader")]
    gs.phase = "buy"
    pre_estate = gs.supply["Estate"]
    pre_silver = gs.supply["Silver"]
    gained = gs.gain_card(p, get_card("Estate"))
    # Trader should have replaced the gain with Silver
    assert any(c.name == "Silver" for c in p.discard + p.deck + p.hand)
    assert gs.supply["Silver"] == pre_silver - 1
    # Estate supply should be restored because original gain was replaced
    assert gs.supply["Estate"] == pre_estate


def test_scheme_topdecks_best_action_on_cleanup():
    gs = make_game()
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
