from dataclasses import dataclass
from dominion.cards.base_card import CardCost

@dataclass
class Project:
    name: str
    cost: CardCost

    def may_be_bought(self, game_state, player) -> bool:
        return True

    def on_buy(self, game_state, player) -> None:
        pass

    def on_turn_start(self, game_state, player) -> None:
        pass

    def on_trash(self, game_state, player, card) -> None:
        pass

    def on_shuffle(self, game_state, player):
        """Fires after a player shuffles their discard into the deck.

        May optionally return a card (or list of cards) removed from the
        discard during the hook; those cards are placed on top of the
        newly-shuffled deck. Return ``None`` for no-op.
        """
        return None

    @property
    def is_project(self) -> bool:
        return True
