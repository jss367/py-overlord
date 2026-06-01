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


def test_carnival_routes_duplicate_discards_through_engine():
    """Duplicates discarded by Carnival should fire discard hooks
    (Tunnel reveals to gain Gold, etc.). Routing through
    ``game_state.discard_card`` ensures triggers don't silently drop."""

    state, player = _make_state()
    carnival = get_card("Carnival")
    state.supply["Gold"] = 30
    tunnel_a = get_card("Tunnel")
    tunnel_b = get_card("Tunnel")
    # Two Tunnels in a row -> the duplicate goes through discard_card,
    # firing Tunnel's "on discard, gain a Gold" reaction.
    player.deck = [tunnel_a, tunnel_b]
    player.hand = [carnival]

    player.hand.remove(carnival)
    player.in_play.append(carnival)
    carnival.on_play(state)

    assert any(c.name == "Gold" for c in player.discard), (
        "Tunnel discarded by Carnival should have triggered its on-discard "
        "reaction (gain a Gold)"
    )


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


def test_shop_grants_card_and_coin_and_plays_unique_action_from_hand():
    """+1 Card / +$1, may play an Action from hand whose name is not
    already represented among Actions in play. Shop does NOT grant
    +1 Action — the Action it plays is played without spending one."""

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
    # Shop draws 1 (Copper) into hand. Smithy plays from hand without
    # spending an action.
    assert any(c.name == "Smithy" for c in player.in_play), (
        "Smithy should have been played from hand"
    )
    assert not any(c.name == "Smithy" for c in player.hand)
    # Village (already-named in_play) was not played: it stays in hand.
    assert any(c.name == "Village" for c in player.hand)


def test_shop_does_not_consume_action_to_play_card():
    """Shop plays an Action from hand WITHOUT spending an action from the
    pool. Shop itself grants no +1 Action."""

    state, player = _make_state()
    shop = get_card("Shop")
    village = get_card("Village")
    player.hand = [shop, village]
    player.actions = 0

    player.hand.remove(shop)
    player.in_play.append(shop)
    shop.on_play(state)

    # Village played for free → +2 actions from Village's effect, no
    # contribution from Shop itself.
    assert player.actions == 2


def test_shop_treats_duration_actions_as_in_play():
    """A Duration Action sitting in player.duration is still 'in play';
    Shop must not allow chaining a same-named Action from hand."""

    state, player = _make_state()
    haunted_woods = get_card("Haunted Woods")
    shop = get_card("Shop")
    duplicate_haunted_woods = get_card("Haunted Woods")
    player.duration = [haunted_woods]
    player.in_play = []
    player.hand = [duplicate_haunted_woods]

    shop.play_effect(state)

    # The Haunted Woods in hand was NOT played because there is already
    # one in duration.
    assert duplicate_haunted_woods in player.hand
    assert duplicate_haunted_woods not in player.in_play


def test_shop_chain_blocked_when_another_shop_already_in_play():
    """A Shop currently resolving counts as 'in play', so a second Shop in
    hand cannot be auto-played by the resolving Shop's effect."""

    state, player = _make_state()
    shop_a = get_card("Shop")
    shop_b = get_card("Shop")
    player.hand = [shop_b]
    player.in_play = [shop_a]  # the first Shop is mid-resolution

    shop_a.play_effect(state)

    # Shop B remained in hand — chaining was blocked.
    assert shop_b in player.hand
    assert shop_b not in player.in_play


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


