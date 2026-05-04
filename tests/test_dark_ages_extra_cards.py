"""Tests for Wandering Minstrel, Market Square, Feodum, Hunting Grounds, Samurai."""

from typing import Optional

from dominion.cards.base_card import Card
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import ChooseFirstActionAI, DummyAI


class GainFirstBuyAI(ChooseFirstActionAI):
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

    def choose_treasure(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None


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
    player.duration = []
    player.actions = 1
    player.buys = 1
    player.coins = 0
    return state, player


# --- Wandering Minstrel ---

def test_wandering_minstrel_cards_actions_and_topdeck():
    state, player = _setup(GainFirstBuyAI())
    minstrel = get_card("Wandering Minstrel")
    player.hand = [minstrel]
    player.deck = [get_card("Copper"), get_card("Estate"), get_card("Village"), get_card("Silver")]

    player.hand.remove(minstrel)
    player.in_play.append(minstrel)
    minstrel.on_play(state)

    # +1 Card, +2 Actions
    assert player.actions == 3
    # Drew Silver (top of deck pre-reveal)
    assert any(c.name == "Silver" for c in player.hand)
    # Revealed three: Village (action), Estate (victory), Copper (treasure).
    # Action goes back on top; the others are discarded.
    assert player.deck[-1].name == "Village"
    assert any(c.name == "Estate" for c in player.discard)
    assert any(c.name == "Copper" for c in player.discard)


class BadOrderAI(GainFirstBuyAI):
    """AI that returns a malformed topdeck order (duplicates an entry)."""

    def order_cards_for_topdeck(self, state, player, cards):
        if cards:
            return cards + [cards[0]]
        return list(cards)


def test_wandering_minstrel_rejects_malformed_topdeck_order():
    state, player = _setup(BadOrderAI())
    minstrel = get_card("Wandering Minstrel")
    village_a = get_card("Village")
    village_b = get_card("Village")
    estate = get_card("Estate")
    copper = get_card("Copper")
    player.hand = [minstrel]
    # Drawn first (top of deck), then 3 revealed (in pop order):
    # village_b (action), village_a (action), estate (victory).
    player.deck = [estate, village_a, village_b, copper]

    player.hand.remove(minstrel)
    player.in_play.append(minstrel)
    minstrel.on_play(state)

    # Two action cards were revealed; both should be on the deck exactly once
    # despite the AI trying to inject a duplicate.
    deck_villages = [c for c in player.deck if c.name == "Village"]
    assert len(deck_villages) == 2
    assert village_a in deck_villages and village_b in deck_villages
    # Estate (non-action) was discarded.
    assert estate in player.discard


def test_wandering_minstrel_with_short_deck():
    state, player = _setup(GainFirstBuyAI())
    minstrel = get_card("Wandering Minstrel")
    player.hand = [minstrel]
    # 1 card to draw, then nothing left to reveal
    player.deck = [get_card("Copper")]
    player.discard = []

    player.hand.remove(minstrel)
    player.in_play.append(minstrel)
    minstrel.on_play(state)

    # +1 Card brings Copper into hand. Deck/discard now empty for reveals.
    assert any(c.name == "Copper" for c in player.hand)
    assert player.actions == 3


# --- Market Square ---

def test_market_square_basic_play_stats():
    state, player = _setup(GainFirstBuyAI())
    square = get_card("Market Square")
    player.hand = [square]
    player.deck = [get_card("Copper")]

    player.hand.remove(square)
    player.in_play.append(square)
    square.on_play(state)

    # on_play applies card stats directly without deducting the action cost
    assert player.actions == 2  # 1 + 1
    assert player.buys == 2
    assert len(player.hand) == 1


def test_market_square_reaction_grants_gold_when_trashing():
    state, player = _setup(GainFirstBuyAI())
    square = get_card("Market Square")
    estate = get_card("Estate")
    player.hand = [square, estate]
    state.supply["Gold"] = 10

    # Player trashes Estate -> reaction triggers, discarding Market Square,
    # gaining a Gold.
    player.hand.remove(estate)
    state.trash_card(player, estate)

    assert estate in state.trash
    assert square not in player.hand
    assert square in player.discard
    assert any(c.name == "Gold" for c in player.discard)
    assert state.supply["Gold"] == 9


def test_market_square_reaction_skips_when_not_in_hand():
    state, player = _setup(GainFirstBuyAI())
    square = get_card("Market Square")
    estate = get_card("Estate")
    player.in_play = [square]  # Market Square in play, not hand
    player.hand = [estate]
    state.supply["Gold"] = 10

    player.hand.remove(estate)
    state.trash_card(player, estate)

    # No reaction since Market Square is not in hand.
    assert square in player.in_play
    assert state.supply["Gold"] == 10
    assert all(c.name != "Gold" for c in player.discard)


class DeclineSquareAI(GainFirstBuyAI):
    def should_react_with_market_square(self, state, player, trashed_card):
        return False


def test_market_square_reaction_can_decline():
    state, player = _setup(DeclineSquareAI())
    square = get_card("Market Square")
    estate = get_card("Estate")
    player.hand = [square, estate]
    state.supply["Gold"] = 10

    player.hand.remove(estate)
    state.trash_card(player, estate)

    assert square in player.hand
    assert state.supply["Gold"] == 10


# --- Feodum ---

def test_feodum_victory_points_scale_with_silvers():
    state, player = _setup(GainFirstBuyAI())
    feodum = get_card("Feodum")
    player.discard = [feodum]
    # 0 Silvers -> 0 VP
    assert feodum.get_victory_points(player) == 0

    player.discard.extend(get_card("Silver") for _ in range(2))
    assert feodum.get_victory_points(player) == 0

    player.discard.append(get_card("Silver"))  # 3 Silvers
    assert feodum.get_victory_points(player) == 1

    player.discard.extend(get_card("Silver") for _ in range(3))  # 6 Silvers
    assert feodum.get_victory_points(player) == 2


def test_feodum_on_trash_gains_three_silvers():
    state, player = _setup(GainFirstBuyAI())
    feodum = get_card("Feodum")
    player.hand = [feodum]
    state.supply["Silver"] = 10

    player.hand.remove(feodum)
    state.trash_card(player, feodum)

    assert feodum in state.trash
    silvers = sum(1 for c in player.discard if c.name == "Silver")
    assert silvers == 3
    assert state.supply["Silver"] == 7


def test_feodum_on_trash_respects_empty_supply():
    state, player = _setup(GainFirstBuyAI())
    feodum = get_card("Feodum")
    player.hand = [feodum]
    state.supply["Silver"] = 1

    player.hand.remove(feodum)
    state.trash_card(player, feodum)

    silvers = sum(1 for c in player.discard if c.name == "Silver")
    assert silvers == 1
    assert state.supply["Silver"] == 0


# --- Hunting Grounds ---

def test_hunting_grounds_draws_four():
    state, player = _setup(GainFirstBuyAI())
    grounds = get_card("Hunting Grounds")
    player.hand = [grounds]
    player.deck = [get_card("Copper") for _ in range(4)]

    player.hand.remove(grounds)
    player.in_play.append(grounds)
    grounds.on_play(state)

    assert len(player.hand) == 4


def test_hunting_grounds_on_trash_gains_duchy_when_chosen():
    state, player = _setup(GainFirstBuyAI())
    grounds = get_card("Hunting Grounds")
    state.supply["Duchy"] = 8
    state.supply["Estate"] = 8

    state.trash_card(player, grounds)

    assert grounds in state.trash
    assert any(c.name == "Duchy" for c in player.discard)
    assert state.supply["Duchy"] == 7


class EstatesGroundsAI(GainFirstBuyAI):
    def choose_hunting_grounds_reward(self, state, player):
        return "estates"


def test_hunting_grounds_on_trash_gains_three_estates_when_chosen():
    state, player = _setup(EstatesGroundsAI())
    grounds = get_card("Hunting Grounds")
    state.supply["Duchy"] = 8
    state.supply["Estate"] = 8

    state.trash_card(player, grounds)

    estates = sum(1 for c in player.discard if c.name == "Estate")
    assert estates == 3
    assert state.supply["Estate"] == 5
    assert state.supply["Duchy"] == 8


def test_hunting_grounds_falls_back_when_duchy_pile_empty():
    state, player = _setup(GainFirstBuyAI())
    grounds = get_card("Hunting Grounds")
    state.supply["Duchy"] = 0
    state.supply["Estate"] = 8

    state.trash_card(player, grounds)

    estates = sum(1 for c in player.discard if c.name == "Estate")
    assert estates == 3


# --- Samurai ---

def test_samurai_attacks_other_players_to_three_cards():
    ai1 = GainFirstBuyAI()
    ai2 = DummyAI()
    state = GameState(players=[])
    state.initialize_game([ai1, ai2], [get_card("Village")])
    attacker, victim = state.players

    samurai = get_card("Samurai")
    attacker.hand = [samurai]
    attacker.in_play = []
    attacker.duration = []

    victim.hand = [get_card("Copper") for _ in range(5)]

    attacker.hand.remove(samurai)
    attacker.in_play.append(samurai)
    samurai.on_play(state)

    assert len(victim.hand) == 3
    assert samurai in attacker.duration
    assert samurai.duration_persistent is True


def test_samurai_skips_attack_for_small_hand():
    ai1 = GainFirstBuyAI()
    ai2 = DummyAI()
    state = GameState(players=[])
    state.initialize_game([ai1, ai2], [get_card("Village")])
    attacker, victim = state.players

    samurai = get_card("Samurai")
    attacker.hand = [samurai]
    attacker.in_play = []
    attacker.duration = []

    victim.hand = [get_card("Copper") for _ in range(3)]

    attacker.hand.remove(samurai)
    attacker.in_play.append(samurai)
    samurai.on_play(state)

    assert len(victim.hand) == 3  # unchanged


def test_samurai_trims_four_card_hand_to_three():
    ai1 = GainFirstBuyAI()
    ai2 = DummyAI()
    state = GameState(players=[])
    state.initialize_game([ai1, ai2], [get_card("Village")])
    attacker, victim = state.players

    samurai = get_card("Samurai")
    attacker.hand = [samurai]
    attacker.in_play = []
    attacker.duration = []

    victim.hand = [get_card("Copper") for _ in range(4)]

    attacker.hand.remove(samurai)
    attacker.in_play.append(samurai)
    samurai.on_play(state)

    assert len(victim.hand) == 3


def test_samurai_on_duration_grants_one_coin_and_persists():
    state, player = _setup(GainFirstBuyAI())
    samurai = get_card("Samurai")
    player.duration = [samurai]
    samurai.duration_persistent = True
    player.coins = 0

    samurai.on_duration(state)

    assert player.coins == 1
    assert samurai.duration_persistent is True
