"""Tests for newly implemented cards: Harbinger, Astrolabe, Imperial Envoy,
Treasury, Cargo Ship, Pickaxe, Graverobber, Joust, Road Network, Way of the Mouse."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.projects.road_network import RoadNetwork
from dominion.ways.mouse import WayOfTheMouse
from tests.utils import ChooseFirstActionAI, DummyAI


class GainFirstBuyAI(ChooseFirstActionAI):
    """AI that picks the first available option in buy/gain choices."""

    def choose_buy(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_card_to_trash(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_card_to_topdeck_from_discard(self, state, player, choices):
        if not choices:
            return None
        return max(choices, key=lambda c: (c.cost.coins, c.name))

    def choose_graverobber_mode(self, state, player, options):
        return options[0] if options else "gain_from_trash"

    def should_joust_province(self, state, player):
        return True

    def should_set_aside_cargo_ship(self, state, player, gained_card):
        return True

    def should_topdeck_treasury(self, state, player):
        return True

    def choose_treasure(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None


class NoTopdeckTreasuryAI(GainFirstBuyAI):
    def should_topdeck_treasury(self, state, player):
        return False


class NoJoustAI(GainFirstBuyAI):
    def should_joust_province(self, state, player):
        return False


class UpgradeGraverobberAI(GainFirstBuyAI):
    def choose_graverobber_mode(self, state, player, options):
        if "upgrade" in options:
            return "upgrade"
        return options[0]


def _setup(ai, kingdom_cards=None):
    if kingdom_cards is None:
        kingdom_cards = [get_card("Village")]
    state = GameState(players=[])
    state.initialize_game([ai], kingdom_cards)
    player = state.players[0]
    player.hand = []
    player.deck = []
    player.discard = []
    player.in_play = []
    player.actions = 1
    player.buys = 1
    player.coins = 0
    player.actions_this_turn = 0
    player.actions_played = 0
    return state, player


# --- Harbinger ---

def test_harbinger_topdecks_from_discard():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    harbinger = get_card("Harbinger")
    silver = get_card("Silver")
    copper = get_card("Copper")
    player.hand = [harbinger]
    player.deck = [copper]
    player.discard = [silver]

    player.hand.remove(harbinger)
    player.in_play.append(harbinger)
    harbinger.on_play(state)

    assert silver in player.deck
    assert silver not in player.discard
    assert len(player.hand) == 1  # drew copper


def test_harbinger_empty_discard():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    harbinger = get_card("Harbinger")
    copper = get_card("Copper")
    player.hand = [harbinger]
    player.deck = [copper]
    player.discard = []

    player.hand.remove(harbinger)
    player.in_play.append(harbinger)
    harbinger.on_play(state)

    assert len(player.hand) == 1  # drew copper
    assert player.discard == []


# --- Astrolabe ---

def test_astrolabe_provides_coins_and_buys():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    astrolabe = get_card("Astrolabe")
    player.hand = [astrolabe]
    player.coins = 0
    player.buys = 0

    player.hand.remove(astrolabe)
    player.in_play.append(astrolabe)
    astrolabe.on_play(state)

    assert player.coins == 1
    assert player.buys == 1
    assert astrolabe in player.duration


def test_astrolabe_duration_effect():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    astrolabe = get_card("Astrolabe")
    player.duration = [astrolabe]
    astrolabe.duration_persistent = True
    player.coins = 0
    player.buys = 0

    astrolabe.on_duration(state)

    assert player.coins == 1
    assert player.buys == 1
    assert astrolabe.duration_persistent is False


# --- Imperial Envoy ---

def test_imperial_envoy_draws_five_adds_debt():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    envoy = get_card("Imperial Envoy")
    player.hand = [envoy]
    player.deck = [get_card("Copper") for _ in range(5)]
    player.debt = 0
    player.buys = 0

    player.hand.remove(envoy)
    player.in_play.append(envoy)
    envoy.on_play(state)

    assert len(player.hand) == 5
    assert player.buys == 1
    assert player.debt == 2


# --- Treasury ---

def test_treasury_topdecks_when_no_victory_gained():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    treasury = get_card("Treasury")
    player.in_play = [treasury]
    player.gained_victory_this_buy_phase = False

    treasury.on_buy_phase_end(state)

    assert treasury in player.deck
    assert treasury not in player.in_play


def test_treasury_stays_when_victory_gained():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    treasury = get_card("Treasury")
    player.in_play = [treasury]
    player.gained_victory_this_buy_phase = True

    treasury.on_buy_phase_end(state)

    assert treasury in player.in_play
    assert treasury not in player.deck


def test_treasury_stays_when_ai_declines():
    ai = NoTopdeckTreasuryAI()
    state, player = _setup(ai)
    treasury = get_card("Treasury")
    player.in_play = [treasury]
    player.gained_victory_this_buy_phase = False

    treasury.on_buy_phase_end(state)

    assert treasury in player.in_play


# --- Cargo Ship ---

def test_cargo_ship_sets_aside_gained_card():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    cargo_ship = get_card("Cargo Ship")
    player.hand = [cargo_ship]
    player.coins = 0

    player.hand.remove(cargo_ship)
    player.in_play.append(cargo_ship)
    cargo_ship.on_play(state)

    assert player.coins == 2
    assert cargo_ship.waiting_for_gain is True

    silver = get_card("Silver")
    state.supply["Silver"] = 10
    state.supply["Silver"] -= 1
    gained = state.gain_card(player, silver)

    assert cargo_ship.set_aside is gained
    assert cargo_ship.waiting_for_gain is False
    assert cargo_ship in player.duration


def test_cargo_ship_duration_returns_card():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    cargo_ship = get_card("Cargo Ship")
    silver = get_card("Silver")
    cargo_ship.set_aside = silver
    cargo_ship.duration_persistent = True
    player.duration = [cargo_ship]
    player.hand = []

    cargo_ship.on_duration(state)

    assert silver in player.hand
    assert cargo_ship.set_aside is None


# --- Pickaxe ---

def test_pickaxe_trashes_and_gains_loot():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    pickaxe = get_card("Pickaxe")
    silver = get_card("Silver")
    player.hand = [pickaxe, silver]
    player.coins = 0

    player.hand.remove(pickaxe)
    player.in_play.append(pickaxe)

    import random
    random.seed(42)
    pickaxe.on_play(state)

    assert player.coins == 1
    assert silver in state.trash
    # Silver costs $3, so a loot should be gained to hand
    loot_in_hand = [c for c in player.hand if c.cost.coins == 7]
    assert len(loot_in_hand) >= 1


def test_pickaxe_no_loot_for_cheap_trash():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    pickaxe = get_card("Pickaxe")
    copper = get_card("Copper")
    player.hand = [pickaxe, copper]
    player.coins = 0
    hand_count_before = len(player.hand) - 1  # minus pickaxe

    player.hand.remove(pickaxe)
    player.in_play.append(pickaxe)
    pickaxe.on_play(state)

    assert copper in state.trash
    # Copper costs $0, no loot gained
    loot_in_hand = [c for c in player.hand if c.cost.coins == 7]
    assert len(loot_in_hand) == 0


# --- Graverobber ---

def test_graverobber_gain_from_trash():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    graverobber = get_card("Graverobber")
    silver = get_card("Silver")
    state.trash = [silver]
    player.hand = [graverobber]

    player.hand.remove(graverobber)
    player.in_play.append(graverobber)
    graverobber.on_play(state)

    assert silver not in state.trash
    assert silver in player.deck


def test_graverobber_upgrade():
    ai = UpgradeGraverobberAI()
    state, player = _setup(ai)
    graverobber = get_card("Graverobber")
    village = get_card("Village")
    player.hand = [graverobber, village]
    state.supply["Gold"] = 10

    player.hand.remove(graverobber)
    player.in_play.append(graverobber)
    graverobber.on_play(state)

    assert village in state.trash
    # Village costs $3, can gain up to $6
    gained = [c for c in player.discard + list(player.deck) if c.name != "Graverobber"]
    assert len(gained) >= 1


# --- Joust ---

def test_joust_sets_aside_province_gains_reward():
    ai = GainFirstBuyAI()
    state, player = _setup(ai, [get_card("Joust")])
    joust = get_card("Joust")
    province = get_card("Province")
    player.hand = [joust, province]
    player.deck = [get_card("Copper")]

    player.hand.remove(joust)
    player.in_play.append(joust)
    joust.on_play(state)

    # Province should be set aside
    assert joust.province_set_aside is province
    assert province not in player.hand
    # +1 card, +1 action, +$1 from stats
    assert player.coins == 1
    # A reward should have been gained to hand
    reward_names = {"Coronet", "Demesne", "Housecarl", "Huge Turnip", "Renown"}
    rewards_in_hand = [c for c in player.hand if c.name in reward_names]
    assert len(rewards_in_hand) >= 1


def test_joust_returns_province_on_cleanup():
    ai = GainFirstBuyAI()
    state, player = _setup(ai, [get_card("Joust")])
    joust = get_card("Joust")
    province = get_card("Province")
    joust.province_set_aside = province

    joust.on_cleanup_return_province(player)

    assert province in player.hand
    assert joust.province_set_aside is None


def test_joust_without_province():
    ai = GainFirstBuyAI()
    state, player = _setup(ai, [get_card("Joust")])
    joust = get_card("Joust")
    player.hand = [joust]
    player.deck = [get_card("Copper")]

    player.hand.remove(joust)
    player.in_play.append(joust)
    joust.on_play(state)

    assert joust.province_set_aside is None


def test_joust_decline_province():
    ai = NoJoustAI()
    state, player = _setup(ai, [get_card("Joust")])
    joust = get_card("Joust")
    province = get_card("Province")
    player.hand = [joust, province]
    player.deck = [get_card("Copper")]

    player.hand.remove(joust)
    player.in_play.append(joust)
    joust.on_play(state)

    assert joust.province_set_aside is None
    assert province in player.hand


# --- Road Network ---

def test_road_network_draws_on_opponent_victory_gain():
    ai = GainFirstBuyAI()
    ai2 = DummyAI()
    state = GameState(players=[])
    state.initialize_game([ai, ai2], [get_card("Village")])
    p1 = state.players[0]
    p2 = state.players[1]

    road_network = RoadNetwork()
    p1.projects.append(road_network)

    p1.hand = []
    p1.deck = [get_card("Silver"), get_card("Gold")]
    p2.hand = []
    p2.deck = []

    estate = get_card("Estate")
    state.supply["Estate"] = 10
    state.supply["Estate"] -= 1
    state.gain_card(p2, estate)

    assert len(p1.hand) == 1  # drew 1 card from Road Network


def test_road_network_no_draw_on_nonvictory_gain():
    ai = GainFirstBuyAI()
    ai2 = DummyAI()
    state = GameState(players=[])
    state.initialize_game([ai, ai2], [get_card("Village")])
    p1 = state.players[0]
    p2 = state.players[1]

    road_network = RoadNetwork()
    p1.projects.append(road_network)

    p1.hand = []
    p1.deck = [get_card("Silver")]
    p2.hand = []
    p2.deck = []

    silver = get_card("Silver")
    state.supply["Silver"] -= 1
    state.gain_card(p2, silver)

    assert len(p1.hand) == 0  # no draw for non-victory


# --- Way of the Mouse ---

def test_way_of_the_mouse_applies_set_aside_effect():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    way = WayOfTheMouse(set_aside_card_name="Village")

    # Village gives +1 Card, +2 Actions
    village_card = get_card("Village")
    player.deck = [get_card("Copper"), get_card("Silver")]
    player.actions = 0
    player.hand = []

    dummy_action = get_card("Smithy")
    player.in_play.append(dummy_action)

    way.apply(state, dummy_action)

    # Village effect: +1 Card, +2 Actions
    assert player.actions == 2
    assert len(player.hand) == 1


def test_way_of_the_mouse_with_smithy_set_aside():
    ai = GainFirstBuyAI()
    state, player = _setup(ai)
    way = WayOfTheMouse(set_aside_card_name="Smithy")

    player.deck = [get_card("Copper") for _ in range(5)]
    player.actions = 0
    player.hand = []

    dummy_action = get_card("Village")
    player.in_play.append(dummy_action)

    way.apply(state, dummy_action)

    # Smithy effect: +3 Cards
    assert len(player.hand) == 3
