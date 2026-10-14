"""Physical gain effects follow owner choices, not one global hook order."""

import pytest

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.projects.innovation import Innovation
from dominion.landmarks.registry import get_landmark
from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.ai.genetic_ai import GeneticAI


def setup(hand=(), order=(), *, observe=False):
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
    if observe:
        player.projects = [type('Observer', (), {'name': 'Observer', 'on_gain': lambda *args: None})()]
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


@pytest.mark.parametrize('name', ['Black Cat', 'Footpad', 'Stowaway', 'Monkey', 'Blockade'])
@pytest.mark.parametrize('gain', ['Gold', 'Province'])
def test_opponent_hand_menu_filters_inactive_reactions(name, gain):
    state, owner, seen = setup([name])
    gainer = PlayerState(GeneticAI(EnhancedStrategy()))
    state.players.append(gainer)
    state.current_player_index = 1
    # Two other instructions keep the ordering hook observable even when
    # the hand card has no legal reaction to this gain.
    owner.projects = [type('Observer', (), {
        'name': 'Observer', 'on_opponent_gain': lambda *args: None,
    })() for _ in range(2)]
    state.gain_from_supply(gainer, gain)
    offered = any('opponent_reaction' in kinds for _, kinds in seen)
    assert offered == (gain == 'Province' and name in {'Black Cat', 'Footpad', 'Stowaway'})


@pytest.mark.parametrize('order', [('gatekeeper', 'sleigh'), ('sleigh', 'gatekeeper')])
def test_gatekeeper_cannot_follow_a_gain_moved_to_hand_by_sleigh(order):
    state, player, _ = setup(['Sleigh'], order)
    player.gatekeeper_attacks = 1
    player.ai.strategy.choose_sleigh_reaction = lambda *args: 'hand'
    silver = state.gain_from_supply(player, 'Silver')
    assert (silver in player.hand) == (order[0] == 'sleigh')
    assert (silver in player.exile) == (order[0] == 'gatekeeper')
    assert player.count('Silver') == 1
    assert any(c.name == 'Sleigh' for c in player.discard)


@pytest.mark.parametrize('prophecy_name', ['Rapid Expansion', 'Progress'])
@pytest.mark.parametrize('first', ['sleigh', 'prophecy'])
def test_prophecy_and_sleigh_respect_the_first_mover(prophecy_name, first):
    from dominion.prophecies.registry import get_prophecy
    state, player, _ = setup(['Sleigh'], [first])
    player.ai.strategy.choose_sleigh_reaction = lambda *args: 'hand'
    state.prophecy = get_prophecy(prophecy_name)
    state.prophecy.is_active = True
    gold = state.gain_from_supply(player, 'Gold')
    assert (gold in player.hand) == (first == 'sleigh')
    assert (gold in player.rapid_expansion_set_aside) == (first == 'prophecy' and prophecy_name == 'Rapid Expansion')
    assert (gold in player.deck) == (first == 'prophecy' and prophecy_name == 'Progress')
    assert sum(c is gold for zone in (player.hand, player.deck, player.discard, player.rapid_expansion_set_aside) for c in zone) == 1


@pytest.mark.parametrize('destination', ['discard', 'hand', 'deck'])
def test_changeling_exchange_puts_replacement_in_discard(destination):
    state, player, _ = setup(order=['changeling'])
    state.supply['Changeling'] = 10
    player.ai.should_exchange_changeling = lambda *args: True
    replacement = state.gain_from_supply(player, 'Gold', destination=destination)
    assert replacement.name == 'Changeling'
    assert replacement in player.discard
    assert replacement not in player.hand and replacement not in player.deck
    assert state.supply['Gold'] == 10
    assert state.supply['Changeling'] == 9


@pytest.mark.parametrize('first', ['sleigh', 'changeling'])
def test_changeling_cannot_exchange_a_sleigh_moved_gain(first):
    state, player, _ = setup(['Sleigh'], [first])
    player.ai.strategy.choose_sleigh_reaction = lambda *args: 'hand'
    player.ai.should_exchange_changeling = lambda *args: True
    state.supply['Changeling'] = 10
    result = state.gain_from_supply(player, 'Gold')
    assert result.name == ('Gold' if first == 'sleigh' else 'Changeling')
    assert (result in player.hand) == (first == 'sleigh')
    assert (result in player.discard) == (first == 'changeling')
    assert state.supply['Changeling'] == (10 if first == 'sleigh' else 9)