def test_infirmary_overpay_moves_card_into_play_before_replaying():
    """The just-bought Infirmary should be in player.in_play during the
    overpay replays so a mid-replay shuffle cannot pull it back into the
    deck and effects keying on the in-play zone see it correctly."""

    ai = InfirmaryBuyer(overpay=2, trash_target=None)
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.setup_supply([])
    state.supply["Infirmary"] = 10
    player.hand = []
    # Empty deck, no discard either: each replay's +1 Card finds nothing.
    # If Infirmary were left in discard during replay, the empty-deck
    # shuffle would put it into the deck and we could draw it.
    player.deck = []
    player.discard = []
    player.in_play = []
    player.actions = 0
    player.buys = 1
    player.coins = 5  # cost 3 + overpay 2
    state.current_player_index = 0
    state.phase = "buy"

    state.handle_buy_phase()

    # The Infirmary should be in play after overpay (not back in discard,
    # not shuffled into deck/hand).
    infirmaries_in_play = [c for c in player.in_play if c.name == "Infirmary"]
    assert len(infirmaries_in_play) == 1
    assert not any(c.name == "Infirmary" for c in player.deck)
    assert not any(c.name == "Infirmary" for c in player.hand)
    assert not any(c.name == "Infirmary" for c in player.discard)


def test_infirmary_overpay_replays_when_reclaimed_from_exile():
    """If the player has an Infirmary on the Exile mat, gain_card reclaims
    that instance instead of placing the freshly-bought one. on_overpay is
    called on the freshly-bought ``self`` (not the reclaimed instance), so
    the handler must search for any Infirmary by name rather than ``self``
    identity. The replays must still happen."""

    ai = InfirmaryBuyer(overpay=2, trash_target=None)
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.setup_supply([])
    state.supply["Infirmary"] = 10
    player.hand = []
    player.deck = [get_card("Copper"), get_card("Copper")]
    player.discard = []
    player.in_play = []
    player.duration = []
    # Simulate an Infirmary already on the Exile mat.
    exiled_infirmary = get_card("Infirmary")
    player.exile = [exiled_infirmary]
    player.actions = 0
    player.buys = 1
    player.coins = 5  # cost 3 + overpay 2
    state.current_player_index = 0
    state.phase = "buy"

    state.handle_buy_phase()

    # 2 replays of Infirmary = 2 Coppers drawn (each play: +1 Card).
    coppers_in_hand = sum(1 for c in player.hand if c.name == "Copper")
    assert coppers_in_hand == 2, (
        f"Reclaim-from-Exile case should still replay Infirmary; got "
        f"{coppers_in_hand} Coppers"
    )
    # The Infirmary in play is the reclaimed (formerly exiled) instance.
    assert exiled_infirmary in player.in_play
    assert exiled_infirmary not in player.exile


def test_infirmary_overpay_skips_replays_if_trader_swapped_for_silver():
    """If Trader's reaction substitutes a Silver for the gained Infirmary,
    on_overpay receives the Silver as ``gained_card``. The handler must
    not move/replay the Silver as if it were an Infirmary."""

    ai = InfirmaryBuyer(overpay=2, trash_target=None)
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.setup_supply([])
    silver = get_card("Silver")
    player.discard = [silver]  # the substituted Silver lives in discard
    player.deck = [get_card("Copper") for _ in range(3)]
    player.hand = []
    player.in_play = []
    player.actions = 0
    state.current_player_index = 0
    state.phase = "buy"

    # Simulate post-Trader on_overpay: the gained_card is a Silver.
    fresh_infirmary = get_card("Infirmary")
    fresh_infirmary.on_overpay(state, player, 2, gained_card=silver)

    # No Coppers drawn (no replays happened); Silver still in discard.
    assert sum(1 for c in player.hand if c.name == "Copper") == 0
    assert silver in player.discard
    assert silver not in player.in_play


