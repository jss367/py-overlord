"""Tests for Menagerie kingdom cards."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI, ChooseFirstActionAI


def _two_player_state(extra_kingdom=None):
    extra_kingdom = extra_kingdom or []
    ai1 = ChooseFirstActionAI()
    ai2 = ChooseFirstActionAI()
    state = GameState(players=[])
    kingdom = [get_card("Village")] + extra_kingdom
    state.initialize_game([ai1, ai2], kingdom)
    state.supply.setdefault("Horse", 30)
    state.supply.setdefault("Curse", 10)
    state.supply.setdefault("Silver", 40)
    state.supply.setdefault("Gold", 30)
    state.supply.setdefault("Estate", 8)
    state.supply.setdefault("Duchy", 8)
    state.supply.setdefault("Province", 8)
    state.supply.setdefault("Copper", 46)
    return state, state.players[0], state.players[1]


def test_supplies_gain_horse_on_top_of_deck():
    state, p1, _ = _two_player_state()
    supplies = get_card("Supplies")
    state.supply["Supplies"] = state.supply.get("Supplies", 10)
    state.supply["Supplies"] -= 1
    state.gain_card(p1, supplies)
    # to_deck=True places at deck[-1], which draw_cards pops next.
    assert any(c.name == "Horse" for c in p1.deck)


def test_camel_train_exiles_non_victory():
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Camel Train")]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Gold" or c.name == "Silver" or c.name == "Copper" for c in p1.exile)
    # The exiled card is not a Victory
    for c in p1.exile:
        assert not c.is_victory


def test_camel_train_exiles_gold_on_gain():
    state, p1, _ = _two_player_state()
    state.supply["Camel Train"] = state.supply.get("Camel Train", 10)
    state.supply["Camel Train"] -= 1
    state.gain_card(p1, get_card("Camel Train"))
    assert any(c.name == "Gold" for c in p1.exile)


def test_goatherd_left_count():
    state, p1, p2 = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Goatherd"), get_card("Estate"), get_card("Copper")]
    # Pad p2 hand to >= 5
    p2.hand = [get_card("Copper")] * 5
    state.phase = "action"
    state.handle_action_phase()
    # +$1 from card + $1 from p2's 5 cards
    assert p1.coins >= 2


def test_stockpile_exiles_itself_when_played():
    state, p1, _ = _two_player_state()
    s = get_card("Stockpile")
    p1.in_play = [s]
    s.on_play(state)
    assert s in p1.exile
    assert s not in p1.in_play
    assert p1.coins == 3
    assert p1.buys == 2  # base 1 + 1 from card


def test_bounty_hunter_no_coin_when_already_exiled():
    state, p1, _ = _two_player_state()
    p1.exile = [get_card("Estate")]
    p1.hand = [get_card("Bounty Hunter"), get_card("Estate")]
    p1.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Estate name already exiled → no +$3
    assert p1.coins == 0


def test_bounty_hunter_gives_three_coins_for_new_exile():
    state, p1, _ = _two_player_state()
    p1.hand = [get_card("Bounty Hunter"), get_card("Copper")]
    p1.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    assert p1.coins == 3


def test_groom_action_gain_horse():
    state, p1, _ = _two_player_state()
    state.supply["Village"] = state.supply.get("Village", 10)
    p1.hand = [get_card("Groom")]
    p1.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Should have gained a Village (action) and a Horse
    gained_names = {c.name for c in p1.discard + p1.deck}
    assert "Horse" in gained_names


def test_cavalry_gains_two_horses_on_play():
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Cavalry")]
    state.phase = "action"
    state.handle_action_phase()
    horse_count = sum(1 for c in p1.discard if c.name == "Horse")
    assert horse_count == 2


def test_sheepdog_plays_when_gaining():
    state, p1, _ = _two_player_state()
    p1.hand = [get_card("Sheepdog")]
    # Trigger gain
    state.supply["Silver"] -= 1
    state.gain_card(p1, get_card("Silver"))
    # Sheepdog should be in play (after self-trigger), and we drew 2 cards.
    assert any(c.name == "Sheepdog" for c in p1.in_play)


def test_sleigh_puts_gained_card_into_hand():
    state, p1, _ = _two_player_state()
    p1.hand = [get_card("Sleigh")]
    state.supply["Silver"] -= 1
    state.gain_card(p1, get_card("Silver"))
    # Silver should be in hand (Sleigh used 'hand' option)
    assert any(c.name == "Silver" for c in p1.hand)
    assert any(c.name == "Sleigh" for c in p1.discard)


def test_falconer_play_gains_cheaper_card_to_hand():
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Falconer")]
    state.supply["Silver"] = state.supply.get("Silver", 40)
    state.phase = "action"
    state.handle_action_phase()
    # Falconer cost = $5; should have gained a card costing < $5 (Silver) into hand
    assert any(c.name in ("Silver", "Village", "Estate") for c in p1.hand)


def test_kiln_gains_copy_of_next_play():
    state, p1, _ = _two_player_state()
    state.supply["Village"] = 10
    p1.actions = 1
    # Kiln in play, then play a Village; should gain a Village copy.
    kiln = get_card("Kiln")
    p1.in_play.append(kiln)
    kiln.on_play(state)
    # Now simulate playing a Village (cost=3)
    village = get_card("Village")
    p1.hand = [village]
    state.phase = "action"
    state.handle_action_phase()
    village_gained = sum(1 for c in p1.discard if c.name == "Village")
    assert village_gained == 1


def test_livery_grants_horse_on_gain_4plus():
    state, p1, _ = _two_player_state()
    state.supply["Village"] = state.supply.get("Village", 10)
    p1.in_play.append(get_card("Livery"))
    # Gain a $4 card (Smithy substitute → use Wayfarer? No: use a $4 card.
    # Use Bounty Hunter which is $4.
    state.supply["Bounty Hunter"] = state.supply.get("Bounty Hunter", 10)
    state.supply["Bounty Hunter"] -= 1
    state.gain_card(p1, get_card("Bounty Hunter"))
    horse_count = sum(1 for c in p1.discard if c.name == "Horse")
    assert horse_count == 1


def test_animal_fair_cost_reduction():
    state, p1, _ = _two_player_state()
    af = get_card("Animal Fair")
    p1.in_play = [get_card("Village"), get_card("Smithy")]
    cost = state.get_card_cost(p1, af)
    # 7 - 2*2 = 3
    assert cost == 3


def test_wayfarer_cost_matches_last_gain():
    state, p1, _ = _two_player_state()
    p1.gained_cards_this_turn = ["Silver"]  # Silver costs 3
    wf = get_card("Wayfarer")
    cost = state.get_card_cost(p1, wf)
    assert cost == 3


def test_sanctuary_basics():
    state, p1, _ = _two_player_state()
    p1.hand = [get_card("Sanctuary"), get_card("Estate"), get_card("Copper"), get_card("Copper")]
    p1.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Should have +1 buy and have exiled an Estate
    assert any(c.name == "Estate" for c in p1.exile)
    assert p1.buys == 2


def test_black_cat_curses_opponents_when_reacted_off_turn():
    state, p1, p2 = _two_player_state()
    # p2 owns the Black Cat in hand; p1 (current player) gains a Victory
    # card → p2's Black Cat triggers, cursing p1.
    p2.hand.append(get_card("Black Cat"))
    state.supply["Estate"] = state.supply.get("Estate", 8)
    state.supply["Estate"] -= 1
    curses_before = state.supply.get("Curse", 0)
    state.gain_card(p1, get_card("Estate"))
    # The Black Cat owner curses each other player (p1 gets a Curse).
    assert any(c.name == "Curse" for c in p1.exile + p1.discard + p1.deck + p1.hand)
    assert state.supply["Curse"] == curses_before - 1


def test_falconer_reaction_gains_cheaper_card():
    state, p1, p2 = _two_player_state()
    # p2 has a Falconer in hand, p1 gains a Gold ($6).
    p2.hand.append(get_card("Falconer"))
    state.supply["Gold"] = state.supply.get("Gold", 30)
    state.supply["Gold"] -= 1
    state.gain_card(p1, get_card("Gold"))
    # p2 should have gained something cheaper than Gold.
    cheaper_gain = any(c.cost.coins < 6 for c in p2.discard + p2.deck)
    assert cheaper_gain


def test_coven_exiles_curse_for_opponent():
    state, p1, p2 = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Coven")]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Curse" for c in p2.exile)


def test_cavalry_on_gain_in_buy_phase_does_not_grant_action():
    """Buying Cavalry returns to action phase but must not grant a free Action."""
    state, p1, _ = _two_player_state()
    state.supply["Cavalry"] = state.supply.get("Cavalry", 10)
    state.phase = "buy"
    p1.actions = 0
    state.supply["Cavalry"] -= 1
    state.gain_card(p1, get_card("Cavalry"))
    # Phase reverts but actions stay at 0 — the card text never grants +1 Action.
    assert state.phase == "action"
    assert p1.actions == 0


def test_multiple_sheepdogs_all_react_to_single_gain():
    """Each Sheepdog in hand should independently react to a gain."""
    state, p1, _ = _two_player_state()
    p1.hand = [get_card("Sheepdog"), get_card("Sheepdog")]
    p1.deck = [get_card("Copper")] * 10
    state.supply["Silver"] -= 1
    state.gain_card(p1, get_card("Silver"))
    # Both Sheepdogs played from hand into in_play.
    assert sum(1 for c in p1.in_play if c.name == "Sheepdog") == 2


def test_sheepdog_off_turn_reacts_for_owner():
    """Sheepdog should draw cards for its owner, not the active player, when
    the gain happens on another player's turn."""
    state, p1, p2 = _two_player_state()
    # p1 is the current player; p2 owns Sheepdog and is gaining a Curse via
    # an opponent's effect (e.g. Black Cat). Simulate by directly gaining on
    # p2 while p1 is the current player.
    p2.hand = [get_card("Sheepdog")]
    p2.deck = [get_card("Estate"), get_card("Estate")]
    p1_hand_before = len(p1.hand)
    state.supply["Curse"] -= 1
    state.gain_card(p2, get_card("Curse"))
    # p2 should have +2 cards drawn (their hand grew by 2 from deck).
    assert any(c.name == "Estate" for c in p2.hand)
    # p1's hand size is unchanged — Sheepdog did not draw for the active player.
    assert len(p1.hand) == p1_hand_before


