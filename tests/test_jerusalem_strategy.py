"""Policy regressions for the Jerusalem board strategy family.

These cover the play rules the board search depends on, independently of
which parameter set currently wins.
"""

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategies.jerusalem_seeds import (
    CARD_KEYS,
    DEFAULTS,
    Jerusalem,
)
from tests.test_jerusalem_board_cards import BOARD


def _state(strategy, opponent=None):
    ais = [GeneticAI(strategy), GeneticAI(opponent or Jerusalem())]
    state = GameState(players=[], supply={})
    state.log_callback = lambda *_: None
    state.initialize_game(ais, [get_card(n) for n in BOARD])
    for p in state.players:
        p.hand = []
        p.deck = []
        p.discard = []
        p.in_play = []
        p.actions = 1
        p.buys = 1
        p.coins = 0
    return state


def _deck(player, names):
    player.discard = [get_card(n) for n in names]


# --------------------------------------------------- Ambassador economy floor


def test_ambassador_will_not_shed_copper_below_the_floor():
    """The floor is what stops an Ambassador deck thinning itself broke."""
    strategy = Jerusalem(ambassador=1, copper_floor=3)
    state = _state(strategy)
    player = state.players[0]
    _deck(player, ["Copper"] * 2)
    copper = get_card("Copper")
    player.hand = [copper]  # three Coppers in the deck, floor of three

    assert strategy.choose_card_to_ambassador(state, player, [copper]) is None
    assert strategy.choose_ambassador_return_count(state, player, copper, 2) == 0


def test_ambassador_sheds_copper_once_the_deck_has_spares():
    strategy = Jerusalem(ambassador=1, copper_floor=3)
    state = _state(strategy)
    player = state.players[0]
    _deck(player, ["Copper"] * 6)
    copper = get_card("Copper")
    assert strategy.choose_card_to_ambassador(state, player, [copper]) is copper
    assert strategy.choose_ambassador_return_count(state, player, copper, 2) == 2


def test_the_copper_reserve_is_flat_and_not_discounted_by_bought_treasure():
    """Buying Silver does not license shedding another Copper.

    The reserve has to be one number: it governs both which card Ambassador
    names and how many copies it returns, and those disagreeing is what makes
    the deck name Copper and then return none of it.
    """
    strategy = Jerusalem(ambassador=1, copper_floor=3)
    state = _state(strategy)
    player = state.players[0]
    _deck(player, ["Copper", "Copper", "Copper", "Silver", "Silver"])
    copper = get_card("Copper")

    assert strategy._copper_floor(player) == 3
    assert strategy.choose_card_to_ambassador(state, player, [copper]) is None
    assert strategy.choose_ambassador_return_count(state, player, copper, 2) == 0


def test_ambassador_return_count_uses_the_same_floor_as_the_choice():
    """Naming Copper and then returning zero wastes the Ambassador.

    The selection and the count must read the same reserve. When they
    disagreed, three Coppers plus a Silver at a reserve of three selected
    Copper and returned none of it -- spending an action to hand the
    opponent a free Copper.
    """
    strategy = Jerusalem(ambassador=1, copper_floor=3)
    state = _state(strategy)
    player = state.players[0]
    _deck(player, ["Copper", "Copper", "Copper", "Silver"])
    copper = get_card("Copper")

    assert strategy._copper_floor(player) == 3
    assert strategy.choose_card_to_ambassador(state, player, [copper]) is None
    assert strategy.choose_ambassador_return_count(state, player, copper, 2) == 0


def test_ambassador_never_names_a_card_it_would_return_zero_of():
    """The selection and the count must agree for every Copper total."""
    strategy = Jerusalem(ambassador=1, copper_floor=4)
    state = _state(strategy)
    player = state.players[0]
    copper = get_card("Copper")
    for coppers in range(0, 8):
        for silvers in range(0, 3):
            _deck(player, ["Copper"] * coppers + ["Silver"] * silvers)
            named = strategy.choose_card_to_ambassador(state, player, [copper])
            count = strategy.choose_ambassador_return_count(state, player, copper, 2)
            if named is copper:
                assert count >= 1, (coppers, silvers, count)


def test_ambassador_always_sheds_curses_and_estates():
    strategy = Jerusalem(ambassador=1, copper_floor=99)
    state = _state(strategy)
    player = state.players[0]
    _deck(player, ["Copper"])
    curse, estate = get_card("Curse"), get_card("Estate")
    assert strategy.choose_card_to_ambassador(state, player, [estate, curse]) is curse
    assert strategy.choose_ambassador_return_count(state, player, curse, 2) == 2


