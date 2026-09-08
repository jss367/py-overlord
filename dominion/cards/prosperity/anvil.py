from ..base_card import Card, CardCost, CardStats, CardType


class Anvil(Card):
    """Treasure ($3): $1.

    You may discard a Treasure from your hand to gain a card costing up to $4.
    """

    def __init__(self):
        super().__init__(
            name="Anvil",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        """Resolve the optional gain when Anvil is played.

        Asks the AI which Treasure (if any) to discard from hand. If a
        Treasure is offered, discard it and gain a card costing up to $4.
        """

        player = game_state.current_player
        treasures = [card for card in player.hand if game_state.is_treasure(card)]
        if not treasures:
            return

        choice = player.ai.choose_anvil_treasure_to_discard(
            game_state, player, list(treasures)
        )
        if (
            choice is None
            or choice not in player.hand
            or not game_state.is_treasure(choice)
        ):
            return

        # Discard the chosen Treasure from hand.
        player.hand.remove(choice)
        game_state.discard_card(player, choice)

        from ..registry import get_card

        gainable = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if (
                game_state.get_card_cost(player, card) <= 4
                and card.cost.potions == 0
                and card.cost.debt == 0
            ):
                gainable.append(card)

        if not gainable:
            return

        target = player.ai.choose_anvil_gain(game_state, player, gainable)
        if target not in gainable:
            # The discard is optional; after discarding, the gain is mandatory.
            target = max(gainable, key=lambda c: (c.cost.coins, c.name))

        if game_state.supply.get(target.name, 0) <= 0:
            return

        game_state.supply[target.name] -= 1
        game_state.gain_card(player, get_card(target.name))
