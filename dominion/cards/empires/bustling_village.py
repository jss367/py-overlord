from ..base_card import CardCost, CardStats, CardType
from ..split_pile import BottomSplitPileCard


class BustlingVillage(BottomSplitPileCard):
    partner_card_name = "Settlers"

    def __init__(self):
        super().__init__(
            name="Bustling Village",
            cost=CardCost(coins=5),
            stats=CardStats(actions=3, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed: list = []

        for _ in range(3):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        for card in revealed:
            if card.is_action:
                player.hand.append(card)
            else:
                player.discard.append(card)
