"""Rule regressions that materially affect the Kind Emperor strategy search."""

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.projects.registry import get_project
from dominion.prophecies.registry import get_prophecy
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from tests.utils import DummyAI


def setup(*names, ai=None):
    player = PlayerState(ai or DummyAI())
    state = GameState([player])
    state.log_callback = lambda *_: None
    state.setup_supply([get_card(n) for n in names])
    return state, player


def test_anvil_gains_during_play_and_cannot_gain_debt_card():
    class AnvilAI(DummyAI):
        def choose_anvil_gain(self, state, player, choices):
            assert "City Quarter" not in [c.name for c in choices]
            return next(c for c in choices if c.name == "Courier")

    state, player = setup("Anvil", "City Quarter", "Courier", ai=AnvilAI())
    copper = get_card("Copper")
    player.hand = [copper]
    anvil = get_card("Anvil")
    player.in_play = [anvil]
    anvil.on_play(state)
    assert copper in player.discard
    assert player.coins == 1
    assert state.supply["Courier"] == 9
    assert any(c.name == "Courier" for c in player.discard)
    state.handle_cleanup_phase()
    assert state.supply["Courier"] == 9


def test_courier_plays_previously_discarded_treasure_without_trashing():
    state, player = setup("Courier")
    copper, gold = get_card("Copper"), get_card("Gold")
    player.deck = [copper]
    player.discard = [gold]
    get_card("Courier").on_play(state)
    assert gold in player.in_play
    assert copper in player.discard
    assert player.coins == 4
    assert not state.trash


@pytest.mark.parametrize("charlatan", [False, True])
def test_courier_uses_current_treasure_type_for_curses(charlatan):
    state, player = setup("Courier", *(["Charlatan"] if charlatan else []))
    curse = get_card("Curse")
    player.deck = [curse]

    get_card("Courier").on_play(state)

    assert player.coins == 1 + int(charlatan)
    assert (curse in player.in_play) == charlatan
    assert (curse in player.discard) != charlatan


@pytest.mark.parametrize("highwayman", [False, True])
def test_courier_crown_gets_action_and_treasure_bookkeeping(highwayman):
    from collections import Counter

    class ObservePlays:
        def __init__(self):
            self.plays = Counter()

        def on_play_card(self, state, player, card):
            self.plays[card.name] += 1

    state, player = setup("Courier", "Crown", "Smithy")
    observer = ObservePlays()
    state.allies = [observer]
    state.prophecy = get_prophecy("Panic")
    state.prophecy.is_active = True
    state.phase = "action"
    player.highwayman_attacks = int(highwayman)
    crown, smithy = get_card("Crown"), get_card("Smithy")
    player.deck = [get_card("Copper") for _ in range(6)] + [crown]
    player.hand = [smithy]
    buys = player.buys

    get_card("Courier").on_play(state)

    assert crown in player.in_play
    assert player.buys == buys + 2  # Panic sees Crown even if its text is blocked.
    assert observer.plays["Crown"] == 1
    assert player.actions_this_turn == (1 if highwayman else 3)
    assert observer.plays["Smithy"] == (0 if highwayman else 2)
    if highwayman:
        assert player.hand == [smithy]
    else:
        assert [c.name for c in player.hand] == ["Copper"] * 6


@pytest.mark.parametrize("capitalism", [False, True])
@pytest.mark.parametrize("off_turn", [False, True])
@pytest.mark.parametrize("highwayman", [False, True])
def test_courier_market_uses_capitalism_treasure_type(capitalism, off_turn, highwayman):
    state, player = setup("Courier", "Market")
    if capitalism:
        player.projects = [get_project("Capitalism")]
    if off_turn:
        state.players.append(PlayerState(DummyAI()))
        state.reaction_turn_player_index = 1
    state.prophecy = get_prophecy("Panic")
    state.prophecy.is_active = True
    state.phase = "action"
    player.highwayman_attacks = int(highwayman)
    market = get_card("Market")
    player.deck = [get_card("Estate"), market]
    buys = player.buys

    get_card("Courier").on_play(state)

    treasure = capitalism and not off_turn
    blocked = treasure and highwayman
    assert state.is_treasure(market) == treasure
    assert player.coins == (1 if blocked else 2)
    assert player.buys == buys + int(not blocked) + (2 if treasure else 0)
    assert len(player.hand) == int(not blocked)
    assert player.actions_this_turn == 1


