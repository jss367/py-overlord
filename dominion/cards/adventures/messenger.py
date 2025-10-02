from ..base_card import Card, CardCost, CardStats, CardType


class Messenger(Card):
    """Implements the Adventures card Messenger."""

    def __init__(self):
        super().__init__(
            name="Messenger",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        """Allow the current player to discard their deck."""

        player = game_state.current_player

        if not player.deck:
            return

        if player.ai.should_discard_deck_with_messenger(game_state, player):
            player.discard.extend(player.deck)
            player.deck.clear()

    def on_gain(self, game_state, player):
        """Distribute a chosen card when Messenger is first gained in the buy phase."""

        super().on_gain(game_state, player)

        if (
            player is not game_state.current_player
            or game_state.phase != "buy"
            or getattr(player, "cards_gained_this_buy_phase", 0) != 0
        ):
            return

        from ..registry import get_card  # Local import to avoid circular dependency

        gain_options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins <= 4:
                gain_options.append(card)

        if not gain_options:
            return

        choice = player.ai.choose_buy(game_state, gain_options)
        if (
            choice is None
            or choice.name not in game_state.supply
            or game_state.supply[choice.name] <= 0
            or choice.cost.coins > 4
        ):
            choice = gain_options[0]

        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, choice)

        choice_name = choice.name
        for other in game_state.players:
            if other is player:
                continue
            if game_state.supply.get(choice_name, 0) <= 0:
                break
            game_state.supply[choice_name] -= 1
            game_state.gain_card(other, get_card(choice_name))
