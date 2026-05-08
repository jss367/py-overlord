"""Tests for Renaissance Projects."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.projects import (
    Academy,
    Barracks,
    Canal,
    Capitalism,
    Cathedral,
    Citadel,
    CityGate,
    CropRotation,
    Exploration,
    Fair,
    Fleet,
    Guildhall,
    Pageant,
    Piazza,
    Silos,
    SinisterPlot,
    StarChart,
)
from tests.utils import BuyEventAI, ChooseFirstActionAI, DummyAI, TrashFirstAI


def make_state(project, kingdom: str = "Village", n: int = 1):
    ais = [DummyAI() for _ in range(n)]
    state = GameState(players=[])
    state.initialize_game(ais, [get_card(kingdom)], projects=[project])
    return state


def test_cathedral_trashes_card_at_turn_start():
    state = make_state(Cathedral())
    state.players[0].projects.append(state.projects[0])
    p = state.players[0]
    state.current_player_index = 0
    p.hand = [get_card("Copper"), get_card("Estate")]
    p.deck = [get_card("Copper")]
    state.phase = "start"
    state.handle_start_phase()
    assert len(state.trash) == 1


def test_city_gate_draws_then_topdecks():
    state = make_state(CityGate())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.hand = [get_card("Copper")]
    p.deck = [get_card("Estate"), get_card("Silver")]
    hand_before = len(p.hand)
    state.phase = "start"
    state.handle_start_phase()
    # Drew 1 then topdecked 1 → hand size unchanged (vs drew 1).
    assert len(p.hand) == hand_before
    assert len(p.deck) >= 1


def test_pageant_pays_one_for_coffer():
    state = make_state(Pageant())
    p = state.players[0]
    p.projects.append(state.projects[0])
    p.coins = 3
    p.coin_tokens = 0
    state.current_player_index = 0
    state.phase = "buy"
    state.handle_buy_phase()
    # Pageant fires at end of Buy phase; coins reduced by 1, +1 Coffers.
    assert p.coin_tokens == 1


def test_star_chart_promotes_action_from_discard():
    state = make_state(StarChart())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.deck = [get_card("Copper")]
    p.discard = [get_card("Village"), get_card("Estate")]
    p.hand = []
    state.phase = "start"
    state.handle_start_phase()
    # The Village should have been moved out of discard.
    assert not any(c.name == "Village" for c in p.discard)


def test_exploration_grants_bonus_when_no_action_treasure_gain():
    state = make_state(Exploration())
    p = state.players[0]
    p.projects.append(state.projects[0])
    p.coin_tokens = 0
    p.villagers = 0
    state.current_player_index = 0
    state.phase = "buy"
    state.handle_buy_phase()
    assert p.coin_tokens == 1
    assert p.villagers == 1


def test_fair_grants_buy_at_turn_start():
    state = make_state(Fair())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.deck = [get_card("Copper")]
    p.hand = []
    p.buys = 1
    state.phase = "start"
    state.handle_start_phase()
    assert p.buys == 2


def test_silos_discards_coppers_and_redraws():
    state = make_state(Silos())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.hand = [get_card("Copper"), get_card("Copper"), get_card("Estate")]
    p.deck = [get_card("Silver"), get_card("Gold")]
    state.phase = "start"
    state.handle_start_phase()
    coppers_in_hand = sum(1 for c in p.hand if c.name == "Copper")
    assert coppers_in_hand == 0
    # Should have replaced 2 Coppers with 2 cards.
    assert len(p.hand) == 3


def test_sinister_plot_stockpiles_then_draws():
    state = make_state(SinisterPlot())
    p = state.players[0]
    project = state.projects[0]
    p.projects.append(project)
    state.current_player_index = 0
    p.deck = [get_card("Copper") for _ in range(10)]
    p.hand = []
    state.phase = "start"
    # First 3 turn-starts should stockpile to 3.
    for _ in range(3):
        state.handle_start_phase()
        state.phase = "start"
    assert project.tokens == 3
    # 4th turn-start: remove ALL tokens and +X Cards where X = tokens removed.
    p.hand = []
    state.handle_start_phase()
    assert project.tokens == 0
    assert len(p.hand) >= 3


def test_academy_grants_villager_on_action_gain():
    state = make_state(Academy())
    p = state.players[0]
    p.projects.append(state.projects[0])
    villagers_before = p.villagers
    state.gain_card(p, get_card("Village"))
    assert p.villagers == villagers_before + 1


def test_capitalism_lets_action_play_in_treasure_phase():
    """With Capitalism, a +$ Action is also a Treasure during your turn."""
    from typing import Optional
    from dominion.cards.base_card import Card

    class PlayAllTreasuresAI(DummyAI):
        def choose_treasure(self, state, choices) -> Optional[Card]:
            for c in choices:
                if c is not None:
                    return c
            return None

    ai = PlayAllTreasuresAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")], projects=[Capitalism()])
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    bazaar = get_card("Bazaar")  # +1 Card +2 Actions +$1
    p.hand = [bazaar]
    p.deck = [get_card("Copper")]
    coins_before = p.coins
    state.phase = "treasure"
    state.handle_treasure_phase()
    assert p.coins > coins_before


def test_fleet_grants_extra_round():
    ais = [DummyAI(), DummyAI()]
    state = GameState(players=[])
    state.initialize_game(ais, [get_card("Village")], projects=[Fleet()])
    p1, p2 = state.players
    p1.projects.append(state.projects[0])
    # Force end-of-game by emptying Provinces.
    state.supply["Province"] = 0
    assert state.is_game_over() is False
    assert state.fleet_extra_round_active
    assert p1 in state.fleet_extra_players
    assert p2 not in state.fleet_extra_players


def test_guildhall_grants_coffers_on_treasure_gain():
    state = make_state(Guildhall())
    p = state.players[0]
    p.projects.append(state.projects[0])
    coffers_before = p.coin_tokens
    state.gain_card(p, get_card("Silver"))
    assert p.coin_tokens == coffers_before + 1


def test_piazza_plays_top_action():
    state = make_state(Piazza())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.deck = [get_card("Copper"), get_card("Village")]
    p.hand = []
    actions_before = p.actions
    state.phase = "start"
    state.handle_start_phase()
    # Piazza played the Village (top of deck via deck.pop()) → +2 Actions.
    assert p.actions >= actions_before + 2


def test_barracks_adds_action():
    state = make_state(Barracks())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.deck = [get_card("Copper")]
    p.hand = []
    actions_before = p.actions
    state.phase = "start"
    state.handle_start_phase()
    assert p.actions == actions_before + 1


def test_canal_reduces_cost_during_turn():
    state = make_state(Canal())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.deck = [get_card("Copper")]
    p.hand = []
    state.phase = "start"
    state.handle_start_phase()
    assert p.cost_reduction == 1
    # A Province costs $8 normally; with Canal in effect it costs $7.
    province = get_card("Province")
    assert state.get_card_cost(p, province) == 7


def test_canal_does_not_reduce_below_zero():
    state = make_state(Canal())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.hand = []
    p.deck = [get_card("Copper")]
    state.phase = "start"
    state.handle_start_phase()
    copper = get_card("Copper")  # costs $0
    assert state.get_card_cost(p, copper) >= 0


def test_citadel_replays_first_action():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")], projects=[Citadel()])
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    village = get_card("Village")
    p.hand = [village]
    p.deck = [get_card("Copper") for _ in range(5)]
    p.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Village played twice: +1 Card +2 Actions per play.
    # Started with 1 action, used 1 to play Village, +2 from each of 2 plays = 4.
    assert p.actions == 4
    assert p.citadel_used


def test_citadel_only_fires_once_per_turn():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")], projects=[Citadel()])
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    v1 = get_card("Village")
    v2 = get_card("Village")
    p.hand = [v1, v2]
    p.deck = [get_card("Copper") for _ in range(10)]
    p.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # First Village played twice (+4 actions, -1 to play = +3); +2 actions free.
    # Second Village plays once (no Citadel replay): +2 actions, -1 to play = +1.
    # Net: started 1, ended 1 + 3 + 1 = 5.
    assert p.actions == 5


def test_citadel_does_not_trigger_on_treasure_under_enlightenment():
    """Under Rising Sun's Enlightenment, Treasures may be played in the
    Action phase. Citadel must only trigger on Action cards, not Treasures —
    the Treasure should not be replayed nor consume citadel_used.
    """
    from dominion.prophecies.enlightenment import Enlightenment

    class TreasureFirstAI(ChooseFirstActionAI):
        def choose_action(self, state, choices):
            for ch in choices:
                if ch is not None and ch.is_treasure and not ch.is_action:
                    return ch
            for ch in choices:
                if ch is not None:
                    return ch
            return None

    ai = TreasureFirstAI()
    state = GameState(players=[])
    prophecy = Enlightenment()
    prophecy.is_active = True
    state.initialize_game(
        [ai], [get_card("Village")], projects=[Citadel()], prophecy=prophecy
    )
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    silver = get_card("Silver")
    p.hand = [silver]
    # Empty deck so reshuffles don't pull more Actions in.
    p.deck = []
    p.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Silver played as the only "action" under Enlightenment: +1 Card,
    # +1 Action, no replay. citadel_used must remain False so a future
    # Action this turn would still trigger Citadel.
    assert p.citadel_used is False
    # Started with 1 action, -1 to play Silver, +1 from Enlightenment text.
    assert p.actions == 1


def test_citadel_replays_first_action_played_via_way():
    """A Way-played Action still counts as the first Action played, and
    Citadel replays it using the card's normal text.
    """
    from dominion.ways.otter import WayOfTheOtter

    class WayOtterAI(ChooseFirstActionAI):
        def choose_way(self, state, card, ways):
            for w in ways:
                if w and w.name == "Way of the Otter":
                    return w
            return None

    ai = WayOtterAI()
    state = GameState(players=[])
    state.initialize_game(
        [ai], [get_card("Village")], projects=[Citadel()], ways=[WayOfTheOtter()]
    )
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    village = get_card("Village")
    p.hand = [village]
    p.deck = [get_card("Copper") for _ in range(10)]
    p.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Village played via Way of the Otter (+2 Cards from Otter, no actions).
    # Citadel replays Village using normal text (+1 Card, +2 Actions).
    # Actions: 1 - 1 (play) + 2 (replay) = 2.
    assert p.citadel_used
    assert p.actions == 2


def test_citadel_replays_hasty_played_action():
    """A Hasty-trait Action played at start of turn (before the action
    phase loop) is the first Action of the turn, so Citadel replays it.
    """
    state = make_state(Citadel())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    village = get_card("Village")
    p.deck = [get_card("Copper") for _ in range(10)]
    p.hand = []
    p.actions = 1
    state.hasty_set_aside.setdefault(id(p), []).append(village)
    state._handle_hasty_start_of_turn(p)
    # Village played twice (Hasty + Citadel replay): +2 cards drawn,
    # +4 actions. Started with 1 → 5.
    assert p.citadel_used
    assert p.actions == 5


def test_citadel_replays_captain_supply_play_on_duration():
    """Captain plays an Action from Supply via on_duration. If that's
    the first Action of the new turn, Citadel must replay it.
    """
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game(
        [ai],
        [get_card("Captain"), get_card("Village")],
        projects=[Citadel()],
    )
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    captain = get_card("Captain")
    p.duration.append(captain)
    p.citadel_used = False
    p.deck = [get_card("Copper") for _ in range(10)]
    p.hand = []
    actions_before = p.actions
    captain.on_duration(state)
    # Captain plays a Village from Supply (+2 actions); Citadel replays
    # that Village (+2 actions). Net: +4 actions.
    assert p.citadel_used
    assert p.actions == actions_before + 4


def test_citadel_replays_capitalism_treasure_phase_action():
    """With Capitalism, an Action with +$ can be played in the Treasure
    phase. That play still counts as the first Action of the turn and
    Citadel replays it.
    """
    from typing import Optional
    from dominion.cards.base_card import Card

    class PlayAllTreasuresAI(DummyAI):
        def choose_treasure(self, state, choices) -> Optional[Card]:
            for c in choices:
                if c is not None:
                    return c
            return None

    ai = PlayAllTreasuresAI()
    state = GameState(players=[])
    state.initialize_game(
        [ai], [get_card("Village")], projects=[Capitalism(), Citadel()]
    )
    p = state.players[0]
    p.projects.extend(state.projects)
    state.current_player_index = 0
    bazaar = get_card("Bazaar")  # +1 Card +2 Actions +$1 (Action with +$)
    p.hand = [bazaar]
    # Empty deck so the +1 Card doesn't pull more treasures into hand.
    p.deck = []
    coins_before = p.coins
    state.phase = "treasure"
    state.handle_treasure_phase()
    # Bazaar plays as Treasure (Capitalism), Citadel replays it once.
    # Each play gives +$1 → coins increase by 2.
    assert p.citadel_used
    assert p.coins == coins_before + 2


def test_citadel_does_not_trigger_on_plain_treasure_in_buy_phase():
    """Plain Treasures (Silver/Gold/Copper) don't trigger Citadel even
    when played first this turn — they aren't Action cards.
    """
    from typing import Optional
    from dominion.cards.base_card import Card

    class PlayAllTreasuresAI(DummyAI):
        def choose_treasure(self, state, choices) -> Optional[Card]:
            for c in choices:
                if c is not None:
                    return c
            return None

    ai = PlayAllTreasuresAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")], projects=[Citadel()])
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.hand = [get_card("Silver")]
    p.deck = [get_card("Copper") for _ in range(5)]
    state.phase = "treasure"
    state.handle_treasure_phase()
    assert p.citadel_used is False


def test_citadel_replays_inherited_estate():
    """Adventures Inheritance: an Estate played as the inherited Action
    is an Action play, and Citadel must trigger / replay it.
    """
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game(
        [ai], [get_card("Village")], projects=[Citadel()]
    )
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.inherited_action_name = "Village"
    estate = get_card("Estate")
    p.hand = [estate]
    p.deck = [get_card("Copper") for _ in range(10)]
    p.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Estate played as Village twice (once + Citadel replay): +2 Actions
    # per play. Started 1, -1 to play, +2 +2 from replays = 4.
    assert p.citadel_used
    assert p.actions == 4


def test_citadel_replays_inherited_estate_played_via_way():
    """Inheritance + Way: an Estate played via a Way (e.g. Way of the
    Otter) is still an Action play because Inheritance binds an Action
    to it. Citadel must trigger and replay it via the inherited card.
    """
    from dominion.ways.otter import WayOfTheOtter

    class WayOtterAI(ChooseFirstActionAI):
        def choose_way(self, state, card, ways):
            for w in ways:
                if w and w.name == "Way of the Otter":
                    return w
            return None

    ai = WayOtterAI()
    state = GameState(players=[])
    state.initialize_game(
        [ai], [get_card("Village")], projects=[Citadel()], ways=[WayOfTheOtter()]
    )
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.inherited_action_name = "Village"
    estate = get_card("Estate")
    p.hand = [estate]
    p.deck = [get_card("Copper") for _ in range(10)]
    p.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Estate played via Way of the Otter (+2 Cards). Citadel replays it
    # as the inherited Village (+1 Card, +2 Actions). Started 1 action,
    # -1 to play, +2 from inherited Village = 2.
    assert p.citadel_used
    assert p.actions == 2


def test_citadel_resets_at_turn_start():
    state = make_state(Citadel())
    p = state.players[0]
    p.projects.append(state.projects[0])
    p.citadel_used = True
    state.current_player_index = 0
    p.deck = [get_card("Copper")]
    p.hand = []
    state.phase = "start"
    state.handle_start_phase()
    assert p.citadel_used is False


def test_crop_rotation_discards_victory_for_cards():
    state = make_state(CropRotation())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.hand = [get_card("Estate"), get_card("Copper")]
    p.deck = [get_card("Silver"), get_card("Gold")]
    state.phase = "start"
    state.handle_start_phase()
    # Estate discarded; +2 Cards drawn.
    assert any(c.name == "Estate" for c in p.discard)
    assert len(p.hand) == 1 + 2  # Copper + 2 drawn
