"""Tests for the Seaside expansion cards."""

from typing import Optional

from dominion.cards.base_card import Card
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI, ChooseFirstActionAI


def play_action(state, player, card):
    if card in player.hand:
        player.hand.remove(card)
    player.in_play.append(card)
    card.on_play(state)


def _make_state(num_players=1, ai_class=DummyAI):
    players = [PlayerState(ai_class()) for _ in range(num_players)]
    state = GameState(players=players)
    state.setup_supply([])
    for p in players:
        p.hand = []
        p.deck = []
        p.discard = []
        p.in_play = []
        p.duration = []
    return state


# -- Easy cards --------------------------------------------------------------


def test_lighthouse_grants_now_and_next_turn_coin():
    state = _make_state()
    player = state.players[0]
    lighthouse = get_card("Lighthouse")
    player.hand = [lighthouse]
    play_action(state, player, lighthouse)

    assert player.coins == 1
    assert player.actions == 2  # 1 starting + 1 from Lighthouse
    assert lighthouse in player.duration

    # Next turn duration effect: +$1
    coins_before = player.coins
    lighthouse.on_duration(state)
    assert player.coins == coins_before + 1


def test_lighthouse_blocks_attacks():
    state = _make_state(num_players=2)
    attacker, defender = state.players
    state.current_player_index = 0

    lighthouse = get_card("Lighthouse")
    defender.duration.append(lighthouse)

    militia = get_card("Militia")
    attacker.hand = [militia]
    defender.hand = [
        get_card("Copper"), get_card("Copper"), get_card("Copper"),
        get_card("Estate"), get_card("Estate"),
    ]

    play_action(state, attacker, militia)
    # Defender shouldn't have been forced to discard.
    assert len(defender.hand) == 5


def test_pearl_diver_topdecks_action_from_bottom():
    state = _make_state()
    player = state.players[0]
    village = get_card("Village")
    copper = get_card("Copper")
    # bottom = index 0, top = end
    player.deck = [village, copper]

    pearl = get_card("Pearl Diver")
    player.hand = [pearl]
    play_action(state, player, pearl)

    # Top card was drawn (Copper or Village from end), then Pearl Diver looked
    # at the new bottom. With 2 cards original, draw takes the top (copper),
    # then the bottom-look sees village and topdecks it.
    assert player.deck and player.deck[-1].name == "Village"


def test_fishing_village_grants_now_and_next_turn():
    state = _make_state()
    player = state.players[0]
    fv = get_card("Fishing Village")
    player.hand = [fv]
    play_action(state, player, fv)

    assert player.actions == 3  # 1 starting + 2 from FV
    assert player.coins == 1
    assert fv in player.duration

    actions_before = player.actions
    coins_before = player.coins
    fv.on_duration(state)
    assert player.actions == actions_before + 1
    assert player.coins == coins_before + 1


def test_warehouse_draws_three_and_discards_three():
    state = _make_state()
    player = state.players[0]

    warehouse = get_card("Warehouse")
    # Provide enough deck to draw 3 cards.
    player.deck = [get_card("Copper") for _ in range(5)]
    player.hand = [warehouse]
    play_action(state, player, warehouse)

    # Draws 3, discards 3 → hand size unchanged (was 1, became 4, then 1 discarded → ends at 1)
    # Actually: hand started with [warehouse], played, removed; then drew 3 (3 in hand);
    # then discarded 3 from those (0 in hand).
    assert len(player.hand) == 0
    assert len(player.discard) == 3
    assert player.actions == 2  # 1 starting + 1 from Warehouse


def test_caravan_draws_now_and_next_turn():
    state = _make_state()
    player = state.players[0]
    caravan = get_card("Caravan")

    player.deck = [get_card("Estate"), get_card("Copper")]
    player.hand = [caravan]
    play_action(state, player, caravan)

    # +1 Card now
    assert len(player.hand) == 1
    assert caravan in player.duration

    hand_size_before = len(player.hand)
    caravan.on_duration(state)
    assert len(player.hand) == hand_size_before + 1


def test_salvager_forces_trash_when_ai_skips():
    """Salvager's trash is mandatory if the hand has cards.

    With an AI that always returns None for trash choices, Salvager must
    still trash something (and credit the +$ for that card's cost).
    """
    state = _make_state()
    player = state.players[0]
    salvager = get_card("Salvager")
    estate = get_card("Estate")

    player.hand = [salvager, estate]
    play_action(state, player, salvager)

    # Default DummyAI.choose_card_to_trash returns None — Salvager must
    # still pick a card to trash (Estate, since it's the only choice).
    assert estate in state.trash
    assert player.coins == 2  # Estate costs 2