@pytest.mark.parametrize('off_turn', [False, True])
@pytest.mark.parametrize('debt', [0, 2])
def test_harsh_winter_gain_uses_real_turn_for_placing_and_taking_debt(off_turn, debt):
    from dominion.prophecies.registry import get_prophecy
    state, player, _ = setup()
    other = PlayerState(GeneticAI(EnhancedStrategy()))
    state.players.append(other)
    state.current_player_index = int(off_turn)
    state.prophecy = get_prophecy('Harsh Winter')
    state.prophecy.is_active = True
    if debt:
        state.harsh_winter_debt['Gold'] = debt
    state.gain_from_supply(player, 'Gold')
    assert player.debt == (debt if not off_turn else 0)
    expected = debt if off_turn else 0 if debt else 2
    assert state.harsh_winter_debt.get('Gold', 0) == expected


@pytest.mark.parametrize('gain,exiled,expected', [('Province', False, False), ('Silver', True, False), ('Silver', False, True)])
def test_gatekeeper_menu_only_contains_qualified_gain_time_triggers(gain, exiled, expected):
    state, player, seen = setup(['Sheepdog'])
    player.gatekeeper_attacks = 1
    if exiled:
        player.exile = [get_card('Silver')]
    state.gain_from_supply(player, gain)
    assert any('gatekeeper' in choices for _, choices in seen) == expected


def test_gatekeeper_keeps_both_triggers_when_nested_gain_adds_an_exiled_copy():
    state, player, _ = setup(order=['card_on_gain', 'gatekeeper'])
    player.gatekeeper_attacks = 1
    outer = get_card('Silver')
    outer.on_gain = lambda s, p: s.gain_from_supply(p, 'Silver')
    state.gain_card(player, outer)
    assert len(player.exile) == 2 and outer in player.exile
    assert all(c.name == 'Silver' for c in player.exile)


@pytest.mark.parametrize('gain', ['Estate', 'Curse'])
def test_gatekeeper_uses_live_gain_types(gain):
    state, player, _ = setup()
    player.gatekeeper_attacks = 1
    state.supply[gain] = 10
    if gain == 'Estate':
        player.inherited_action_name = 'Village'
    else:
        state.supply['Charlatan'] = 10
    gained = state.gain_from_supply(player, gain)
    assert gained in player.exile


def test_nonmoving_growth_trigger_still_resolves_after_sleigh_moves_the_gain():
    from dominion.prophecies.registry import get_prophecy
    state, player, _ = setup(['Sleigh'], ['sleigh', 'prophecy'])
    player.ai.strategy.choose_sleigh_reaction = lambda *args: 'hand'
    player.ai.choose_buy = lambda s, choices: next((c for c in choices if getattr(c, 'name', None) == 'Village'), None)
    state.prophecy = get_prophecy('Growth')
    state.prophecy.is_active = True
    gold = state.gain_from_supply(player, 'Gold')
    assert gold in player.hand
    assert state.gain_destination(gold) is None
    assert player.count('Village') == 1
    assert state.supply['Village'] == 9


@pytest.mark.parametrize('name,expected', [('Silver', True), ('Changeling', False), ('Ghost', False)])
def test_changeling_menu_excludes_unavailable_exchanges(name, expected):
    state, player, seen = setup(['Sheepdog'])
    state.supply['Changeling'] = 10
    if name == 'Ghost':
        state.gain_card(player, get_card(name), from_supply=False)
    else:
        state.gain_from_supply(player, name)
    assert any('changeling' in choices for _, choices in seen) == expected


