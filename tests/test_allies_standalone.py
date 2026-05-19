"""Tests for the standalone (non-split) Allies kingdom cards."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import ChooseFirstActionAI, DummyAI


def _state() -> tuple[GameState, PlayerState]:
    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    state.supply = {}
    return state, player


def test_bauble_does_not_grant_unconditional_favor():
    """Bauble offers +1 Favor as ONE of four choices. Without a choice
    mechanism wired up, it must not grant Favor unconditionally."""
    state, player = _state()
    bauble = get_card("Bauble")
    player.in_play.append(bauble)
    favors_before = player.favors
    bauble.on_play(state)
    # Bauble's printed text: "Choose two different options: +1 Buy,
    # +$1, +1 Favor, or this turn when you gain a card you may
    # put it onto your deck." Favor is one of four options, not automatic.
    assert player.favors == favors_before


def test_bauble_can_choose_favor_and_topdeck_gain():
    state, player = _state()

    class _AI(DummyAI):
        def choose_bauble_options(self, state, player, choices, count):
            return ["favor", "topdeck"]

    player.ai = _AI()
    bauble = get_card("Bauble")
    player.in_play.append(bauble)
    favors_before = player.favors
    bauble.on_play(state)

    assert player.favors == favors_before + 1
    assert player.topdeck_gains is True

    gained = state.gain_card(player, get_card("Silver"))
    assert player.deck[-1] is gained
    assert gained not in player.discard


def test_sycophant_grants_favor_on_gain():
    """Per Allies rules: '+2 Favors when you gain or trash this'."""
    state, player = _state()
    sycophant = get_card("Sycophant")
    state.supply = {"Sycophant": 5}
    favors_before = player.favors
    state.gain_card(player, sycophant)
    assert player.favors == favors_before + 2


def test_sycophant_grants_favor_on_trash():
    state, player = _state()
    sycophant = get_card("Sycophant")
    player.in_play.append(sycophant)
    favors_before = player.favors
    state.trash_card(player, sycophant)
    assert player.favors == favors_before + 2


def test_sycophant_does_not_grant_favor_on_play():
    """Sycophant's +2 Favors trigger is on gain/trash, not on play."""
    state, player = _state()
    sycophant = get_card("Sycophant")
    player.in_play.append(sycophant)
    player.hand = [
        get_card("Estate"),
        get_card("Estate"),
        get_card("Estate"),
        get_card("Copper"),
    ]
    favors_before = player.favors
    sycophant.on_play(state)
    assert player.favors == favors_before


def test_sycophant_discards_without_coins_when_fewer_than_three_cards():
    state, player = _state()
    sycophant = get_card("Sycophant")
    player.in_play.append(sycophant)
    player.hand = [
        get_card("Estate"),
        get_card("Copper"),
    ]
    coins_before = player.coins

    sycophant.on_play(state)

    assert player.coins == coins_before
    assert player.hand == []
    assert len(player.discard) == 2


def test_sycophant_discards_three_cards_for_three_coins():
    state, player = _state()
    sycophant = get_card("Sycophant")
    player.in_play.append(sycophant)
    player.hand = [
        get_card("Estate"),
        get_card("Estate"),
        get_card("Copper"),
    ]
    coins_before = player.coins

    sycophant.on_play(state)

    assert player.coins == coins_before + 3
    assert player.hand == []
    assert len(player.discard) == 3


def test_underling_cantrips_with_favor():
    state, player = _state()
    underling = get_card("Underling")
    player.deck = [get_card("Gold")]
    player.in_play.append(underling)
    favors_before = player.favors
    actions_before = player.actions
    underling.on_play(state)
    assert player.favors == favors_before + 1
    assert player.actions == actions_before + 1
    assert any(c.name == "Gold" for c in player.hand)


def test_galleria_grants_buy_on_3_to_5_gain():
    state, player = _state()
    galleria = get_card("Galleria")
    player.in_play.append(galleria)
    galleria.on_play(state)  # +$3
    state.supply["Silver"] = 5
    silver = get_card("Silver")
    buys_before = player.buys
    state.gain_card(player, silver)
    assert player.buys == buys_before + 1


