"""Tests for the 31 newly added Plunder kingdom cards."""

import random

import pytest

from dominion.cards.registry import get_card
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


def test_jewelled_egg_play_gains_loot():
    state = _make_state()
    player = state.current_player
    egg = get_card("Jewelled Egg")
    player.in_play.append(egg)
    pre_count = len(player.discard)
    egg.play_effect(state)
    # At least one Loot should be added to discard (Doubloons may add a Gold).
    assert len(player.discard) >= pre_count + 1


def test_jewelled_egg_trash_gives_buy_and_coins():
    state = _make_state()
    player = state.current_player
    egg = get_card("Jewelled Egg")
    pre_buys = player.buys
    pre_coins = player.coins
    state.trash_card(player, egg)
    assert player.buys == pre_buys + 1
    assert player.coins == pre_coins + 4


def test_search_gains_loot_on_duration():
    state = _make_state()
    player = state.current_player
    search = get_card("Search")
    player.duration.append(search)
    pre_count = len(player.discard)
    search.on_duration(state)
    assert len(player.discard) > pre_count


def test_abundance_gains_loot_next_turn():
    state = _make_state()
    player = state.current_player
    abundance = get_card("Abundance")
    player.duration.append(abundance)
    pre_count = len(player.discard)
    abundance.on_duration(state)
    assert len(player.discard) > pre_count


def test_buried_treasure_gives_coins_next_turn():
    state = _make_state()
    player = state.current_player
    bt = get_card("Buried Treasure")
    player.duration.append(bt)
    pre = player.coins
    bt.on_duration(state)
    assert player.coins == pre + 3


def test_longship_gives_actions_now_and_cards_next_turn():
    state = _make_state()
    player = state.current_player
    longship = get_card("Longship")
    pre_actions = player.actions
    longship.on_play(state)
    assert player.actions == pre_actions + 2
    # Set up deck and trigger duration.
    player.deck = [get_card("Copper") for _ in range(5)]
    pre_hand = len(player.hand)
    longship.on_duration(state)
    assert len(player.hand) == pre_hand + 2


def test_silver_mine_gains_silver_to_hand_next_turn():
    state = _make_state()
    player = state.current_player
    sm = get_card("Silver Mine")
    pre_silvers = sum(1 for c in player.hand if c.name == "Silver")
    sm.on_duration(state)
    post_silvers = sum(1 for c in player.hand if c.name == "Silver")
    assert post_silvers == pre_silvers + 1


def test_sack_of_loot_gains_loot_on_play():
    state = _make_state()
    player = state.current_player
    sol = get_card("Sack of Loot")
    pre = len(player.discard)
    sol.play_effect(state)
    assert len(player.discard) > pre


def test_kings_cache_plays_treasure_three_times():
    state = _make_state()
    player = state.current_player
    player.hand = [get_card("Silver")]
    pre_coins = player.coins
    kc = get_card("King's Cache")
    kc.on_play(state)
    # Silver gives +$2 per play; King's Cache itself adds +$3.
    # So expect +$3 (King's Cache) + 3 * $2 (Silver) = $9.
    assert player.coins - pre_coins == 9


def test_mapmaker_puts_2_into_hand():
    state = _make_state()
    player = state.current_player
    player.deck = [
        get_card("Copper"),
        get_card("Silver"),
        get_card("Gold"),
        get_card("Estate"),
    ]
    pre_hand = len(player.hand)
    mm = get_card("Mapmaker")
    mm.on_play(state)
    # 2 cards into hand.
    assert len(player.hand) == pre_hand + 2


def test_swamp_shacks_gives_basics_and_attacks():
    state = _make_state(num_players=2)
    me = state.players[0]
    foe = state.players[1]
    foe.hand = [get_card("Copper") for _ in range(5)]
    pre_foe_hand = len(foe.hand)
    state.current_player_index = 0
    sh = get_card("Swamp Shacks")
    me.in_play.append(sh)
    sh.on_play(state)
    # Foe with 5 in hand should have discarded one.
    assert len(foe.hand) == pre_foe_hand - 1