def test_infirmary_overpay_replays_gained_copy_not_preexisting_one():
    """If the player already has an old Infirmary in discard, buying a
    new Infirmary with overpay must replay the just-gained copy — not
    the stale one. The engine passes ``gained_card`` to make this
    determination unambiguous."""

    ai = InfirmaryBuyer(overpay=2, trash_target=None)
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.setup_supply([])
    state.supply["Infirmary"] = 10
    old_infirmary = get_card("Infirmary")
    new_infirmary = get_card("Infirmary")
    player.hand = []
    player.deck = [get_card("Copper"), get_card("Copper")]
    player.discard = [old_infirmary]  # pre-existing
    player.in_play = []
    player.actions = 0
    player.buys = 1
    player.coins = 5
    state.current_player_index = 0
    state.phase = "buy"

    # Manually call on_overpay with the freshly-gained instance simulated.
    state.gain_card(player, new_infirmary)
    new_infirmary.on_overpay(state, player, 2, gained_card=new_infirmary)

    # The freshly-gained Infirmary should be in play (got moved out of
    # discard); the old one should still be sitting in discard.
    assert new_infirmary in player.in_play
    assert old_infirmary in player.discard
    assert old_infirmary not in player.in_play


def test_infirmary_overpay_finds_card_in_deck_after_topdeck_on_gain():
    """If a topdeck-on-gain effect has moved Infirmary from discard onto
    the deck before on_overpay fires, the replays should still find and
    move the card to in-play, not phantom-replay while it sits on deck."""

    ai = InfirmaryBuyer(overpay=2, trash_target=None)
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.setup_supply([])
    state.supply["Infirmary"] = 10
    player.hand = []
    player.deck = []
    player.discard = []
    player.in_play = []
    player.actions = 0
    player.buys = 1
    player.coins = 5
    state.current_player_index = 0
    state.phase = "buy"

    # Patch _prompt_overpay: between gain and overpay, simulate a topdeck
    # effect by moving the gained Infirmary from discard to deck.
    real_prompt = state._prompt_overpay

    def topdeck_then_prompt(player_, card_):
        amt = real_prompt(player_, card_)
        if card_.name == "Infirmary" and card_ in player_.discard:
            player_.discard.remove(card_)
            player_.deck.append(card_)
        return amt

    state._prompt_overpay = topdeck_then_prompt

    state.handle_buy_phase()

    in_play_names = [c.name for c in player.in_play]
    assert in_play_names.count("Infirmary") == 1, (
        f"Infirmary should be moved into play before replay, got in_play={in_play_names}"
    )
    assert not any(c.name == "Infirmary" for c in player.deck)
    assert not any(c.name == "Infirmary" for c in player.discard)


def test_infirmary_overpay_skips_replays_if_card_was_trashed():
    """If Watchtower trashed the Infirmary, the replays don't run — the
    card no longer exists in the player's zones to be played."""

    ai = InfirmaryBuyer(overpay=2, trash_target=None)
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.setup_supply([])
    player.hand = []
    player.deck = [get_card("Copper") for _ in range(5)]
    player.discard = []
    player.in_play = []
    player.actions = 0
    state.current_player_index = 0
    state.phase = "buy"

    # Simulate post-gain Watchtower trash: the Infirmary instance lives in
    # state.trash, not in any player zone.
    infirmary = get_card("Infirmary")
    state.trash.append(infirmary)

    infirmary.on_overpay(state, player, 2)

    # No replays happened, so no Coppers were drawn.
    assert sum(1 for c in player.hand if c.name == "Copper") == 0
    # Infirmary remains in trash, not moved to in-play.
    assert infirmary in state.trash
    assert not any(c is infirmary for c in player.in_play)


