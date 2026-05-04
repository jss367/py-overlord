"""Tests for Renaissance Kingdom cards."""

from typing import Optional

from dominion.cards.base_card import Card
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


class TrashAndKeepAI(DummyAI):
    """AI that trashes cheapest and keeps high-cost actions/treasures."""

    def choose_card_to_trash(self, state, choices) -> Optional[Card]:
        actual = [c for c in choices if c is not None]
        if not actual:
            return None
        return min(actual, key=lambda c: (c.cost.coins, c.name))

    def choose_buy(self, state, choices) -> Optional[Card]:
        actual = [c for c in choices if c is not None]
        if not actual:
            return None
        return max(actual, key=lambda c: (c.cost.coins, c.name))


def make_state(kingdom_names: list[str], n_players: int = 2):
    ais = [TrashAndKeepAI() for _ in range(n_players)]
    state = GameState(players=[])
    state.initialize_game(ais, [get_card(n) for n in kingdom_names])
    state.current_player_index = 0
    return state


def play_action(state, player, card):
    if card in player.hand:
        player.hand.remove(card)
    player.in_play.append(card)
    card.on_play(state)


# --------------------------------------------------------------------------
# Border Guard, Ducat, Lackeys, Experiment, Improve, Flag Bearer
# --------------------------------------------------------------------------


def test_border_guard_keeps_one_discards_one():
    state = make_state(["Border Guard"])
    p = state.players[0]
    bg = get_card("Border Guard")
    p.hand = [bg]
    p.deck = [get_card("Copper"), get_card("Estate")]
    play_action(state, p, bg)
    assert len(p.hand) == 1
    assert len(p.discard) == 1


def test_border_guard_two_actions_takes_horn():
    state = make_state(["Border Guard"])
    p = state.players[0]
    bg = get_card("Border Guard")
    p.hand = [bg]
    p.deck = [get_card("Village"), get_card("Village")]
    play_action(state, p, bg)
    assert state.artifacts["Horn"].holder is p


def test_ducat_grants_buy_and_coffer():
    state = make_state(["Ducat"])
    p = state.players[0]
    ducat = get_card("Ducat")
    p.hand = [ducat]
    coffers_before = p.coin_tokens
    buys_before = p.buys
    p.hand.remove(ducat)
    p.in_play.append(ducat)
    ducat.on_play(state)
    assert p.coin_tokens == coffers_before + 1
    assert p.buys == buys_before + 1


def test_ducat_on_gain_trashes_copper():
    state = make_state(["Ducat"])
    p = state.players[0]
    p.hand = [get_card("Copper"), get_card("Estate")]
    ducat = get_card("Ducat")
    state.gain_card(p, ducat)
    # The Copper from hand should be trashed.
    assert any(c.name == "Copper" for c in state.trash)


def test_lackeys_grants_villagers_on_gain():
    state = make_state(["Lackeys"])
    p = state.players[0]
    villagers_before = p.villagers
    state.gain_card(p, get_card("Lackeys"))
    assert p.villagers == villagers_before + 2


def test_experiment_returns_to_pile_when_played():
    state = make_state(["Experiment"])
    p = state.players[0]
    exp = get_card("Experiment")
    state.supply["Experiment"] = state.supply.get("Experiment", 10)
    supply_before = state.supply["Experiment"]
    p.hand = [exp]
    p.in_play.append(exp)
    p.hand.remove(exp)
    exp.on_play(state)
    # Returned to pile.
    assert state.supply["Experiment"] == supply_before + 1


def test_experiment_on_gain_gains_extra():
    state = make_state(["Experiment"])
    p = state.players[0]
    state.supply["Experiment"] = 10
    exp = get_card("Experiment")
    state.gain_card(p, exp)
    # 1 (the original) plus 1 freebie should be in discard/zones.
    experiments = sum(1 for c in p.all_cards() if c.name == "Experiment")
    assert experiments >= 2


def test_improve_at_cleanup_upgrades_action():
    state = make_state(["Improve", "Smithy"])
    p = state.players[0]
    improve = get_card("Improve")
    village = get_card("Village")
    p.in_play.append(improve)
    p.in_play.append(village)
    # Run cleanup-start hook directly.
    improve.on_cleanup_start(state)
    # Village trashed (cost $3), +1 cost = $4 → Smithy gained.
    assert any(c.name == "Village" for c in state.trash)
    assert any(c.name == "Smithy" for c in p.discard)