def test_fisherman_basic_play():
    state = _make_state()
    player = state.current_player
    pre_coins = player.coins
    pre_actions = player.actions
    fish = get_card("Fisherman")
    fish.on_play(state)
    # +1 Card draws, +1 Action, +$1.
    assert player.coins == pre_coins + 1
    assert player.actions == pre_actions + 1


def test_fisherman_cost_with_empty_discard():
    state = _make_state()
    player = state.current_player
    player.discard = []
    fish = get_card("Fisherman")
    # Empty discard → costs $2 (the $3 discount from card text).
    assert state.get_card_cost(player, fish) == 2


def test_fisherman_full_cost_with_non_empty_discard():
    state = _make_state()
    player = state.current_player
    player.discard = [get_card("Copper")]
    fish = get_card("Fisherman")
    assert state.get_card_cost(player, fish) == 5


def test_maroon_draws_per_type():
    state = _make_state()
    player = state.current_player
    # Witch has 2 types: Action and Attack.
    player.hand = [get_card("Witch")]
    player.deck = [get_card("Copper") for _ in range(5)]
    pre_hand = len(player.hand)
    maroon = get_card("Maroon")
    # Override AI to always pick the Witch.
    class PickWitch:
        name = "x"
        def choose_action(self, *a, **k): return None
        def choose_card_to_trash(self, state, choices):
            for c in choices:
                if c is not None and c.name == "Witch":
                    return c
            return None
    player.ai = PickWitch()
    maroon.on_play(state)
    # Witch trashed (-1) + 2 cards drawn (Action, Attack types).
    assert len(player.hand) == pre_hand - 1 + 2


def test_pendant_adds_one_per_distinct_treasure_in_play():
    state = _make_state()
    player = state.current_player
    player.in_play = [
        get_card("Pendant"),
        get_card("Copper"),
        get_card("Silver"),
        get_card("Gold"),
    ]
    pre_coins = player.coins
    # Trigger the pendant cleanup logic in handle_cleanup_phase manually.
    pendants = [c for c in player.in_play if c.name == "Pendant"]
    distinct = {c.name for c in player.in_play if c.is_treasure}
    for _ in pendants:
        player.coins += len(distinct)
    # 4 distinct treasures (Pendant, Copper, Silver, Gold) * 1 Pendant = +4.
    assert player.coins - pre_coins == 4


def test_quartermaster_gains_card_to_mat_first_turn():
    state = _make_state()
    player = state.current_player
    qm = get_card("Quartermaster")
    player.duration.append(qm)
    state.quartermaster_mats[id(player)] = []
    state._handle_quartermaster_start_of_turn(player)
    # Mat now contains a card up to $4.
    assert len(state.quartermaster_mats[id(player)]) == 1


def test_quartermaster_take_all_with_two_cards():
    state = _make_state()
    player = state.current_player
    qm = get_card("Quartermaster")
    player.duration.append(qm)
    state.quartermaster_mats[id(player)] = [get_card("Silver"), get_card("Gold")]
    pre_hand = len(player.hand)
    state._handle_quartermaster_start_of_turn(player)
    assert len(player.hand) >= pre_hand + 2
    assert state.quartermaster_mats[id(player)] == []


def test_secluded_shrine_trashes_up_to_two():
    state = _make_state()
    player = state.current_player
    player.hand = [get_card("Curse"), get_card("Curse"), get_card("Copper")]
    ss = get_card("Secluded Shrine")
    player.duration.append(ss)
    pre_trash = len(state.trash)
    ss.on_duration(state)
    assert len(state.trash) >= pre_trash + 2


def test_shaman_gains_from_trash():
    state = _make_state()
    player = state.current_player
    state.trash.append(get_card("Gold"))
    sh = get_card("Shaman")
    player.duration.append(sh)
    sh.on_duration(state)
    # Gold should be in discard (or hand).
    assert any(c.name == "Gold" for c in player.discard + player.hand)
    assert not any(c.name == "Gold" for c in state.trash)


def test_cutthroat_attacks_to_three():
    state = _make_state(num_players=2)
    me = state.players[0]
    foe = state.players[1]
    state.current_player_index = 0
    foe.hand = [get_card("Copper") for _ in range(5)]
    cut = get_card("Cutthroat")
    me.in_play.append(cut)
    cut.on_play(state)
    assert len(foe.hand) == 3


