from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..base_card import Card, CardCost, CardStats, CardType

if TYPE_CHECKING:
    from dominion.game.player_state import PlayerState


@dataclass(eq=False)
class _BlockadePlay:
    card: Card
    player: PlayerState
    # Player references preserve identity when a GameState is deep-copied.
    affected: tuple[PlayerState, ...]


class Blockade(Card):
    """Gain and store one card per play; watch it until its next-turn return."""

    def __init__(self):
        super().__init__(
            name="Blockade",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )
        self._pending_plays: list[_BlockadePlay] = []

    @property
    def set_aside(self):
        """All real stored cards, exposed to the shared ownership collector."""
        return [play.card for play in self._pending_plays]

    def set_aside_for_owner(self, player):
        return [play.card for play in self._pending_plays if play.player is player]

    @property
    def pending_plays(self):
        return tuple(self._pending_plays)

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        affected = []
        for other in game_state.opponents_in_order(player):
            game_state.attack_player(other, affected.append)

        choice = player.ai.choose_card_to_gain_with_blockade(game_state, player, max_cost=4)
        if choice is None or game_state.supply.get(choice.name, 0) <= 0:
            return

        game_state.supply[choice.name] -= 1
        actual_gain = []
        game_state.gain_card(
            player, get_card(choice.name), gain_observer=actual_gain.append,
            to_zone=player.pending_gain_set_aside,
        )
        if not actual_gain:
            return
        gained = actual_gain[0]
        if not game_state._remove_gained_card_from_zones(player, gained):
            return
        self._pending_plays.append(_BlockadePlay(gained, player, tuple(affected)))
        # Each entry is a one-shot return instruction, not a recurring Duration.
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        play = next((p for p in self._pending_plays if p.player is player), None)
        if play is not None:
            self._pending_plays.remove(play)
            player.hand.append(play.card)

    def watch_applies(self, play, game_state, owner, gainer, gained_card):
        return (
            play in self._pending_plays
            and play.player is owner
            and self in owner.duration
            and not getattr(play.card, "returned_to_supply", False)
            and play.card.name == gained_card.name
            and gainer is game_state.turn_player
            and any(gainer is opponent for opponent in play.affected)
        )

    def resolve_watch(self, play, game_state, owner, gainer, gained_card):
        if self.watch_applies(play, game_state, owner, gainer, gained_card):
            game_state.give_curse_to_player(gainer)

    def on_opponent_gain(self, game_state, owner, gainer, gained_card):
        """Compatibility entry point: resolve each active play once."""
        for play in self.pending_plays:
            self.resolve_watch(play, game_state, owner, gainer, gained_card)
