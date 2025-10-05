from ..base_card import Card, CardCost, CardStats, CardType


class ChariotRace(Card):
    def __init__(self):
        super().__init__(
            name="Chariot Race",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return
        revealed = player.deck.pop()
        player.hand.append(revealed)

        if len(game_state.players) <= 1:
            return

        opponent_index = (game_state.current_player_index + 1) % len(game_state.players)
        opponent = game_state.players[opponent_index]

        if not opponent.deck and opponent.discard:
            opponent.shuffle_discard_into_deck()

        opponent_cost = (0, 0, 0)
        if opponent.deck:
            opponent_cost = opponent.deck[-1].cost.comparison_tuple()

        if revealed.cost.comparison_tuple() > opponent_cost:
            player.coins += 1
            player.vp_tokens += 1
