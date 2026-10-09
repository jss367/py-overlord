"""Ordered end-of-turn resolution for the game engine.

Keep these stages in order: cleanup triggers may gain cards, discard hooks must
run before the hand leaves play, Donate follows the redraw, and turn-end scoring
must see gain history before it is reset. GameState keeps the public entry point.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dominion.cards.base_card import Card
from dominion.cards.registry import get_card

if TYPE_CHECKING:
    from dominion.game.game_state import GameState
    from dominion.game.player_state import PlayerState


def cleanup_turn(state: GameState) -> None:
    """Resolve cleanup for the active player, then select the next turn."""
    player = state.current_player
    _resolve_cleanup_triggers(state, player)
    tireless_set_aside, journey_extra_turn = _discard_cards(state, player)
    outpost_extra_turn = _draw_next_hand(state, player, tireless_set_aside)
    _finish_turn(state, player, outpost_extra_turn)
    _advance_player(state, player, outpost_extra_turn, journey_extra_turn)


def _resolve_cleanup_triggers(state: GameState, player: PlayerState) -> None:
    """Resolve start-of-cleanup effects and Scheme before discarding."""
    # Log turn summary before resetting state
    state.log_callback(
        (
            "turn_summary",
            player.ai.name,
            player.actions_this_turn,
            list(player.bought_this_turn),
            player.coins_spent_this_turn + player.coins,
        )
    )

    player.actions_this_turn = 0
    player.bought_this_turn = []

    # Rising Sun: Prophecy cleanup-start hook (Biding Time, Sickness)
    if state.prophecy is not None and state.prophecy.is_active:
        state.prophecy.on_cleanup_start(state, player)

    # Rising Sun: Cards in play with cleanup-start triggers (River Shrine)
    # and Renaissance: Improve. These hooks may gain cards which are
    # still part of THIS turn — if the player bought Deliver and had
    # not yet gained, those cleanup-start gains are eligible for the
    # Deliver set-aside trigger.
    for card in list(player.in_play):
        if hasattr(card, "on_cleanup_start"):
            card.on_cleanup_start(state)

    # Plunder Deliver: the "set aside the next gain THIS TURN" trigger
    # only persists until end of turn. Cards already set aside in
    # ``deliver_set_aside`` still return at start of next turn, but
    # any pending-but-unfired count expires here so it cannot leak
    # onto a future turn's gains. Reset AFTER cleanup-start hooks so
    # gains made by River Shrine / Improve during cleanup remain
    # eligible for Deliver.
    player.deliver_pending_count = 0

    # Allies: end-of-turn / cleanup hook.
    # Coastal Haven keeps selected cards through the cleanup redraw.
    for ally in state.allies:
        hook = getattr(ally, "on_cleanup_start", None)
        if hook is not None:
            hook(state, player)

    # Adventures: tavern dispatch at cleanup-start (Wine Merchant).
    state._call_tavern_triggers(player, "cleanup_start")

    # Discard hand and in-play cards
    # Scheme's trigger belongs to the turn it was played. Actions kept in
    # play by Journey (including a Scheme) were not played on the extra
    # turn, so they do not trigger at its Clean-up.
    journey_retained = set(getattr(player, "journey_retained_actions", []))
    scheme_count = sum(
        1
        for card in player.in_play
        if card.name == "Scheme" and card not in journey_retained
    )
    # After buying Journey nothing is discarded from play this Clean-up,
    # so Scheme has no card to put on the deck.
    if scheme_count and not getattr(player, "journey_extra_turn_pending", False):
        # Only Actions that are actually discarded from play this
        # Clean-up qualify: a Duration staying in play is not discarded,
        # and neither is a multiplier (Throne Room, King's Court) that is
        # retained because one of its ``duration_targets`` stays.
        staying = state._cards_retained_in_play(player)
        playable_actions = [
            card for card in player.in_play if card.is_action and card not in staying
        ]
        for _ in range(scheme_count):
            if not playable_actions:
                break
            hook = getattr(player.ai, "choose_card_to_topdeck_for_scheme", None)
            if hook is not None:
                chosen = hook(state, player, list(playable_actions))
            else:
                chosen = max(
                    playable_actions,
                    key=lambda c: (
                        c.cost.coins,
                        c.stats.cards,
                        c.stats.actions,
                        c.name,
                    ),
                )
            if chosen is None or chosen not in playable_actions:
                break
            playable_actions.remove(chosen)
            if chosen in player.in_play:
                player.in_play.remove(chosen)
            player.deck.append(chosen)


def _discard_cards(state: GameState, player: PlayerState) -> tuple[list[Card], bool]:
    """Retain, redirect, or discard cards; return Tireless cards and Journey status."""
    # Duration cards remain in play until their lingering effects finish.
    durations_to_keep = state._cards_retained_in_play(player)

    # Plunder Journey event: "Don't discard your Action cards from play
    # this turn." Keep every Action card from in_play in the same set so
    # they survive cleanup. They will be discarded normally at the end of
    # the granted extra turn.
    journey_extra_turn = bool(getattr(player, "journey_extra_turn_pending", False))
    if journey_extra_turn:
        player.journey_retained_actions = [
            card for card in player.in_play if card.is_action
        ]
        for card in player.journey_retained_actions:
            durations_to_keep.add(card)
    else:
        player.journey_retained_actions = []

    # Determine which Treasures (if any) Trickster will set aside before
    # firing discard-from-play hooks, so we don't trigger those hooks on
    # cards that ultimately won't be discarded this cleanup.
    trickster_selected: list[Card] = []
    trickster_uses = getattr(player, "trickster_uses_remaining", 0)
    if trickster_uses > 0:
        non_duration_in_play = [
            card for card in player.in_play if card not in durations_to_keep
        ]
        treasures_in_play = [card for card in non_duration_in_play if card.is_treasure]
        if treasures_in_play:
            max_set_aside = min(trickster_uses, len(treasures_in_play))
            chosen = player.ai.choose_treasures_to_set_aside_with_trickster(
                state, player, list(treasures_in_play), max_set_aside
            )
            remaining_choices = list(treasures_in_play)
            for card in chosen:
                if card in remaining_choices:
                    remaining_choices.remove(card)
                    trickster_selected.append(card)
            if trickster_selected:
                player.trickster_set_aside.extend(trickster_selected)
                player.trickster_uses_remaining = max(
                    0, player.trickster_uses_remaining - len(trickster_selected)
                )

    from ..cards.allies._rules import decide

    allies_topdecks = {
        card
        for card in player.in_play
        if card.name in {"Merchant Camp", "Tent"}
        and card not in durations_to_keep
        and decide(state, player, "topdeck_from_play", [False, True], True)
    }

    def _will_be_discarded_from_play(card) -> bool:
        """Return True if ``card`` will actually be discarded from play
        during this cleanup (i.e. won't stay as a duration, get topdecked,
        be set aside by Trickster/Tireless, or get returned to the supply
        by Panic). Used to gate ``on_discard_from_play`` hooks so they
        only fire for cards that genuinely get discarded."""
        if card in durations_to_keep:
            return False
        if card in trickster_selected:
            return False
        if getattr(card, "_frog_topdeck", None) == (id(player), player.turns_taken):
            return False
        if card in allies_topdecks:
            return False
        if (
            card.name == "Walled Village"
            and getattr(player, "walled_villages_played", 0) <= 1
        ):
            return False
        if card.name == "Border Guard" and getattr(card, "horn_topdeck_pending", False):
            return False
        if (
            card.is_treasure
            and getattr(player, "panic_active", False)
            and card.name in state.supply
        ):
            return False
        if (
            state.tireless_piles
            and state.supply_pile_key(card.name) in state.tireless_piles
        ):
            return False
        return True

    # Discard-from-play hooks fire before the hand is discarded, only
    # for cards that will actually leave play during this cleanup.
    for card in list(player.in_play):
        if hasattr(card, "on_discard_from_play") and _will_be_discarded_from_play(card):
            card.on_discard_from_play(state, player)

    # Plunder Patient trait: at end of turn, mat cards from Patient pile.
    patient_pile = state.trait_piles.get("Patient")
    if patient_pile:
        patient_cards = [
            c for c in player.hand if state.supply_pile_key(c.name) == patient_pile
        ]
        if patient_cards:
            state.patient_mat.setdefault(id(player), []).extend(patient_cards)
            for card in patient_cards:
                player.hand.remove(card)

    hand_cards = list(player.hand)
    player.hand = []
    state.discard_cards(player, hand_cards, from_cleanup=True)

    # Resolve ordinary discards before cards with deferred gain instructions
    # and their multipliers. Friendly discards can schedule Cargo Ship here.
    # Keep physical cards in play until each actually leaves, so gain hooks and
    # transitive Command retention still see the owner and its multipliers.
    in_play_cards = sorted(
        player.in_play,
        key=lambda card: bool(
            getattr(card, "waiting_for_gain", False)
            or getattr(card, "duration_targets", [])
        ),
    )
    for card in trickster_selected:
        if card in in_play_cards:
            in_play_cards.remove(card)
            player.in_play.remove(card)

    tireless_set_aside: list[Card] = []

    for card in in_play_cards:
        # Hand discards and earlier discard hooks may add pending Durations.
        durations_to_keep.update(state._cards_retained_in_play(player))
        if card in durations_to_keep:
            continue
        if card not in player.in_play:
            continue
        player.in_play.remove(card)
        if getattr(card, "_frog_topdeck", None) == (id(player), player.turns_taken):
            # Menagerie Way of the Frog: topdeck on cleanup. The marker is
            # (owner, turn it was set in), so a stale marker on a card that
            # left play and came back on a later turn -- or under another
            # player whose turn counter happens to match -- does not fire.
            card._frog_topdeck = None
            player.deck.append(card)
        elif card in allies_topdecks:
            # These discard-from-play options also apply after a Way.
            player.deck.append(card)
        elif (
            card.name == "Walled Village"
            and getattr(player, "walled_villages_played", 0) <= 1
        ):
            player.deck.append(card)
        elif card.name == "Border Guard" and getattr(
            card, "horn_topdeck_pending", False
        ):
            # Renaissance Horn: topdeck this Border Guard during cleanup.
            card.horn_topdeck_pending = False
            player.deck.append(card)
        elif (
            card.is_treasure
            and getattr(player, "panic_active", False)
            and card.name in state.supply
        ):
            # Rising Sun Panic: discarded Treasures return to their pile
            # (essentially a one-shot Treasure under Panic).
            state._restore_to_supply_pile(card)
        else:
            if card.name == "Capital":
                player.debt += 6
                context = {
                    "gained_debt": 6,
                    "total_debt": player.debt,
                }
                state.log_callback(
                    ("action", player.ai.name, "gains 6 Debt from Capital", context)
                )
            # Adventures Traveller exchange: when a Traveller is discarded
            # from play, the player may exchange it for the next card in
            # the chain (Page → Treasure Hunter → ... → Champion).
            if (
                getattr(card, "is_traveller", False)
                and getattr(card, "next_traveller", None)
                and player.ai.should_exchange_traveller(state, player, card)
            ):
                next_name = card.next_traveller
                if state.supply.get(next_name, 0) > 0:
                    state.supply[next_name] -= 1
                    replacement = get_card(next_name)
                    # Return the original to its pile (per Traveller rules).
                    state._restore_to_supply_pile(card)
                    # Discard the replacement (Travellers go to discard
                    # like a normal gain after exchange).
                    state.gain_card(player, replacement, from_supply=False)
                    continue
            # Tireless trait: set aside instead of discarding
            if (
                state.tireless_piles
                and state.supply_pile_key(card.name) in state.tireless_piles
            ):
                tireless_set_aside.append(card)
            else:
                state.discard_card(player, card, from_cleanup=True)

    # Prune completed targets only after cleanup gains can schedule them.
    # A reused multiplier must not retain targets from an unrelated later play.
    durations_to_keep = state._cards_retained_in_play(player)
    for card in player.all_cards() + state.trash:
        if hasattr(card, "duration_targets"):
            card.duration_targets = [
                target for target in card.duration_targets if target in durations_to_keep
            ]

    if player.trickster_set_aside:
        player.hand.extend(player.trickster_set_aside)
        player.trickster_set_aside = []
    player.trickster_uses_remaining = 0

    return tireless_set_aside, journey_extra_turn


def _draw_next_hand(
    state: GameState, player: PlayerState, tireless_set_aside: list[Card]
) -> bool:
    """Draw and resolve post-draw effects, including Donate; report an Outpost turn."""
    # Outpost: schedule an extra turn for this player with a 3-card hand.
    outpost_extra_turn = bool(getattr(player, "outpost_pending", False))
    cards_to_draw = 3 if outpost_extra_turn else 5

    # Nocturne — The River's Gift: +1 Card at end of turn (per active copy).
    # Druid's set-aside River's Gift also delivers the cleanup draw.
    rivers_count = sum(
        1 for b in getattr(player, "active_boons", []) if b == "The River's Gift"
    )
    rivers_count += sum(
        1 for b in getattr(player, "druid_active_boons", []) if b == "The River's Gift"
    )
    cards_to_draw += rivers_count
    # Adventures Expedition: +2 cards at end-of-turn redraw.
    cards_to_draw += getattr(player, "expedition_extra_draws", 0)
    player.expedition_extra_draws = 0

    # Cornucopia & Guilds 2E Farrier overpay: +N cards into next hand.
    cards_to_draw += getattr(player, "farrier_pending_draw", 0)
    player.farrier_pending_draw = 0

    # Adventures: -1 Card tokens (Borrow, Relic). Each token removes one
    # card from the next end-of-turn draw and is then removed. Bridge
    # Troll hands out the -$1 token instead and is not a source here.
    minus_tokens = getattr(player, "minus_card_tokens", 0)
    if minus_tokens > 0:
        cards_to_draw = max(0, cards_to_draw - minus_tokens)
        player.minus_card_tokens = 0

    # Draw new hand
    player.draw_cards(cards_to_draw)

    # Rising Sun Foresight: cards set aside earlier go into hand after
    # drawing the next hand.
    if getattr(player, "foresight_set_aside", None):
        player.hand.extend(player.foresight_set_aside)
        player.foresight_set_aside = []

    # Tireless: put set-aside cards on top of deck after drawing
    for card in tireless_set_aside:
        player.deck.append(card)

    # Nocturne — Faithful Hound: set-aside Hounds return to hand at end of turn
    if getattr(player, "hound_set_aside", None):
        player.hand.extend(player.hound_set_aside)
        player.hound_set_aside = []

    # Empires Donate: resolved AFTER cleanup's normal discard-and-draw so
    # the Donate-drawn hand survives into the next turn instead of being
    # immediately discarded. Per the Empires rules, Donate fires "between
    # turns": put hand+deck+discard together, trash any, shuffle the rest
    # into the deck, and draw 5.
    donates = getattr(player, "donate_pending", 0)
    if donates:
        for _ in range(donates):
            state._resolve_donate(player)
        player.donate_pending = 0

    return outpost_extra_turn


def _finish_turn(
    state: GameState, player: PlayerState, outpost_extra_turn: bool
) -> None:
    """Run end-of-turn hooks and expire resources without losing scoring history."""
    for ally in state.allies:
        hook = getattr(ally, "on_turn_end", None)
        if hook is not None:
            hook(state, player)

    # Reset resources for every player, not just the turn player. Off-turn
    # Reaction plays (Sheepdog, Trail, Falconer...) resolve with the reactor
    # as current player, so a Way (Ox, Sheep, Monkey, Mule...) or the card
    # itself can hand them +Actions/+$/+Buys. Those mean nothing off-turn
    # and expire with this turn; only the cards drawn persist. Coffers,
    # Villagers and pending_* fields are banked and deliberately untouched.
    # Seal's "this turn" flag likewise ends with the turn player's turn.
    state._gain_destinations = {}
    for other in state.players:
        other.allies_gain_effects = []
        other.elder_choices = {}
        other.actions = 1
        other.buys = 1
        other.coins = 0
        other.potions = 0
        other.way_of_seal_active = False
        # An off-turn Reaction play bumps the reactor's per-turn count too;
        # in 3+ player games it would otherwise leak into the next turn.
        other.actions_this_turn = 0
        if other is player:
            continue
        # An off-turn Way can gain the reactor cards (Worm's Estate, Rat's
        # Action) and ``gain_card`` records them in turn-scoped history.
        # That is not a gain on *their* turn, so clear it without rotating
        # it into ``*_last_turn`` (Smugglers, Taskmaster); the turn player's
        # own history is rotated below.
        other.gained_cards_this_turn = []
        other.cards_gained_this_turn = 0
        other.cards_gained_this_turn_count = 0
        other.gained_five_this_turn = False
        other.gained_victory_this_turn = False
    # Adventures: clear Mission no-buy flag at end of the bonus turn.
    player.mission_no_buy_turn = False
    # Allies Voyage: clear the extra-turn card-play limit.
    player.voyage_cards_from_hand_remaining = None
    # Adventures Haunted Woods / Swamp Hag: the attack lingers "until
    # your next turn" — i.e. through the victim's whole next turn. We
    # clear at end-of-turn cleanup so it expires AFTER the victim
    # finishes their turn (and before the attacker's following turn).
    player.haunted_woods_attacks = 0
    player.swamp_hag_attacks = 0
    player.ignore_action_bonuses = False
    player.collection_played = 0
    player.goons_played = 0
    player.groundskeeper_bonus = 0
    player.topdeck_gains = False
    player.cannot_buy_actions = False
    player.envious_effect_active = False
    player.cost_reduction = 0
    player.innovation_used = False
    player.citadel_used = False

    # Empires Landmarks: end-of-turn hook (Baths). Fired before
    # cards_gained_this_turn resets so the landmark can inspect it.
    for landmark in state.landmarks:
        landmark.on_turn_end(state, player)

    player.cards_gained_this_turn = 0
    player.cards_gained_this_buy_phase = 0
    player.gained_victory_this_buy_phase = False
    player.flagship_pending = [
        card for card in player.flagship_pending if card in player.duration
    ]
    player.highwayman_blocked_this_turn = False
    player.insignia_active = False
    player.virtual_gain_effects = []
    player.sailor_play_uses = 0
    player.corsair_trashed_this_turn = False
    # Rotate gain history for Smugglers.
    player.gained_cards_last_turn = list(getattr(player, "gained_cards_this_turn", []))
    player.gained_cards_this_turn = []
    # Outpost bookkeeping.
    player.outpost_taken_last_turn = outpost_extra_turn
    player.outpost_pending = False
    # Journey bookkeeping.
    player.journey_extra_turn_pending = False


def _advance_player(
    state: GameState,
    player: PlayerState,
    outpost_extra_turn: bool,
    journey_extra_turn: bool,
) -> None:
    """Honor extra turns and Fleet before advancing the normal turn order."""
    # Move to next player
    if outpost_extra_turn:
        state.extra_turn = True
    if journey_extra_turn:
        state.extra_turn = True

    # Generic "the upcoming turn is an extra turn" flag — set after all
    # extra-turn sources (Outpost, Journey, Seize the Day, Mission, ...)
    # have been settled. Used by Journey for "not a 3rd in a row".
    player.took_extra_turn_last_turn = bool(state.extra_turn)

    if state.fleet_extra_round_active and not state.extra_turn:
        # Fleet extra round: pop the player whose turn just ended and
        # advance to the next Fleet owner in the queue.
        if state.fleet_extra_players and state.fleet_extra_players[0] is player:
            state.fleet_extra_players.pop(0)
        if state.fleet_extra_players:
            next_player = state.fleet_extra_players[0]
            state.current_player_index = state.players.index(next_player)
        state.phase = "start"
        state.extra_turn = False
        return

    if not state.extra_turn:
        state.current_player_index = (state.current_player_index + 1) % len(
            state.players
        )
        if state.current_player_index == 0:
            state.turn_number += 1

    state.extra_turn = False
    state.phase = "start"