def test_salvager_trashes_for_coins():
    class TrashEstateAI(DummyAI):
        def choose_card_to_trash(self, state, choices):
            for c in choices:
                if c.name == "Estate":
                    return c
            return None

    state = _make_state(ai_class=TrashEstateAI)
    player = state.players[0]
    salvager = get_card("Salvager")
    estate = get_card("Estate")

    player.hand = [salvager, estate]
    play_action(state, player, salvager)

    # +1 buy, +$2 (Estate cost), Estate in trash
    assert player.buys == 2
    assert player.coins == 2  # Estate costs 2
    assert estate in state.trash


def test_haven_forces_set_aside_when_hand_has_only_junk():
    """Haven must set aside a card whenever the hand is non-empty.

    The default heuristic only picks Actions/expensive Treasures; this test
    proves Haven still picks something when the hand is all low-value cards.
    """
    state = _make_state()
    player = state.players[0]
    haven = get_card("Haven")
    copper = get_card("Copper")
    estate = get_card("Estate")

    player.deck = [get_card("Copper")]
    player.hand = [haven, copper, estate]
    play_action(state, player, haven)

    assert haven.set_aside is not None, \
        "Haven must set aside something when hand has cards"


def test_haven_sets_aside_card_for_next_turn():
    state = _make_state()
    player = state.players[0]
    haven = get_card("Haven")
    gold = get_card("Gold")

    player.deck = [get_card("Estate")]
    player.hand = [haven, gold]
    play_action(state, player, haven)

    # Gold should be set aside, Estate drawn
    assert haven.set_aside is gold
    assert gold not in player.hand
    assert haven in player.duration

    haven.on_duration(state)
    assert gold in player.hand


def test_treasure_map_gains_four_golds_when_two_trashed():
    state = _make_state()
    player = state.players[0]
    state.supply["Gold"] = 30

    map1 = get_card("Treasure Map")
    map2 = get_card("Treasure Map")
    player.hand = [map1, map2]
    play_action(state, player, map1)

    assert map1 in state.trash
    assert map2 in state.trash
    golds_on_top = sum(1 for c in player.deck if c.name == "Gold")
    assert golds_on_top == 4


def test_treasure_map_alone_just_trashes_self():
    state = _make_state()
    player = state.players[0]
    state.supply["Gold"] = 30

    map1 = get_card("Treasure Map")
    player.hand = [map1]
    play_action(state, player, map1)

    assert map1 in state.trash
    assert all(c.name != "Gold" for c in player.deck)


def test_merchant_ship_gives_two_coins_now_and_next_turn():
    state = _make_state()
    player = state.players[0]
    ms = get_card("Merchant Ship")
    player.hand = [ms]
    play_action(state, player, ms)

    assert player.coins == 2
    assert ms in player.duration

    coins_before = player.coins
    ms.on_duration(state)
    assert player.coins == coins_before + 2


def test_tide_pools_draws_three_and_discards_two_next_turn():
    state = _make_state()
    player = state.players[0]
    tp = get_card("Tide Pools")
    player.deck = [get_card("Copper") for _ in range(3)]
    player.hand = [tp]
    play_action(state, player, tp)

    assert len(player.hand) == 3
    assert tp in player.duration

    tp.on_duration(state)
    assert len(player.hand) == 1
    assert len(player.discard) == 2


def test_sea_witch_draws_and_curses_then_drawback_next_turn():
    state = _make_state(num_players=2)
    attacker, defender = state.players
    state.current_player_index = 0
    state.supply["Curse"] = 10

    sw = get_card("Sea Witch")
    attacker.deck = [get_card("Copper") for _ in range(4)]
    attacker.hand = [sw]
    play_action(state, attacker, sw)

    assert len(attacker.hand) == 2  # +2 cards
    assert any(c.name == "Curse" for c in defender.discard)

    state.current_player_index = 0
    sw.on_duration(state)
    # Drew 2, then discarded 2.
    assert len(attacker.discard) >= 2