def test_ferryman_gain_iterates_pile_order_after_top_empties():
    """If Ferryman's pile is a split pile, gaining Ferryman should
    consume the current top — and once the top empties, gain from the
    lower half."""

    state = GameState(players=[])
    state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
    # Force a known split-pile setup so we can test the bottom-fallback.
    state.ferryman_card_name = "Catapult"
    state.ferryman_pile_order = ["Catapult", "Rocks"]
    state.supply["Catapult"] = 1
    state.supply["Rocks"] = 5
    state.supply["Ferryman"] = 10
    player = state.players[0]
    player.hand = []
    player.deck = []
    player.discard = []
    player.in_play = []
    player.duration = []
    player.exile = []

    # Gain 1: Catapult is on top (1 copy), so we gain Catapult.
    state.supply["Ferryman"] -= 1
    state.gain_card(player, get_card("Ferryman"))
    assert any(c.name == "Catapult" for c in player.discard)
    assert state.supply["Catapult"] == 0
    assert state.supply["Rocks"] == 5

    # Gain 2: Catapult pile is empty, so Ferryman now gains Rocks.
    player.discard.clear()
    state.supply["Ferryman"] -= 1
    state.gain_card(player, get_card("Ferryman"))
    assert any(c.name == "Rocks" for c in player.discard)
    assert state.supply["Rocks"] == 4


def test_ferryman_setup_can_pick_split_pile_tops_and_adds_partners():
    """Split-pile tops (Tent for Forts, Old Map for Odysseys, Catapult
    for Catapult/Rocks, etc.) are eligible Ferryman picks. When picked,
    partner piles must also be added to the supply so the pile evolves
    correctly as the top empties."""

    # Force a deterministic seed sweep until we land on a known split-pile
    # top, then verify the partner was registered.
    import random as _random

    tops_seen: dict[str, list[str]] = {
        "Tent": ["Garrison", "Hill Fort", "Stronghold"],
        "Old Map": ["Voyage", "Sunken Treasure", "Distant Shore"],
        "Catapult": ["Rocks"],
        "Encampment": ["Plunder"],
        "Patrician": ["Emporium"],
        "Settlers": ["Bustling Village"],
        "Sauna": ["Avanto"],
    }
    found = False
    for seed in range(500):
        _random.seed(seed)
        state = GameState(players=[])
        state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
        name = state.ferryman_card_name
        if name in tops_seen:
            found = True
            for partner in tops_seen[name]:
                assert partner in state.supply, (
                    f"Ferryman picked {name} but partner {partner} "
                    f"was not registered in supply"
                )
            break
    assert found, "No split-pile top was selected in 500 seeds"


def test_ferryman_setup_never_picks_split_pile_non_top():
    """Only the TOP of a split pile is a legal Ferryman pick. Bottom
    halves (Rocks, Plunder, Garrison, etc.) must be filtered out."""

    bottoms = {"Rocks", "Plunder", "Emporium", "Bustling Village",
               "Avanto", "Garrison", "Hill Fort", "Stronghold",
               "Voyage", "Sunken Treasure", "Distant Shore"}
    for _ in range(150):
        state = GameState(players=[])
        state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
        assert state.ferryman_card_name not in bottoms, (
            f"Ferryman picked split-pile bottom {state.ferryman_card_name}"
        )


def test_ferryman_setup_never_picks_potion_or_other_non_kingdom_supply():
    """Ferryman's setup says 'Choose an unused Kingdom card pile.'
    Non-Kingdom piles (Potion, Plunder Loot) are not eligible even
    though Potion passes the cost / starting_supply / may_be_bought
    filters."""

    bad = {"Potion"}
    for _ in range(150):
        state = GameState(players=[])
        state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
        assert state.ferryman_card_name not in bad, (
            f"Ferryman picked non-Kingdom pile {state.ferryman_card_name}"
        )