def test_ambassador_is_not_played_without_a_target_it_will_shed():
    strategy = Jerusalem(ambassador=1, copper_floor=99)
    state = _state(strategy)
    player = state.players[0]
    _deck(player, ["Copper"])
    ambassador, gold = get_card("Ambassador"), get_card("Gold")
    player.hand = [ambassador, gold]
    assert strategy.choose_action(state, player, [ambassador, None]) is None


def test_trash_policy_measures_the_responder_not_the_current_player():
    """Governor asks every player, and the hook has no player argument.

    ``GeneticAI.choose_card_to_trash`` passes ``state.current_player``. When
    this strategy answers an opponent's Governor that is the attacker, so an
    economy floor read off the attacker's deck would shed a Copper the
    responder still needs.
    """
    strategy = Jerusalem(ambassador=1, copper_floor=3)
    state = _state(strategy)
    attacker, responder = state.players
    # The attacker is Copper-rich; the responder is down to its floor.
    _deck(attacker, ["Copper"] * 9)
    _deck(responder, ["Copper"] * 2)
    copper = get_card("Copper")
    responder.hand = [copper]
    state.current_player_index = 0

    # Governor offers opponents an optional trash, so declining is legal.
    assert strategy.choose_trash(state, attacker, [copper, None]) is None
    # Reading the attacker's nine Coppers instead would have shed this one.
    assert strategy._sheddable(attacker) == ["Curse", "Estate", "Copper"]


def test_trash_policy_falls_back_to_the_given_player_for_loose_cards():
    """Cards not in anyone's hand (a revealed pile) keep the old behaviour."""
    strategy = Jerusalem(ambassador=1, copper_floor=3)
    state = _state(strategy)
    player = state.players[0]
    _deck(player, ["Copper"] * 9)
    assert strategy.choose_trash(state, player, [get_card("Copper")]).name == "Copper"


# ------------------------------------------------------------ Goons and buys


def test_goons_filler_spends_a_spare_buy_on_a_point():
    strategy = Jerusalem(goons=2, goons_filler=True, filler="Copper")
    state = _state(strategy)
    player = state.players[0]
    player.goons_played = 1
    player.coins = 0
    state.phase = "buy"
    copper = get_card("Copper")
    assert strategy.choose_gain(state, player, [copper, None]) is copper


def test_no_filler_buy_without_goons_in_play():
    strategy = Jerusalem(goons=2, goons_filler=True, filler="Copper")
    state = _state(strategy)
    player = state.players[0]
    player.goons_played = 0
    state.phase = "buy"
    assert strategy.choose_gain(state, player, [get_card("Copper"), None]) is None


def test_filler_can_be_switched_off():
    strategy = Jerusalem(goons=2, goons_filler=False)
    state = _state(strategy)
    player = state.players[0]
    player.goons_played = 2
    state.phase = "buy"
    assert strategy.choose_gain(state, player, [get_card("Copper"), None]) is None


# ------------------------------------------------- Ill-Gotten Gains liveness


def test_ill_gotten_gains_is_skipped_once_the_curses_are_gone():
    strategy = Jerusalem(igg=10, build="rush", green_first=False, silver=99)
    state = _state(strategy)
    player = state.players[0]
    state.phase = "buy"
    igg, silver = get_card("Ill-Gotten Gains"), get_card("Silver")

    state.supply["Curse"] = 1
    assert strategy.choose_gain(state, player, [igg, silver, None]) is igg

    state.supply["Curse"] = 0
    state.supply["Ill-Gotten Gains"] = 5
    assert strategy.choose_gain(state, player, [igg, silver, None]) is silver


def test_last_ill_gotten_gains_is_still_worth_taking_for_the_pile():
    strategy = Jerusalem(igg=10, build="rush", green_first=False, silver=99)
    state = _state(strategy)
    player = state.players[0]
    state.phase = "buy"
    state.supply["Curse"] = 0
    state.supply["Ill-Gotten Gains"] = 1
    igg = get_card("Ill-Gotten Gains")
    assert strategy.choose_gain(state, player, [igg, get_card("Silver"), None]) is igg


# ---------------------------------------------------------- greening order


def test_green_first_takes_the_duchy_ahead_of_the_build_order():
    strategy = Jerusalem(igg=10, build="rush", green_first=True, duchy=8)
    state = _state(strategy)
    player = state.players[0]
    state.phase = "buy"
    duchy, igg = get_card("Duchy"), get_card("Ill-Gotten Gains")
    assert strategy.choose_gain(state, player, [duchy, igg, None]) is duchy


