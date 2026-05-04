from ..base_card import Card, CardCost, CardStats, CardType


class CrystalBall(Card):
    """Treasure ($5): $1. When you play this, look at the top card of your
    deck. You may trash it, discard it, or, if it's an Action or Treasure,
    play it.
    """

    def __init__(self):
        super().__init__(
            name="Crystal Ball",
            cost=CardCost(coins=5),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Reveal top of deck (shuffle if needed).
        if not player.deck:
            if player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                return

        top_card = player.deck[-1]

        choice = player.ai.choose_crystal_ball_action(game_state, player, top_card)

        if choice == "trash":
            player.deck.pop()
            game_state.trash_card(player, top_card)
            return

        if choice == "discard":
            player.deck.pop()
            game_state.discard_card(player, top_card)
            return

        if choice == "play" and (top_card.is_action or top_card.is_treasure):
            player.deck.pop()
            player.in_play.append(top_card)
            top_card.on_play(game_state)
            game_state.fire_ally_play_hooks(player, top_card)
            return

        # 'leave' (default) — do nothing; card stays on top of the deck.
