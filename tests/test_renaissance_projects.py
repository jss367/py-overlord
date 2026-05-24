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


def test_star_chart_promotes_action_on_shuffle():
    state = make_state(StarChart())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.deck = []
    p.discard = [
        get_card("Copper"),
        get_card("Village"),
        get_card("Estate"),
        get_card("Silver"),
        get_card("Copper"),
    ]
    p.hand = []
    p.shuffle_discard_into_deck()
    # Star Chart promotes the best action/treasure to the top of the deck.
    # Top of deck is the last element (drawn via deck.pop()).
    assert p.deck[-1].name == "Village"
    assert p.discard == []


def test_star_chart_fires_on_midturn_shuffle_via_draw():
    """Star Chart should fire whenever the deck is reshuffled mid-turn,
    not only at start-of-turn."""
    state = make_state(StarChart())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.deck = []
    p.discard = [get_card("Copper"), get_card("Village"), get_card("Estate")]
    p.hand = []
    # draw_cards triggers the shuffle internally.
    p.draw_cards(1)
    assert any(c.name == "Village" for c in p.hand)


def test_star_chart_does_nothing_without_shuffle():
    """If no shuffle happens, Star Chart should not promote anything."""
    state = make_state(StarChart())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.deck = [get_card("Copper"), get_card("Copper")]
    p.discard = [get_card("Village")]
    p.hand = []
    state.phase = "start"
    state.handle_start_phase()
    # No shuffle occurred, so Village stays in discard.
    assert any(c.name == "Village" for c in p.discard)


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


def test_canal_discount_applies_immediately_on_buy():
    """Buying Canal mid-turn must apply the -$1 discount to subsequent
    buys this same turn — Canal's effect is "during your turns",
    continuous from the moment it's owned.
    """
    state = make_state(Canal())
    p = state.players[0]
    state.current_player_index = 0
    canal_project = state.projects[0]
    # Simulate the buy-side hook firing.
    canal_project.on_buy(state, p)
    p.projects.append(canal_project)
    province = get_card("Province")
    # Province costs $8 normally; with Canal owned mid-turn it costs $7.
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


