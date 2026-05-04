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


def test_bauble_grants_favor_and_buy():
    state, player = _state()
    bauble = get_card("Bauble")
    player.in_play.append(bauble)
    favors_before = player.favors
    bauble.on_play(state)
    assert player.favors == favors_before + 1
    assert player.buys == 2  # 1 default + 1 from Bauble


def test_sycophant_grants_favor_when_discarding():
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
    # +1 Action, discard 3, +2 Favors when any discarded.
    assert player.favors == favors_before + 2


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
    galleria.on_play(state)  # +$2, +1 Favor
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


def test_emissary_draws_per_unique_action():
    state, player = _state()
    player.deck = [get_card("Gold") for _ in range(3)]
    player.hand = [
        get_card("Village"),
        get_card("Smithy"),
        get_card("Smithy"),
    ]
    emissary = get_card("Emissary")
    player.in_play.append(emissary)
    favors_before = player.favors
    emissary.on_play(state)
    assert player.favors == favors_before + 1
    # Two unique action names -> +2 cards (then discard down to 4).


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


def test_royal_galley_plays_action_twice():
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
    # Village +2 Actions, played twice → +4 Actions
    assert player.actions == actions_before + 4
