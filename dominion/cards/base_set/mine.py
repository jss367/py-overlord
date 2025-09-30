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
        from ..registry import get_card

        # Find treasures in hand
        treasure_cards = [card for card in player.hand if card.is_treasure]

        if not treasure_cards:
            return

        # Let AI choose a treasure to trash
        treasure_to_trash = player.ai.choose_treasure(game_state, treasure_cards)

        if treasure_to_trash:
            # Remove from hand and add to trash
            player.hand.remove(treasure_to_trash)
            game_state.trash_card(player, treasure_to_trash)

            # Find treasures that can be gained
            possible_gains = []
            for name, count in game_state.supply.items():
                if count <= 0:
                    continue
                candidate = get_card(name)
                if not candidate.is_treasure:
                    continue
                if candidate.cost.coins > treasure_to_trash.cost.coins + 3:
                    continue
                possible_gains.append(candidate)

            # Let AI choose what to gain
            if possible_gains:
                chosen_card = player.ai.choose_buy(game_state, possible_gains)

                if chosen_card and game_state.supply.get(chosen_card.name, 0) > 0:
                    # Gain the chosen treasure to hand
                    game_state.supply[chosen_card.name] -= 1
                    gained_card = game_state.gain_card(player, chosen_card)
                    if gained_card:
                        if gained_card in player.discard:
                            player.discard.remove(gained_card)
                        elif gained_card in player.deck:
                            player.deck.remove(gained_card)
                        if gained_card not in player.hand:
                            player.hand.append(gained_card)