def test_galleria_no_buy_below_range():
    state, player = _state()
    galleria = get_card("Galleria")
    player.in_play.append(galleria)
    galleria.on_play(state)
    state.supply["Copper"] = 5
    state.gain_card(player, get_card("Copper"))
    # Copper cost $0; no extra buy.
    assert player.buys == 1


def test_galleria_does_not_grant_favor_on_play():
    """Galleria's printed text is '+$3' and a buys-on-gain trigger;
    it does not grant +1 Favor on play."""
    state, player = _state()
    galleria = get_card("Galleria")
    player.in_play.append(galleria)
    favors_before = player.favors
    galleria.on_play(state)
    assert player.favors == favors_before


def test_skirmisher_attacks_on_action_gain():
    p1 = PlayerState(DummyAI())
    p2 = PlayerState(DummyAI())
    state = GameState(players=[p1, p2])
    state.supply = {"Smithy": 5}
    state.current_player_index = 0

    skirmisher = get_card("Skirmisher")
    p1.in_play.append(skirmisher)
    skirmisher.on_play(state)

    # Opponent has 5 cards in hand.
    p2.hand = [
        get_card("Copper"),
        get_card("Copper"),
        get_card("Copper"),
        get_card("Copper"),
        get_card("Estate"),
    ]
    smithy = get_card("Smithy")
    state.gain_card(p1, smithy)
    # P2 should have discarded one card (the Estate as worst).
    assert len(p2.hand) == 4


def test_carpenter_no_empty_piles_gains_4():
    state, player = _state()
    state.supply = {"Smithy": 5, "Silver": 5}

    class _AI(DummyAI):
        def choose_buy(self, state, choices):
            for c in choices:
                if c is not None and c.name == "Smithy":
                    return c
            return None

    player.ai = _AI()
    carpenter = get_card("Carpenter")
    player.in_play.append(carpenter)
    carpenter.on_play(state)
    assert any(c.name in {"Smithy", "Silver"} for c in player.discard)


def test_carpenter_with_empty_pile_trashes_and_gains_5():
    state, player = _state()
    state.supply = {"Smithy": 5, "Silver": 5, "Workshop": 0}
    player.hand = [get_card("Estate")]

    class TrashAI(DummyAI):
        def choose_card_to_trash(self, state, choices):
            return choices[0] if choices else None
        def choose_buy(self, state, choices):
            for c in choices:
                if c is not None and c.name == "Smithy":
                    return c
            return choices[-1] if choices else None

    player.ai = TrashAI()
    carpenter = get_card("Carpenter")
    player.in_play.append(carpenter)
    carpenter.on_play(state)
    assert any(c.name == "Estate" for c in state.trash)


def test_courier_plays_action_from_top_of_deck():
    state, player = _state()
    village = get_card("Village")
    player.deck = [village]
    player.actions = 0  # Will gain +1 Action from Village.
    courier = get_card("Courier")
    player.in_play.append(courier)
    courier.on_play(state)
    assert village in player.in_play
    assert player.actions == 2  # +2 Actions from Village


def test_innkeeper_3_minus_3_with_clutter():
    state, player = _state()
    player.deck = [get_card("Gold") for _ in range(5)]
    player.hand = [
        get_card("Curse"),
        get_card("Curse"),
        get_card("Estate"),
    ]

    class DAI(DummyAI):
        def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
            order = sorted(choices, key=lambda c: c.cost.coins)
            return order[:count]

    player.ai = DAI()
    innkeeper = get_card("Innkeeper")
    player.in_play.append(innkeeper)
    innkeeper.on_play(state)
    # Drew 3 then discarded 3.
    assert sum(1 for c in player.discard if c.name == "Curse") == 2


def test_emissary_does_not_grant_unconditional_favor():
    """Per Allies rules, Emissary's +1 Action and +2 Favors are conditional on
    shuffling while drawing. The bonus must not fire unconditionally on play."""
    state, player = _state()
    # No discard pile -> drawing 3 cards from the deck cannot cause a shuffle,
    # so Emissary's conditional bonus must not trigger.
    player.discard = []
    player.deck = [get_card("Gold") for _ in range(5)]
    emissary = get_card("Emissary")
    player.in_play.append(emissary)
    favors_before = player.favors
    emissary.on_play(state)
    assert player.favors == favors_before