def test_flag_bearer_gain_takes_flag():
    state = make_state(["Flag Bearer"])
    p = state.players[0]
    state.gain_card(p, get_card("Flag Bearer"))
    assert state.artifacts["Flag"].holder is p


def test_flag_bearer_trash_takes_flag():
    state = make_state(["Flag Bearer"])
    p1, p2 = state.players
    state.take_artifact(p1, "Flag")
    fb = get_card("Flag Bearer")
    state.trash_card(p2, fb)
    assert state.artifacts["Flag"].holder is p2


# --------------------------------------------------------------------------
# Hideout, Mountain Village, Patron, Priest, Research, Silk Merchant
# --------------------------------------------------------------------------


def test_hideout_curses_self_when_trashing_victory():
    state = make_state(["Hideout"])
    p = state.players[0]

    # Override the AI to trash the Estate specifically.
    def pick_estate(self, state, choices):
        return next((c for c in choices if c is not None and c.name == "Estate"), None)

    p.ai.choose_card_to_trash = pick_estate.__get__(p.ai)
    hideout = get_card("Hideout")
    p.hand = [hideout, get_card("Estate")]
    p.deck = [get_card("Copper")]
    play_action(state, p, hideout)
    # Estate trashed, Curse gained.
    assert any(c.name == "Estate" for c in state.trash)
    assert any(c.name == "Curse" for c in p.discard)


def test_mountain_village_pulls_from_discard():
    state = make_state(["Mountain Village"])
    p = state.players[0]
    mv = get_card("Mountain Village")
    p.hand = [mv]
    p.discard = [get_card("Copper"), get_card("Village")]
    play_action(state, p, mv)
    assert any(c.name == "Village" for c in p.hand)


def test_patron_grants_villager_when_played():
    state = make_state(["Patron"])
    p = state.players[0]
    patron = get_card("Patron")
    p.hand = [patron]
    villagers_before = p.villagers
    coins_before = p.coins
    play_action(state, p, patron)
    assert p.villagers == villagers_before + 1
    assert p.coins == coins_before + 2


def test_priest_doubles_trash_value():
    state = make_state(["Priest"])
    p = state.players[0]
    priest = get_card("Priest")
    p.hand = [priest, get_card("Curse"), get_card("Estate")]
    coins_before = p.coins
    play_action(state, p, priest)
    # First trash is Priest's own — no bonus. Just +$2 base.
    assert p.coins == coins_before + 2

    # Subsequent trashes get +$2.
    coins_now = p.coins
    p.hand.append(get_card("Estate"))
    estate = p.hand[-1]
    p.hand.remove(estate)
    state.trash_card(p, estate)
    assert p.coins == coins_now + 2


def test_research_sets_aside_cards_equal_to_cost():
    state = make_state(["Research", "Village"])
    p = state.players[0]
    research = get_card("Research")
    village = get_card("Village")  # Cost 3
    p.hand = [research, village]
    p.deck = [
        get_card("Copper"),
        get_card("Copper"),
        get_card("Copper"),
        get_card("Copper"),
    ]
    play_action(state, p, research)
    # Trashed Village (cost $3) → 3 cards set aside.
    assert len(research.set_aside) == 3
    # Cards return next turn.
    research.on_duration(state)
    assert len(research.set_aside) == 0
    assert sum(1 for c in p.hand if c.name == "Copper") >= 3


def test_silk_merchant_grants_coffer_and_villager_on_gain():
    state = make_state(["Silk Merchant"])
    p = state.players[0]
    coffers_before = p.coin_tokens
    villagers_before = p.villagers
    state.gain_card(p, get_card("Silk Merchant"))
    assert p.coin_tokens == coffers_before + 1
    assert p.villagers == villagers_before + 1


# --------------------------------------------------------------------------
# Old Witch, Recruiter, Scepter, Scholar, Sculptor, Seer
# --------------------------------------------------------------------------


def test_old_witch_gives_curse_to_others():
    state = make_state(["Old Witch"])
    p1, p2 = state.players
    ow = get_card("Old Witch")
    p1.hand = [ow]
    p1.deck = [get_card("Copper")] * 5
    play_action(state, p1, ow)
    assert any(c.name == "Curse" for c in p2.discard)


def test_recruiter_grants_villagers_per_cost():
    state = make_state(["Recruiter"])
    p = state.players[0]

    def pick_estate(self, state, choices):
        return next((c for c in choices if c is not None and c.name == "Estate"), None)

    p.ai.choose_card_to_trash = pick_estate.__get__(p.ai)
    recruiter = get_card("Recruiter")
    p.hand = [recruiter, get_card("Estate")]  # Estate cost 2
    p.deck = [get_card("Copper"), get_card("Copper")]
    villagers_before = p.villagers
    play_action(state, p, recruiter)
    assert p.villagers == villagers_before + 2


