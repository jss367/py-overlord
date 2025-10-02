from __future__ import annotations

from typing import List

from ..base_card import Card, CardCost, CardStats, CardType

class BlackMarket(Card):
    """Provides +$2 and access to the Black Market deck."""

    def __init__(self):
        super().__init__(
            name="Black Market",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not getattr(game_state, "black_market_deck", None):
            return

        reveal_count = min(3, len(game_state.black_market_deck))
        revealed_names: List[str] = [
            game_state.black_market_deck.pop(0) for _ in range(reveal_count)
        ]
        from ..registry import get_card

        revealed_cards = [get_card(name) for name in revealed_names]

        choice = player.ai.choose_black_market_purchase(
            game_state, player, revealed_cards
        )
        purchased_name: str | None = None

        if choice and choice.name in revealed_names:
            if self._can_afford(game_state, player, choice):
                purchased_name = choice.name
                self._complete_purchase(game_state, player, choice)
            else:
                choice = None

        remaining = [name for name in revealed_names if name != purchased_name]
        if remaining:
            ordered = player.ai.order_cards_for_black_market_bottom(
                game_state, player, [get_card(name) for name in remaining]
            )
            ordered_names = [card.name for card in ordered if card.name in remaining]
            unused = [name for name in remaining if name not in ordered_names]
            game_state.black_market_deck.extend(ordered_names + unused)

        if choice:
            game_state.log_callback(
                (
                    "action",
                    player.ai.name,
                    f"buys {choice.name} from the Black Market",
                    {},
                )
            )

    def _can_afford(self, game_state, player, card: Card) -> bool:
        cost = game_state.get_card_cost(player, card)
        available = player.coins + player.coin_tokens
        if cost > available:
            return False
        if card.cost.potions > player.potions:
            return False
        return True

    def _complete_purchase(self, game_state, player, card: Card) -> None:
        cost = game_state.get_card_cost(player, card)
        coins_spent = min(player.coins, cost)
        tokens_spent = max(0, cost - coins_spent)

        player.coins -= coins_spent
        player.coin_tokens -= tokens_spent
        player.potions -= card.cost.potions

        if player.buys > 0:
            player.buys -= 1

        from ..registry import get_card

        card.on_buy(game_state)
        gained = game_state.gain_card(player, get_card(card.name))

        game_state._handle_on_buy_in_play_effects(player, card, gained)
        if player.goons_played:
            player.vp_tokens += player.goons_played
        if getattr(player, "merchant_guilds_played", 0):
            player.coin_tokens += player.merchant_guilds_played
        game_state._trigger_haggler_bonus(player, card)
