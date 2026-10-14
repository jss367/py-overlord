"""Owner-ordered gain events with bounded, refreshable reaction menus."""

from dataclasses import dataclass
from typing import Any, Callable

from dominion.cards.registry import get_card

GAIN_EFFECT_LIMIT = 256


@dataclass(frozen=True, eq=False)
class GainEffect:
    """A legal simultaneous effect offered to one owner for one gain."""
    kind: str
    source: Any = None

    @property
    def label(self):
        name = getattr(self.source, "name", None)
        return f"{self.kind.replace('_', ' ')} ({name})" if name else self.kind.replace('_', ' ')


@dataclass
class _Trigger:
    effect: GainEffect
    resolve: Callable
    eligible: Callable
    priority: int


class GainEvent:
    """Keep active instructions fixed while discovering current hand reactions."""
    def __init__(self, state, player, card):
        self.state, self.player, self.card = state, player, card
        self.result = card
        self.pending = {id(p): [] for p in state.players}
        self.seen = set()
        self.hand_sources = []  # Keep identities alive for this event.
        self.steps = 0
        self.gain_number = player.cards_gained_this_turn
        self.collection_bonus = player.collection_played
        self.type_count = state.live_type_count(card)

    def add(self, owner, kind, callback, *, source=None, priority=50, eligible=lambda: True, dynamic=False):
        key = (id(owner), kind, id(source))
        if dynamic and key in self.seen:
            return
        if dynamic:
            self.seen.add(key)
            self.hand_sources.append(source)
        self.pending[id(owner)].append(_Trigger(GainEffect(kind, source), callback, eligible, priority))

    def movable(self):
        zone = self.state.gain_destination(self.card)
        return zone is not None and self.card in zone and any(
            zone is z for z in (self.player.hand, self.player.deck, self.player.discard)
        )

    def move(self, target):
        if not self.movable():
            return False
        self.state.gain_destination(self.card).remove(self.card)
        self.state._gain_destinations[self.card] = None
        target.append(self.card)
        return True

    def hand_reactions(self, owner):
        state, player, gained = self.state, self.player, self.card
        for card in list(owner.hand):
            eligible = lambda c=card, p=owner: c in p.hand
            if owner is player and card.name == 'Watchtower':
                self.add(owner, 'watchtower', lambda: state._handle_watchtower_reaction(player, gained),
                         source=card, priority=30, eligible=eligible, dynamic=True)
            elif owner is player and card.name == 'Sleigh':
                def sleigh(c=card):
                    can_move = self.movable()
                    answer = c.react_to_own_gain(state, player, gained)
                    if can_move and answer in ('hand', 'deck'):
                        self.move(player.hand if answer == 'hand' else player.deck)
                self.add(owner, 'sleigh', sleigh, source=card, priority=50, eligible=eligible, dynamic=True)
            elif owner is player and card.name == 'Sheepdog':
                self.add(owner, 'sheepdog', lambda c=card: c.react_to_own_gain(state, player, gained),
                         source=card, priority=51, eligible=eligible, dynamic=True)
            elif card.name == 'Falconer' and self.type_count >= 2:
                self.add(owner, 'falconer', lambda c=card, p=owner: state._play_falconer_reaction(p, player, gained, c),
                         source=card, priority=61, eligible=eligible, dynamic=True)
            elif owner is not player and hasattr(card, 'on_opponent_gain'):
                self.add(owner, 'opponent_reaction', lambda c=card, p=owner: c.on_opponent_gain(state, p, player, gained),
                         source=card, priority=55, eligible=eligible, dynamic=True)
            elif owner is not player and card.name == "Fool's Gold" and gained.name == 'Province':
                def fools_gold(c=card, p=owner):
                    if state.supply.get('Gold', 0) > 0 and state._should_trash_fools_gold(p):
                        p.hand.remove(c)
                        state.trash_card(p, c)
                        state.supply['Gold'] -= 1
                        state.gain_card(p, get_card('Gold'), to_deck=True)
                self.add(owner, 'fools_gold', fools_gold, source=card, priority=45, eligible=eligible, dynamic=True)

    def resolve(self):
        state = self.state
        start = next(i for i, p in enumerate(state.players) if p is state.turn_player)
        for owner in state.players[start:] + state.players[:start]:
            while True:
                self.hand_reactions(owner)
                pending = self.pending[id(owner)]
                offered = sorted((t for t in pending if t.eligible()), key=lambda t: t.priority)
                if not offered:
                    break
                if self.steps >= GAIN_EFFECT_LIMIT:
                    raise RuntimeError('Gain effect limit exceeded')
                old_index, old_turn = state.current_player_index, state.reaction_turn_player_index
                old_number = getattr(state, '_gain_event_number', None)
                old_collection = getattr(state, '_gain_event_collection_bonus', None)
                zone = state.gain_destination(self.card)
                had_card = self.movable()
                try:
                    state.reaction_turn_player_index = next(i for i, p in enumerate(state.players) if p is state.turn_player)
                    state.current_player_index = next(i for i, p in enumerate(state.players) if p is owner)
                    state._gain_event_number = self.gain_number
                    state._gain_event_collection_bonus = self.collection_bonus
                    choices = [t.effect for t in offered]
                    choose = getattr(owner.ai, 'choose_gain_effect', None)
                    pick = choose(state, owner, self.card, list(choices)) if choose and len(choices) > 1 else choices[0]
                    trigger = next((t for t in offered if t.effect is pick or isinstance(pick, str) and t.effect.kind == pick), offered[0])
                    pending.remove(trigger)  # Consume before any nested gain.
                    self.steps += 1
                    trigger.resolve()
                finally:
                    state.current_player_index, state.reaction_turn_player_index = old_index, old_turn
                    state._gain_event_number = old_number
                    state._gain_event_collection_bonus = old_collection
                    if had_card and (self.card not in zone or not any(zone is z for z in (self.player.hand, self.player.deck, self.player.discard))):
                        state._gain_destinations[self.card] = None
        return self.result


