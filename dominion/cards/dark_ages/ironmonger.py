from ..base_card import Card, CardCost, CardStats, CardType


class Ironmonger(Card):
    """Implementation of Ironmonger with simple discard heuristics."""

    def __init__(self):
        super().__init__(
            name="Ironmonger",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Reveal the top card of the deck, shuffling if necessary
        revealed = None
        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if player.deck:
            revealed = player.deck.pop()
        else:
            return

        # Apply conditional bonuses based on the revealed card's type
        if revealed.is_action:
            player.actions += 1
        if revealed.is_treasure:
            player.coins += 1
        if revealed.is_victory or revealed.name == "Curse":
            game_state.draw_cards(player, 1)

        # Basic heuristic: discard obvious junk to cycle, otherwise put it back
        should_discard = False
        if revealed.is_victory or revealed.name == "Curse":
            should_discard = True
        elif revealed.name == "Ruins":
            should_discard = True

        if should_discard:
            player.discard.append(revealed)
        else:
            player.deck.append(revealed)
