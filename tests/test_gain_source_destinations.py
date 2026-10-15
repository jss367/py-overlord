"""Gain sources declare destinations before reactions and preserve exchanges."""

import pytest

from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.player_state import PlayerState
from dominion.ai.genetic_ai import GeneticAI
from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.prophecies.registry import get_prophecy
from tests.test_gain_effect_ordering import setup

HAND_SOURCES = ('Mine', 'Artisan', 'Sculptor', 'Falconer', 'Transmogrify', 'Cobbler',
                'Silver Mine', 'Explorer', 'Pirate', 'Trading Post', 'Wish', 'Mining Road', 'Kind Emperor')
CASES = [(name, mode) for name in HAND_SOURCES for mode in ('none', 'trash', 'topdeck', 'exchange')]
CASES += [(name, mode) for name in ('Treasure Map', 'Jack of All Trades', 'Dismantle', 'Blockade', 'Summon', 'Continue', 'Quartermaster')
          for mode in ('none', 'trash', 'topdeck', 'exchange')]
CASES += [(name, mode) for name in ('Sea Hag', 'Sickness', 'Pickaxe', 'Joust') for mode in ('none', 'trash', 'topdeck')]


def fixture(source, mode, monkeypatch):
    state, player, _ = setup(['Watchtower'])
    player.hand += [get_card('Copper') for _ in range(4)]
    player.deck = [get_card('Estate') for _ in range(10)]
    state.supply = {'Silver': 10, 'Village': 10, 'Gold': 10, 'Copper': 10,
                    'Estate': 10, 'Curse': 10, 'Changeling': 10}
    target = 'Village' if source in ('Kind Emperor', 'Summon', 'Continue') else 'Silver'
    if source in ('Treasure Map', 'Dismantle', 'Pirate', 'Mining Road'):
        target = 'Gold'
    elif source in ('Sea Hag', 'Sickness'):
        target = 'Curse'
    elif source == 'Pickaxe':
        target = 'Hammer'
        monkeypatch.setattr('dominion.cards.plunder.pickaxe.random.choice', lambda choices: target)
    elif source == 'Joust':
        target = 'Courser'
        state.supply[target] = 5
    initial = 'pending_gain_set_aside' if source == 'Blockade' else 'hand' if source in HAND_SOURCES or source in ('Pickaxe', 'Joust') else 'deck' if source in ('Treasure Map', 'Sea Hag', 'Sickness') else 'discard'
    if source == 'Summon':
        state.original_kingdom_pile_names = {'Village'}
    observed = []
    def react(s, p, gained):
        if gained.name != target:
            return None
        observed.append((gained, gained in getattr(p, initial)))
        return mode if mode in ('trash', 'topdeck') else None
    player.ai.strategy.choose_watchtower_reaction = react
    player.ai.should_exchange_changeling = lambda *args: mode == 'exchange'
    def pick(choices):
        return next((c for c in choices if getattr(c, 'name', None) == target), None)
    player.ai.choose_buy = lambda s, choices: pick(choices)
    player.ai.choose_mine_gain = lambda s, p, choices: pick(choices)
    player.ai.choose_mine_treasure = lambda s, p, choices: choices[0]
    player.ai.choose_card_to_gain_to_hand = lambda s, p, choices, limit: pick(choices)
    player.ai.choose_kind_emperor_gain = lambda s, p, choices: pick(choices)
    player.ai.choose_continue_target = lambda s, p, choices: pick(choices)
    player.ai.choose_gain_for_summon = lambda s, p, choices: pick(choices)
    player.ai.choose_quartermaster_option = lambda s, p, mat, choices: ('gain', pick(choices))
    player.ai.choose_card_to_gain_with_blockade = lambda *args, **kw: get_card(target)
    player.ai.choose_card_to_topdeck_from_hand = lambda s, p, choices, **kw: next(c for c in choices if c.name == 'Copper')
    player.ai.choose_cards_to_trash = lambda s, choices, n: [c for c in choices if c.name == 'Copper'][:n]
    player.ai.should_joust_province = lambda *args: True
    player.ai.choose_sickness_mode = lambda *args: 'curse'
    if source in ('Dismantle', 'Pickaxe'):
        doomed = get_card('Village')
        player.hand.append(doomed)
        player.ai.choose_card_to_trash = lambda *args: doomed
    if source == 'Transmogrify':
        doomed = get_card('Estate')
        player.hand.append(doomed)
        player.ai.choose_card_to_transmogrify = lambda *args: doomed
        player.ai.choose_gain_for_transmogrify = lambda s, p, choices: pick(choices)
        player.ai.should_call_from_tavern = lambda *args: True
    if source == 'Treasure Map':
        player.hand.append(get_card('Treasure Map'))
    if source == 'Joust':
        player.hand.append(get_card('Province'))
    phase_calls = []
    if source in ('Kind Emperor', 'Sickness'):
        card = get_prophecy(source)
        state.prophecy = card
        card.is_active = True
        invoke = lambda: card.on_turn_start(state, player)
    elif source in ('Summon', 'Continue'):
        card = get_event(source)
        state.phase = 'buy'
        state.handle_action_phase = lambda: phase_calls.append(state.phase)
        invoke = lambda: card.on_buy(state, player)
    else:
        card = get_card(source)
        player.in_play = [card]
        invoke = lambda: card.play_effect(state)
        if source in ('Cobbler', 'Silver Mine', 'Pirate'):
            player.duration = [card]
            invoke = lambda: card.on_duration(state)
        elif source == 'Transmogrify':
            player.tavern_mat = [card]
            invoke = lambda: card.on_call_from_tavern(state, player, 'start_of_turn')
        elif source == 'Quartermaster':
            player.duration = [card]
            invoke = lambda: state._handle_quartermaster_start_of_turn(player)
        elif source == 'Mining Road':
            invoke = lambda: state.gain_from_supply(player, 'Copper')
        elif source == 'Sea Hag':
            attacker = PlayerState(GeneticAI(EnhancedStrategy()))
            state.players.append(attacker)
            state.current_player_index = 1
    return state, player, card, target, initial, observed, phase_calls, invoke


