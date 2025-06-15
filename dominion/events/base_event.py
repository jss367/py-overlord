from dataclasses import dataclass
from dominion.cards.base_card import CardCost

@dataclass
class Event:
    name: str
    cost: CardCost

    def may_be_bought(self, game_state, player) -> bool:
        """Return True if the event can currently be bought."""
        return True

    def on_buy(self, game_state, player) -> None:
        """Apply the effect when the event is bought."""
        pass

    @property
    def is_event(self) -> bool:
        return True