def test_displace_exiles_and_gains_upgraded_card():
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Displace"), get_card("Estate")]
    state.supply["Duchy"] = state.supply.get("Duchy", 8)
    pre_exile = list(p1.exile)
    state.phase = "action"
    state.handle_action_phase()
    # Estate (cost 2) exiled; nothing else moved through exile mat.
    assert any(c.name == "Estate" for c in p1.exile)
    assert len(p1.exile) == len(pre_exile) + 1
    # A non-Estate replacement card costing up to $4 was gained.
    new_cards = p1.discard + p1.deck
    assert any(
        c.name != "Estate" and c.cost.coins <= 4 for c in new_cards
    )


def test_displace_does_not_gain_same_named_card():
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Displace"), get_card("Copper")]
    # Restrict supply to only Copper (cost 0) → no differently named affordable
    # card exists, so nothing should be gained.
    state.supply = {"Copper": 40}
    pre_supply = state.supply["Copper"]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Copper" for c in p1.exile)
    # Supply Copper count unchanged — no Copper was gained as replacement.
    assert state.supply["Copper"] == pre_supply


def test_displace_can_gain_duration_card():
    state, p1, _ = _two_player_state()
    p1.actions = 1
    # Silver (cost $3) → ceiling $5. Wharf is $5 Duration, gainable.
    p1.hand = [get_card("Displace"), get_card("Silver")]
    state.supply = {"Wharf": 10}
    pre_supply = state.supply["Wharf"]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Silver" for c in p1.exile)
    assert state.supply["Wharf"] == pre_supply - 1


