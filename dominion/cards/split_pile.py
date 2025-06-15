from .base_card import Card


class SplitPileMixin(Card):
    """Mixin for cards that share a split pile."""

    partner_card_name: str = ""
    bottom: bool = False

    def starting_supply(self, game_state) -> int:
        # Each half of the split pile starts with five or eight copies
        return 5 if len(game_state.players) <= 2 else 8

    def may_be_bought(self, game_state) -> bool:
        if self.bottom and game_state.supply.get(self.partner_card_name, 0) > 0:
            return False
        return super().may_be_bought(game_state)