def test_changeling_qualification_keeps_the_gain_time_cost_after_other_effects():
    state, player, _ = setup(order=['card_on_gain', 'changeling'])
    state.supply['Changeling'] = 10
    player.ai.should_exchange_changeling = lambda *args: True
    silver = get_card('Silver')
    def lower_cost(s, p):
        highway = get_card('Highway')
        p.in_play.append(highway)
        highway.play_effect(s)
    silver.on_gain = lower_cost
    state.supply['Silver'] -= 1
    result = state.gain_card(player, silver)
    assert state.get_card_cost(player, silver) == 2
    assert result.name == 'Changeling' and result in player.discard
    assert state.supply['Silver'] == 10


@pytest.mark.parametrize('change', ['deplete', 'refill', 'remove_origin'])
def test_changeling_menu_refreshes_availability_after_nested_effects(change):
    state, player, _ = setup(order=['card_on_gain'])
    state.supply['Changeling'] = 0 if change == 'refill' else 1
    player.ai.should_exchange_changeling = lambda *args: True
    # Independent nonmoving instructions keep the menu observable after the
    # nested effect, including when the exchange is no longer available.
    player.projects = [type('Observer', (), {'name': 'Observer', 'on_gain': lambda *args: None})() for _ in range(2)]
    ready = []
    menus = []
    returned = get_card('Changeling')
    if change == 'refill':
        player.hand.append(returned)
    outer = get_card('Village')
    def alter_supply(s, p):
        if change == 'deplete':
            s.gain_from_supply(p, 'Silver')
        elif change == 'refill':
            p.hand.remove(returned)
            s._restore_to_supply_pile(returned)
        else:
            del s.supply['Village']
        ready.append(True)
    outer.on_gain = alter_supply
    def choose(s, p, gained, choices):
        if gained is outer and ready:
            menus.append([effect.kind for effect in choices])
        return next((effect for effect in choices if effect.kind == 'card_on_gain'), choices[0])
    player.ai.strategy.choose_gain_effect = choose
    state.supply['Village'] -= 1
    result = state.gain_card(player, outer)
    assert menus
    assert any('changeling' in menu for menu in menus) == (change == 'refill')
    assert result.name == ('Changeling' if change == 'refill' else 'Village')


@pytest.mark.parametrize('gold_available', [0, 1])
def test_fools_gold_can_be_trashed_after_gold_runs_out(gold_available):
    state, gainer, _ = setup()
    owners = [PlayerState(GeneticAI(EnhancedStrategy())) for _ in range(2)]
    state.players += owners
    state.supply['Gold'] = gold_available
    originals = []
    for owner in owners:
        card = get_card("Fool's Gold")
        originals.append(card)
        owner.hand = [card]
        owner.ai.should_trash_fools_gold_for_gold = lambda *args: True
    state.gain_from_supply(gainer, 'Province')
    assert all(card in state.trash for card in originals)
    assert sum(p.count('Gold') for p in owners) == gold_available
    assert state.supply['Gold'] == 0


@pytest.mark.parametrize('name,gain,pool,pile_vp,expected', [
    ('Arena', 'Gold', 12, {}, False),
    ('Baths', 'Gold', 12, {}, False),
    ('Battlefield', 'Gold', 12, {}, False),
    ('Battlefield', 'Province', 0, {}, False),
    ('Battlefield', 'Province', 12, {}, True),
    ('Aqueduct', 'Gold', 0, {'Gold': 0}, False),
    ('Aqueduct', 'Gold', 0, {'Gold': 1}, True),
    ('Aqueduct', 'Province', 1, {}, True),
    ('Defiled Shrine', 'Village', 0, {'Village': 0}, False),
    ('Defiled Shrine', 'Village', 0, {'Village': 1}, True),
    ('Labyrinth', 'Gold', 12, {}, False),
])
def test_landmark_menu_only_offers_applicable_gain_instructions(name, gain, pool, pile_vp, expected):
    state, player, seen = setup(observe=True)
    landmark = get_landmark(name)
    landmark.vp_pool, landmark.pile_vp = pool, pile_vp
    state.landmarks = [landmark]
    state.gain_from_supply(player, gain)
    assert any('landmark' in choices for _, choices in seen) == expected