def test_cutpurse_makes_opponents_discard_copper():
    state = _make_state(num_players=2)
    attacker, defender = state.players
    state.current_player_index = 0

    cp = get_card("Cutpurse")
    defender.hand = [get_card("Copper"), get_card("Estate")]
    attacker.hand = [cp]
    play_action(state, attacker, cp)

    assert attacker.coins == 2
    assert all(c.name != "Copper" for c in defender.hand)
    assert any(c.name == "Copper" for c in defender.discard)


def test_sea_hag_curses_top_of_opponent_deck():
    state = _make_state(num_players=2)
    attacker, defender = state.players
    state.current_player_index = 0
    state.supply["Curse"] = 10

    defender.deck = [get_card("Estate"), get_card("Copper")]

    hag = get_card("Sea Hag")
    attacker.hand = [hag]
    play_action(state, attacker, hag)

    assert defender.deck and defender.deck[-1].name == "Curse"


def test_monkey_draws_when_right_neighbor_gains():
    state = _make_state(num_players=2)
    player_a, player_b = state.players
    state.current_player_index = 0
    state.supply["Silver"] = 10

    monkey = get_card("Monkey")
    player_a.deck = [get_card("Copper") for _ in range(3)]
    player_a.hand = [monkey]
    play_action(state, player_a, monkey)

    # Right of player_a (index 0) is player_b (index 1).
    hand_before = len(player_a.hand)

    state.supply["Silver"] -= 1
    state.gain_card(player_b, get_card("Silver"))

    assert len(player_a.hand) == hand_before + 1


def test_monkey_only_triggers_on_right_neighbor_in_three_player_game():
    """Monkey watches the player to the owner's right (previous player).

    For owner at index 1, right = index 0. Gains by p2 (left) must NOT trigger.
    """
    state = _make_state(num_players=3)
    p0, p1, p2 = state.players
    state.current_player_index = 1
    state.supply["Silver"] = 10
    state.supply["Gold"] = 10

    monkey = get_card("Monkey")
    p1.deck = [get_card("Copper") for _ in range(5)]
    p1.hand = [monkey]
    play_action(state, p1, monkey)

    hand_after_play = len(p1.hand)

    # Left neighbor (p2) gains — must NOT trigger Monkey.
    state.supply["Silver"] -= 1
    state.gain_card(p2, get_card("Silver"))
    assert len(p1.hand) == hand_after_play, \
        "Monkey should NOT draw on left-neighbor gains"

    # Right neighbor (p0) gains — must trigger Monkey.
    state.supply["Gold"] -= 1
    state.gain_card(p0, get_card("Gold"))
    assert len(p1.hand) == hand_after_play + 1, \
        "Monkey should draw on right-neighbor gains"


# -- Medium cards ------------------------------------------------------------


def test_ambassador_does_not_fizzle_on_non_junk_hand():
    """Ambassador must reveal something when the hand is non-empty.

    Default heuristic only picks junk; with a Silver-only non-junk hand it
    returns None, but the reveal is mandatory per the printed card.
    """
    state = _make_state(num_players=2)
    attacker, defender = state.players
    state.current_player_index = 0
    state.supply["Silver"] = 10

    amb = get_card("Ambassador")
    silver = get_card("Silver")
    attacker.hand = [amb, silver]
    play_action(state, attacker, amb)

    # Defender should have gained a Silver — the play didn't fizzle.
    assert any(c.name == "Silver" for c in defender.discard), \
        "Ambassador must still attack opponents even on non-junk hands"


def test_ambassador_returns_copies_and_others_gain():
    state = _make_state(num_players=2)
    attacker, defender = state.players
    state.current_player_index = 0
    state.supply["Estate"] = 8

    amb = get_card("Ambassador")
    estate1 = get_card("Estate")
    estate2 = get_card("Estate")
    attacker.hand = [amb, estate1, estate2]
    play_action(state, attacker, amb)

    # Both estates returned to supply.
    assert state.supply["Estate"] == 8 + 2 - 1  # +2 returned, -1 given to defender
    # Defender gained an Estate.
    assert any(c.name == "Estate" for c in defender.discard)


def test_embargo_places_token_and_curses_buyer():
    state = _make_state()
    player = state.players[0]
    state.supply["Curse"] = 10

    emb = get_card("Embargo")
    player.hand = [emb]
    play_action(state, player, emb)

    assert emb in state.trash
    # Default AI embargoes Province
    assert state.embargo_tokens.get("Province", 0) == 1

    # Now simulate buying a Province
    state.supply["Province"] = 8
    state._apply_embargo_tokens(player, "Province")
    assert any(c.name == "Curse" for c in player.discard)


