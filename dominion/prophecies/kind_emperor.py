"""Kind Emperor Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class KindEmperor(Prophecy):
    name: str = "Kind Emperor"
    description: str = (
        "While active: at the start of your turn, gain an Action card to "
        "your hand. (The activating player gains one immediately.)"
    )

    def on_activate(self, game_state) -> None:
        # Per rulebook: only the player who removed the last Sun token gains
        # an Action immediately.
        self._gain_action_to_hand(game_state, game_state.current_player)

    def on_turn_start(self, game_state, player) -> None:
        self._gain_action_to_hand(game_state, player)

    def _gain_action_to_hand(self, game_state, player) -> None:
        from dominion.cards.registry import get_card

        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_action:
                continue
            if not card.may_be_bought(game_state):
                continue
            candidates.append(card)
        if not candidates:
            return
        chosen = player.ai.choose_buy(game_state, candidates + [None])
        if chosen is None:
            chosen = max(candidates, key=lambda c: (c.cost.coins, c.name))
        if game_state.supply.get(chosen.name, 0) <= 0:
            return
        game_state.supply[chosen.name] -= 1
        gained = game_state.gain_card(player, chosen)
        # Move the gained card from wherever it landed (typically discard)
        # into hand.
        for zone in (player.discard, player.deck):
            if gained in zone:
                zone.remove(gained)
                player.hand.append(gained)
                return