def test_emissary_grants_bonus_when_its_draw_shuffles():
    state, player = _state()
    # Emissary's own +3 Cards starts with fewer than 3 cards in deck and
    # at least one card in discard, so it causes a shuffle.
    player.deck = [get_card("Gold")]
    player.discard = [get_card("Silver"), get_card("Estate")]
    emissary = get_card("Emissary")
    player.in_play.append(emissary)
    favors_before = player.favors
    actions_before = player.actions

    emissary.on_play(state)

    assert len(player.hand) == 3
    assert player.favors == favors_before + 2
    assert player.actions == actions_before + 1


def test_specialist_gains_copy_or_replays():
    state, player = _state()
    state.supply = {"Village": 5}
    village = get_card("Village")
    player.hand = [village]

    class _AI(DummyAI):
        def choose_action(self, state, choices):
            for c in choices:
                if c is not None:
                    return c
            return None

    player.ai = _AI()
    specialist = get_card("Specialist")
    player.in_play.append(specialist)
    specialist.on_play(state)
    # Village played; Specialist heuristic chose to gain a copy.
    assert any(c.name == "Village" for c in player.discard) or village in player.in_play


def test_swap_returns_action_for_better():
    state, player = _state()
    state.supply = {"Village": 5, "Smithy": 5}  # Village $3, Smithy $4
    village = get_card("Village")
    player.hand = [village]
    swap = get_card("Swap")
    player.in_play.append(swap)
    swap.on_play(state)
    # Village returned; Smithy gained.
    assert state.supply["Village"] >= 5
    assert any(c.name == "Smithy" for c in player.discard)


def test_broker_trash_options():
    state, player = _state()
    player.hand = [get_card("Silver")]
    player.deck = [get_card("Gold") for _ in range(3)]

    class TrashAI(DummyAI):
        def choose_card_to_trash(self, state, choices):
            return choices[0] if choices else None

    player.ai = TrashAI()
    broker = get_card("Broker")
    player.in_play.append(broker)
    coins_before = player.coins
    favors_before = player.favors
    actions_before = player.actions
    broker.on_play(state)
    # Trashed Silver (cost 3); Broker chose +Cards / +Favor / +Action / +$.
    delta_coins = player.coins - coins_before
    delta_favors = player.favors - favors_before
    delta_actions = player.actions - actions_before
    drew = sum(1 for c in player.hand if c.name == "Gold")
    assert (
        delta_coins == 3
        or delta_favors == 3
        or drew == 3
        or delta_actions == 3
    )


def test_importer_gains_card_at_start_of_next_turn():
    state, player = _state()
    state.supply = {"Smithy": 5, "Silver": 5}

    class _AI(DummyAI):
        def choose_buy(self, state, choices):
            for c in choices:
                if c is not None:
                    return c
            return None

    player.ai = _AI()
    importer = get_card("Importer")
    player.in_play.append(importer)
    importer.on_play(state)
    # Should be staged for duration; at start of next turn fires the gain.
    assert importer in player.duration
    importer.on_duration(state)
    assert any(c.name in {"Smithy", "Silver"} for c in player.discard)


def test_contract_sets_aside_action_and_plays_it():
    state, player = _state()
    village = get_card("Village")
    player.hand = [village]

    class _AI(DummyAI):
        def choose_action(self, state, choices):
            for c in choices:
                if c is not None:
                    return c
            return None

    player.ai = _AI()
    contract = get_card("Contract")
    player.in_play.append(contract)
    contract.on_play(state)
    assert village not in player.hand
    assert contract in player.duration
    actions_before = player.actions
    contract.on_duration(state)
    assert village in player.in_play
    # Village adds +2 Actions; +1 Card requires deck contents we don't have.
    assert player.actions == actions_before + 2


def test_town_chooses_village_mode_when_actions_in_hand():
    state, player = _state()
    player.deck = [get_card("Gold")]
    player.hand = [get_card("Village"), get_card("Smithy")]
    player.actions = 1
    town = get_card("Town")
    player.in_play.append(town)
    town.on_play(state)
    # Village mode: +1 Card +2 Actions.
    assert player.actions == 3