@pytest.mark.parametrize("active", [False, True])
@pytest.mark.parametrize("phase", ["action", "treasure"])
def test_courier_gold_uses_enlightenment_action_phase_instructions(active, phase):
    state, player = setup("Courier")
    state.prophecy = get_prophecy("Enlightenment")
    state.prophecy.is_active = active
    state.phase = phase
    player.deck = [get_card("Estate"), get_card("Gold")]
    actions = player.actions

    get_card("Courier").on_play(state)

    substituted = active and phase == "action"
    assert player.coins == (1 if substituted else 4)
    assert player.actions == actions + int(substituted)
    assert len(player.hand) == int(substituted)
    assert player.actions_this_turn == int(active)


@pytest.mark.parametrize("name", ["Crown", "Market", "Gold"])
@pytest.mark.parametrize("citadel", [False, True])
def test_main_action_phase_enlightenment_substitutes_all_treasure_types(name, citadel):
    class PlayOnce(DummyAI):
        def choose_action(self, state, choices):
            return None if state.current_player.in_play else next(c for c in choices if c and c.name == name)

    state, player = setup(name, "Smithy", ai=PlayOnce())
    state.prophecy = get_prophecy("Enlightenment")
    state.prophecy.is_active = True
    state.phase = "action"
    player.projects = [get_project("Capitalism")]
    if citadel:
        player.projects.append(get_project("Citadel"))
    card, smithy = get_card(name), get_card("Smithy")
    player.hand = [card, smithy]
    player.deck = [get_card("Estate") for _ in range(6)]
    player.champions_in_play = 1
    actions, buys = player.actions, player.buys

    state.handle_action_phase()

    plays = 1 + int(citadel)
    assert player.in_play == [card]
    assert smithy in player.hand  # Crown never runs its normal multiplier text.
    assert len(player.hand) == 1 + plays
    assert player.coins == 0
    assert player.buys == buys  # Capitalism Market never runs its normal text.
    assert player.actions == actions - 1 + 2 * plays  # Substitution + Champion.
    assert player.citadel_used == citadel


@pytest.mark.parametrize("active", [False, True])
def test_citadel_replays_enlightened_treasure_in_treasure_phase(active):
    state, player = setup("Gold")
    state.prophecy = get_prophecy("Enlightenment")
    state.prophecy.is_active = active
    state.phase = "treasure"
    player.projects = [get_project("Citadel")]
    gold = get_card("Gold")
    player.in_play = [gold]

    state.play_treasure_indirectly(player, gold)

    assert player.coins == (6 if active else 3)
    assert player.citadel_used == active


def test_enlightened_buried_treasure_gain_draws_instead_of_scheduling_duration():
    state, player = setup("Buried Treasure")
    state.prophecy = get_prophecy("Enlightenment")
    state.prophecy.is_active = True
    state.phase = "action"
    player.deck = [get_card("Estate")]
    card = get_card("Buried Treasure")
    actions = player.actions
    state.supply[card.name] -= 1

    state.gain_card(player, card)

    assert [c.name for c in player.hand] == ["Estate"]
    assert player.actions == actions + 1
    assert player.actions_this_turn == 1
    assert card in player.in_play and card not in player.duration


def test_enlightened_buried_treasure_off_turn_action_phase_gain_uses_substitution():
    state, current = setup("Buried Treasure")
    player = PlayerState(DummyAI())
    state.players.append(player)
    state.prophecy = get_prophecy("Enlightenment")
    state.prophecy.is_active = True
    state.phase = "action"
    player.deck = [get_card("Estate")]
    card = get_card("Buried Treasure")
    actions = player.actions
    state.supply[card.name] -= 1

    state.gain_card(player, card)

    assert [c.name for c in player.hand] == ["Estate"]
    assert player.actions == actions + 1
    assert card in player.in_play and card not in player.duration
    assert state.current_player is current and state.turn_player is current


