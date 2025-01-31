from ..base_card import Card, CardCost, CardStats, CardType


class Mine(Card):
    def __init__(self):
        super().__init__(
            name="Mine",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        """Trash a treasure from hand and gain a treasure costing up to 3 coins more."""
        player = game_state.current_player

        # Find treasures in hand
        treasure_cards = [card for card in player.hand if card.is_treasure]

        if not treasure_cards:
            return

        # Let AI choose a treasure to trash
        treasure_to_trash = player.ai.choose_treasure(game_state, treasure_cards)

        if treasure_to_trash:
            # Remove from hand and add to trash
            player.hand.remove(treasure_to_trash)
            game_state.trash.append(treasure_to_trash)

            # Find treasures that can be gained
            possible_gains = [
                card
                for card in game_state.supply.keys()
                if card in ["Copper", "Silver", "Gold"]
                and game_state.supply[card] > 0
                and Card.get_card(card).cost.coins <= treasure_to_trash.cost.coins + 3
            ]

            # Let AI choose what to gain
            if possible_gains:
                chosen_card = player.ai.choose_buy(
                    game_state, [Card.get_card(name) for name in possible_gains]
                )

                if chosen_card:
                    # Gain the chosen treasure
                    game_state.supply[chosen_card.name] -= 1
                    player.discard.append(chosen_card)
                    chosen_card.on_gain(game_state, player)
