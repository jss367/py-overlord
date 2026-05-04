from ..base_card import Card, CardCost, CardStats, CardType


class Anvil(Card):
    """Treasure ($3): $1.

    When you discard this from play, you may discard a Treasure from your
    hand to gain a card costing up to $4.
    """

    def __init__(self):
        super().__init__(
            name="Anvil",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def on_discard_from_play(self, game_state, player):
        """Resolve Anvil's clean-up trigger.

        Asks the AI which Treasure (if any) to discard from hand. If a
        Treasure is offered, discard it and gain a card costing up to $4.
        """

        treasures = [card for card in player.hand if card.is_treasure]
        if not treasures:
            return

        choice = player.ai.choose_anvil_treasure_to_discard(
            game_state, player, list(treasures)
        )
        if choice is None or choice not in player.hand or not choice.is_treasure:
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
            if card.cost.coins <= 4 and card.cost.potions == 0:
                gainable.append(card)

        if not gainable:
            return

        target = player.ai.choose_anvil_gain(game_state, player, gainable)
        if target is None:
            return

        if game_state.supply.get(target.name, 0) <= 0:
            return

        game_state.supply[target.name] -= 1
        game_state.gain_card(player, get_card(target.name))
