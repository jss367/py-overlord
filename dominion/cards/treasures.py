from .base_card import Card, CardCost, CardStats, CardType


class Copper(Card):
    def __init__(self):
        super().__init__(
            name="Copper",
            cost=CardCost(coins=0),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def starting_supply(self, game_state) -> int:
        return 60

    def play_effect(self, game_state):
        # Coppersmith (Intrigue 1E): each Copper played this turn produces
        # an extra +$1 for each Coppersmith already played this turn.
        player = game_state.current_player
        bonus = getattr(player, "coppersmiths_played", 0)
        if bonus:
            player.coins += bonus


class Silver(Card):
    def __init__(self):
        super().__init__(
            name="Silver",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.TREASURE],
        )

    def starting_supply(self, game_state) -> int:
        return 40

    def play_effect(self, game_state):
        """Apply Merchant's "first Silver this turn = +$1" bonus."""

        player = game_state.current_player
        already_played_silver = getattr(
            player, "merchant_silver_bonus_used", False
        )
        bonus = getattr(player, "merchant_silver_bonus", 0)
        if bonus and not already_played_silver:
            player.coins += bonus
            game_state.log_callback(
                (
                    "action",
                    player.ai.name,
                    f"gains +${bonus} from Merchant on first Silver",
                    {"bonus": bonus},
                )
            )
        # Mark that a Silver has been played this turn even if no Merchant
        # bonus was active. Otherwise a Silver played before any Merchant
        # would let a later Silver (after Merchant) incorrectly claim the
        # "first Silver this turn" bonus.
        player.merchant_silver_bonus_used = True


class Gold(Card):
    def __init__(self):
        super().__init__(
            name="Gold",
            cost=CardCost(coins=6),
            stats=CardStats(coins=3),
            types=[CardType.TREASURE],
        )

    def starting_supply(self, game_state) -> int:
        return 30