def resolve_gain_effects(state, player, gained, *, in_play, cargo_ships, owner_cards,
                         allies_effects, gained_cost, had_exiled_copy):
    """Collect per-owner instructions and resolve them in turn order."""
    event = GainEvent(state, player, gained)
    add = lambda kind, callback, **kwargs: event.add(player, kind, callback, **kwargs)
    original_deck = state.gain_destination(gained) is player.deck

    def topdeck(hook):
        if event.movable() and hook():
            event.move(player.deck)
    for kind, active, decide in (
        ('topdeck_gains', player.topdeck_gains, lambda: True),
        ('way_of_seal', getattr(player, 'way_of_seal_active', False), lambda: player.ai.should_topdeck_with_way_of_seal(state, player, gained)),
        ('insignia', getattr(player, 'insignia_active', False), lambda: player.ai.should_topdeck_with_insignia(state, player, gained)),
        ('tiara', any(c.name == 'Tiara' for c in in_play), lambda: player.ai.should_topdeck_with_tiara(state, player, gained)),
    ):
        if active and not original_deck:
            add(kind, lambda decide=decide: topdeck(decide), priority=0)
    if getattr(player, 'gatekeeper_attacks', 0) > 0:
        add('gatekeeper', lambda: state._handle_gatekeeper_exile(player, gained, original_deck, had_exiled_copy), priority=10)
    if had_exiled_copy:
        def exile():
            if player.ai.should_discard_exiled_copies(state, player, gained):
                matching = [c for c in player.exile if c.name == gained.name]
                player.exile[:] = [c for c in player.exile if c.name != gained.name]
                for card in matching:
                    if card in player.invested_exile:
                        player.invested_exile.remove(card)
                    state.discard_card(player, card)
        add('exile_copies', exile, priority=11)
    add('card_on_gain', lambda: gained.on_gain(state, player), source=gained, priority=20)
    if state.prophecy is not None and state.prophecy.is_active:
        prophecy = state.prophecy
        add('prophecy', lambda: prophecy.on_gain(state, player, gained), source=prophecy, priority=21)
    add('trade_route', lambda: state._handle_trade_route_token(gained), priority=22)
    if any(c.name == 'Royal Seal' for c in in_play):
        add('royal_seal', lambda: state._handle_royal_seal_reaction(player, gained), priority=31, eligible=event.movable)
    for project in list(player.projects):
        if hasattr(project, 'on_gain'):
            if project.name == 'Innovation':
                if state.is_action(gained) and not player.innovation_used:
                    player.innovation_used = True
                    add('innovation', lambda p=project: p.on_gain(state, player, gained, claimed=True), source=project, priority=35)
            else:
                add('project', lambda p=project: p.on_gain(state, player, gained), source=project, priority=35)
    if player.groundskeeper_bonus and gained.is_victory:
        bonus = player.groundskeeper_bonus
        add('groundskeeper', lambda: setattr(player, 'vp_tokens', player.vp_tokens + bonus), priority=40)
    for owner in state.players:
        if owner is player:
            continue
        for card in list(owner.invested_exile):
            if card.name == gained.name:
                event.add(owner, 'invest', lambda p=owner: state.draw_cards(p, 2), source=card, priority=44)
        for project in list(owner.projects):
            if hasattr(project, 'on_opponent_gain'):
                event.add(owner, 'opponent_project', lambda p=owner, c=project: c.on_opponent_gain(state, p, gained), source=project, priority=55)
        for card in list(owner.duration):
            if hasattr(card, 'on_opponent_gain'):
                event.add(owner, 'opponent_duration', lambda p=owner, c=card: c.on_opponent_gain(state, p, player, gained), source=card, priority=55)
    if gained.is_action:
        player.actions_gained_this_turn += 1
        number = player.actions_gained_this_turn
        if number == 3 and not player.cauldron_triggered and any(c.name == 'Cauldron' for c in in_play):
            player.cauldron_triggered = True
            add('cauldron', lambda: state._track_action_gain(player, gained, number=number, sources=in_play, claimed=True), priority=46)
    for cargo in dict.fromkeys(cargo_ships):
        if hasattr(cargo, 'on_cargo_ship_gain') and getattr(cargo, 'waiting_for_gain', False):
            def cargo_gain(c=cargo):
                if c.on_cargo_ship_gain(state, player, gained):
                    state._gain_destinations[gained] = None
                    owner = getattr(c, 'virtual_supply_owner', None)
                    if owner is not None and c not in getattr(owner, 'duration_targets', []):
                        owner.duration_targets = getattr(owner, 'duration_targets', []) + [c]
            add('cargo_ship', cargo_gain, source=cargo, priority=48,
                eligible=lambda c=cargo: c.waiting_for_gain and event.movable())
    if gained_cost.coins >= 4 and gained.name != 'Horse':
        for livery in [c for c in in_play if c.name == 'Livery']:
            add('livery', lambda c=livery: state._handle_livery_gain(player, gained, [c], qualified=True), source=livery, priority=56)
    if state.is_treasure(gained):
        for shrine in dict.fromkeys(c for c in owner_cards if c.name == 'Secluded Shrine' and c.shrine_armed):
            charges, shrine.shrine_charges = shrine.shrine_charges, 0
            add('secluded_shrine', lambda c=shrine, n=charges: c.on_owner_gains_treasure(state, player, charges=n), source=shrine, priority=60)
    for landmark in state.landmarks:
        if landmark.name == 'Mountain Pass' and gained.name == 'Province' and not landmark._fired:
            landmark._fired = True
            add('landmark', lambda c=landmark: c.on_gain(state, player, gained, claimed=True), source=landmark, priority=65)
        elif landmark.name != 'Mountain Pass':
            add('landmark', lambda c=landmark: c.on_gain(state, player, gained), source=landmark, priority=65)
    if player.sailor_play_uses and any(c.name == 'Sailor' for c in owner_cards):
        add('sailor', lambda: state._handle_sailor_gain(player, gained), priority=66, eligible=event.movable)
    if state.pile_trait(gained.name) in {'Cursed', 'Rich', 'Hasty'} or gained.name == 'Province' and state.trait_piles.get('Fawning'):
        add('trait', lambda: state._handle_trait_on_gain(player, gained), priority=70,
            eligible=event.movable if state.pile_trait(gained.name) == 'Hasty' else lambda: True)
    if gained.is_action and state.mirror_pending.get(id(player), 0):
        pending = state.mirror_pending[id(player)]
        state.mirror_pending[id(player)] = 0
        def mirror():
            for _ in range(pending):
                state.gain_from_supply(player, gained.name)
        add('mirror', mirror, priority=71)
    if gained.is_treasure and state.landing_party_pending.get(id(player)):
        pending_landings = list(state.landing_party_pending[id(player)])
        state.landing_party_pending[id(player)] = []
        for landing in pending_landings:
            def land(c=landing):
                # The source and the gain move independently. A virtual or
                # trashed source cannot reappear as a physical owned card.
                legacy_duration_zone = c in player.duration and c not in state.trash and not any(c in z for z in (player.hand,player.deck,player.discard)) and not getattr(c,'returned_to_supply',False)
                if (c in player.in_play or legacy_duration_zone) and not getattr(c, 'virtual_supply_play', False):
                    if c in player.in_play:
                        player.in_play.remove(c)
                    player.deck.append(c)
                if c not in state.landing_party_pending.get(id(player), []):
                    while c in player.duration:
                        player.duration.remove(c)
                    c.duration_persistent = False
                event.move(player.deck)
            add('landing_party', land, source=landing, priority=72)
    if player is state.turn_player and gained.is_treasure and not player.mining_road_triggered and any(c.name == 'Mining Road' for c in in_play):
        player.mining_road_triggered = True
        add('mining_road', lambda: state._handle_mining_road_gain(player, gained, claimed=True), priority=73)
    for card in list(player.tavern_mat):
        if card.name == 'Duplicate':
            add('tavern', lambda c=card: c.on_call_from_tavern(state, player, 'gain', gained), source=card,
                priority=75, eligible=lambda c=card: c in player.tavern_mat)
    if player.travelling_fair_active and state.phase == 'buy' and player is state.turn_player:
        add('travelling_fair', lambda: topdeck(lambda: player.ai.should_topdeck_with_travelling_fair(state, player, gained)), priority=76)
    if player.deliver_pending_count:
        player.deliver_pending_count -= 1
        def deliver():
            event.move(player.deliver_set_aside)
        add('deliver', deliver, priority=77)
    for card in owner_cards:
        if hasattr(card, 'on_owner_gain'):
            add('owner_card', lambda c=card: c.on_owner_gain(state, player, gained), source=card, priority=80)
    for effect in allies_effects:
        add('registered_gain_effect', lambda e=effect: state._resolve_allies_gain_effects(player, gained, [e], gained_cost), source=effect[1], priority=81)
    for ally in list(state.allies):
        if hasattr(ally, 'on_owner_gain'):
            priority = 90
            if ally.name == 'City-state' and ally._gain_zone(state, player, gained) is not None:
                from dominion.cards.allies._rules import decide
                if decide(state, player, 'city_state_before_gain_effects', [False, True], state.pile_trait(gained.name) == 'Hasty'):
                    priority = 5
            add('ally', lambda c=ally: c.on_owner_gain(state, player, gained), source=ally, priority=priority)
    def changeling():
        event.result = state._maybe_exchange_for_changeling(player, gained)
    if state.supply.get('Changeling', 0) and gained_cost.coins >= 3:
        add('changeling', changeling, priority=99,
            eligible=lambda: any(gained in z for z in (player.hand, player.deck, player.discard)))
    return event.resolve()