def test_enlightened_courier_treasure_can_use_way_and_champion_bonus():
    from dominion.ways.registry import get_way

    class ChooseSheep(DummyAI):
        def choose_way(self, state, card, choices):
            return choices[0]

    state, player = setup("Courier", ai=ChooseSheep())
    state.prophecy = get_prophecy("Enlightenment")
    state.prophecy.is_active = True
    state.ways = [get_way("Way of the Sheep")]
    state.phase = "action"
    player.champions_in_play = 1
    player.deck = [get_card("Gold")]
    actions = player.actions

    get_card("Courier").on_play(state)

    assert player.coins == 3  # Courier's $1 and the Way's $2, not Gold's $3.
    assert player.actions == actions + 2  # Champion reacts to Courier and Gold.
    assert player.actions_this_turn == 1


def test_courier_may_decline_to_play_the_discarded_card():
    class DeclineAI(DummyAI):
        def choose_courier_target(self, state, player, choices):
            return None

    state, player = setup("Courier", ai=DeclineAI())
    gold = get_card("Gold")
    player.deck = [gold]
    get_card("Courier").on_play(state)
    assert gold in player.discard
    assert player.coins == 1


@pytest.mark.parametrize("prophecy_name", ["Good Harvest", "Panic"])
@pytest.mark.parametrize("active", [False, True])
def test_courier_treasure_plays_trigger_active_prophecy(prophecy_name, active):
    state, player = setup("Courier")
    state.prophecy = get_prophecy(prophecy_name)
    state.prophecy.is_active = active
    player.deck = [get_card("Gold"), get_card("Gold")]
    coins, buys = player.coins, player.buys

    get_card("Courier").on_play(state)
    get_card("Courier").on_play(state)

    bonus_coins = int(active and prophecy_name == "Good Harvest")
    bonus_buys = (1 if prophecy_name == "Good Harvest" else 4) if active else 0
    assert player.coins == coins + 8 + bonus_coins
    assert player.buys == buys + bonus_buys
    if active and prophecy_name == "Good Harvest":
        assert player.good_harvest_treasures_played == {"Gold"}
    if active and prophecy_name == "Panic":
        assert player.panic_active


def test_courier_consumes_highwayman_block_before_normal_treasure_play():
    class PlayGoldAI(DummyAI):
        def choose_treasure(self, state, choices):
            return next((c for c in choices if c is not None), None)

    state, player = setup("Courier", ai=PlayGoldAI())
    player.highwayman_attacks = 1
    player.deck = [get_card("Gold")]
    get_card("Courier").on_play(state)
    assert player.coins == 1
    assert player.highwayman_blocked_this_turn

    player.hand = [get_card("Gold")]
    state.handle_treasure_phase()
    assert player.coins == 4


@pytest.mark.parametrize("highwayman", [False, True])
@pytest.mark.parametrize("off_turn", [False, True])
def test_courier_gold_respects_corsair_and_highwayman_turn_scope(highwayman, off_turn):
    state, player = setup("Courier", "Corsair")
    attacker = PlayerState(DummyAI())
    state.players.append(attacker)
    state.current_player_index = 1
    get_card("Corsair").on_play(state)
    state.current_player_index = 0
    state.reaction_turn_player_index = 1 if off_turn else None
    player.highwayman_attacks = int(highwayman)
    gold = get_card("Gold")
    player.deck = [gold]

    get_card("Courier").on_play(state)

    assert player.coins == (1 if highwayman and not off_turn else 4)
    assert (gold in state.trash) != off_turn
    assert (gold in player.in_play) == off_turn
    assert player.corsair_trashed_this_turn != off_turn


@pytest.mark.parametrize("effect, expected_coins", [("Reckless", 7), ("Envious", 2), ("Tiara", 7)])
def test_courier_gold_applies_treasure_modifiers(effect, expected_coins):
    class ReplayAI(DummyAI):
        def should_replay_treasure_with_tiara(self, state, player, treasure):
            return True

    state, player = setup("Courier", ai=ReplayAI())
    player.deck = [get_card("Gold")]
    if effect == "Reckless":
        state.pile_traits["Gold"] = "Reckless"
    elif effect == "Envious":
        player.envious_effect_active = True
    else:
        player.in_play = [get_card("Tiara")]

    get_card("Courier").on_play(state)

    assert player.coins == expected_coins
    if effect == "Tiara":
        assert player.tiara_replay_used


