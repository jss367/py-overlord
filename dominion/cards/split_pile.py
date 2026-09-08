from .base_card import Card


class SplitPileMixin(Card):
    """Mixin for cards that share a split pile."""

    partner_card_name: str = ""
    bottom: bool = False

    def starting_supply(self, game_state) -> int:
        # Each half of the split pile starts with five or eight copies
        return 5 if len(game_state.players) <= 2 else 8

    def may_be_bought(self, game_state) -> bool:
        if game_state.top_supply_card(self.name) not in (None, self.name):
            return False
        return super().may_be_bought(game_state)


class TopSplitPileCard(SplitPileMixin):
    """Base class for the top card in a split pile."""

    bottom = False


class BottomSplitPileCard(SplitPileMixin):
    """Base class for the bottom card in a split pile."""

    bottom = True
