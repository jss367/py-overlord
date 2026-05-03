"""Sickness Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class Sickness(Prophecy):
    name: str = "Sickness"
    description: str = (
        "While active: at the end of each player's turn (start of cleanup), "
        "they gain a Curse onto their deck OR discard 3 cards."
    )

    def on_cleanup_start(self, game_state, player) -> None:
        from dominion.cards.registry import get_card

        choice = player.ai.choose_sickness_mode(game_state, player)
        if choice == "curse":
            if game_state.supply.get("Curse", 0) > 0:
                game_state.supply["Curse"] -= 1
                # Per rulebook: gain to deck. If pile is empty, the player
                # may still choose to gain a Curse (gain nothing then).
                gained = game_state.gain_card(player, get_card("Curse"), to_deck=True)
                # Ensure on top of deck
                if gained in player.discard:
                    player.discard.remove(gained)
                    player.deck.append(gained)
            return

        # Discard 3 cards from hand (as many as you can if fewer than 3)
        count = min(3, len(player.hand))
        if count <= 0:
            return
        chosen = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), count, reason="sickness"
        )
        chosen = chosen[:count]
        for card in chosen:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