def test_ferryman_setup_skips_cards_needing_special_engine_setup():
    """Cards with engine-level setup that only fires for the original
    kingdom list must not be picked by Ferryman: Black Market (deck),
    Young Witch (bane), Hermit/Urchin (Madman/Mercenary), Marauder
    (Spoils/Ruins), Tournament (Prizes), Death Cart (Ruins), Nocturne
    Heirloom-bearers (Fool→Lucky Coin, Cemetery→Haunted Mirror,
    Shepherd→Pasture, Pixie→Goat, Tracker→Pouch, Secret Cave→Magic
    Lamp, Pooka→Cursed Gold, Leprechaun→none-needed-but-Fate),
    Fate cards (need Boons), Doom cards (need Hexes)."""

    excluded = {
        "Black Market", "Young Witch", "Hermit", "Urchin",
        "Marauder", "Tournament", "Death Cart",
        # Setup-keyed off kingdom_cards.
        "Trade Route", "Riverboat",
        # Heirloom-bearers (need start-of-game Copper replacement).
        "Fool", "Cemetery", "Shepherd", "Secret Cave",
        # Fate / Doom (need Boons / Hexes setup).
        "Bard", "Blessed Village", "Leprechaun",
    }
    for _ in range(150):
        state = GameState(players=[])
        state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
        assert state.ferryman_card_name not in excluded, (
            f"Ferryman picked special-setup card {state.ferryman_card_name}"
        )


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


def test_footpad_reaction_default_with_no_custom_ai_hook():
    """An AI without a custom ``should_react_with_footpad`` hook should
    still trigger Footpad's +1 Card reaction (default behaviour)."""

    state, players = _make_state(players_count=2)
    # Default AIs from FirstChoiceAI — no should_react_with_footpad override.
    state.players[0].ai = FirstChoiceAI()
    state.players[1].ai = FirstChoiceAI()
    p0, p1 = players
    footpad = get_card("Footpad")
    p0.hand = [footpad]
    p0.deck = [get_card("Gold")]
    state.supply["Estate"] = 8

    state.current_player_index = 1
    state.gain_card(p1, get_card("Estate"))

    # Default behaviour: Footpad reacted, Gold drawn into hand.
    assert any(c.name == "Gold" for c in p0.hand), (
        "Footpad must use a sensible default reaction even without a custom AI hook"
    )


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
    """Set-aside card plays at start of next turn via the engine's
    farmhands resolution hook (independent of the duration ability)."""

    state, player = _make_state(ai=FarmhandsAI())
    copper = get_card("Copper")
    player.farmhands_set_aside = [copper]
    player.hand = []
    player.coins = 0

    state._resolve_farmhands_set_aside(player)

    assert player.coins == 1
    assert copper in player.in_play
    assert player.farmhands_set_aside == []


def test_farmhands_set_aside_resolves_after_duration_phase():
    """A Duration card played from Farmhands' set-aside queue must NOT
    have its on_duration fire on the same turn it's played. The queue
    must drain after do_duration_phase, not before."""

    state = GameState(players=[])
    state.initialize_game([FarmhandsAI()], [get_card("Farmhands")])
    player = state.players[0]
    player.hand = []
    player.deck = [get_card("Copper") for _ in range(10)]
    player.discard = []
    player.in_play = []
    player.duration = []
    # Queue a Caravan to play at start of next turn. Caravan is
    # Action-Duration: on play, +1 Card / +1 Action; on_duration: +1 Card.
    caravan = get_card("Caravan")
    player.farmhands_set_aside = [caravan]
    player.coins = 0
    state.current_player_index = 0
    state.phase = "start"
    state.handle_start_phase()

    # Caravan's on_play drew 1 card; if on_duration also fired this turn
    # (the bug), it would have drawn a 2nd card. We expect exactly 1 draw
    # for the just-played Caravan.
    coppers_in_hand = sum(1 for c in player.hand if c.name == "Copper")
    assert coppers_in_hand == 1, (
        f"Caravan played from set-aside should draw 1 card on play; got "
        f"{coppers_in_hand} (likely on_duration fired too early)"
    )
    # Caravan is in duration, awaiting next turn for its on_duration.
    assert caravan in player.duration


def test_farmhands_set_aside_action_counts_toward_actions_this_turn():
    """An Action played from Farmhands' on-gain queue should count toward
    actions_this_turn (matters for Conspirator and similar threshold
    effects)."""

    state = GameState(players=[])
    state.initialize_game([FarmhandsAI()], [get_card("Farmhands")])
    player = state.players[0]
    player.hand = []
    player.deck = []
    player.discard = []
    player.in_play = []
    player.duration = []
    smithy = get_card("Smithy")
    player.farmhands_set_aside = [smithy]
    state.current_player_index = 0

    before = player.actions_this_turn
    state._resolve_farmhands_set_aside(player)
    assert player.actions_this_turn == before + 1