def test_smugglers_gains_copy_of_right_neighbors_last_turn_gain():
    state = _make_state(num_players=2)
    player_a, player_b = state.players
    state.current_player_index = 0
    state.supply["Silver"] = 10

    # Right neighbor of A is B.
    player_b.gained_cards_last_turn = ["Silver"]

    smug = get_card("Smugglers")
    player_a.hand = [smug]
    play_action(state, player_a, smug)

    assert any(c.name == "Silver" for c in player_a.discard)


def test_smugglers_uses_previous_player_in_three_player_game():
    """In 3+ players, Smugglers reads the right (previous) player's gains.

    For player at index 1, "right" = previous in turn order = index 0.
    """
    state = _make_state(num_players=3)
    p0, p1, p2 = state.players
    state.current_player_index = 1
    state.supply["Silver"] = 10
    state.supply["Gold"] = 10

    # Set distinct gains so we can tell which neighbor was sourced.
    p0.gained_cards_last_turn = ["Silver"]  # right neighbor of p1
    p2.gained_cards_last_turn = ["Gold"]    # left neighbor of p1

    smug = get_card("Smugglers")
    p1.hand = [smug]
    play_action(state, p1, smug)

    assert any(c.name == "Silver" for c in p1.discard), \
        "Smugglers must source from p0 (right of p1), not p2 (left)"
    assert all(c.name != "Gold" for c in p1.discard)


def test_navigator_first_ordered_card_lands_on_top():
    """Navigator must put back the AI's first-ordered card on TOP of the deck.

    The AI returns [A, B, C, D, E] meaning "A drawn first, then B, ...".
    Since `deck.pop()` draws from the end, the FIRST item must be appended
    last (i.e. the loop must iterate in reverse).
    """
    class TopdeckOrderAI(DummyAI):
        def order_cards_for_topdeck(self, state, player, cards):
            # Force a specific order: Gold first (top), then Silver, then Coppers.
            order = ["Gold", "Silver", "Copper", "Copper", "Copper"]
            picked = []
            remaining = list(cards)
            for name in order:
                for c in remaining:
                    if c.name == name:
                        picked.append(c)
                        remaining.remove(c)
                        break
            picked.extend(remaining)
            return picked

    state = _make_state(ai_class=TopdeckOrderAI)
    player = state.players[0]
    nav = get_card("Navigator")

    # Mostly non-junk so the topdeck branch (not discard) is taken.
    player.deck = [
        get_card("Gold"), get_card("Silver"),
        get_card("Smithy"), get_card("Smithy"), get_card("Copper"),
    ]
    player.hand = [nav]
    play_action(state, player, nav)

    # Gold should be on top of deck (drawn first by deck.pop()).
    assert player.deck and player.deck[-1].name == "Gold", \
        f"Top of deck should be Gold, got {player.deck[-1].name if player.deck else 'empty'}"


def test_navigator_can_discard_or_topdeck():
    state = _make_state()
    player = state.players[0]
    nav = get_card("Navigator")

    # Stack of mostly junk so default heuristic discards.
    player.deck = [
        get_card("Curse"), get_card("Curse"), get_card("Curse"),
        get_card("Estate"), get_card("Estate"),
    ]

    player.hand = [nav]
    play_action(state, player, nav)

    assert player.coins == 2
    # All junk → all discarded
    assert len(player.discard) == 5


def test_ghost_ship_topdecks_excess_cards():
    state = _make_state(num_players=2)
    attacker, defender = state.players
    state.current_player_index = 0

    gs = get_card("Ghost Ship")
    defender.hand = [get_card("Copper") for _ in range(5)]

    attacker.deck = [get_card("Copper") for _ in range(3)]
    attacker.hand = [gs]
    play_action(state, attacker, gs)

    # Attacker drew 2 cards.
    assert len(attacker.hand) == 2
    # Defender topdecked down to 3.
    assert len(defender.hand) == 3
    assert len(defender.deck) == 2


def test_island_forces_second_card_to_mat_when_only_actions_in_hand():
    """Island's second-card move is mandatory if a card is available.

    Default Island heuristic prefers junk and skips on Action-only hands; this
    proves Island still moves an Action when nothing else is available.
    """
    state = _make_state()
    player = state.players[0]
    island = get_card("Island")
    village = get_card("Village")  # Action, not junk

    player.hand = [island, village]
    play_action(state, player, island)

    assert island in player.island_mat
    assert village in player.island_mat, \
        "Island must move another hand card when one is available"


