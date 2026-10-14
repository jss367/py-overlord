"""Physical gain effects follow owner choices, not one global hook order."""

import pytest

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.projects.innovation import Innovation
from dominion.landmarks.registry import get_landmark
from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.ai.genetic_ai import GeneticAI


def setup(hand=(), order=()):
    strategy = EnhancedStrategy()
    seen = []
    def choose(state, player, gain, choices):
        assert state.current_player is player
        seen.append((gain.name, tuple(e.kind for e in choices)))
        return min(choices, key=lambda e: order.index(e.kind) if e.kind in order else len(order))
    strategy.choose_gain_effect = choose
    strategy.choose_sleigh_reaction = lambda *args: 'deck'
    strategy.should_play_sheepdog = lambda *args: True
    player = PlayerState(GeneticAI(strategy))
    player.hand = [get_card(n) for n in hand]
    player.deck = [get_card('Copper') for _ in range(10)]
    state = GameState([player], supply={'Gold':10,'Silver':10,'Village':10,'Province':8})
    state.log_callback = lambda *_: None
    return state, player, seen


@pytest.mark.parametrize('first', ['sleigh','sheepdog'])
def test_sheepdog_and_sleigh_order_changes_drawn_gain(first):
    state, player, seen = setup(['Sleigh','Sheepdog'], [first])
    gold = state.gain_from_supply(player, 'Gold')
    assert (gold in player.hand) is (first == 'sleigh')
    assert (gold in player.deck) is (first == 'sheepdog')
    assert player.count('Gold') == 1
    assert any({'sleigh','sheepdog'} <= set(kinds) for _, kinds in seen)


def test_newly_drawn_reactions_are_eligible_for_current_gain():
    state, player, _ = setup(['Sheepdog'], ['sheepdog','sleigh'])
    player.deck[-1] = get_card('Sleigh')
    gold = state.gain_from_supply(player, 'Gold')
    assert gold in player.deck
    assert any(c.name == 'Sleigh' for c in player.discard)


def test_multiple_sleighs_can_discard_after_gain_loses_track_and_nest_gains():
    state, player, _ = setup(['Watchtower','Sleigh','Sleigh'], ['watchtower','sleigh'])
    player.ai.strategy.choose_watchtower_reaction = lambda *args: 'topdeck'
    player.ai.strategy.choose_sleigh_reaction = lambda s,p,c: 'deck' if c.name == 'Gold' else None
    state.supply['Sleigh'] = 2
    state.pile_traits['Sleigh'] = 'Friendly'
    original = list(player.hand[1:])
    gold = state.gain_from_supply(player, 'Gold')
    assert gold in player.deck
    assert all(c in player.discard for c in original)
    assert state.supply['Sleigh'] == 0
    assert player.count('Sleigh') == 4
    assert player.count('Gold') == 1


@pytest.mark.parametrize('order', [('cargo_ship','sleigh'),('sleigh','cargo_ship')])
def test_cargo_ship_and_sleigh_cannot_both_move_the_gain(order):
    state, player, _ = setup(['Sleigh'], order)
    cargo = get_card('Cargo Ship')
    player.in_play = [cargo]
    cargo.play_effect(state)
    player.ai.should_set_aside_cargo_ship = lambda *args: True
    gold = state.gain_from_supply(player,'Gold')
    assert (cargo.set_aside is gold) is (order[0] == 'cargo_ship')
    assert (gold in player.deck) is (order[0] == 'sleigh')
    assert player.count('Gold') == 1


def test_topdecking_an_already_topdecked_gain_keeps_it_movable():
    state, player, _ = setup(['Watchtower','Sleigh'], ['watchtower','sleigh'])
    player.ai.strategy.choose_watchtower_reaction = lambda *args: 'topdeck'
    player.ai.strategy.choose_sleigh_reaction = lambda *args: 'hand'
    gold = state.gain_from_supply(player,'Gold',destination='deck')
    assert gold in player.hand and gold not in player.deck


