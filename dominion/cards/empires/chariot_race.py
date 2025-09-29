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
        opponent_card_cost = 0
        for opponent in game_state.players:
            if opponent is player:
                continue
            if not opponent.deck and opponent.discard:
                opponent.shuffle_discard_into_deck()
            if opponent.deck:
                opponent_card_cost = max(opponent_card_cost, opponent.deck[-1].cost.coins)
        player.hand.append(revealed)
        if revealed.cost.coins > opponent_card_cost:
            player.coins += 1
            player.vp_tokens += 1