def test_island_moves_self_and_chosen_card_to_mat():
    state = _make_state()
    player = state.players[0]
    island = get_card("Island")
    estate = get_card("Estate")

    player.hand = [island, estate]
    play_action(state, player, island)

    assert island in player.island_mat
    assert estate in player.island_mat
    assert estate not in player.hand
    # Island provides 2 VP
    assert player.get_victory_points() >= 2


def test_explorer_gains_gold_to_hand_when_revealing_province():
    state = _make_state()
    player = state.players[0]
    state.supply["Gold"] = 10
    state.supply["Silver"] = 10

    explorer = get_card("Explorer")
    province = get_card("Province")
    player.hand = [explorer, province]
    play_action(state, player, explorer)

    assert any(c.name == "Gold" for c in player.hand)


def test_explorer_falls_back_to_silver_when_gold_pile_empty():
    """If Gold is empty, Explorer should not fizzle when Province is in hand —
    the rational play is to skip the optional reveal and take a Silver.
    """
    state = _make_state()
    player = state.players[0]
    state.supply["Gold"] = 0  # No Gold available
    state.supply["Silver"] = 10

    explorer = get_card("Explorer")
    province = get_card("Province")
    player.hand = [explorer, province]
    play_action(state, player, explorer)

    # No Gold to gain → fall back to Silver to hand.
    assert any(c.name == "Silver" for c in player.hand), \
        "Explorer must take Silver when Gold pile is empty, not fizzle"


def test_explorer_gains_silver_to_hand_otherwise():
    state = _make_state()
    player = state.players[0]
    state.supply["Silver"] = 10

    explorer = get_card("Explorer")
    player.hand = [explorer]
    play_action(state, player, explorer)

    assert any(c.name == "Silver" for c in player.hand)


# -- Hard cards --------------------------------------------------------------


def test_outpost_does_not_chain():
    state = _make_state()
    player = state.players[0]

    outpost = get_card("Outpost")
    player.outpost_taken_last_turn = True  # Pretending we just had one
    player.hand = [outpost]
    play_action(state, player, outpost)

    assert outpost in player.duration
    assert player.outpost_pending is False


def test_outpost_schedules_extra_turn_on_first_play():
    state = _make_state()
    player = state.players[0]

    outpost = get_card("Outpost")
    player.outpost_taken_last_turn = False
    player.hand = [outpost]
    play_action(state, player, outpost)

    assert player.outpost_pending is True


def test_tactician_discards_hand_and_pays_off_next_turn():
    state = _make_state()
    player = state.players[0]
    tact = get_card("Tactician")

    player.hand = [tact, get_card("Copper"), get_card("Estate")]
    player.deck = [get_card("Copper") for _ in range(7)]

    play_action(state, player, tact)

    # Hand discarded
    assert len(player.hand) == 0
    assert tact.activated

    actions_before = player.actions
    buys_before = player.buys
    tact.on_duration(state)
    assert len(player.hand) == 5
    assert player.actions == actions_before + 1
    assert player.buys == buys_before + 1


def test_tactician_does_nothing_with_empty_hand():
    state = _make_state()
    player = state.players[0]
    tact = get_card("Tactician")

    player.hand = [tact]
    play_action(state, player, tact)

    assert not tact.activated
    # Tactician shouldn't be in duration since it didn't activate.
    assert tact not in player.duration


def test_pirate_ship_attack_trashes_treasure_and_gains_token():
    state = _make_state(num_players=2)
    attacker, defender = state.players
    state.current_player_index = 0

    ps = get_card("Pirate Ship")
    defender.deck = [get_card("Copper"), get_card("Silver")]
    attacker.hand = [ps]
    play_action(state, attacker, ps)

    assert any(c.name == "Silver" for c in state.trash)
    assert attacker.pirate_ship_tokens == 1


def test_pirate_ship_coins_mode_pays_tokens():
    class CoinsModeAI(DummyAI):
        def choose_pirate_ship_mode(self, state, player, tokens):
            return "coins"

    state = _make_state(ai_class=CoinsModeAI)
    player = state.players[0]
    player.pirate_ship_tokens = 3

    ps = get_card("Pirate Ship")
    player.hand = [ps]
    play_action(state, player, ps)

    assert player.coins == 3