def test_gain_covered_on_deck_stops_moving_after_cover_is_removed():
    state, player, _ = setup(["Watchtower", "Sleigh"], ["card_on_gain", "watchtower", "sleigh"])
    player.ai.strategy.choose_watchtower_reaction = lambda *args: "topdeck"
    player.ai.strategy.choose_sleigh_reaction = lambda *args: "hand"
    gold = get_card("Gold")
    gold.on_gain = lambda s, p: s.gain_from_supply(p, "Silver", destination="deck")
    state.gain_card(player, gold, to_deck=True)
    assert gold in player.deck and gold not in player.hand
    assert any(c.name == "Silver" for c in player.hand)
    assert player.deck[-1] is gold


def test_next_gain_innovation_is_reserved_before_nested_card_ability():
    state, player, _ = setup(order=['card_on_gain','innovation'])
    player.projects = [Innovation()]
    outer = get_card('Village')
    outer.on_gain = lambda s,p: s.gain_from_supply(p,'Village')
    state.gain_card(player,outer)
    assert outer in player.in_play
    assert sum(c.name=='Village' for c in player.in_play) == 1
    assert player.count('Village') == 2


def test_next_gain_deliver_not_stolen_by_nested_gain():
    state, player, _ = setup(order=['card_on_gain','deliver'])
    player.deliver_pending_count = 1
    outer = get_card('Village')
    outer.on_gain = lambda s,p: s.gain_from_supply(p,'Gold')
    state.gain_card(player,outer)
    assert player.deliver_set_aside == [outer]
    assert player.discard[0].name == 'Gold'
    assert player.deliver_pending_count == 0


def test_labyrinth_counts_event_identity_after_nested_third_gain():
    state, player, _ = setup(order=['card_on_gain','landmark'])
    landmark = get_landmark('Labyrinth')
    state.landmarks = [landmark]
    landmark.setup(state)
    state.gain_from_supply(player,'Silver')
    outer = get_card('Village')
    outer.on_gain = lambda s,p: s.gain_from_supply(p,'Gold')
    state.gain_card(player,outer)
    assert player.cards_gained_this_turn == 3
    assert player.vp_tokens == 2


def test_off_turn_owner_context_and_turn_order_are_preserved():
    state, gainer, _ = setup(['Sleigh','Sheepdog'], ['sheepdog'])
    turn = PlayerState(GeneticAI(EnhancedStrategy()))
    turn.projects = [type('Observer',(), {'name':'Observer','on_opponent_gain':lambda self,s,p,c: seen.append((p,s.turn_player))})()]
    seen = []
    state.players.append(turn)
    state.current_player_index = 1
    gold = state.gain_from_supply(gainer,'Gold')
    assert seen == [(turn,turn)]
    assert state.current_player is turn and state.turn_player is turn
    assert gold in gainer.deck


@pytest.mark.parametrize('invalid', [None, 'unknown', 5])
def test_invalid_order_override_falls_back_and_consumes_effects(invalid):
    state, player, _ = setup(['Sleigh','Sheepdog'])
    player.ai.strategy.choose_gain_effect = lambda *args: invalid
    gold = state.gain_from_supply(player,'Gold')
    assert gold in player.hand
    assert len([c for c in player.in_play if c.name=='Sheepdog']) == 1


def test_reaction_is_not_reused_if_custom_reactor_leaves_it_in_hand():
    state,player,_=setup(['Sheepdog'])
    calls=[]
    player.hand[0].react_to_own_gain=lambda *args: calls.append(1)
    state.gain_from_supply(player,'Gold')
    assert calls==[1]


def test_pathological_new_reaction_loop_hits_bounded_guard(monkeypatch):
    import dominion.game.gain_effects as effects
    state,player,_=setup(['Sheepdog'])
    def replenish(*args):
        card=get_card('Sheepdog')
        card.react_to_own_gain=replenish
        player.hand.append(card)
    player.hand[0].react_to_own_gain=replenish
    monkeypatch.setattr(effects,'GAIN_EFFECT_LIMIT',8)
    with pytest.raises(RuntimeError,match='Gain effect limit'):
        state.gain_from_supply(player,'Gold')
    assert state.current_player is player
    assert state.reaction_turn_player_index is None