@pytest.mark.parametrize('source,mode', CASES)
def test_source_destination_precedes_reactions_and_never_redirects_exchange(source, mode, monkeypatch):
    state, player, card, target, initial, observed, phase_calls, invoke = fixture(source, mode, monkeypatch)
    invoke()
    count = 4 if source == 'Treasure Map' else 1
    assert len(observed) == count
    assert all(in_initial for _, in_initial in observed)
    if mode == 'exchange':
        assert sum(c.name == 'Changeling' for c in player.discard) == count
        assert not any(c.name == 'Changeling' for c in player.hand + player.deck + player.in_play + player.summon_set_aside)
        assert state.supply[target] == 10
    elif mode == 'trash':
        assert all(c in state.trash and c not in player.hand + player.deck + player.discard for c, _ in observed)
    elif mode == 'topdeck':
        assert all(c in player.deck and c not in player.hand for c, _ in observed)
    else:
        final_zone = card.set_aside if source in ('Blockade', 'Quartermaster') else player.summon_set_aside if source == 'Summon' else player.in_play if source == 'Continue' else getattr(player, initial)
        assert all(c in final_zone for c, _ in observed)
    if source == 'Sculptor':
        assert player.villagers == 1
    if source == 'Blockade':
        assert [c.name for c in card.set_aside] == ([target] if mode == 'none' else [])
        if mode != 'none':
            assert not card.set_aside
    if source == 'Quartermaster' and mode != 'none':
        assert not card.set_aside
    if source == 'Continue':
        assert phase_calls == ['action'] and state.phase == 'buy'


def test_sculptor_does_not_count_exchanged_silver_as_the_gain(monkeypatch):
    state, player, _, _, _, _, _, invoke = fixture('Sculptor', 'none', monkeypatch)
    player.hand.append(get_card('Trader'))
    player.ai.should_reveal_trader = lambda *args, **kw: True
    player.ai.choose_buy = lambda s, choices: next(c for c in choices if c is not None and c.name == 'Village')
    invoke()
    assert player.villagers == 0  # Village was gained; the exchanged Silver was not.
    assert any(c.name == 'Silver' for c in player.discard)
    assert state.supply['Village'] == 10
