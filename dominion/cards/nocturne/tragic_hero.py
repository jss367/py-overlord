from ..base_card import Card, CardCost, CardStats, CardType


class TragicHero(Card):
    """Nocturne Tragic Hero implementation."""

    def __init__(self):
        super().__init__(
            name="Tragic Hero",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if len(player.hand) < 8:
            return

        if self in player.in_play:
            player.in_play.remove(self)
        game_state.trash_card(player, self)

        from ..registry import get_card

        available: list = []
        for card_name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                candidate = get_card(card_name)
            except ValueError:
                continue
            if candidate.is_treasure:
                available.append(candidate)

        choice = player.ai.choose_tragic_hero_treasure(game_state, player, available)
        if choice is None:
            return

        if game_state.supply.get(choice.name, 0) <= 0:
            return

        game_state.supply[choice.name] -= 1
        gained = game_state.gain_card(player, choice)

        if gained:
            if gained in player.discard:
                player.discard.remove(gained)
            elif gained in player.deck:
                player.deck.remove(gained)
            if gained not in player.hand:
                player.hand.append(gained)