def test_green_last_takes_the_payload_ahead_of_the_duchy():
    strategy = Jerusalem(igg=10, build="rush", green_first=False, duchy=8)
    state = _state(strategy)
    player = state.players[0]
    state.phase = "buy"
    duchy, igg = get_card("Duchy"), get_card("Ill-Gotten Gains")
    assert strategy.choose_gain(state, player, [duchy, igg, None]) is igg


# -------------------------------------------------------------- free gains


def test_a_free_gain_is_never_declined():
    """Governor's upgrade is a gain, not a buy: passing throws it away."""
    strategy = Jerusalem(**(DEFAULTS | dict(governor=1, build="money", silver=0, gold=0)))
    state = _state(strategy)
    player = state.players[0]
    state.phase = "action"
    choices = [get_card("Curse"), get_card("Estate"), get_card("Silver")]
    assert strategy.choose_gain(state, player, choices).name == "Silver"


def test_a_buy_may_still_be_declined():
    strategy = Jerusalem(**(DEFAULTS | dict(build="money", silver=0, gold=0,
                                            goons=0, goons_filler=False)))
    state = _state(strategy)
    player = state.players[0]
    state.phase = "buy"
    assert strategy.choose_gain(state, player, [get_card("Curse"), None]) is None


# --------------------------------------------------- the published finalists


def test_published_winner_matches_the_validated_parameters():
    """The registered strategy must stay the spec the 3,000 games measured.

    Retuning it without rerunning validation would leave the guide quoting a
    win rate for a deck that no longer exists.
    """
    from dominion.strategy.strategies.jerusalem_seeds import (
        create_jerusalem_scrying_pool_goons,
    )

    assert create_jerusalem_scrying_pool_goons().params == DEFAULTS | dict(
        scrying_pool=8, potion=1, fortress=5, goons=5, ambassador=1,
        bridge_troll=3, sea_hag=2, old_witch=1, silver=1, gold=0,
        green=99, duchy=3, estate=3, green_first=False, copper_floor=3,
        filler="Estate", opening="Potion", first_five="Old Witch", build="pool",
    )


def test_published_finalists_are_registered_and_distinct():
    from dominion.strategy.strategy_loader import StrategyLoader

    loader = StrategyLoader()
    names = ["Jerusalem Scrying Pool Goons", "Jerusalem Curse Goons Money"]
    strategies = [loader.get_strategy(name) for name in names]
    assert all(strategies), names
    assert strategies[0].params != strategies[1].params


def test_published_winner_buys_only_the_piles_it_names():
    """A gain priority listing a pile the plan never wants is a drifted spec."""
    from dominion.strategy.strategies.jerusalem_seeds import (
        create_jerusalem_scrying_pool_goons,
    )

    strategy = create_jerusalem_scrying_pool_goons()
    named = {rule.card for rule in strategy.gain_priority}
    assert named == {
        "Province", "Duchy", "Estate", "Goons", "Sea Hag", "Ambassador",
        "Old Witch", "Scrying Pool", "Fortress", "Bridge Troll", "Potion",
        "Silver",
    }, sorted(named)


def test_ablation_specs_actually_remove_the_card():
    """Zeroing a count is not enough: the opening knobs buy cards anyway.

    ``choose_gain`` buys ``opening`` and ``first_five`` on turns 1-2 whatever
    the acquisition target is, so an "Old Witch removed" row that keeps
    ``first_five="Old Witch"`` still opens with one and measures nothing.
    """
    import json
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.search_jerusalem import ablations, without

    winner = dict(DEFAULTS, old_witch=1, scrying_pool=8, potion=1, goons=5,
                  opening="Potion", first_five="Old Witch", build="pool")

    stripped = without(winner, "old_witch")
    assert stripped["old_witch"] == 0
    assert stripped["first_five"] == "Silver", stripped["first_five"]

    stripped = without(winner, "scrying_pool", "potion")
    assert stripped["potion"] == 0
    assert stripped["opening"] == "Silver", stripped["opening"]

    for row in ablations(winner):
        removed = [k for k in ("old_witch", "goons", "scrying_pool")
                   if winner.get(k) and not row.get(k)]
        for key in removed:
            name = next(n for n, p in CARD_KEYS.items() if p == key)
            assert row["opening"] != name, json.dumps(row, sort_keys=True)
            assert row["first_five"] != name, json.dumps(row, sort_keys=True)