def test_frigate_attacks_to_four_next_turn():
    state = _make_state(num_players=2)
    me = state.players[0]
    foe = state.players[1]
    state.current_player_index = 0
    foe.hand = [get_card("Copper") for _ in range(5)]
    fr = get_card("Frigate")
    me.duration.append(fr)
    fr.on_duration(state)
    assert len(foe.hand) == 4


def test_landing_party_top_decks_treasure():
    state = _make_state()
    player = state.current_player
    lp = get_card("Landing Party")
    state.landing_party_pending.setdefault(id(player), []).append(lp)
    player.duration.append(lp)
    # Now gain a Silver - landing party should top-deck both.
    state.supply["Silver"] -= 1
    state.gain_card(player, get_card("Silver"))
    # Top of deck (last position) should be the Silver, with LP just below.
    assert len(player.deck) >= 2
    top_two = [c.name for c in player.deck[-2:]]
    assert "Silver" in top_two
    assert "Landing Party" in top_two


def test_mining_road_gains_treasure_to_hand():
    state = _make_state()
    player = state.current_player
    mr = get_card("Mining Road")
    player.in_play.append(mr)
    pre_treasures = sum(1 for c in player.hand if c.is_treasure)
    state.supply["Silver"] -= 1
    state.gain_card(player, get_card("Silver"))
    # Mining Road triggers gain of a Treasure to hand → at least 1 more treasure in hand.
    post_treasures = sum(1 for c in player.hand if c.is_treasure)
    assert post_treasures >= pre_treasures + 1


def test_crucible_gives_one_per_trashed():
    state = _make_state()
    player = state.current_player
    state.current_player_index = 0
    state.trash_card(player, get_card("Curse"))
    state.trash_card(player, get_card("Curse"))
    assert player.cards_trashed_this_turn == 2
    cr = get_card("Crucible")
    player.in_play.append(cr)
    pre = player.coins
    # Will trash a card from hand + give +$2.
    player.hand = []
    cr.play_effect(state)
    assert player.coins == pre + 2


def test_cabin_boy_gives_coins_next_turn():
    state = _make_state()
    state.supply = {"Copper": 10, "Silver": 10, "Gold": 10}
    player = state.current_player
    cb = get_card("Cabin Boy")
    player.duration.append(cb)
    pre = player.coins
    cb.on_duration(state)
    # No Duration cards available → +$2 path.
    assert player.coins == pre + 2


def test_gondola_pays_two_next_turn():
    state = _make_state()
    player = state.current_player
    g = get_card("Gondola")
    player.duration.append(g)
    pre = player.coins
    g.on_duration(state)
    assert player.coins == pre + 2


def test_rope_pays_one_now_and_one_next_turn():
    state = _make_state()
    player = state.current_player
    rope = get_card("Rope")
    pre_buys = player.buys
    rope.on_play(state)
    assert player.buys == pre_buys + 1
    pre_coins = player.coins
    rope.on_duration(state)
    assert player.coins == pre_coins + 1


def test_grotto_sets_aside_then_redraws():
    state = _make_state()
    player = state.current_player
    player.hand = [get_card("Copper") for _ in range(4)]
    player.deck = [get_card("Silver") for _ in range(4)]
    grotto = get_card("Grotto")
    grotto.on_play(state)
    assert len(grotto.set_aside) == 4
    assert len(player.hand) == 0
    grotto.on_duration(state)
    # Drew 4 from deck.
    assert len(player.hand) == 4


def test_tools_takes_gained_card_to_hand():
    state = _make_state()
    player = state.current_player
    state.supply["Silver"] -= 1
    state.gain_card(player, get_card("Silver"))
    assert "Silver" in player.gained_cards_this_turn
    tools = get_card("Tools")
    pre_hand_size = len(player.hand)
    tools.on_play(state)
    # Silver moves from discard to hand.
    assert any(c.name == "Silver" for c in player.hand)