def test_displace_rejects_higher_debt_candidates():
    """Exiling an Estate (0 debt) must not allow gaining a card with debt
    cost (e.g. City Quarter at $0 + 8 debt), even if its coin cost fits."""
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Displace"), get_card("Estate")]
    state.supply = {"City Quarter": 10}
    pre_supply = state.supply["City Quarter"]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Estate" for c in p1.exile)
    assert state.supply["City Quarter"] == pre_supply


def test_displace_resolves_knights_top_card_not_pile_placeholder():
    """An ordered pile like Knights should expose its top card as the
    candidate, not the pile placeholder; gaining decrements the pile and
    pops its order list."""
    state, p1, _ = _two_player_state()
    p1.actions = 1
    # Silver ($3) → ceiling $5. Knights are $5; the visible top knight
    # should be a legal Displace target.
    p1.hand = [get_card("Displace"), get_card("Silver")]
    state.supply = {"Knights": 10}
    state.pile_order = dict(getattr(state, "pile_order", {}))
    # Mimic how Knights piles are normally seeded — top of pile is the last
    # element of pile_order["Knights"].
    state.pile_order["Knights"] = ["Dame Anna", "Dame Josephine"]
    pre_supply = state.supply["Knights"]
    pre_order_len = len(state.pile_order["Knights"])
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Silver" for c in p1.exile)
    assert state.supply["Knights"] == pre_supply - 1
    assert len(state.pile_order["Knights"]) == pre_order_len - 1
    # The placeholder pile name "Knights" must NOT appear in the player's
    # cards (it isn't a real, instantiable card).
    assert not any(
        c.name == "Knights" for c in p1.discard + p1.deck + p1.hand
    )


