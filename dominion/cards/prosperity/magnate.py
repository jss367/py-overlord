from ..base_card import Card, CardCost, CardStats, CardType


class Magnate(Card):
    """Action ($5): Reveal your hand. +1 Card per Treasure revealed."""

    def __init__(self):
        super().__init__(
            name="Magnate",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Use the game's Treasure check so Curses count when Charlatan is in
        # the kingdom (Prosperity 2E: Curse becomes Curse-Treasure for the
        # entire game).
        treasures_revealed = sum(
            1 for card in player.hand if game_state.is_treasure(card)
        )
        if treasures_revealed:
            game_state.draw_cards(player, treasures_revealed)
