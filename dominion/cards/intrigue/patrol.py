from ..base_card import Card, CardCost, CardStats, CardType


class Patrol(Card):
    def __init__(self):
        super().__init__(
            name="Patrol",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        revealed: list[Card] = []
        for _ in range(4):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        to_hand: list[Card] = []
        to_topdeck: list[Card] = []
        for card in revealed:
            if card.is_victory or CardType.CURSE in card.types:
                to_hand.append(card)
            else:
                to_topdeck.append(card)

        if to_hand:
            player.hand.extend(to_hand)

        if not to_topdeck:
            return

        ordered = player.ai.order_cards_for_patrol(game_state, player, to_topdeck.copy())

        if ordered is None or len(ordered) != len(to_topdeck) or {
            id(card) for card in ordered
        } != {id(card) for card in to_topdeck}:
            ordered = to_topdeck

        for card in reversed(ordered):
            player.deck.append(card)