def test_town_buy_mode_when_no_actions_in_hand():
    state, player = _state()
    player.hand = [get_card("Copper")]
    player.actions = 1
    town = get_card("Town")
    player.in_play.append(town)
    coins_before = player.coins
    buys_before = player.buys
    town.on_play(state)
    assert player.buys == buys_before + 1
    assert player.coins == coins_before + 2


def test_hunter_picks_one_per_type():
    state, player = _state()
    player.deck = [
        get_card("Copper"),  # Treasure
        get_card("Estate"),  # Victory
        get_card("Smithy"),  # Action
    ]
    hunter = get_card("Hunter")
    player.in_play.append(hunter)
    hunter.on_play(state)
    hand_names = {c.name for c in player.hand}
    assert "Copper" in hand_names
    assert "Estate" in hand_names
    assert "Smithy" in hand_names


def test_hunter_does_not_grant_favor():
    """Hunter is a Liaison but its printed text does not include +1 Favor."""
    state, player = _state()
    player.deck = [get_card("Copper"), get_card("Estate"), get_card("Smithy")]
    hunter = get_card("Hunter")
    player.in_play.append(hunter)
    favors_before = player.favors
    hunter.on_play(state)
    assert player.favors == favors_before, (
        f"Hunter should not grant a Favor on play (got {player.favors - favors_before})"
    )


def test_importer_does_not_grant_favor_on_play():
    """Per Allies rules, Importer's only Favor effect is at setup (+5 instead
    of +1). Playing Importer must not grant any Favor."""
    state, player = _state()
    state.supply = {"Smithy": 5}
    importer = get_card("Importer")
    player.in_play.append(importer)
    favors_before = player.favors
    importer.on_play(state)
    assert player.favors == favors_before


def test_contract_does_not_grant_favor_on_play():
    """Contract's printed text: +$2 + set-aside Action. No on-play Favor."""
    state, player = _state()
    contract = get_card("Contract")
    player.in_play.append(contract)
    player.hand = []
    favors_before = player.favors
    contract.on_play(state)
    assert player.favors == favors_before


def test_specialist_does_not_grant_favor_on_play():
    """Specialist's printed text: play an Action/Treasure, then replay it or
    gain a copy. No on-play Favor."""
    state, player = _state()
    state.supply = {"Village": 5}
    specialist = get_card("Specialist")
    player.in_play.append(specialist)
    player.hand = []  # nothing to specialize on; trigger should be a no-op
    favors_before = player.favors
    specialist.on_play(state)
    assert player.favors == favors_before


def test_swap_does_not_grant_favor_on_play():
    """Swap's printed text: +1 Card, +1 Action, return-and-gain. No on-play Favor."""
    state, player = _state()
    state.supply = {"Village": 5}
    swap = get_card("Swap")
    player.in_play.append(swap)
    player.hand = []  # nothing to return; trigger should be a no-op
    favors_before = player.favors
    swap.on_play(state)
    assert player.favors == favors_before


def test_capital_city_base_payload():
    state, player = _state()
    cap = get_card("Capital City")
    player.in_play.append(cap)
    player.deck = [get_card("Silver")]
    player.hand = [get_card("Gold")]  # No junk; not low on cards.
    actions_before = player.actions
    coins_before = player.coins
    cap.on_play(state)
    # Base: +1 Card +2 Actions; neither optional clause should trigger.
    assert player.actions == actions_before + 2
    assert player.coins == coins_before  # No discard-for-$2 trigger.
    # Drew the Silver from deck; pay-for-cards clause did not fire.
    assert sorted(c.name for c in player.hand) == ["Gold", "Silver"]


def test_capital_city_discards_two_for_two_coins():
    state, player = _state()
    cap = get_card("Capital City")
    player.in_play.append(cap)
    # Six cards with two pieces of junk; hand is large enough that the
    # second clause (pay $2 for +2 Cards) won't fire on its hand-size check.
    player.hand = [
        get_card("Estate"),
        get_card("Copper"),
        get_card("Gold"),
        get_card("Gold"),
        get_card("Gold"),
        get_card("Gold"),
    ]

    class _AI(DummyAI):
        def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
            order = sorted(choices, key=lambda c: c.cost.coins)
            return order[:count]

    player.ai = _AI()
    coins_before = player.coins
    cap.on_play(state)
    assert player.coins == coins_before + 2
    assert sum(1 for c in player.discard if c.name in {"Estate", "Copper"}) == 2