def test_shop_played_action_counts_toward_actions_this_turn():
    state, player = _make_state()
    shop = get_card("Shop")
    village = get_card("Village")
    player.hand = [village]
    player.in_play = [shop]
    player.actions_this_turn = 0

    shop.play_effect(state)
    assert player.actions_this_turn == 1


def test_farmhands_set_aside_resolves_even_without_a_played_farmhands():
    """If a player gains Farmhands but never PLAYS one (e.g., gained via
    Workshop, or simply bought without ever drawing it), the on-gain
    set-aside card must still play at the start of the next turn."""

    state = GameState(players=[])
    state.initialize_game([FarmhandsAI()], [get_card("Farmhands")])
    player = state.players[0]
    player.hand = []
    player.deck = []
    player.discard = []
    player.in_play = []
    player.duration = []  # crucially: NO Farmhands in duration
    player.farmhands_set_aside = [get_card("Copper")]
    player.coins = 0
    state.current_player_index = 0
    # End the previous turn cleanly so we re-enter start phase fresh.
    state.phase = "start"
    state.handle_start_phase()

    # The Copper should have been played even though no Farmhands was in
    # duration this turn.
    assert player.coins == 1
    assert player.farmhands_set_aside == []


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


def test_ferryman_setup_designates_a_three_or_four_cost_pile():
    state = GameState(players=[])
    state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
    assert state.ferryman_card_name, "Ferryman setup should pick a $3/$4 card"
    chosen = get_card(state.ferryman_card_name)
    assert chosen.cost.coins in (3, 4)
    # The chosen pile is tracked internally, but is not a Supply pile by rule.
    assert state.ferryman_card_name in state.supply
    assert state.ferryman_card_name in state.non_supply_pile_names


def test_ferryman_set_aside_pile_is_not_buyable():
    state = GameState(players=[])
    state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
    player = state.players[0]
    player.coins = 10

    affordable_names = {card.name for card in state._get_affordable_cards(player)}
    assert state.ferryman_card_name not in affordable_names


class NamedBuyAI(FirstChoiceAI):
    def __init__(self, target_name):
        super().__init__()
        self.target_name = target_name

    def choose_buy(self, state, choices):
        for choice in choices:
            if choice is not None and choice.name == self.target_name:
                return choice
        return super().choose_buy(state, choices)


def test_ferryman_set_aside_pile_cannot_be_gained_by_other_effects():
    state = GameState(players=[])
    state.initialize_game(
        [NamedBuyAI("Smithy")], [get_card("Ferryman"), get_card("Workshop")]
    )
    player = state.players[0]
    player.hand = []
    player.deck = []
    player.discard = []
    state.current_player_index = 0

    state.supply.setdefault("Smithy", get_card("Smithy").starting_supply(state))
    state.ferryman_card_name = "Smithy"
    state.ferryman_pile_order = ["Smithy"]
    state.non_supply_pile_names.add("Smithy")
    initial_smithies = state.supply["Smithy"]

    get_card("Workshop").play_effect(state)

    assert state.supply["Smithy"] == initial_smithies
    assert not any(card.name == "Smithy" for card in player.discard)


def test_ferryman_set_aside_pile_does_not_count_as_empty_supply_pile():
    state = GameState(players=[])
    state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
    state.supply["Smithy"] = 0
    state.ferryman_card_name = "Smithy"
    state.ferryman_pile_order = ["Smithy"]
    state.non_supply_pile_names.add("Smithy")

    assert state.empty_piles == 0


