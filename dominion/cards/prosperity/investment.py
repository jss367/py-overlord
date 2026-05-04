from ..base_card import Card, CardCost, CardStats, CardType


class Investment(Card):
    """Treasure ($4): Trash this. Choose one: +$1; or trash a Treasure from
    your hand and reveal your hand for +1 VP per differently-named Treasure
    revealed.
    """

    def __init__(self):
        super().__init__(
            name="Investment",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Self-trash from in-play.
        if self in player.in_play:
            player.in_play.remove(self)
            game_state.trash_card(player, self)

        treasures_in_hand = [card for card in player.hand if card.is_treasure]
        can_trash_treasure = bool(treasures_in_hand)

        mode = player.ai.choose_investment_mode(
            game_state, player, can_trash_treasure
        )
        if mode == "trash" and not can_trash_treasure:
            mode = "coin"

        if mode == "coin":
            player.coins += 1
            return

        # mode == "trash"
        choice = player.ai.choose_treasure_to_trash_for_investment(
            game_state, player, list(treasures_in_hand)
        )
        if choice is None or choice not in player.hand or not choice.is_treasure:
            # Fall back to coin if AI declined despite committing to trash.
            player.coins += 1
            return

        player.hand.remove(choice)
        game_state.trash_card(player, choice)

        # Reveal hand and count distinct treasure names (after trashing).
        distinct_treasure_names = {
            card.name for card in player.hand if card.is_treasure
        }
        player.vp_tokens += len(distinct_treasure_names)