def test_blockade_gains_card_to_hand_next_turn():
    state = _make_state()
    player = state.players[0]
    state.supply["Silver"] = 10

    blockade = get_card("Blockade")
    player.hand = [blockade]
    play_action(state, player, blockade)

    assert blockade.set_aside is not None
    assert blockade in player.duration

    blockade.on_duration(state)
    assert blockade.set_aside is None
    # The set-aside card landed in the hand.
    assert any(c.name == "Silver" for c in player.hand)


def test_blockade_does_not_set_aside_card_sailor_already_played():
    """If Sailor plays the Duration that Blockade just gained, Blockade must
    not also set it aside — otherwise the same Card object lives in multiple
    zones and gets duplicated when Blockade resolves next turn.
    """
    class SailorAI(DummyAI):
        def should_play_gain_with_sailor(self, state, player, gained_card):
            return True

    state = _make_state(ai_class=SailorAI)
    player = state.players[0]
    state.supply["Caravan"] = 10  # Caravan: Duration, cost $4 — Blockade-eligible

    # Set up Sailor in duration before playing Blockade.
    sailor = get_card("Sailor")
    player.hand = [sailor]
    play_action(state, player, sailor)
    assert player.sailor_play_uses == 1

    blockade = get_card("Blockade")
    player.hand = [blockade]
    play_action(state, player, blockade)

    # Blockade picked Caravan. Sailor played it from gain → it's in in_play
    # as a Duration. Blockade must NOT also stash it for next turn.
    in_play_caravans = [c for c in player.in_play if c.name == "Caravan"]
    assert len(in_play_caravans) == 1
    assert blockade.set_aside is None, \
        "Blockade must not set aside a card Sailor already moved into in_play"

    # Resolve next-turn duration; the Caravan must NOT be re-added to hand.
    blockade.on_duration(state)
    hand_caravans = [c for c in player.hand if c.name == "Caravan"]
    assert len(hand_caravans) == 0, \
        "Caravan should not appear in hand if Blockade had nothing set aside"


def test_blockade_does_not_curse_lighthouse_defender():
    """A Lighthouse-defending opponent at Blockade-play time must not be
    cursed when they later gain a copy of the watched card.
    """
    state = _make_state(num_players=2)
    player_a, player_b = state.players
    state.current_player_index = 0
    state.supply["Silver"] = 10
    state.supply["Curse"] = 10

    # Defender is protected by Lighthouse when Blockade is played.
    player_b.duration.append(get_card("Lighthouse"))

    blockade = get_card("Blockade")
    player_a.hand = [blockade]
    play_action(state, player_a, blockade)

    # Player B (defended) gains the watched card → must not gain a Curse.
    state.supply["Silver"] -= 1
    state.gain_card(player_b, get_card("Silver"))
    assert all(c.name != "Curse" for c in player_b.discard), \
        "Blockade must not curse opponents protected at play time"


def test_blockade_curses_opponent_who_gains_same_card():
    state = _make_state(num_players=2)
    player_a, player_b = state.players
    state.current_player_index = 0
    state.supply["Silver"] = 10
    state.supply["Curse"] = 10

    blockade = get_card("Blockade")
    player_a.hand = [blockade]
    play_action(state, player_a, blockade)

    # Player B gains the same card → should also gain a Curse.
    state.supply["Silver"] -= 1
    state.gain_card(player_b, get_card("Silver"))
    assert any(c.name == "Curse" for c in player_b.discard)


def test_corsair_does_not_trash_treasure_of_lighthouse_defender():
    """A Lighthouse-defending opponent at Corsair-play time must remain immune
    on later turns when they play their first Silver/Gold.
    """
    class PlayTreasuresAI(DummyAI):
        def choose_treasure(self, state, choices):
            for c in choices:
                if c is not None:
                    return c
            return None

    state = _make_state(num_players=2, ai_class=PlayTreasuresAI)
    attacker, defender = state.players
    state.current_player_index = 0

    # Defender has Lighthouse in duration when Corsair is played.
    defender.duration.append(get_card("Lighthouse"))

    corsair = get_card("Corsair")
    attacker.hand = [corsair]
    play_action(state, attacker, corsair)

    # Defender's later turn — plays Silver. Corsair must not trash it.
    state.current_player_index = 1
    silver = get_card("Silver")
    defender.hand = [silver]
    state.phase = "treasure"
    state.handle_treasure_phase()

    assert silver not in state.trash, \
        "Corsair must not trash treasures of opponents protected at play time"
    assert silver in defender.in_play
    assert defender.coins == 2