@pytest.mark.parametrize("highwayman", [False, True])
def test_courier_treasure_consumes_pending_kiln_gain(highwayman):
    class GainCopyAI(DummyAI):
        def should_gain_copy_with_kiln(self, state, player, card):
            return True

    state, player = setup("Courier", ai=GainCopyAI())
    player.deck = [get_card("Gold")]
    player.kiln_pending = 1
    player.highwayman_attacks = int(highwayman)
    supply = state.supply["Gold"]

    get_card("Courier").on_play(state)

    assert player.kiln_pending == 0
    assert state.supply["Gold"] == supply - 1
    assert any(c.name == "Gold" for c in player.discard)


@pytest.mark.parametrize("source", ["treasure_phase", "courier", "gain"])
@pytest.mark.parametrize("prophecy_name", ["Good Harvest", "Panic"])
def test_highwayman_blocked_treasure_still_fires_prophecy(source, prophecy_name):
    class PlayTreasureAI(DummyAI):
        def choose_treasure(self, state, choices):
            return next((c for c in choices if c is not None), None)

    state, player = setup("Courier", "Buried Treasure", ai=PlayTreasureAI())
    card = get_card("Buried Treasure" if source == "gain" else "Gold")
    state.prophecy = get_prophecy(prophecy_name)
    state.prophecy.is_active = True
    player.highwayman_attacks = 1
    buys = player.buys

    if source == "gain":
        state.supply[card.name] -= 1
        state.gain_card(player, card)
    elif source == "courier":
        player.deck = [card]
        get_card("Courier").on_play(state)
    else:
        player.hand = [card]
        state.handle_treasure_phase()

    assert player.buys == buys + (1 if prophecy_name == "Good Harvest" else 2)
    assert player.coins == int(source == "courier") + int(prophecy_name == "Good Harvest")
    assert card not in player.duration
    assert player.highwayman_blocked_this_turn


def test_highwayman_blocked_contract_still_fires_ally_hook():
    from dominion.allies.league_of_shopkeepers import LeagueOfShopkeepers

    state, player = setup("Courier", "Contract")
    state.allies = [LeagueOfShopkeepers()]
    player.favors = 4
    player.highwayman_attacks = 1
    player.deck = [get_card("Contract")]
    buys = player.buys

    get_card("Courier").on_play(state)

    assert player.favors == 5
    assert player.coins == 2  # Courier and the Ally; Contract's $2 is blocked.
    assert player.buys == buys + 1


@pytest.mark.parametrize("replay", ["Tiara", "Reckless"])
def test_highwayman_blocks_only_first_play_of_replayed_treasure(replay):
    class ReplayAI(DummyAI):
        def should_replay_treasure_with_tiara(self, state, player, card):
            return True

    state, player = setup("Courier", ai=ReplayAI())
    player.highwayman_attacks = 1
    player.deck = [get_card("Gold")]
    if replay == "Tiara":
        player.in_play = [get_card("Tiara")]
    else:
        state.pile_traits["Gold"] = "Reckless"

    get_card("Courier").on_play(state)

    assert player.coins == 4
    assert player.highwayman_blocked_this_turn


