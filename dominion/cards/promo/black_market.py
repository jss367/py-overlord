from random import sample

from ..base_card import Card, CardCost, CardStats, CardType


class BlackMarket(Card):
    """Simplified Black Market implementation.

    Provides +$2 and lets the player gain a card from a random sampling of
    affordable cards in the Supply without buying it. This approximates the
    unique deck from the physical game while staying compatible with the
    existing engine.
    """

    SAMPLE_SIZE = 3

    def __init__(self):
        super().__init__(
            name="Black Market",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        from ..registry import get_card

        affordable = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and name not in ("Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse")
        ]
        if not affordable:
            return

        sample_size = min(self.SAMPLE_SIZE, len(affordable))
        revealed_names = sample(affordable, sample_size)
        revealed = [get_card(name) for name in revealed_names]

        choice = player.ai.choose_black_market_gain(game_state, player, revealed + [None])
        if not choice or choice.name not in game_state.supply or game_state.supply[choice.name] <= 0:
            return

        game_state.supply[choice.name] -= 1
        gained = get_card(choice.name)
        game_state.gain_card(player, gained)