def test_corsair_trashes_first_silver_played_by_opponent():
    class PlayTreasuresAI(DummyAI):
        def choose_treasure(self, state, choices):
            for c in choices:
                if c is not None:
                    return c
            return None

    state = _make_state(num_players=2, ai_class=PlayTreasuresAI)
    player_a, player_b = state.players
    state.current_player_index = 0

    corsair = get_card("Corsair")
    player_a.hand = [corsair]
    play_action(state, player_a, corsair)

    # Player B takes their turn — plays Silver.
    state.current_player_index = 1
    silver = get_card("Silver")
    player_b.hand = [silver]
    state.phase = "treasure"
    state.handle_treasure_phase()

    assert silver in state.trash
    assert player_b.corsair_trashed_this_turn
    # The Silver was played first → +$2 should still have been gained before
    # Corsair trashed it from in-play.
    assert player_b.coins == 2, \
        "Corsair must trash AFTER on_play, so the +$ from Silver still applies"


def test_sailor_plays_gained_duration_card():
    class SailorAI(DummyAI):
        def should_play_gain_with_sailor(self, state, player, gained_card):
            return True

    state = _make_state(ai_class=SailorAI)
    player = state.players[0]
    state.supply["Caravan"] = 10

    sailor = get_card("Sailor")
    player.deck = [get_card("Copper") for _ in range(5)]
    player.hand = [sailor]
    play_action(state, player, sailor)

    state.supply["Caravan"] -= 1
    state.gain_card(player, get_card("Caravan"))

    # Sailor played the gained Caravan: +1 Card drawn, Caravan in play.
    assert any(c.name == "Caravan" for c in player.in_play)


def test_sailor_does_not_play_gained_non_duration_action():
    class SailorAI(DummyAI):
        def should_play_gain_with_sailor(self, state, player, gained_card):
            return True

    state = _make_state(ai_class=SailorAI)
    player = state.players[0]
    state.supply["Smithy"] = 10

    sailor = get_card("Sailor")
    player.deck = [get_card("Copper") for _ in range(5)]
    player.hand = [sailor]
    play_action(state, player, sailor)

    hand_before = len(player.hand)
    state.supply["Smithy"] -= 1
    state.gain_card(player, get_card("Smithy"))

    # Smithy is an Action but not a Duration — Sailor should NOT play it.
    assert all(c.name != "Smithy" for c in player.in_play)
    assert any(c.name == "Smithy" for c in player.discard)
    # No extra cards drawn (Smithy would have drawn 3).
    assert len(player.hand) == hand_before


def test_sailor_grants_two_coins_next_turn():
    state = _make_state()
    player = state.players[0]

    sailor = get_card("Sailor")
    player.hand = [sailor]
    play_action(state, player, sailor)

    assert sailor in player.duration
    coins_before = player.coins
    sailor.on_duration(state)
    assert player.coins == coins_before + 2


# -- Sea Chart ---------------------------------------------------------------


def test_sea_chart_reveals_and_takes_when_no_copy_in_play():
    state = _make_state()
    player = state.players[0]

    sea_chart = get_card("Sea Chart")
    # deck[-1] = top. We want Sea Chart's +1 Card to draw the Copper
    # (top), then reveal Village, no matching Village in play, so Village
    # goes to hand.
    village = get_card("Village")
    copper = get_card("Copper")
    player.deck = [village, copper]  # bottom=village, top=copper
    player.hand = [sea_chart]

    play_action(state, player, sea_chart)

    # +1 Card drew the Copper from the top.
    assert copper in player.hand
    # Sea Chart then revealed the new top (Village). No copy of Village in
    # play, so Village goes to hand.
    assert village in player.hand
    assert player.deck == []


def test_sea_chart_revealed_card_stays_when_matching_copy_in_play():
    state = _make_state()
    player = state.players[0]

    sea_chart = get_card("Sea Chart")
    matching = get_card("Village")
    village_top = get_card("Village")
    # Place a Village already in play, and arrange for the reveal to land
    # on a Village too.
    player.in_play = [matching]
    # Top of deck after +1 Card draw must be Village.
    # We need at least 2 cards: top one drawn by +1 Card, top of remaining
    # is what Sea Chart reveals.
    drawn_first = get_card("Copper")
    player.deck = [village_top, drawn_first]  # top=drawn_first, then village_top
    player.hand = [sea_chart]

    play_action(state, player, sea_chart)

    # +1 Card drew the Copper.
    assert drawn_first in player.hand
    # Sea Chart revealed Village. Copy of Village IS in play (the one set
    # aside as `matching`), so revealed card stays on top of the deck.
    assert village_top not in player.hand
    assert player.deck and player.deck[-1] is village_top


