"""Death Cart — $4 Action-Looter that trashes an Action for +$5 and gains 2 Ruins on gain."""

from ..base_card import Card, CardCost, CardStats, CardType


class DeathCart(Card):
    """You may trash an Action card from your hand. If you do (or if you
    trashed Death Cart instead), +$5.

    When you gain Death Cart, gain 2 Ruins.
    """

    def __init__(self):
        super().__init__(
            name="Death Cart",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.LOOTER],
        )

    def get_additional_piles(self) -> dict[str, int]:
        # Ensure Ruins pile is set up
        return {"Ruins": 10}

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        # Gain 2 Ruins
        for _ in range(2):
            game_state.gain_ruins(player)

    def play_effect(self, game_state):
        player = game_state.current_player

        actions_in_hand = [c for c in player.hand if c.is_action]
        choice = player.ai.should_trash_action_for_death_cart(
            game_state, player, actions_in_hand
        )
        if choice and choice in player.hand:
            player.hand.remove(choice)
            game_state.trash_card(player, choice)
            player.coins += 5
            return

        # No Action trashed; player may trash Death Cart itself for +$5.
        if self in player.in_play:
            player.in_play.remove(self)
            game_state.trash_card(player, self)
            player.coins += 5
