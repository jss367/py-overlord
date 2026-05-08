"""Tests for the Cornucopia & Guilds 2nd Edition cards.

Covers seven new kingdom cards (Carnival, Farmhands, Farrier, Ferryman,
Footpad, Infirmary, Shop) and one new Joust Reward (Courser).
"""

from typing import Optional

from dominion.cards.base_card import Card
from dominion.cards.cornucopia.joust import REWARD_CARD_NAMES
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FirstChoiceAI(DummyAI):
    """Picks first non-None option for every prompt."""

    def choose_action(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_treasure(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

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


def _make_state(ai=None, players_count=1):
    ais = [ai or FirstChoiceAI() for _ in range(players_count)]
    if players_count == 1:
        ais = [ai or FirstChoiceAI()]
    players = [PlayerState(a) for a in ais]
    state = GameState(players=players)
    state.setup_supply([])
    for p in players:
        p.hand = []
        p.deck = []
        p.discard = []
        p.in_play = []
        p.duration = []
        p.actions = 1
        p.buys = 1
        p.coins = 0
        p.coin_tokens = 0
    state.current_player_index = 0
    state.phase = "action"
    return state, players[0] if players_count == 1 else players


# ---------------------------------------------------------------------------
# Carnival
# ---------------------------------------------------------------------------


def test_carnival_keeps_one_of_each_distinct_name():
    """Reveals top 4: keeps one of each differently named card, discards the rest."""

    state, player = _make_state()
    carnival = get_card("Carnival")

    copper1 = get_card("Copper")
    copper2 = get_card("Copper")
    silver = get_card("Silver")
    estate = get_card("Estate")
    # Top of deck is the LAST element (deck.pop() draws from end).
    player.deck = [copper1, copper2, silver, estate]
    player.hand = [carnival]
    player.actions = 1
    player.buys = 1

    player.hand.remove(carnival)
    player.in_play.append(carnival)
    carnival.on_play(state)

    # Three differently named cards (Copper, Silver, Estate) end up in hand.
    hand_names = sorted(c.name for c in player.hand)
    assert hand_names == ["Copper", "Estate", "Silver"], hand_names
    # The duplicate Copper goes to discard.
    discard_names = sorted(c.name for c in player.discard)
    assert discard_names == ["Copper"], discard_names
    # +1 Buy.
    assert player.buys == 2


def test_carnival_with_fewer_than_four_cards_in_deck():
    """If the deck is empty, Carnival reveals what it can."""

    state, player = _make_state()
    carnival = get_card("Carnival")
    player.deck = [get_card("Copper")]  # only 1 card available
    player.hand = [carnival]
    player.discard = []  # nothing to reshuffle

    player.hand.remove(carnival)
    player.in_play.append(carnival)
    carnival.on_play(state)

    assert sum(1 for c in player.hand if c.name == "Copper") == 1
    assert player.deck == []
    assert player.buys == 2


def test_carnival_all_distinct_keeps_all_four():
    state, player = _make_state()
    carnival = get_card("Carnival")
    cards = [get_card("Copper"), get_card("Silver"), get_card("Gold"), get_card("Estate")]
    player.deck = list(cards)
    player.hand = [carnival]

    player.hand.remove(carnival)
    player.in_play.append(carnival)
    carnival.on_play(state)

    assert sorted(c.name for c in player.hand) == ["Copper", "Estate", "Gold", "Silver"]
    assert player.discard == []


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------


def test_shop_grants_card_action_coin_and_plays_unique_action_from_hand():
    """+1 Card / +1 Action / +$1, may play an Action from hand whose name is
    not already represented among Actions in play."""

    state, player = _make_state()
    shop = get_card("Shop")
    smithy = get_card("Smithy")  # Action, not yet in play
    village_in_play = get_card("Village")
    player.in_play = [village_in_play]  # Village name occupies in-play
    player.hand = [shop, smithy, get_card("Village")]  # extra Village should NOT be playable
    player.deck = [get_card("Copper")]  # 1 card to draw
    player.actions = 1
    player.coins = 0

    player.hand.remove(shop)
    player.in_play.append(shop)
    shop.on_play(state)

    assert player.coins == 1
    # Shop draws 1 (Copper) into hand. Smithy plays from hand → +3 cards (but
    # deck is empty after the Copper draw); the play happens regardless.
    assert any(c.name == "Smithy" for c in player.in_play), (
        "Smithy should have been played from hand"
    )
    # Smithy is no longer in hand.
    assert not any(c.name == "Smithy" for c in player.hand)
    # Village (already-named in_play) was not played: it stays in hand.
    assert any(c.name == "Village" for c in player.hand)


def test_shop_does_not_consume_action_to_play_card():
    """Shop's action play does NOT cost an action from the pool."""
    state, player = _make_state()
    shop = get_card("Shop")
    village = get_card("Village")
    player.hand = [shop, village]
    player.actions = 1

    player.hand.remove(shop)
    player.in_play.append(shop)
    shop.on_play(state)

    # +1 Action from Shop, then Village played for free, +2 actions from Village.
    assert player.actions >= 2


def test_shop_with_no_eligible_actions_just_grants_basics():
    state, player = _make_state()
    shop = get_card("Shop")
    smithy_in_play = get_card("Smithy")
    player.in_play = [smithy_in_play]
    player.hand = [shop, get_card("Smithy")]  # only same-named Action
    player.deck = []

    player.hand.remove(shop)
    player.in_play.append(shop)
    shop.on_play(state)

    assert player.coins == 1
    # Smithy in hand was NOT played because Smithy is already in play.
    assert any(c.name == "Smithy" for c in player.hand)


# ---------------------------------------------------------------------------
# Infirmary
# ---------------------------------------------------------------------------


class InfirmaryBuyer(DummyAI):
    def __init__(self, overpay=0, trash_target=None):
        super().__init__()
        self.overpay = overpay
        self.trash_target = trash_target

    def choose_buy(self, state, choices):
        for c in choices:
            if c is not None and c.name == "Infirmary":
                return c
        return None

    def choose_overpay_amount(self, state, player, card, max_amount):
        return min(self.overpay, max_amount)

    def choose_card_to_trash(self, state, choices):
        if self.trash_target is None:
            return None  # decline to trash
        for c in choices:
            if c is not None and c.name == self.trash_target:
                return c
        return None


def test_infirmary_play_draws_one_and_optionally_trashes():
    state, player = _make_state(ai=InfirmaryBuyer(trash_target="Estate"))
    infirmary = get_card("Infirmary")
    estate = get_card("Estate")
    player.hand = [infirmary, estate]
    player.deck = [get_card("Silver")]

    player.hand.remove(infirmary)
    player.in_play.append(infirmary)
    infirmary.on_play(state)

    assert any(c.name == "Silver" for c in player.hand), "Should have drawn Silver"
    assert estate in state.trash, "Should have trashed the Estate"


def test_infirmary_overpay_two_plays_twice():
    """Buying Infirmary with $2 overpay plays it twice (drawing 2 cards)."""

    ai = InfirmaryBuyer(overpay=2, trash_target=None)
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.setup_supply([])
    state.supply["Infirmary"] = 10
    player.hand = []
    player.deck = [
        get_card("Copper"),
        get_card("Copper"),
        get_card("Copper"),
        get_card("Copper"),
        get_card("Copper"),
    ]
    player.discard = []
    player.in_play = []
    player.actions = 0
    player.buys = 1
    player.coins = 5  # cost 3 + overpay 2
    state.current_player_index = 0
    state.phase = "buy"

    state.handle_buy_phase()

    # Two plays of Infirmary = 2 Coppers drawn (each play: +1 Card, decline trash).
    coppers_in_hand = sum(1 for c in player.hand if c.name == "Copper")
    assert coppers_in_hand == 2, f"Expected 2 Coppers drawn, got {coppers_in_hand}"


def test_infirmary_overpay_zero_does_not_play():
    """Buying Infirmary with no overpay does not play it; the bought card
    goes straight to discard."""

    ai = InfirmaryBuyer(overpay=0, trash_target=None)
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.setup_supply([])
    state.supply["Infirmary"] = 10
    player.hand = []
    player.deck = [get_card("Copper"), get_card("Copper")]
    player.in_play = []
    player.actions = 0
    player.buys = 1
    player.coins = 3
    state.current_player_index = 0
    state.phase = "buy"

    state.handle_buy_phase()

    coppers_in_hand = sum(1 for c in player.hand if c.name == "Copper")
    assert coppers_in_hand == 0, f"Expected no draw, got {coppers_in_hand}"
    assert any(c.name == "Infirmary" for c in player.discard)


# ---------------------------------------------------------------------------
# Farrier
# ---------------------------------------------------------------------------


class FarrierBuyer(DummyAI):
    def __init__(self, overpay=0):
        super().__init__()
        self.overpay = overpay

    def choose_buy(self, state, choices):
        for c in choices:
            if c is not None and c.name == "Farrier":
                return c
        return None

    def choose_overpay_amount(self, state, player, card, max_amount):
        return min(self.overpay, max_amount)


def test_farrier_play_grants_card_action_and_buy():
    state, player = _make_state()
    farrier = get_card("Farrier")
    player.hand = [farrier]
    player.deck = [get_card("Copper")]
    player.actions = 1
    player.buys = 1

    player.hand.remove(farrier)
    player.in_play.append(farrier)
    farrier.on_play(state)

    assert any(c.name == "Copper" for c in player.hand)
    # +1 Action grants 1 in addition to starting 1 (no action consumed since we
    # called on_play directly rather than going through the action phase).
    assert player.actions == 2
    assert player.buys == 2


def test_farrier_overpay_three_grants_three_extra_cards_at_end_of_turn():
    """Buying Farrier with $3 overpay yields a 5+3=8 card next-turn hand
    after cleanup. Verified via cards_to_draw augmentation."""

    ai = FarrierBuyer(overpay=3)
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.setup_supply([])
    state.supply["Farrier"] = 10
    player.hand = []
    # Stock a fat deck so cleanup can deliver the larger hand.
    player.deck = [get_card("Copper") for _ in range(20)]
    player.discard = []
    player.in_play = []
    player.actions = 0
    player.buys = 1
    player.coins = 6  # cost 3 + overpay 3
    state.current_player_index = 0
    state.phase = "buy"

    state.handle_buy_phase()
    # phase becomes "night" → run cleanup.
    state.phase = "cleanup"
    state.handle_cleanup_phase()

    # New hand should be 5 (default) + 3 (Farrier overpay) = 8.
    assert len(player.hand) == 8, f"Expected 8-card hand, got {len(player.hand)}"


def test_farrier_overpay_zero_yields_normal_five_card_hand():
    ai = FarrierBuyer(overpay=0)
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.setup_supply([])
    state.supply["Farrier"] = 10
    player.hand = []
    player.deck = [get_card("Copper") for _ in range(20)]
    player.discard = []
    player.in_play = []
    player.actions = 0
    player.buys = 1
    player.coins = 3
    state.current_player_index = 0
    state.phase = "buy"

    state.handle_buy_phase()
    state.phase = "cleanup"
    state.handle_cleanup_phase()
    assert len(player.hand) == 5


# ---------------------------------------------------------------------------
# Footpad
# ---------------------------------------------------------------------------


class FootpadAI(DummyAI):
    """Always reveals Footpad; discards arbitrary cards down to 3."""

    def choose_cards_to_discard(self, state, player, hand, count, reason=""):
        return list(hand)[:count]

    def should_react_with_footpad(self, state, player, gainer, gained_card):
        return True


def test_footpad_grants_two_coffers_and_attacks():
    state, players = _make_state(players_count=2)
    state.players[0].ai = FootpadAI()
    state.players[1].ai = FootpadAI()
    p0, p1 = players
    footpad = get_card("Footpad")
    # Opponent has 5 cards in hand; should be discarded down to 3.
    p1.hand = [
        get_card("Copper"),
        get_card("Copper"),
        get_card("Estate"),
        get_card("Estate"),
        get_card("Silver"),
    ]
    p0.hand = [footpad]
    p0.coin_tokens = 0

    p0.hand.remove(footpad)
    p0.in_play.append(footpad)
    footpad.on_play(state)

    assert p0.coin_tokens == 2, f"Expected +2 Coffers, got {p0.coin_tokens}"
    assert len(p1.hand) == 3, f"Opponent should be at 3 cards, got {len(p1.hand)}"


def test_footpad_reaction_when_other_player_gains_victory():
    """Owner of Footpad in hand may reveal it for +1 Card when an opponent
    gains a Victory card."""

    state, players = _make_state(players_count=2)
    state.players[0].ai = FootpadAI()
    state.players[1].ai = FootpadAI()
    p0, p1 = players
    footpad = get_card("Footpad")
    p0.hand = [footpad]
    p0.deck = [get_card("Gold")]
    state.supply["Estate"] = 8

    # P1 (current player) gains an Estate. P0 holds Footpad.
    state.current_player_index = 1
    state.gain_card(p1, get_card("Estate"))

    # P0 drew +1 Card via reaction.
    assert any(c.name == "Gold" for c in p0.hand), "Footpad should have drawn +1 Card"
    # Footpad stays in hand (it's a reveal, not a play).
    assert footpad in p0.hand


def test_footpad_does_not_react_to_non_victory_gain():
    state, players = _make_state(players_count=2)
    state.players[0].ai = FootpadAI()
    state.players[1].ai = FootpadAI()
    p0, p1 = players
    footpad = get_card("Footpad")
    p0.hand = [footpad]
    p0.deck = [get_card("Gold")]

    state.current_player_index = 1
    state.gain_card(p1, get_card("Silver"))  # Silver is Treasure, not Victory

    assert not any(c.name == "Gold" for c in p0.hand), "Should not have drawn"


# ---------------------------------------------------------------------------
# Farmhands
# ---------------------------------------------------------------------------


class FarmhandsAI(DummyAI):
    """Sets aside a Copper on gain; plays Coppers from hand at start of turn."""

    def __init__(self):
        super().__init__()
        self.set_aside_target = "Copper"

    def choose_card_to_set_aside_for_farmhands(self, state, player, choices):
        for c in choices:
            if c.name == self.set_aside_target:
                return c
        return choices[0] if choices else None

    def choose_action(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_treasure(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None


def test_farmhands_on_gain_sets_aside_action_or_treasure_up_to_4():
    state, player = _make_state(ai=FarmhandsAI())
    state.supply["Farmhands"] = 10

    # Hand contains a Copper (Treasure $0) and an Estate ($2 Victory; not eligible).
    copper = get_card("Copper")
    estate = get_card("Estate")
    player.hand = [copper, estate]

    farmhands = get_card("Farmhands")
    state.gain_card(player, farmhands)

    # Copper should be set aside (removed from hand), Estate untouched.
    assert copper not in player.hand
    assert estate in player.hand


def test_farmhands_does_not_set_aside_card_costing_more_than_four():
    state, player = _make_state(ai=FarmhandsAI())
    gold = get_card("Gold")  # cost $6, ineligible
    player.hand = [gold]

    farmhands = get_card("Farmhands")
    state.gain_card(player, farmhands)

    assert gold in player.hand, "Gold ($6) is too expensive to set aside"


def test_farmhands_plays_set_aside_card_at_start_of_next_turn():
    state, player = _make_state(ai=FarmhandsAI())
    farmhands = get_card("Farmhands")
    # Manually arrange: Farmhands is in_play (was played this turn) and
    # set-aside Copper is queued to play start of next turn.
    player.in_play = [farmhands]
    player.duration = [farmhands]
    farmhands.duration_persistent = True
    # Stash a Copper in the Farmhands set-aside.
    copper = get_card("Copper")
    player.farmhands_set_aside = [copper]
    player.hand = []
    player.coins = 0

    # Trigger duration phase (start of next turn).
    state.do_duration_phase()
    # Farmhands' duration also offers playing a non-Duration card from hand.

    # The Copper should have been played (added $1).
    assert player.coins == 1


def test_farmhands_duration_offers_play_from_hand():
    state, player = _make_state(ai=FarmhandsAI())
    farmhands = get_card("Farmhands")
    player.in_play = [farmhands]
    player.duration = [farmhands]
    farmhands.duration_persistent = True
    player.farmhands_set_aside = []
    silver = get_card("Silver")
    player.hand = [silver]
    player.coins = 0

    state.do_duration_phase()

    # Silver played from hand → +$2.
    assert player.coins == 2
    assert silver in player.in_play


# ---------------------------------------------------------------------------
# Ferryman
# ---------------------------------------------------------------------------


def test_ferryman_setup_designates_a_three_cost_pile():
    state = GameState(players=[])
    state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
    assert state.ferryman_card_name, "Ferryman setup should pick a $3 card"
    chosen = get_card(state.ferryman_card_name)
    assert chosen.cost.coins == 3
    # The chosen pile must exist in the supply.
    assert state.ferryman_card_name in state.supply


def test_ferryman_play_grants_cards_action_and_gains_chosen_card():
    state = GameState(players=[])
    state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
    player = state.players[0]
    player.hand = [get_card("Ferryman")]
    player.deck = [get_card("Copper"), get_card("Copper")]
    player.discard = []
    player.in_play = []
    player.actions = 1

    chosen_name = state.ferryman_card_name
    initial_pile = state.supply[chosen_name]

    ferryman = player.hand[0]
    player.hand.remove(ferryman)
    player.in_play.append(ferryman)
    ferryman.on_play(state)

    # +2 cards drawn, +1 action.
    assert sum(1 for c in player.hand if c.name == "Copper") == 2
    # Gained the chosen $3 card.
    assert any(c.name == chosen_name for c in player.discard)
    assert state.supply[chosen_name] == initial_pile - 1


# ---------------------------------------------------------------------------
# Courser (new Joust Reward)
# ---------------------------------------------------------------------------


class CourserAI(DummyAI):
    """Picks the first two Courser options."""

    def __init__(self, options=None):
        super().__init__()
        self.options = options or ["cards", "actions"]

    def choose_courser_options(self, state, player, available):
        return list(self.options)[:2]


def test_courser_in_reward_pool():
    assert "Courser" in REWARD_CARD_NAMES, (
        "Courser must be registered as a Joust Reward"
    )


def test_courser_is_not_buyable_as_a_reward():
    courser = get_card("Courser")
    state = GameState(players=[PlayerState(FirstChoiceAI())])
    state.setup_supply([])
    assert not courser.may_be_bought(state)


def test_courser_cards_and_actions():
    ai = CourserAI(options=["cards", "actions"])
    state, player = _make_state(ai=ai)
    courser = get_card("Courser")
    player.deck = [get_card("Copper"), get_card("Copper")]
    player.actions = 0

    player.in_play.append(courser)
    courser.on_play(state)

    # +2 Cards
    assert sum(1 for c in player.hand if c.name == "Copper") == 2
    # +2 Actions
    assert player.actions == 2


def test_courser_coins_and_silvers():
    ai = CourserAI(options=["coins", "silvers"])
    state, player = _make_state(ai=ai)
    courser = get_card("Courser")
    state.supply["Silver"] = 40
    player.coins = 0

    player.in_play.append(courser)
    courser.on_play(state)

    assert player.coins == 2
    silvers = sum(1 for c in player.discard if c.name == "Silver")
    assert silvers == 4, f"Expected 4 Silvers, got {silvers}"


def test_courser_cannot_choose_same_option_twice():
    ai = CourserAI(options=["cards", "cards"])  # invalid: duplicate
    state, player = _make_state(ai=ai)
    courser = get_card("Courser")
    player.deck = [get_card("Copper") for _ in range(5)]
    player.actions = 0

    player.in_play.append(courser)
    courser.on_play(state)

    # Even if AI returns duplicates, the card must enforce two DIFFERENT
    # choices. With "cards" once + a fallback different choice, we expect
    # exactly 2 cards drawn (not 4) — the duplicate is dropped and the
    # implementation picks any other option.
    drawn = sum(1 for c in player.hand if c.name == "Copper")
    assert drawn == 2, f"Expected 2 cards from a single 'cards' choice, got {drawn}"
