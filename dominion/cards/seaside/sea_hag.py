from ..base_card import Card, CardCost, CardStats, CardType


class SeaHag(Card):
    """Action-Attack ($4): Each other player discards the top card of their deck,
    then gains a Curse onto their deck.
    """

    def __init__(self):
        super().__init__(
            name="Sea Hag",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        def attack_target(target):
            # Discard top card of deck (top = end of list).
            if not target.deck and target.discard:
                target.shuffle_discard_into_deck()
            if target.deck:
                top = target.deck.pop()
                game_state.discard_card(target, top)

            # Gain a Curse onto the top of the deck.
            if game_state.supply.get("Curse", 0) > 0:
                game_state.supply["Curse"] -= 1
                gained = game_state.gain_card(target, get_card("Curse"))
                if gained in target.discard:
                    target.discard.remove(gained)
                    target.deck.append(gained)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