def test_ferryman_set_aside_pile_is_removed_from_black_market_deck():
    state = GameState(players=[])
    state.initialize_game(
        [FirstChoiceAI()],
        [get_card("Black Market"), get_card("Ferryman")],
    )

    for name in state.ferryman_pile_order:
        assert name not in state.black_market_deck


def test_ferryman_setup_can_pick_either_three_or_four_cost():
    """Across many setups, Ferryman should sample from both $3 and $4
    Kingdom piles (not just $3)."""

    saw_three = saw_four = False
    for _ in range(80):
        state = GameState(players=[])
        state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
        cost = get_card(state.ferryman_card_name).cost.coins
        if cost == 3:
            saw_three = True
        elif cost == 4:
            saw_four = True
        if saw_three and saw_four:
            break
    assert saw_three, "Ferryman never picked a $3 pile across 80 setups"
    assert saw_four, "Ferryman never picked a $4 pile across 80 setups"


class FerrymanDiscardingAI(FirstChoiceAI):
    """Discards the first card from hand when prompted (Ferryman play)."""

    def choose_cards_to_discard(self, state, player, hand, count, reason=""):
        return list(hand)[:count]


def test_ferryman_play_grants_cards_action_and_discards():
    """Playing Ferryman: +2 Cards / +1 Action / discard a card. Bonus
    gain only triggers on GAIN, not on play."""

    state = GameState(players=[])
    state.initialize_game([FerrymanDiscardingAI()], [get_card("Ferryman")])
    player = state.players[0]
    ferryman = get_card("Ferryman")
    estate = get_card("Estate")
    player.hand = [ferryman, estate]
    player.deck = [get_card("Copper"), get_card("Copper")]
    player.discard = []
    player.in_play = []
    player.actions = 1

    chosen_name = state.ferryman_card_name
    initial_pile = state.supply[chosen_name]

    player.hand.remove(ferryman)
    player.in_play.append(ferryman)
    ferryman.on_play(state)

    # +2 cards drawn (2 Coppers), then 1 card discarded — net +1 card in
    # hand (the original Estate stayed, Coppers drawn, then one discarded).
    # Hand size before: 1 (Estate). After draw: 3. After discard: 2.
    assert len(player.hand) == 2
    # Exactly one card moved to discard.
    assert len(player.discard) == 1
    # Bonus gain did NOT happen (only on gain).
    assert not any(c.name == chosen_name for c in player.discard)
    assert state.supply[chosen_name] == initial_pile


def test_ferryman_play_with_empty_hand_after_draws_discards_nothing():
    """If hand is empty after the +2 Cards (deck and discard exhausted),
    there's nothing to discard. The card should not error out."""

    state = GameState(players=[])
    state.initialize_game([FerrymanDiscardingAI()], [get_card("Ferryman")])
    player = state.players[0]
    ferryman = get_card("Ferryman")
    player.hand = [ferryman]
    player.deck = []
    player.discard = []
    player.in_play = []
    player.actions = 1

    player.hand.remove(ferryman)
    player.in_play.append(ferryman)
    # No-op discard: deck is empty, so +2 Cards draws 0; then nothing to
    # discard. Should not raise.
    ferryman.on_play(state)
    assert player.hand == []
    assert player.discard == []


def test_ferryman_on_gain_grants_chosen_card():
    """Gaining Ferryman gains a copy of the chosen pile. We pin the chosen
    pile to a benign card (Smithy) to avoid triggering unrelated on-gain
    cascades from cards like Siren which gain extra Actions on gain."""

    state = GameState(players=[])
    state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
    # Override the random pick with a known well-behaved $4 Action.
    state.supply.setdefault("Smithy", get_card("Smithy").starting_supply(state))
    state.ferryman_card_name = "Smithy"
    state.ferryman_pile_order = ["Smithy"]
    player = state.players[0]
    player.hand = []
    player.deck = []
    player.discard = []
    player.in_play = []
    player.duration = []

    initial_pile = state.supply["Smithy"]
    state.supply["Ferryman"] = 10
    state.supply["Ferryman"] -= 1
    state.gain_card(player, get_card("Ferryman"))

    assert state.supply["Smithy"] == initial_pile - 1
    assert any(c.name == "Smithy" for c in player.discard)