@pytest.mark.parametrize("source", ["treasure_phase", "courier", "gain"])
@pytest.mark.parametrize("prophecy_name", ["Good Harvest", "Panic"])
def test_reckless_treasure_replay_fires_prophecy_hooks(source, prophecy_name):
    class PlayTreasureAI(DummyAI):
        def choose_treasure(self, state, choices):
            return next((c for c in choices if c is not None), None)

    state, player = setup("Courier", "Buried Treasure", ai=PlayTreasureAI())
    card = get_card("Buried Treasure" if source == "gain" else "Gold")
    state.pile_traits[card.name] = "Reckless"
    state.prophecy = get_prophecy(prophecy_name)
    state.prophecy.is_active = True
    buys = player.buys

    if source == "gain":
        state.supply[card.name] -= 1
        state.gain_card(player, card)
    elif source == "courier":
        player.deck = [card]
        get_card("Courier").on_play(state)
    else:
        player.hand = [card]
        state.handle_treasure_phase()

    assert player.buys == buys + (1 if prophecy_name == "Good Harvest" else 4)
    if prophecy_name == "Good Harvest":
        assert player.good_harvest_treasures_played == {card.name}


def test_reckless_courier_contract_fires_league_of_shopkeepers_twice():
    from dominion.allies.league_of_shopkeepers import LeagueOfShopkeepers

    state, player = setup("Courier", "Contract")
    state.allies = [LeagueOfShopkeepers()]
    state.pile_traits["Contract"] = "Reckless"
    player.favors = 3
    player.deck = [get_card("Contract")]
    buys = player.buys

    get_card("Courier").on_play(state)

    assert player.favors == 5
    assert player.coins == 7  # Courier + two Contracts + two Ally bonuses.
    assert player.buys == buys + 1


def test_courier_inspiring_treasure_plays_action_from_hand():
    class PlayVillageAI(DummyAI):
        def choose_action(self, state, choices):
            return next((c for c in choices if c and c.name == "Village"), None)

    state, player = setup("Courier", "Village", ai=PlayVillageAI())
    state.pile_traits["Gold"] = "Inspiring"
    village = get_card("Village")
    player.hand = [village]
    player.deck = [get_card("Estate"), get_card("Gold")]
    actions = player.actions

    get_card("Courier").on_play(state)

    assert village in player.in_play and village not in player.hand
    assert player.actions == actions + 2
    assert [c.name for c in player.hand] == ["Estate"]


def test_fortune_hunter_keeps_existing_top_card_out_of_reshuffle():
    state, player = setup("Fortune Hunter")
    gold = get_card("Gold")
    player.deck = [gold]
    player.discard = [get_card("Estate") for _ in range(8)]
    get_card("Fortune Hunter").on_play(state)
    assert gold in player.in_play
    assert player.coins == 5


def test_buried_treasure_gain_plays_now_but_resources_arrive_next_turn():
    state, player = setup("Buried Treasure")
    player.projects = [get_project("Guildhall")]
    card = get_card("Buried Treasure")
    buys = player.buys
    state.supply[card.name] -= 1
    state.gain_card(player, card)
    assert card in player.in_play and card in player.duration
    assert card not in player.discard
    assert player.coins == 0 and player.buys == buys
    assert player.coin_tokens == 1
    state.do_duration_phase()
    assert player.coins == 3 and player.buys == buys + 1
    assert card in player.in_play and card not in player.discard
    assert card not in player.duration
    state.handle_cleanup_phase()
    assert sum(c is card for c in player.hand + player.deck + player.discard) == 1


@pytest.mark.parametrize("reckless, tiara, plays", [(True, False, 2), (False, True, 2), (True, True, 3)])
def test_buried_treasure_replays_each_schedule_next_turn_resources(reckless, tiara, plays):
    class ReplayAI(DummyAI):
        def should_replay_treasure_with_tiara(self, state, player, card):
            return True

    state, player = setup("Buried Treasure", ai=ReplayAI())
    if reckless:
        state.pile_traits["Buried Treasure"] = "Reckless"
    if tiara:
        player.in_play = [get_card("Tiara")]
    card = get_card("Buried Treasure")
    state.supply[card.name] -= 1
    state.gain_card(player, card)
    assert player.duration == [card]
    assert player.multiplied_durations == [card] * (plays - 1)

    state.handle_cleanup_phase()
    coins, buys = player.coins, player.buys
    state.do_duration_phase()

    assert player.coins == coins + 3 * plays
    assert player.buys == buys + plays
    assert not player.duration and not player.multiplied_durations
    state.handle_cleanup_phase()
    assert sum(c is card for c in player.hand + player.deck + player.discard) == 1