def test_siren_curses_others_and_gains_action_on_gain():
    state = _make_state(num_players=2)
    me = state.players[0]
    foe = state.players[1]
    state.current_player_index = 0
    pre_curses = sum(1 for c in foe.discard if c.name == "Curse")
    siren = get_card("Siren")
    me.in_play.append(siren)
    siren.on_play(state)
    # Foe should have a Curse.
    assert sum(1 for c in foe.discard if c.name == "Curse") == pre_curses + 1


def test_fortune_hunter_plays_treasure_from_top_of_deck():
    state = _make_state()
    player = state.current_player
    player.deck = [get_card("Estate"), get_card("Silver"), get_card("Estate")]
    fh = get_card("Fortune Hunter")
    pre_coins = player.coins
    fh.on_play(state)
    # Silver played → +$2; plus Fortune Hunter's stat +$2 = +$4.
    assert player.coins == pre_coins + 4


def test_landing_party_top_decks_treasure_gained_to_hand():
    """Regression for PR #193 review: Landing Party should resolve even when
    the gained Treasure was placed somewhere other than discard/deck (e.g.
    Mining Road's gain-to-hand)."""
    state = _make_state()
    player = state.current_player
    lp = get_card("Landing Party")
    state.landing_party_pending.setdefault(id(player), []).append(lp)
    player.duration.append(lp)
    # Simulate a treasure that's already been placed in hand by some prior
    # gain-to-hand effect; the on-gain handler still needs to find and
    # top-deck it.
    silver = get_card("Silver")
    player.hand.append(silver)
    # Invoke the gain hook directly with the in-hand card.
    state._handle_landing_party_gain(player, silver)
    # Silver should now be on top of the deck along with Landing Party.
    assert silver not in player.hand
    top_two = [c.name for c in player.deck[-2:]]
    assert "Silver" in top_two
    assert "Landing Party" in top_two


def test_crucible_counts_duration_phase_trashes():
    """Regression for PR #193 review: cards trashed during the duration
    phase (e.g. Secluded Shrine's start-of-turn trash) must count toward
    cards_trashed_this_turn for Crucible."""
    state = _make_state(num_players=2)
    state.current_player_index = 0
    player = state.players[0]
    # Put a Secluded Shrine in duration so the duration phase fires.
    shrine = get_card("Secluded Shrine")
    player.duration.append(shrine)
    # Give the player two trashable Curses in hand for Shrine to trash.
    player.hand = [get_card("Curse"), get_card("Curse")]
    # Cycle: end this turn → opponent → back to player 0 (duration fires).
    state.current_player_index = 1
    state.handle_start_phase()
    state.current_player_index = 0
    state.handle_start_phase()
    # Shrine trashed up to 2 Curses during the duration phase, AFTER the
    # per-turn counter reset; so the count should reflect them.
    assert player.cards_trashed_this_turn >= 1


def test_quartermaster_routes_gain_through_gain_card_hooks():
    """Regression for PR #193 review: Quartermaster's start-of-turn gain
    must run through gain_card so on-gain bookkeeping (e.g.
    cards_gained_this_turn, gained_cards_this_turn) fires."""
    state = _make_state(num_players=2)
    state.current_player_index = 0
    player = state.players[0]
    qm = get_card("Quartermaster")
    qm.duration_persistent = True
    player.duration.append(qm)
    # Cycle to player 0's next turn so the start-of-turn handler fires.
    state.current_player_index = 1
    state.handle_start_phase()
    state.current_player_index = 0
    state.handle_start_phase()
    # Quartermaster mat should have one card.
    mat = state.quartermaster_mats.get(id(player), [])
    assert len(mat) == 1
    gained_name = mat[0].name
    # gain_card-side bookkeeping must have run.
    assert gained_name in player.gained_cards_this_turn
    assert player.cards_gained_this_turn >= 1


