from ..base_card import Card, CardCost, CardStats, CardType


class Envoy(Card):
    """Big draw that lets the next player discard one of the drawn cards."""

    def __init__(self):
        super().__init__(
            name="Envoy",
            cost=CardCost(coins=4),
            stats=CardStats(cards=4),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        drawn_cards = []

        for _ in range(5):
            drawn = player.draw_cards(1)
            if not drawn:
                break
            drawn_cards.extend(drawn)

        if not drawn_cards:
            return

        left_index = (game_state.current_player_index + 1) % len(game_state.players)
        chooser = game_state.players[left_index]
        choice = chooser.ai.choose_envoy_discard(
            game_state, chooser, player, list(drawn_cards)
        )

        if choice and choice in player.hand:
            player.hand.remove(choice)
            game_state.discard_card(player, choice)
        else:
            worst = min(
                drawn_cards,
                key=lambda card: (
                    card.cost.coins,
                    card.stats.cards,
                    card.stats.actions,
                    card.name,
                ),
            )
            if worst in player.hand:
                player.hand.remove(worst)
                game_state.discard_card(player, worst)