def test_aqueduct_gain_instruction_becomes_eligible_after_nested_refill():
    state, player, _ = setup(order=['card_on_gain', 'landmark'])
    landmark = get_landmark('Aqueduct')
    landmark.setup(state)
    state.landmarks = [landmark]
    outer = get_card('Province')
    outer.on_gain = lambda s, p: s.gain_from_supply(p, 'Gold')
    state.gain_card(player, outer)
    assert player.vp_tokens == 1
    assert landmark.vp_pool == 0
    assert landmark.pile_vp['Gold'] == 7


@pytest.mark.parametrize('name,expected', [('Gold', True), ('Province', False), ('Alchemist', False), ('Engineer', False)])
def test_duplicate_menu_qualifies_all_cost_components(name, expected):
    state, player, seen = setup(observe=True)
    player.tavern_mat = [get_card('Duplicate')]
    player.ai.should_call_from_tavern = lambda *args: False
    state.gain_card(player, get_card(name))
    assert any('tavern' in choices for _, choices in seen) == expected


def test_duplicate_keeps_discounted_gain_time_cost_after_discount_disappears():
    state, player, _ = setup(order=['card_on_gain', 'tavern'])
    dup = get_card('Duplicate')
    player.tavern_mat = [dup]
    player.ai.should_call_from_tavern = lambda *args: True
    highway = get_card('Highway')
    player.in_play = [highway, get_card('Highway')]
    for card in player.in_play:
        card.play_effect(state)
    province = get_card('Province')
    def remove_discount(s, p):
        p.in_play.clear()
        p.highway_count = 0
    province.on_gain = remove_discount
    state.gain_card(player, province)
    assert dup in player.in_play and dup not in player.tavern_mat
    assert player.count('Province') == 2


@pytest.mark.parametrize('name', ['Gold', 'Horse', 'Patrician'])
def test_duplicate_can_be_called_even_without_a_matching_supply_copy(name):
    state, player, _ = setup(order=['tavern', 'card_on_gain'])
    dup = get_card('Duplicate')
    player.tavern_mat = [dup]
    player.ai.should_call_from_tavern = lambda *args: True
    state.supply[name] = 0
    gained = get_card(name)
    state.gain_card(player, gained, from_supply=False)
    assert dup in player.in_play and dup not in player.tavern_mat
    assert player.count(name) == 1
    state.handle_cleanup_phase()
    assert dup in player.discard and dup not in player.in_play
    assert player.count('Duplicate') == 1


def test_duplicate_called_on_empty_emporium_enables_its_fifth_action_bonus():
    state, player, _ = setup(order=['tavern', 'card_on_gain'])
    dup = get_card('Duplicate')
    player.tavern_mat = [dup]
    player.in_play = [get_card('Village') for _ in range(4)]
    player.ai.should_call_from_tavern = lambda *args: True
    state.supply['Emporium'] = 0
    state.gain_card(player, get_card('Emporium'), from_supply=False)
    assert dup in player.in_play
    assert player.vp_tokens == 2
    assert player.count('Emporium') == 1


def test_duplicate_cannot_be_enabled_by_a_later_price_reduction():
    state, player, seen = setup(order=['card_on_gain', 'tavern'])
    dup = get_card('Duplicate')
    player.tavern_mat = [dup]
    player.ai.should_call_from_tavern = lambda *args: True
    province = get_card('Province')
    def add_discount(s, p):
        for _ in range(2):
            highway = get_card('Highway')
            p.in_play.append(highway)
            highway.play_effect(s)
    province.on_gain = add_discount
    state.gain_card(player, province)
    assert dup in player.tavern_mat
    assert not any('tavern' in choices for _, choices in seen)


def test_duplicate_call_does_not_take_an_exposed_different_split_pile_card():
    state, player, _ = setup(order=['tavern'])
    dup = get_card('Duplicate')
    player.tavern_mat = [dup]
    player.ai.should_call_from_tavern = lambda *args: True
    state.supply['Patrician'] = 0
    state.supply['Emporium'] = 5
    state.gain_card(player, get_card('Patrician'), from_supply=False)
    assert dup in player.in_play
    assert state.supply['Emporium'] == 5
    assert player.count('Emporium') == 0


