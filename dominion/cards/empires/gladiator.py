from ..base_card import Card, CardCost, CardStats, CardType


class Gladiator(Card):
    partner_card_name = "Fortune"

    def __init__(self):
        super().__init__(
            name="Gladiator",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        reveal_target = player.ai.choose_gladiator_reveal_target(game_state, player)
        if not reveal_target:
            return

        if reveal_target not in player.hand:
            if not player.hand:
                return
            reveal_target = max(
                player.hand,
                key=lambda card: (card.cost.coins, card.stats.coins, card.name),
            )

        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"reveals {reveal_target.name}",
                {"card": reveal_target.name},
            )
        )

        if len(game_state.players) <= 1:
            self._award_duel(player, game_state)
            return

        opponent_index = (game_state.current_player_index + 1) % len(game_state.players)
        opponent = game_state.players[opponent_index]

        matching_cards = [card for card in opponent.hand if card.name == reveal_target.name]
        if matching_cards:
            if opponent.ai.should_reveal_matching_gladiator(
                game_state, opponent, reveal_target.name, player
            ):
                game_state.log_callback(
                    (
                        "action",
                        opponent.ai.name,
                        f"reveals {reveal_target.name}",
                        {"card": reveal_target.name},
                    )
                )
                return

        self._award_duel(player, game_state)

    @staticmethod
    def _award_duel(player, game_state):
        player.coins += 1
        if game_state.supply.get("Gladiator", 0) > 0:
            game_state.supply["Gladiator"] -= 1