def test_reckless_buried_treasure_gained_by_duration_waits_until_next_turn(monkeypatch):
    state, player = setup("Buried Treasure", "Mastermind")
    state.pile_traits["Buried Treasure"] = "Reckless"
    trigger = get_card("Mastermind")
    treasure = get_card("Buried Treasure")

    def gain_treasure(current_state):
        current_state.supply[treasure.name] -= 1
        current_state.gain_card(player, treasure)
        trigger.duration_persistent = False

    monkeypatch.setattr(trigger, "on_duration", gain_treasure)
    player.duration = [trigger]
    coins, buys = player.coins, player.buys
    state.do_duration_phase()
    assert (player.coins, player.buys) == (coins, buys)
    assert player.duration == [treasure]
    assert player.multiplied_durations == [treasure]

    state.do_duration_phase()
    assert player.coins == coins + 6
    assert player.buys == buys + 2


def test_buried_treasure_off_turn_gain_preserves_current_player():
    state, current = setup("Buried Treasure")
    other = PlayerState(DummyAI())
    state.players.append(other)
    card = get_card("Buried Treasure")
    state.gain_card(other, card)
    assert state.current_player is current
    assert state.turn_player is current
    assert card in other.duration and card not in current.duration


def test_good_harvest_resets_off_turn_plays_between_opponents_turns():
    state, first = setup("Buried Treasure")
    second, recipient = PlayerState(DummyAI()), PlayerState(DummyAI())
    state.players.extend([second, recipient])
    state.prophecy = get_prophecy("Good Harvest")
    state.prophecy.is_active = True

    for opponent_index in (0, 1):
        state.current_player_index = opponent_index
        state.handle_start_phase()
        coins, buys = recipient.coins, recipient.buys
        for _ in range(2):
            state.supply["Buried Treasure"] -= 1
            state.gain_card(recipient, get_card("Buried Treasure"))
        # Once on each opponent's distinct turn, not once until our next turn.
        assert recipient.coins == coins + 1
        assert recipient.buys == buys + 1
        state.handle_cleanup_phase()


def test_buried_treasure_gain_can_be_blocked_by_highwayman():
    state, player = setup("Buried Treasure")
    player.highwayman_attacks = 1
    card = get_card("Buried Treasure")
    state.supply[card.name] -= 1

    state.gain_card(player, card)

    assert player.highwayman_blocked_this_turn
    assert card in player.in_play
    assert card not in player.duration
    assert player.gained_five_this_turn


def test_highwayman_does_not_block_off_turn_buried_treasure_gain():
    state, current = setup("Buried Treasure")
    player = PlayerState(DummyAI())
    state.players.append(player)
    player.highwayman_attacks = 1
    card = get_card("Buried Treasure")
    state.supply[card.name] -= 1

    state.gain_card(player, card)

    assert card in player.duration
    assert not player.highwayman_blocked_this_turn
    assert state.current_player is current and state.turn_player is current
    state.current_player_index = 1
    coins, buys = player.coins, player.buys
    state.do_duration_phase()
    assert player.coins == coins + 3
    assert player.buys == buys + 1


@pytest.mark.parametrize("prophecy_name", ["Good Harvest", "Panic"])
@pytest.mark.parametrize("active", [False, True])
@pytest.mark.parametrize("off_turn", [False, True])
def test_buried_treasure_gain_triggers_active_prophecy_for_owner(
    prophecy_name, active, off_turn
):
    state, current = setup("Buried Treasure")
    player = PlayerState(DummyAI()) if off_turn else current
    if off_turn:
        state.players.append(player)
    state.prophecy = get_prophecy(prophecy_name)
    state.prophecy.is_active = active
    coins, buys = player.coins, player.buys
    current_resources = current.coins, current.buys

    for _ in range(2):
        state.supply["Buried Treasure"] -= 1
        state.gain_card(player, get_card("Buried Treasure"))

    bonus_coins = int(active and prophecy_name == "Good Harvest")
    bonus_buys = (1 if prophecy_name == "Good Harvest" else 4) if active else 0
    assert player.coins == coins + bonus_coins
    assert player.buys == buys + bonus_buys
    assert len(player.duration) == 2
    assert state.current_player is current and state.turn_player is current
    if off_turn:
        assert (current.coins, current.buys) == current_resources
    if active and prophecy_name == "Good Harvest":
        assert player.good_harvest_treasures_played == {"Buried Treasure"}
    if active and prophecy_name == "Panic":
        assert player.panic_active


