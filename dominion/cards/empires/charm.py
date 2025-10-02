from ..base_card import Card, CardCost, CardStats, CardType


class Charm(Card):

    """Full implementation of Charm's flexible choices."""

    COIN_OPTION = "coins"
    GAIN_OPTION = "gain"
    COPY_NEXT_BUY_OPTION = "copy_next_buy"

    def __init__(self):
        super().__init__(
            name="Charm",
            cost=CardCost(coins=5),
            stats=CardStats(buys=1),
            types=[CardType.TREASURE],

        )

    def play_effect(self, game_state):
        """Offer Charm's choice of coin, gain, or duplicating the next buy."""

        player = game_state.current_player

        from ..registry import get_card  # Local import to avoid circular dependency

        gainable_cards = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.is_victory or card.cost.coins > 4 or card.cost.potions > 0:
                continue
            gainable_cards.append(card)

        options = [self.COIN_OPTION]
        if gainable_cards:
            options.append(self.GAIN_OPTION)
        options.append(self.COPY_NEXT_BUY_OPTION)

        choice = player.ai.choose_charm_option(game_state, player, options)
        if choice not in options:
            choice = options[0]

        if choice == self.GAIN_OPTION and gainable_cards:
            gain_choice = player.ai.choose_buy(game_state, gainable_cards + [None])
            if gain_choice:
                game_state.supply[gain_choice.name] -= 1
                game_state.gain_card(player, gain_choice)
        elif choice == self.COPY_NEXT_BUY_OPTION:
            player.charm_next_buy_copies = getattr(player, "charm_next_buy_copies", 0) + 1
        else:
            player.coins += 2