@pytest.mark.parametrize('copies', [1, 2])
def test_off_turn_duplicate_is_discarded_at_active_players_cleanup(copies):
    state, active, _ = setup()
    owner = PlayerState(GeneticAI(EnhancedStrategy()))
    state.players.append(owner)
    duplicate, duration, hand = get_card('Duplicate'), get_card('Hireling'), get_card('Estate')
    owner.tavern_mat = [duplicate]
    owner.hand = [hand]
    owner.in_play = [duration]
    owner.duration = [duration]
    owner.ai.should_call_from_tavern = lambda *args: True
    state.supply['Gold'] = copies
    state.gain_from_supply(owner, 'Gold')
    assert state.turn_player is active
    assert duplicate in owner.in_play and duplicate not in owner.discard
    assert owner.count('Gold') == copies
    state.handle_cleanup_phase()
    assert duplicate not in owner.in_play and owner.discard.count(duplicate) == 1
    assert owner.hand == [hand]
    assert duration in owner.in_play and owner.duration == [duration]
    assert not state._off_turn_called_duplicates


@pytest.mark.parametrize('token', [False, True])
def test_trade_route_menu_requires_a_token_on_the_gained_pile(token):
    state, player, seen = setup(observe=True)
    state.trade_route_tokens_on_piles = {'Gold': token}
    state.gain_from_supply(player, 'Gold')
    assert any('trade_route' in choices for _, choices in seen) == token
    assert state.trade_route_mat_tokens == int(token)


def test_trade_route_pending_instruction_refreshes_after_nested_gain_takes_token():
    state, player, _ = setup(order=['card_on_gain'])
    state.trade_route_tokens_on_piles = {'Gold': True}
    outer = get_card('Gold')
    outer.on_gain = lambda s, p: s.gain_from_supply(p, 'Gold')
    state.gain_card(player, outer)
    assert state.trade_route_mat_tokens == 1
    assert not state.trade_route_tokens_on_piles['Gold']


@pytest.mark.parametrize('source,gain,position,affected,expected', [
    ('Road Network', 'Gold', 1, True, False),
    ('Road Network', 'Province', 1, True, True),
    ('Monkey', 'Gold', 1, True, True),
    ('Monkey', 'Gold', 2, True, False),
    ('Blockade', 'Gold', 1, True, True),
    ('Blockade', 'Silver', 1, True, False),
    ('Blockade', 'Gold', 1, False, False),
])
def test_opponent_gain_menu_qualifies_project_and_duration_sources(source, gain, position, affected, expected):
    from dominion.projects.road_network import RoadNetwork
    state, gainer, _ = setup()
    others = [PlayerState(GeneticAI(EnhancedStrategy())) for _ in range(2)]
    state.players += others
    owner = state.players[position]
    card = RoadNetwork() if source == 'Road Network' else get_card(source)
    if source == 'Road Network':
        owner.projects = [card]
    else:
        owner.duration = [card]
    if source == 'Blockade':
        card.watched_card_name = 'Gold'
        card._affected_player_ids = {id(gainer)} if affected else set()
    owner.projects += [type('Observer', (), {'name': 'Observer', 'on_opponent_gain': lambda *args: None})() for _ in range(2)]
    menus = []
    def choose(s, p, gained, choices):
        menus.append([getattr(e.source, 'name', '') for e in choices])
        return choices[0]
    owner.ai.strategy.choose_gain_effect = choose
    state.gain_from_supply(gainer, gain)
    assert any(source in menu for menu in menus) == expected


@pytest.mark.parametrize('ally,cost', [('Band of Nomads', 1), ("Architects' Guild", 2), ("Trappers' Lodge", 1), ('City-state', 2)])
@pytest.mark.parametrize('payable', [False, True])
def test_ally_gain_menu_checks_actual_payable_favor_cost(ally, cost, payable):
    from dominion.allies.registry import get_ally
    state, player, seen = setup(observe=True)
    state.allies = [get_ally(ally)]
    player.favors = cost if payable else cost - 1
    player.ai.choose_allies_option = lambda s,p,reason,options,default: False
    state.gain_from_supply(player, 'Village')
    assert any('ally' in choices for _, choices in seen) == payable