def test_citadel_inheritance_replay_preserves_inherited_identity():
    """Citadel's replay of an inherited Estate must keep the inheritance
    overlay active through the per-play hooks, so name-gated effects
    (training token, Kiln) see the inherited Action's name — matching
    the action-phase loop's behaviour.
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
    # Adventures: place the training-token on the inherited pile so the
    # +$1 fires per-play of "Village" (not "Estate"). If the overlay is
    # not held through the post-play hook, the helper would compare
    # card.name == "Estate" and skip the bonus.
    p.training_pile = "Village"
    estate = get_card("Estate")
    p.hand = [estate]
    p.deck = []
    p.actions = 1
    coins_before = p.coins
    state.phase = "action"
    state.handle_action_phase()
    # Way-played first play (Way of the Otter draws cards; no coin) +
    # Citadel replay as inherited Village (+$1 from the training token
    # because the helper now overlays the Estate's identity to "Village"
    # during the post-play hooks).
    assert p.citadel_used
    assert p.coins == coins_before + 1


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


def test_citadel_replays_ghost_pending_action():
    """Ghost (Nocturne) plays a set-aside Action at start of turn before
    the action phase. If that's the turn's first Action, Citadel must
    trigger and replay it.
    """
    state = make_state(Citadel())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    village = get_card("Village")
    p.ghost_pending_actions = [(village, 1)]
    p.deck = [get_card("Copper") for _ in range(10)]
    p.hand = []
    actions_before = p.actions
    state.phase = "start"
    state.handle_start_phase()
    # Ghost plays Village (+2 actions); Citadel replays it (+2 actions).
    assert p.citadel_used
    assert p.actions == actions_before + 4


def test_citadel_replays_turtle_set_aside_action():
    """Way of the Turtle sets an Action aside to be played at start of
    next turn. That play is the turn's first Action and Citadel replays.
    """
    state = make_state(Citadel())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    village = get_card("Village")
    p.turtle_set_aside = [village]
    p.deck = [get_card("Copper") for _ in range(10)]
    p.hand = []
    actions_before = p.actions
    state.phase = "start"
    state.handle_start_phase()
    # Turtle plays Village (+2 actions); Citadel replays it (+2 actions).
    assert p.citadel_used
    assert p.actions == actions_before + 4


def test_citadel_helper_fires_tavern_triggers():
    """Royal Carriage on the Tavern mat must react to a Citadel-helper
    replay (e.g. Way-played first Action), the same way it would in the
    non-Way action-phase loop. The replay is a real play of the action.
    """
    from dominion.cards.adventures.royal_carriage import RoyalCarriage
    from dominion.ways.otter import WayOfTheOtter

    class WayOtterAI(ChooseFirstActionAI):
        def choose_way(self, state, card, ways):
            for w in ways:
                if w and w.name == "Way of the Otter":
                    return w
            return None

        def should_call_from_tavern(self, state, player, card, trigger, *args):
            return True

    ai = WayOtterAI()
    state = GameState(players=[])
    state.initialize_game(
        [ai], [get_card("Village")], projects=[Citadel()], ways=[WayOfTheOtter()]
    )
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    rc = RoyalCarriage()
    p.tavern_mat.append(rc)
    village = get_card("Village")
    p.hand = [village]
    p.deck = []
    p.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Way of the Otter draws (no actions); Citadel helper-path replays
    # Village (+2 actions); Royal Carriage reacts to the replay's
    # action_played trigger and replays Village again (+2 actions).
    # Started 1 action, -1 to play, +2 +2 = 4.
    assert p.citadel_used
    assert p.actions == 4
    # Royal Carriage moved from tavern_mat to discard after firing.
    assert rc not in p.tavern_mat
    assert rc in p.discard


def test_citadel_helper_fires_prophecy_hooks():
    """Citadel's helper-path replay must fire active Prophecy hooks
    (Great Leader's +1 Action, etc.), matching the action-phase loop.
    Use Way of the Otter so the replay goes through the helper.
    """
    from dominion.prophecies.great_leader import GreatLeader
    from dominion.ways.otter import WayOfTheOtter

    class WayOtterAI(ChooseFirstActionAI):
        def choose_way(self, state, card, ways):
            for w in ways:
                if w and w.name == "Way of the Otter":
                    return w
            return None

    ai = WayOtterAI()
    state = GameState(players=[])
    prophecy = GreatLeader()
    prophecy.is_active = True
    state.initialize_game(
        [ai],
        [get_card("Village")],
        projects=[Citadel()],
        ways=[WayOfTheOtter()],
        prophecy=prophecy,
    )
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    village = get_card("Village")
    p.hand = [village]
    p.deck = []
    p.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Way play: no actions. Citadel replay: +2 (Village). Great Leader
    # fires once on the helper replay → +1 more. Started 1, -1 to play,
    # +2 (replay) +1 (Great Leader) = 3.
    assert p.citadel_used
    assert p.actions == 3


def test_citadel_replays_prince_set_aside_action():
    """Prince plays its set-aside Action via on_duration. If that's the
    turn's first Action, Citadel must replay it.
    """
    from dominion.cards.promo.prince import Prince

    state = make_state(Citadel())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    village = get_card("Village")
    prince = Prince()
    prince.set_aside_card = village
    p.deck = [get_card("Copper") for _ in range(10)]
    p.hand = []
    actions_before = p.actions
    prince.on_duration(state)
    # Village plays once via Prince (+2 actions); Citadel replays it
    # via the helper (+2 actions).
    assert p.citadel_used
    assert p.actions == actions_before + 4


def test_citadel_replays_riverboat_target_action():
    """Riverboat plays the set-aside target Action via on_duration. If
    that's the turn's first Action, Citadel must replay it.
    """
    from dominion.cards.rising_sun.riverboat import Riverboat

    state = make_state(Citadel())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    village = get_card("Village")
    state.riverboat_set_aside = village
    riverboat = Riverboat()
    p.deck = [get_card("Copper") for _ in range(10)]
    p.hand = []
    actions_before = p.actions
    riverboat.on_duration(state)
    # Village plays once via Riverboat (+2 actions); Citadel replays
    # via the helper (+2 actions).
    assert p.citadel_used
    assert p.actions == actions_before + 4


def test_citadel_replays_summon_set_aside_action():
    """Summon (promo) plays a set-aside Action at start of turn before
    the action phase. If that's the turn's first Action, Citadel must
    replay it.
    """
    state = make_state(Citadel())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    village = get_card("Village")
    p.summon_set_aside = [village]
    p.deck = [get_card("Copper") for _ in range(10)]
    p.hand = []
    actions_before = p.actions
    state.phase = "start"
    state.handle_start_phase()
    # Summon plays Village (+2 actions); Citadel replays (+2 actions).
    assert p.citadel_used
    assert p.actions == actions_before + 4


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