def test_mine_does_not_move_played_buried_treasure_back_to_hand():
    strategy = EnhancedStrategy()
    strategy.treasure_priority = [PriorityRule("Silver")]
    strategy.gain_priority = [PriorityRule("Buried Treasure")]
    state, player = setup("Mine", "Buried Treasure", ai=GeneticAI(strategy))
    player.hand = [get_card("Silver")]
    get_card("Mine").on_play(state)
    assert any(c.name == "Buried Treasure" for c in player.duration)
    assert not player.hand


def test_kind_emperor_can_gain_city_quarter_while_in_debt_without_more_debt():
    class EmperorStrategy(EnhancedStrategy):
        def choose_kind_emperor_gain(self, state, player, choices):
            return next(c for c in choices if c.name == "City Quarter")

    state, player = setup("City Quarter", ai=GeneticAI(EmperorStrategy()))
    player.debt = 2
    prophecy = get_prophecy("Kind Emperor")
    prophecy.on_turn_start(state, player)
    assert any(c.name == "City Quarter" for c in player.hand)
    assert player.debt == 2
    assert state.supply["City Quarter"] == 9


def test_coffers_pay_debt_before_a_purchase():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Silver")]
    state, player = setup("Imperial Envoy", ai=GeneticAI(strategy))
    player.coins = 1
    player.coin_tokens = 4
    player.debt = 2
    player.buys = 1
    state.handle_buy_phase()
    assert player.debt == 0
    assert player.coin_tokens == 0
    assert any(c.name == "Silver" for c in player.discard)


@pytest.mark.parametrize("choice, spent", [(0, 0), (1, 1), (99, 3), (-1, 0), (None, 0)])
def test_strategy_can_preserve_coffers_during_debt_payment(choice, spent):
    class SaveCoffers(EnhancedStrategy):
        def choose_coffers_for_debt(self, state, player, maximum):
            assert maximum == 3
            return choice

    state, player = setup("Imperial Envoy", ai=GeneticAI(SaveCoffers()))
    player.coins = 1
    player.coin_tokens = 3
    player.debt = 5
    player.buys = 0

    state.handle_buy_phase()

    assert player.coins == 0
    assert player.coin_tokens == 3 - spent
    assert player.debt == 4 - spent
    assert player.coins_spent_this_turn == 1 + spent


def test_mastermind_mine_upgrades_then_recycles_gold_for_three_coffers():
    from generated_strategies.mine_guildhall import MineGuildhall

    strategy = MineGuildhall()
    state, player = setup("Mine", "Mastermind", ai=GeneticAI(strategy))
    player.projects = [get_project("Guildhall")]
    mine = get_card("Mine")
    player.hand = [mine, get_card("Copper")]
    mastermind = get_card("Mastermind")
    player.in_play = [mastermind]
    player.duration = [mastermind]
    state.do_duration_phase()
    assert player.coin_tokens == 3
    assert [c.name for c in player.hand] == ["Gold"]
    assert strategy.mine_gains == {
        "Copper -> Silver": 1,
        "Silver -> Gold": 1,
        "Gold -> Gold": 1,
    }
    assert mine in player.in_play and mastermind in player.in_play


def test_mine_upgrade_selection_does_not_change_treasure_play_order():
    from generated_strategies.mine_guildhall import MineGuildhall

    strategy = MineGuildhall()
    state, player = setup("Mine", ai=GeneticAI(strategy))
    copper, gold = get_card("Copper"), get_card("Gold")
    player.hand = [copper, gold]
    assert player.ai.choose_treasure(state, player.hand) is gold
    get_card("Mine").on_play(state)
    assert copper in state.trash
    assert gold in player.hand
    assert any(c.name == "Silver" for c in player.hand)