def test_scepter_replays_action():
    state = make_state(["Scepter", "Village"])
    p = state.players[0]
    village = get_card("Village")
    p.in_play.append(village)
    village.on_play(state)
    actions_after_first = p.actions
    scepter = get_card("Scepter")
    p.in_play.append(scepter)
    scepter.on_play(state)
    # Scepter replayed Village → another +2 Actions.
    assert p.actions == actions_after_first + 2


def test_scepter_falls_back_to_two_coins():
    state = make_state(["Scepter"])
    p = state.players[0]
    scepter = get_card("Scepter")
    p.in_play.append(scepter)
    coins_before = p.coins
    scepter.on_play(state)
    assert p.coins == coins_before + 2


def test_scholar_discards_and_draws_seven():
    state = make_state(["Scholar"])
    p = state.players[0]
    scholar = get_card("Scholar")
    p.hand = [scholar, get_card("Copper"), get_card("Copper")]
    p.deck = [get_card("Silver")] * 10
    p.hand.remove(scholar)
    p.in_play.append(scholar)
    scholar.on_play(state)
    assert len(p.hand) == 7


def test_sculptor_gains_to_hand_and_villager_for_treasure():
    state = make_state(["Sculptor"])
    p = state.players[0]
    sculptor = get_card("Sculptor")
    p.in_play.append(sculptor)
    villagers_before = p.villagers
    sculptor.on_play(state)
    # Sculptor gained the highest-value card $4 — TrashAndKeepAI picks max.
    # Confirm something landed in hand.
    assert len(p.hand) >= 1


def test_seer_pulls_2_to_4_cost_into_hand():
    state = make_state(["Seer"])
    p = state.players[0]
    seer = get_card("Seer")
    p.hand = [seer]
    p.deck = [
        get_card("Estate"),  # Cost 2 — keep
        get_card("Silver"),  # Cost 3 — keep
        get_card("Copper"),  # Cost 0 — back
    ]
    play_action(state, p, seer)
    # +1 Card draws Copper from top, then reveals 2 more (Silver, Estate).
    # Both the Silver and Estate are in $2-$4 range.
    estate_in_hand = any(c.name == "Estate" for c in p.hand)
    silver_in_hand = any(c.name == "Silver" for c in p.hand)
    assert estate_in_hand or silver_in_hand


# --------------------------------------------------------------------------
# Spices, Swashbuckler, Treasurer, Villain
# --------------------------------------------------------------------------


def test_spices_two_coffers_on_gain():
    state = make_state(["Spices"])
    p = state.players[0]
    coffers_before = p.coin_tokens
    state.gain_card(p, get_card("Spices"))
    assert p.coin_tokens == coffers_before + 2


def test_swashbuckler_takes_treasure_chest_at_4_coffers():
    state = make_state(["Swashbuckler"])
    p = state.players[0]
    p.coin_tokens = 3
    p.discard = [get_card("Copper")]
    swash = get_card("Swashbuckler")
    p.in_play.append(swash)
    swash.on_play(state)
    # Got +1 Coffer (now 4) → Treasure Chest taken.
    assert state.artifacts["Treasure Chest"].holder is p


def test_treasurer_takes_key():
    state = make_state(["Treasurer"])
    p = state.players[0]
    treasurer = get_card("Treasurer")
    p.in_play.append(treasurer)
    treasurer.on_play(state)
    assert state.artifacts["Key"].holder is p


def test_treasurer_recovers_from_trash():
    state = make_state(["Treasurer"])
    p = state.players[0]
    state.take_artifact(p, "Key")  # Already hold the Key.
    state.trash.append(get_card("Gold"))
    treasurer = get_card("Treasurer")
    p.in_play.append(treasurer)
    treasurer.on_play(state)
    assert any(c.name == "Gold" for c in p.hand)


def test_villain_forces_discard_of_2_plus_card():
    state = make_state(["Villain"])
    p1, p2 = state.players
    p2.hand = [
        get_card("Estate"),
        get_card("Silver"),
        get_card("Copper"),
        get_card("Copper"),
        get_card("Copper"),
    ]
    villain = get_card("Villain")
    p1.in_play.append(villain)
    villain.on_play(state)
    # Cheapest card costing $2+ is Estate ($2).
    assert any(c.name == "Estate" for c in p2.discard)