# -- Lighthouse vs Witch -----------------------------------------------------


def test_lighthouse_blocks_witch_curse():
    """A defender with a Lighthouse in their duration zone must not gain a
    Curse when an opponent plays Witch.
    """
    state = _make_state(num_players=2)
    attacker, defender = state.players
    state.current_player_index = 0

    # Defender has a Lighthouse in duration (i.e. previously played).
    defender.duration.append(get_card("Lighthouse"))

    # Need Curses in supply.
    state.supply["Curse"] = 10
    initial_curse_supply = state.supply["Curse"]

    witch = get_card("Witch")
    attacker.hand = [witch]
    play_action(state, attacker, witch)

    # Defender shouldn't have gained a Curse.
    assert not any(c.name == "Curse" for c in defender.discard)
    assert not any(c.name == "Curse" for c in defender.hand)
    assert state.supply["Curse"] == initial_curse_supply


def test_lighthouse_played_then_witch_attacks_no_curse():
    """End-to-end: defender plays Lighthouse on their turn; when an opponent
    later plays Witch (still during the Lighthouse's duration window), the
    defender is immune.
    """
    state = _make_state(num_players=2)
    defender, attacker = state.players
    state.current_player_index = 0

    # Defender plays Lighthouse on their own turn.
    lighthouse = get_card("Lighthouse")
    defender.hand = [lighthouse]
    play_action(state, defender, lighthouse)
    assert lighthouse in defender.duration

    # Hand off the turn.
    state.current_player_index = 1
    state.supply["Curse"] = 10
    initial_curses = state.supply["Curse"]

    witch = get_card("Witch")
    attacker.hand = [witch]
    play_action(state, attacker, witch)

    assert not any(c.name == "Curse" for c in defender.discard)
    assert state.supply["Curse"] == initial_curses


def test_lighthouse_immunity_ends_after_duration_resolves():
    """Once Lighthouse's on_duration runs (next turn cleanup), the card is
    no longer in the duration zone and immunity ends.
    """
    state = _make_state(num_players=2)
    defender, attacker = state.players
    state.current_player_index = 0

    lighthouse = get_card("Lighthouse")
    defender.duration.append(lighthouse)

    # Resolve the duration effect (start of defender's next turn).
    lighthouse.on_duration(state)
    # Mimic GameState.do_duration_phase removing it after the effect.
    if not lighthouse.duration_persistent:
        defender.duration.remove(lighthouse)
        defender.discard.append(lighthouse)

    assert lighthouse not in defender.duration

    # Now an attack should land — defender takes a curse.
    state.current_player_index = 1
    state.supply["Curse"] = 10
    witch = get_card("Witch")
    attacker.hand = [witch]
    play_action(state, attacker, witch)

    assert any(c.name == "Curse" for c in defender.discard)


# -- Treasury topdeck end-to-end --------------------------------------------


def test_treasury_topdecks_to_top_of_deck():
    """Treasury's on_buy_phase_end places the card on the top of the deck
    (i.e. ``deck[-1]``), so it will be drawn first next turn.
    """
    state = _make_state()
    player = state.players[0]

    treasury = get_card("Treasury")
    other = get_card("Copper")
    player.in_play = [treasury]
    player.deck = [other]  # bottom card
    player.gained_victory_this_turn = False

    treasury.on_buy_phase_end(state)

    # Treasury should be the top of the deck now.
    assert player.deck and player.deck[-1] is treasury
    assert treasury not in player.in_play


def test_treasury_does_not_topdeck_when_action_phase_victory_gained():
    """gained_victory_this_turn covers Action-phase Victory gains too
    (e.g. Workshop, Charm, Ironworks gaining an Estate).
    """
    state = _make_state()
    player = state.players[0]

    treasury = get_card("Treasury")
    player.in_play = [treasury]
    # Simulate a Victory card gain during the Action phase.
    player.gained_victory_this_turn = True
    player.gained_victory_this_buy_phase = False

    treasury.on_buy_phase_end(state)

    assert treasury in player.in_play
    assert treasury not in player.deck
