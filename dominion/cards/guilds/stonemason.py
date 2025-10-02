from ..base_card import Card, CardCost, CardStats, CardType


class Stonemason(Card):
    """Trashes a card to gain up to two cheaper cards."""

    def __init__(self):
        super().__init__(
            name="Stonemason",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return

        trash_choice = player.ai.choose_card_to_trash(game_state, list(player.hand) + [None])
        if trash_choice is None or trash_choice not in player.hand:
            return

        player.hand.remove(trash_choice)
        game_state.trash_card(player, trash_choice)
        trashed_cost = trash_choice.cost.coins

        candidates: list[Card] = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins < trashed_cost:
                candidates.append(card)

        if not candidates:
            return

        candidates.sort(key=lambda c: (c.cost.coins, c.stats.vp, c.name), reverse=True)
        gained = 0
        for card in candidates:
            if gained >= 2:
                break
            if game_state.supply.get(card.name, 0) <= 0:
                continue
            game_state.supply[card.name] -= 1
            game_state.gain_card(player, card)
            gained += 1
