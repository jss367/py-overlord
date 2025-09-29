from ..base_card import Card, CardCost, CardStats, CardType


class JackOfAllTrades(Card):
    def __init__(self):
        super().__init__(
            name="Jack of All Trades",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        from ..registry import get_card

        if game_state.supply.get("Silver", 0) > 0:
            game_state.supply["Silver"] -= 1
            gained = game_state.gain_card(player, get_card("Silver"))
            if gained in player.discard:
                player.discard.remove(gained)
                player.hand.append(gained)

        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if player.deck:
            top = player.deck.pop()
            if self._should_discard(top):
                game_state.discard_card(player, top)
            else:
                player.deck.append(top)

        while len(player.hand) < 5:
            drawn = game_state.draw_cards(player, 1)
            if not drawn:
                break

        trash_choice = self._choose_trash_card(player)
        if trash_choice and trash_choice in player.hand:
            player.hand.remove(trash_choice)
            game_state.trash_card(player, trash_choice)

    @staticmethod
    def _should_discard(card) -> bool:
        if card.name == "Curse":
            return True
        if card.is_victory and not card.is_action:
            return True
        return False

    @staticmethod
    def _choose_trash_card(player):
        priorities = ["Curse", "Estate", "Hovel", "Overgrown Estate", "Copper"]
        for name in priorities:
            for card in player.hand:
                if card.name == name:
                    return card
        return None