def test_capital_city_pays_two_for_two_cards():
    state, player = _state()
    cap = get_card("Capital City")
    player.in_play.append(cap)
    player.deck = [get_card("Gold"), get_card("Silver")]
    player.hand = [get_card("Gold")]
    player.coins = 5  # Enough to pay $2.
    cap.on_play(state)
    # Hand was short (<=4) and we had >=$2: pay $2, draw 2.
    assert player.coins == 3
    assert len(player.hand) == 3


def test_guildmaster_grants_favor_per_gain():
    state, player = _state()
    state.supply = {"Silver": 5, "Estate": 5}
    gm = get_card("Guildmaster")
    player.in_play.append(gm)
    favors_before = player.favors
    coins_before = player.coins
    actions_before = player.actions
    gm.on_play(state)
    # Terminal +$3. Guildmaster does NOT give +1 Action.
    assert player.actions == actions_before
    assert player.coins == coins_before + 3
    # While in play, every gain produces +1 Favor.
    state.gain_card(player, get_card("Silver"))
    state.gain_card(player, get_card("Estate"))
    assert player.favors == favors_before + 2


def test_marquis_draws_per_card_then_discards_to_ten():
    state, player = _state()
    player.deck = [get_card("Copper") for _ in range(20)]
    # 8 cards in hand → draw 8 → 16 in hand → discard 6 → 10 left.
    player.hand = [get_card("Estate") for _ in range(4)] + [
        get_card("Copper") for _ in range(4)
    ]

    class _AI(DummyAI):
        def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
            order = sorted(choices, key=lambda c: c.cost.coins)
            return order[:count]

    player.ai = _AI()
    buys_before = player.buys
    marquis = get_card("Marquis")
    player.in_play.append(marquis)
    marquis.on_play(state)
    assert player.buys == buys_before + 1
    assert len(player.hand) == 10


def test_marquis_no_discard_when_under_ten():
    state, player = _state()
    player.deck = [get_card("Copper") for _ in range(5)]
    player.hand = [get_card("Estate"), get_card("Estate")]
    marquis = get_card("Marquis")
    player.in_play.append(marquis)
    marquis.on_play(state)
    # Drew 2; total hand is 4 — no discard required.
    assert len(player.hand) == 4


def test_merchant_camp_topdecks_when_played_via_way():
    """Merchant Camp's "when discarded from play" rider must fire even when
    play_effect is bypassed (e.g. played via a Way like Frog/Sheep). The
    cleanup logic identifies the card by name, not via a flag set inside
    play_effect.
    """
    from dominion.cards.registry import get_card as _get_card
    from dominion.game.game_state import GameState
    from dominion.ways.registry import get_way
    from tests.utils import ChooseFirstActionAI

    class WayPickerAI(ChooseFirstActionAI):
        def choose_way(self, state, card, ways):
            for w in ways:
                if w and w.name == "Way of the Sheep":
                    return w
            return None

    state = GameState(players=[])
    state.initialize_game(
        [WayPickerAI(), ChooseFirstActionAI()],
        [_get_card("Village"), _get_card("Merchant Camp")],
        ways=[get_way("Way of the Sheep")],
    )
    state.supply.setdefault("Silver", 40)
    state.supply.setdefault("Copper", 46)
    p1 = state.players[0]
    p1.actions = 1
    camp = _get_card("Merchant Camp")
    p1.hand = [camp]
    state.phase = "action"
    state.handle_action_phase()  # plays Merchant Camp via Way of the Sheep
    state.handle_treasure_phase()
    state.handle_buy_phase()
    state.handle_cleanup_phase()
    # Merchant Camp should land on top of the deck (drawn into the next
    # hand by the cleanup-end draw), not into the discard pile.
    assert any(c.name == "Merchant Camp" for c in p1.hand)
    assert all(c.name != "Merchant Camp" for c in p1.discard)