def test_drawn_watchtower_cannot_follow_gain_through_a_shuffle():
    state,player,_=setup(['Sheepdog'],['sheepdog','watchtower'])
    player.deck=[]
    player.discard=[get_card('Watchtower')]
    player.ai.strategy.choose_watchtower_reaction=lambda *args: 'trash'
    gold=state.gain_from_supply(player,'Gold')
    assert gold in player.hand
    assert gold not in state.trash
    assert state.gain_destination(gold) is None


def test_reaction_qualification_uses_gain_time_types():
    from dominion.prophecies.registry import get_prophecy
    state,player,seen=setup(['Falconer'],['card_on_gain'])
    state.prophecy=get_prophecy('Enlightenment')
    state.prophecy.is_active=False
    silver=get_card('Silver')
    silver.on_gain=lambda s,p: setattr(s.prophecy,'is_active',True)
    state.gain_card(player,silver)
    assert not any('falconer' in kinds for _,kinds in seen)
    assert player.hand[0].name=='Falconer'


@pytest.mark.parametrize('trashed,virtual',[(False,False),(True,False),(False,True)])
def test_landing_party_does_not_revive_or_own_an_instruction_proxy(trashed,virtual):
    state,player,_=setup(order=['landing_party'])
    landing=get_card('Landing Party')
    landing.virtual_supply_play=virtual
    player.in_play=[] if virtual or trashed else [landing]
    if trashed:state.trash.append(landing)
    player.duration=[landing]
    state.landing_party_pending[id(player)]=[landing,landing]
    gold=state.gain_from_supply(player,'Gold')
    assert player.count('Gold')==1 and gold in player.deck
    assert sum(c is landing for c in player.all_cards())==(not (virtual or trashed))
    assert landing not in player.duration
    assert state.landing_party_pending[id(player)]==[]


def test_cloned_gain_instruction_maps_follow_the_cloned_owner():
    import copy
    state,player,_=setup()
    state.mirror_pending[id(player)]=1
    state.landing_party_pending[id(player)]=[get_card('Landing Party')]
    clone=copy.deepcopy(state)
    cloned=clone.players[0]
    assert clone.mirror_pending[id(cloned)]==1
    assert clone.landing_party_pending[id(cloned)][0] is not state.landing_party_pending[id(player)][0]


def test_already_triggered_royal_seal_survives_its_source_leaving_play():
    state,player,_=setup()
    royal=get_card('Royal Seal')
    player.in_play=[royal]
    player.ai.should_topdeck_with_royal_seal=lambda *args: True
    village=get_card('Village')
    def remove_source(s,p):
        p.in_play.remove(royal)
        s.trash_card(p,royal)
    village.on_gain=remove_source
    state.gain_card(player,village)
    assert village in player.deck and royal in state.trash


@pytest.mark.parametrize('off_turn', [False, True])
def test_watchtower_trash_respects_real_turn_for_priest_and_crucible(off_turn):
    state, player, _ = setup(['Watchtower'])
    other = PlayerState(GeneticAI(EnhancedStrategy()))
    state.players.append(other)
    state.current_player_index = int(off_turn)
    player.priest_played_this_turn = 2
    player.cards_trashed_this_turn = 3
    player.ai.strategy.choose_watchtower_reaction = lambda *args: 'trash'
    state.supply['Curse'] = 10
    curse = state.gain_from_supply(player, 'Curse')
    assert curse in state.trash
    assert player.coins == (0 if off_turn else 4)
    assert player.cards_trashed_this_turn == (3 if off_turn else 4)
    assert state.current_player is (other if off_turn else player)
    assert state.turn_player is state.current_player