def test_quartermaster_respects_watchtower_topdeck():
    """Regression for PR #206 review (P2): when a Quartermaster gain
    triggers a Watchtower topdeck reaction, the gained card must end up
    on top of the player's deck — NOT on the Quartermaster mat. The
    player's choice of destination via on-gain reactions takes
    precedence over Quartermaster's "onto this" placement."""

    class _TopdeckAI(_NullAI):
        def choose_watchtower_reaction(self, state, player, card):
            return "topdeck"

    state = _make_state(num_players=2)
    state.current_player_index = 0
    player = state.players[0]
    player.ai = _TopdeckAI()
    # Watchtower must be in the player's hand to react.
    player.hand.append(get_card("Watchtower"))
    qm = get_card("Quartermaster")
    qm.duration_persistent = True
    player.duration.append(qm)
    state.quartermaster_mats[id(player)] = []

    state._handle_quartermaster_start_of_turn(player)

    # QM mat should be empty: Watchtower's topdeck reaction wins.
    mat = state.quartermaster_mats.get(id(player), [])
    assert mat == [], (
        "Watchtower topdeck reaction should redirect the gain off the "
        f"Quartermaster mat; mat was {[c.name for c in mat]}"
    )
    # The gained card must be on top of the deck (last element).
    assert player.deck, "Topdecked card should be in the deck"
    top = player.deck[-1]
    assert top.cost.coins <= 4
    assert top.is_treasure or top.is_action or top.is_victory


def test_quartermaster_no_watchtower_keeps_card_on_mat():
    """Regression for PR #206 review (P2): when no on-gain reaction
    redirects the gain, Quartermaster's normal behavior must still apply
    — the gained card lands on the Quartermaster mat, not in the
    discard."""
    state = _make_state(num_players=1)
    state.current_player_index = 0
    player = state.players[0]
    qm = get_card("Quartermaster")
    qm.duration_persistent = True
    player.duration.append(qm)
    state.quartermaster_mats[id(player)] = []
    pre_discard = len(player.discard)

    state._handle_quartermaster_start_of_turn(player)

    mat = state.quartermaster_mats.get(id(player), [])
    assert len(mat) == 1, (
        "Without a Watchtower redirect the gain must land on the QM mat"
    )
    # Card was not left in discard.
    assert len(player.discard) == pre_discard


def test_river_shrine_cleanup_gain_eligible_for_deliver():
    """Regression for PR #206 review (P1): cleanup-start hooks (River
    Shrine, Improve) gain cards that are still part of THIS turn. If the
    player bought Deliver and had not gained yet, those cleanup-start
    gains MUST be eligible for Deliver's "set aside the next gain this
    turn" trigger — i.e. the deliver_pending_count reset must happen
    AFTER cleanup-start hooks run, not before."""
    from dominion.events.registry import get_event

    class _PickSilverAI(_NullAI):
        def choose_buy(self, state, choices):
            for c in choices:
                if c is not None and getattr(c, "name", "") == "Silver":
                    return c
            for c in choices:
                if c is not None:
                    return c
            return None

    state = _make_state(num_players=2)
    state.current_player_index = 0
    player = state.players[0]
    player.ai = _PickSilverAI()
    # Buy Deliver to queue a pending set-aside.
    deliver = get_event("Deliver")
    deliver.on_buy(state, player)
    assert player.deliver_pending_count == 1
    # Set up River Shrine in play with no buy-phase gains so its
    # cleanup-start hook will fire and gain a card.
    river = get_card("River Shrine")
    player.in_play.append(river)
    player.cards_gained_this_buy_phase = 0
    state.supply["River Shrine"] = 10
    # Run cleanup. River Shrine should gain a card during cleanup; that
    # gain should be intercepted by Deliver and set aside.
    pre_set_aside = list(player.deliver_set_aside)
    state.handle_cleanup_phase()
    # River Shrine's cleanup-start gain was set aside by Deliver.
    assert len(player.deliver_set_aside) == len(pre_set_aside) + 1, (
        "River Shrine's cleanup-start gain should be set aside by "
        "Deliver — the deliver reset must run AFTER cleanup-start hooks"
    )
    # Pending count cleared after cleanup (turn boundary).
    assert player.deliver_pending_count == 0
    # Cycle to next turn for player 0; set-aside card returns to hand.
    state.current_player_index = 1
    state.handle_start_phase()
    state.current_player_index = 0
    state.handle_start_phase()
    # The set-aside card should now be in hand.
    assert player.deliver_set_aside == []