def test_merchant_camp_topdecks_on_cleanup():
    state, player = _state()
    state.supply = {}
    state.current_player_index = 0
    camp = get_card("Merchant Camp")
    player.actions = 1
    player.in_play.append(camp)
    actions_before = player.actions
    coins_before = player.coins
    camp.on_play(state)
    # +2 Actions +$1.
    assert player.actions == actions_before + 2
    assert player.coins == coins_before + 1
    # Now run cleanup; Merchant Camp should topdeck instead of discarding.
    # Cleanup itself draws the next 5-card hand, so a topdecked card ends
    # up at the top of the deck and is drawn first into the new hand.
    state.phase = "buy"
    state.handle_cleanup_phase()
    assert any(c.name == "Merchant Camp" for c in player.hand)
    assert all(c.name != "Merchant Camp" for c in player.discard)


def test_sentinel_trashes_junk_and_keeps_the_rest():
    state, player = _state()
    # ``deck.pop()`` draws from the end, so the LAST item in this list is
    # the first card Sentinel reveals.
    player.deck = [
        get_card("Gold"),     # 5th revealed
        get_card("Silver"),   # 4th revealed
        get_card("Smithy"),   # 3rd revealed
        get_card("Estate"),   # 2nd revealed (junk, should trash)
        get_card("Curse"),    # 1st revealed (junk, should trash)
    ]
    sentinel = get_card("Sentinel")
    player.in_play.append(sentinel)
    sentinel.on_play(state)
    trashed_names = {c.name for c in state.trash}
    assert "Curse" in trashed_names
    assert "Estate" in trashed_names
    # Three non-junk cards are back on the deck.
    deck_names = [c.name for c in player.deck]
    assert sorted(deck_names) == sorted(["Gold", "Silver", "Smithy"])


def test_sentinel_redeck_sinks_victory_to_bottom():
    """Untrashed Victory cards should land at the BOTTOM of the deck (drawn
    last), and the highest-cost non-Victory should be on TOP (drawn first
    next turn). ``deck.pop()`` draws from the end, so 'top' means high
    index in ``player.deck``.
    """
    state, player = _state()
    # All cards survive the trash step (none are in the junk-priority list
    # apart from Estate, but only one Estate so up to 2 trashes — Estate
    # gets trashed; the remaining four are kept).
    player.deck = [
        get_card("Gold"),     # 5th revealed
        get_card("Silver"),   # 4th
        get_card("Smithy"),   # 3rd
        get_card("Province"), # 2nd  (Victory; should sink to bottom)
        get_card("Duchy"),    # 1st  (Victory; should sink to bottom)
    ]
    sentinel = get_card("Sentinel")
    player.in_play.append(sentinel)
    sentinel.on_play(state)
    # Victories should be at the BOTTOM (low index in deck).
    assert player.deck[0].is_victory
    assert player.deck[1].is_victory
    # Highest-cost non-Victory (Gold, $6) on TOP (drawn first).
    assert player.deck[-1].name == "Gold"


def test_sentinel_no_trash_when_only_good_cards():
    state, player = _state()
    player.deck = [
        get_card("Gold"),
        get_card("Silver"),
        get_card("Smithy"),
        get_card("Village"),
        get_card("Market"),
    ]
    sentinel = get_card("Sentinel")
    player.in_play.append(sentinel)
    sentinel.on_play(state)
    assert state.trash == []
    assert len(player.deck) == 5


def test_royal_galley_sets_aside_action_for_next_turn_replay():
    state, player = _state()
    village = get_card("Village")
    player.hand = [village]

    class _AI(DummyAI):
        def choose_action(self, state, choices):
            for c in choices:
                if c is not None:
                    return c
            return None

    player.ai = _AI()
    galley = get_card("Royal Galley")
    player.in_play.append(galley)
    actions_before = player.actions
    galley.on_play(state)
    # Village is played once now, then set aside for next turn.
    assert player.actions == actions_before + 2
    assert village not in player.in_play
    assert galley in player.duration

    state.do_duration_phase()

    assert player.actions == actions_before + 4
    assert village in player.in_play
    assert galley in player.discard
    assert galley not in player.duration