def test_ferryman_on_gain_does_not_fire_on_play():
    """Sanity: playing Ferryman does NOT trigger the bonus gain — only
    gaining Ferryman does."""

    state = GameState(players=[])
    state.initialize_game([FerrymanDiscardingAI()], [get_card("Ferryman")])
    state.supply.setdefault("Smithy", 10)
    state.ferryman_card_name = "Smithy"
    state.ferryman_pile_order = ["Smithy"]
    player = state.players[0]
    ferryman = get_card("Ferryman")
    player.hand = [ferryman, get_card("Estate")]
    player.deck = [get_card("Copper"), get_card("Copper")]
    player.discard = []
    player.in_play = []
    player.actions = 1

    initial_smithy = state.supply["Smithy"]
    player.hand.remove(ferryman)
    player.in_play.append(ferryman)
    ferryman.on_play(state)
    assert state.supply["Smithy"] == initial_smithy
    assert not any(c.name == "Smithy" for c in player.discard)


def test_ferryman_setup_skips_castles_and_split_pile_bottoms():
    """Ferryman supports split-pile TOPs (Tent, Old Map, Catapult, ...)
    but must not pick split-pile BOTTOMS or any Castle variant (the
    Castles expansion is a special-case setup we don't replicate)."""

    bad_names = {
        "Humble Castle", "Crumbling Castle", "Small Castle",
        "Haunted Castle", "Opulent Castle", "Sprawling Castle",
        "Grand Castle", "King's Castle",
        # Split-pile bottoms
        "Rocks", "Plunder", "Bustling Village", "Emporium", "Avanto",
        "Garrison", "Hill Fort", "Stronghold",
        "Voyage", "Sunken Treasure", "Distant Shore",
    }
    for _ in range(200):
        state = GameState(players=[])
        state.initialize_game([FirstChoiceAI()], [get_card("Ferryman")])
        assert state.ferryman_card_name not in bad_names, (
            f"Ferryman picked illegal split-pile bottom / Castle "
            f"{state.ferryman_card_name}"
        )


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


def test_courser_resolves_choices_in_printed_order():
    """When AI picks 'silvers' and 'cards', Silvers must NOT be gained
    before the +2 Cards draw — printed order is cards, actions, coins,
    silvers, so cards resolve first regardless of AI selection order."""

    class TrackingAI(CourserAI):
        def __init__(self):
            super().__init__(options=["silvers", "cards"])
            self.draw_call_seen_silvers_in_discard = None

    ai = TrackingAI()
    state, player = _make_state(ai=ai)
    state.supply["Silver"] = 40
    courser = get_card("Courser")
    # Stack the deck so the +2 Cards draw is observable.
    player.deck = [get_card("Copper"), get_card("Copper")]
    player.discard = []

    # Wrap draw_cards to record what's already in discard at draw time.
    real_draw = state.draw_cards

    def tracking_draw(p, n):
        ai.draw_call_seen_silvers_in_discard = sum(
            1 for c in p.discard if c.name == "Silver"
        )
        return real_draw(p, n)

    state.draw_cards = tracking_draw

    player.in_play.append(courser)
    courser.on_play(state)

    # +2 Cards drew first → no Silvers in discard at the moment of draw.
    assert ai.draw_call_seen_silvers_in_discard == 0, (
        "Cards effect must resolve before Silvers gain (printed order)"
    )
    # Final state: 2 Coppers drawn, 4 Silvers in discard.
    assert sum(1 for c in player.hand if c.name == "Copper") == 2
    assert sum(1 for c in player.discard if c.name == "Silver") == 4


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