def test_displace_restores_ordered_pile_when_trader_replaces_gain():
    """If Trader replaces a Displace gain from an ordered pile, the pile's
    supply count and order list must be restored — gain_card's standard
    Trader restore keys off the specific knight name and silently misses
    for the pile placeholder."""
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [
        get_card("Displace"),
        get_card("Silver"),
        get_card("Trader"),
    ]
    # Force the Trader reaction to fire on any gain.
    p1.ai.should_reveal_trader = lambda *args, **kwargs: True
    state.supply = {"Knights": 10, "Silver": 40}
    state.pile_order = dict(getattr(state, "pile_order", {}))
    state.pile_order["Knights"] = ["Dame Anna", "Dame Josephine"]
    pre_supply = state.supply["Knights"]
    pre_order = list(state.pile_order["Knights"])
    state.phase = "action"
    state.handle_action_phase()
    # Trader should have intercepted the Knight gain and given a Silver
    # instead. The Knights pile must look untouched.
    assert state.supply["Knights"] == pre_supply
    assert state.pile_order["Knights"] == pre_order
    assert any(c.name == "Silver" for c in p1.discard + p1.deck)


def test_displace_does_not_gain_horse_from_non_supply_pile():
    """Horse lives in game_state.supply for lookup convenience but is a
    non-Supply pile per Menagerie rules. Displace must not gain Horses."""
    state, p1, _ = _two_player_state()
    p1.actions = 1
    # Copper ($0) → ceiling $2; Horse ($0) would otherwise fit.
    p1.hand = [get_card("Displace"), get_card("Copper")]
    state.supply = {"Horse": 30}
    pre_supply = state.supply["Horse"]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Copper" for c in p1.exile)
    assert state.supply["Horse"] == pre_supply
    assert not any(c.name == "Horse" for c in p1.discard + p1.deck + p1.hand)


def test_displace_skips_non_supply_piles_even_when_untagged():
    """Madman, Mercenary, Imp, etc. are added to state.supply by setup
    paths that don't tag non_supply_pile_names. Their may_be_gained
    must filter them out so Displace can't illegally gain them."""
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Displace"), get_card("Copper")]
    state.supply = {"Madman": 10, "Mercenary": 10, "Imp": 13}
    pre = dict(state.supply)
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Copper" for c in p1.exile)
    # No non-Supply cards were gained.
    for name, count in pre.items():
        assert state.supply[name] == count


def test_displace_can_gain_grand_market_with_copper_in_play():
    """Grand Market's may_be_bought returns False while Copper is in
    play, but that's a buy-only restriction — Displace gains can still
    target Grand Market."""
    state, p1, _ = _two_player_state()
    p1.actions = 1
    # Copper in play makes Grand Market unbuyable; doesn't block gains.
    p1.in_play.append(get_card("Copper"))
    # Estate ($2) → ceiling $4. Use Silver ($3) → ceiling $5. Grand
    # Market is $6 — too expensive. Use Gold ($6) → ceiling $8.
    p1.hand = [get_card("Displace"), get_card("Gold")]
    state.supply = {"Grand Market": 10}
    pre_supply = state.supply["Grand Market"]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Gold" for c in p1.exile)
    assert state.supply["Grand Market"] == pre_supply - 1


def test_displace_skips_split_pile_bottom_when_covered():
    """Catapult/Rocks split pile: while Catapult (top) is present, Rocks
    (bottom) is not gainable via Displace even though Rocks is in supply
    at a permitted cost."""
    state, p1, _ = _two_player_state()
    p1.actions = 1
    # Silver ($3) → ceiling $5. Rocks costs $4; Catapult costs $3.
    p1.hand = [get_card("Displace"), get_card("Silver")]
    state.supply = {"Catapult": 5, "Rocks": 5}
    pre_rocks = state.supply["Rocks"]
    pre_cat = state.supply["Catapult"]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Silver" for c in p1.exile)
    # Rocks is still untouched; only Catapult could legally be gained.
    assert state.supply["Rocks"] == pre_rocks
    assert state.supply["Catapult"] == pre_cat - 1