def test_ally_becomes_payable_after_gain_time_guildmaster_favor():
    from dominion.allies.registry import get_ally
    state, player, _ = setup(order=['registered_gain_effect', 'ally'])
    state.allies = [get_ally('Band of Nomads')]
    player.allies_gain_effects = [('guildmaster', get_card('Guildmaster'), [])]
    player.ai.choose_allies_option = lambda s,p,reason,options,default: 'buy' if reason == 'band_of_nomads' else default
    state.gain_from_supply(player, 'Gold')
    assert player.favors == 0
    assert player.buys == 2


def test_nomads_qualification_uses_gain_time_cost_after_nested_discount():
    from dominion.allies.registry import get_ally
    state, player, _ = setup(order=['card_on_gain', 'ally'])
    state.allies = [get_ally('Band of Nomads')]
    player.favors = 1
    player.ai.choose_allies_option = lambda s,p,reason,options,default: 'buy' if reason == 'band_of_nomads' else default
    silver = get_card('Silver')
    def discount(s, p):
        card = get_card('Highway')
        p.in_play.append(card)
        card.play_effect(s)
    silver.on_gain = discount
    state.gain_card(player, silver)
    assert player.favors == 0 and player.buys == 2


def test_trappers_lodge_can_pay_for_a_gain_to_hand_and_preserves_move_tracking():
    from dominion.allies.registry import get_ally
    state, player, _ = setup()
    state.allies = [get_ally("Trappers' Lodge")]
    player.favors = 1
    player.ai.choose_allies_option = lambda *args: True
    gold = state.gain_from_supply(player, 'Gold', destination='hand')
    assert gold in player.deck and gold not in player.hand
    assert player.favors == 0 and state.gain_destination(gold) is None


def test_architects_guild_can_pay_even_if_no_cheaper_card_is_available():
    from dominion.allies.registry import get_ally
    state, player, _ = setup()
    state.supply = {'Copper': 1}
    player.deck = []
    state.allies = [get_ally("Architects' Guild")]
    player.favors = 2
    player.ai.choose_allies_option = lambda *args: True
    state.gain_from_supply(player, 'Copper')
    assert player.favors == 0 and player.count('Copper') == 1


def test_plain_gain_has_no_inherited_card_or_trade_route_menu_entries():
    state, player, seen = setup()
    state.gain_from_supply(player, 'Gold')
    assert seen == []


@pytest.mark.parametrize('name,gain', [('Good Harvest', 'Gold'), ('Growth', 'Province'), ('Bureaucracy', 'Copper')])
def test_prophecy_menu_requires_an_actual_applicable_gain_instruction(name, gain):
    from dominion.prophecies.registry import get_prophecy
    state, player, seen = setup(['Sheepdog'])
    state.prophecy = get_prophecy(name)
    state.prophecy.is_active = True
    state.gain_card(player, get_card(gain))
    assert not any('prophecy' in choices for _, choices in seen)


def test_academy_menu_excludes_non_action_gains():
    from dominion.projects.academy import Academy
    state, player, seen = setup(['Sheepdog'])
    player.projects = [Academy()]
    state.gain_from_supply(player, 'Gold')
    assert not any('project' in choices for _, choices in seen)


@pytest.mark.parametrize('kind,source,gain,expected', [
    ('galleria', 'Galleria', 'Gold', False),
    ('galleria', 'Galleria', 'Village', True),
    ('skirmisher', 'Skirmisher', 'Gold', False),
    ('skirmisher', 'Skirmisher', 'Militia', True),
])
def test_registered_allies_menu_requires_the_gain_trigger(kind, source, gain, expected):
    state, player, seen = setup(observe=True)
    player.allies_gain_effects = [(kind, get_card(source), [])]
    state.gain_card(player, get_card(gain))
    assert any('registered_gain_effect' in choices for _, choices in seen) == expected


@pytest.mark.parametrize('active', [False, True])
def test_garrison_menu_requires_an_active_gain_instruction(active):
    state, player, seen = setup(observe=True)
    garrison = get_card('Garrison')
    player.in_play = [garrison]
    if active:
        garrison.play_effect(state)
    state.gain_from_supply(player, 'Gold')
    assert any('owner_card' in choices for _, choices in seen) == active
    assert garrison.tokens == int(active)