@pytest.mark.parametrize("name", ["Buried Treasure", "Gold"])
@pytest.mark.parametrize("gatekeeper", [False, True])
def test_rapid_expansion_does_not_set_aside_a_gain_that_already_moved(name, gatekeeper):
    state, player = setup(name)
    state.prophecy = get_prophecy("Rapid Expansion")
    state.prophecy.is_active = True
    player.gatekeeper_attacks = int(gatekeeper)
    card = get_card(name)
    state.supply[name] -= 1

    state.gain_card(player, card)

    if gatekeeper:
        assert player.exile == [card]
        assert not player.in_play and not player.duration
        assert not player.rapid_expansion_set_aside
    elif name == "Buried Treasure":
        assert player.in_play == [card]
        assert player.duration == [card]
        assert not player.rapid_expansion_set_aside
        state.prophecy.on_turn_start(state, player)
        state.do_duration_phase()
        assert player.coins == 3
        assert player.buys == 2
        assert player.in_play == [card]
    else:
        assert player.rapid_expansion_set_aside == [card]
        assert not player.discard
        state.prophecy.on_turn_start(state, player)
        assert player.coins == 3
        assert player.in_play == [card]


@pytest.mark.parametrize("had_exiled_copy", [False, True])
def test_buried_treasure_respects_prior_gatekeeper_movement(had_exiled_copy):
    state, player = setup("Buried Treasure")
    player.gatekeeper_attacks = 1
    if had_exiled_copy:
        player.exile = [get_card("Buried Treasure")]
    card = get_card("Buried Treasure")
    state.supply[card.name] -= 1

    state.gain_card(player, card)

    if had_exiled_copy:
        assert card in player.in_play and card in player.duration
    else:
        # The engine resolves Gatekeeper first. Once exiled, the gained card
        # cannot move again to satisfy its mandatory on-gain play trigger.
        assert player.exile == [card]
        assert not player.in_play and not player.duration


def test_main_enlightenment_substitution_preserves_urchin_attack_reaction():
    class PlayMilitia(DummyAI):
        def choose_action(self, state, choices):
            return next((c for c in choices if c and c.name == "Militia"), None)

    state, player = setup("Militia", "Urchin", "Mercenary", ai=PlayMilitia())
    state.prophecy = get_prophecy("Enlightenment")
    state.prophecy.is_active = True
    state.phase = "action"
    player.projects = [get_project("Capitalism")]
    urchin, militia = get_card("Urchin"), get_card("Militia")
    player.in_play = [urchin]
    player.hand = [militia]
    player.deck = [get_card("Estate")]
    state.supply["Mercenary"] = mercenaries = 10

    state.handle_action_phase()

    assert player.in_play == [militia]
    assert urchin in state.trash
    assert state.supply["Mercenary"] == mercenaries - 1
    assert any(c.name == "Mercenary" for c in player.discard)
    assert [c.name for c in player.hand] == ["Estate"]
    assert player.coins == 0


@pytest.mark.parametrize("good_harvest", [False, True])
@pytest.mark.parametrize("tiara", [False, True])
def test_treasure_log_includes_observer_and_replay_coins(good_harvest, tiara):
    class ReplayGold(DummyAI):
        def choose_treasure(self, state, choices):
            return next((c for c in choices if c and c.name == "Gold"), None)

        def should_replay_treasure_with_tiara(self, state, player, card):
            return True

    state, player = setup("Gold", "Tiara", ai=ReplayGold())
    state.phase = "treasure"
    if good_harvest:
        state.prophecy = get_prophecy("Good Harvest")
        state.prophecy.is_active = True
    if tiara:
        player.in_play = [get_card("Tiara")]
    player.hand = [get_card("Gold")]
    player.coins = 5
    logs = []
    state.log_callback = logs.append

    state.handle_treasure_phase()

    added = 3 * (1 + int(tiara)) + int(good_harvest)
    context = next(entry[3] for entry in logs if entry[2] == "plays Gold")
    assert player.coins == 5 + added
    assert context["coins_before"] == 5
    assert context["coins_added"] == added
    assert context["coins_after"] == player.coins