def test_displace_restores_ordered_pile_on_exile_reclamation():
    """If the player has the top Knight already on their Exile mat,
    gain_card reclaims that exile copy and tries to restore the supply
    via the specific knight's name — which doesn't exist as a supply
    key for ordered piles — silently no-opping. The Knights pile must
    be restored manually so it isn't permanently decremented."""
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Displace"), get_card("Silver")]
    state.supply = {"Knights": 10}
    state.pile_order = dict(getattr(state, "pile_order", {}))
    state.pile_order["Knights"] = ["Dame Anna", "Dame Josephine"]
    # Top knight already exiled — Displace's gain will reclaim it.
    p1.exile.append(get_card("Dame Josephine"))
    pre_supply = state.supply["Knights"]
    pre_order = list(state.pile_order["Knights"])
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Silver" for c in p1.exile)
    assert state.supply["Knights"] == pre_supply
    assert state.pile_order["Knights"] == pre_order
    assert any(c.name == "Dame Josephine" for c in p1.discard)


def test_displace_does_not_double_restore_pile_on_changeling_exchange():
    """When Displace gains from an ordered pile and Changeling exchanges
    the gain, gain_card's Changeling path already restores the pile.
    Displace must not restore a second time."""
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Displace"), get_card("Silver")]
    p1.ai.should_exchange_changeling = lambda *args, **kwargs: True
    state.supply = {"Knights": 10, "Changeling": 10}
    state.pile_order = dict(getattr(state, "pile_order", {}))
    state.pile_order["Knights"] = ["Dame Anna", "Dame Josephine"]
    pre_supply = state.supply["Knights"]
    pre_order = list(state.pile_order["Knights"])
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Silver" for c in p1.exile)
    # After Changeling exchange, the Knights pile must be exactly as it
    # was before — not double-restored. The placeholder count must not
    # exceed pre-game state, and pile_order must not contain duplicates.
    assert state.supply["Knights"] == pre_supply
    assert state.pile_order["Knights"] == pre_order
    assert any(c.name == "Changeling" for c in p1.discard + p1.deck)


def test_displace_uses_effective_cost_for_candidates():
    """Cost-reducing cards in play (e.g. Bridge) must lower a candidate's
    effective cost, allowing a Province-cost gain when discounted."""
    state, p1, _ = _two_player_state()
    p1.actions = 1
    # Bridge in play reduces every card's cost by $1.
    p1.in_play.append(get_card("Bridge"))
    p1.hand = [get_card("Displace"), get_card("Silver")]  # Silver costs $3
    # Supply contains Gold ($6, but $5 with Bridge). Silver's effective cost
    # is $2; ceiling = $4. Without the Bridge fix, Gold (printed $6) is
    # rejected; with the fix, Gold ($5 effective) is still > $4, so still
    # rejected. Use Province ($8 → $7) — also rejected. Use Duchy ($5 → $4)
    # which should now be gainable.
    state.supply = {"Duchy": 8}
    pre_supply = state.supply["Duchy"]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Silver" for c in p1.exile)
    # Duchy is now gainable because Bridge brings its effective cost to $4.
    assert state.supply["Duchy"] == pre_supply - 1


def test_kiln_consumes_trigger_when_pile_empty():
    """If the next-played card has no supply pile to copy from, Kiln still
    consumes its pending charge so it cannot carry over to a later card."""
    state, p1, _ = _two_player_state()
    state.supply["Village"] = 10
    p1.actions = 5
    kiln = get_card("Kiln")
    p1.in_play.append(kiln)
    kiln.on_play(state)  # Sets kiln_pending = 1
    # Empty the Village pile and play a Village (which has no copies left).
    village_a = get_card("Village")
    state.supply["Village"] = 0
    p1.hand = [village_a, get_card("Village")]
    state.phase = "action"
    state.handle_action_phase()
    # Pending must have been consumed by the first play even though no copy
    # could be gained.
    assert getattr(p1, "kiln_pending", 0) == 0
