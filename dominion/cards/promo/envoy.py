from ..base_card import Card, CardCost, CardStats, CardType


class Envoy(Card):
    def __init__(self):
        super().__init__(
            name="Envoy",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed = []

        for _ in range(5):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        opponents = [p for p in game_state.players if p is not player]
        chosen = None
        if opponents:
            chooser = opponents[0]
            chosen = chooser.ai.choose_envoy_discard(game_state, chooser, list(revealed))
        if chosen is None or chosen not in revealed:
            chosen = max(revealed, key=lambda card: (card.cost.coins, card.stats.cards, card.stats.actions, card.name))

        revealed.remove(chosen)
        game_state.discard_card(player, chosen)
        player.hand.extend(revealed)
