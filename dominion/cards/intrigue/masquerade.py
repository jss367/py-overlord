"""Implementation of Masquerade."""

from ..base_card import Card, CardCost, CardStats, CardType


class Masquerade(Card):
    """+2 Cards. Each player passes a card from their hand to the next player
    to their left at once. Then you may trash a card from your hand."""

    def __init__(self):
        super().__init__(
            name="Masquerade",
            cost=CardCost(coins=3),
            stats=CardStats(cards=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Step 1: All players (with non-empty hands) simultaneously pick a
        # card to pass to the player on their left. Cards already passed
        # to a player this turn are NOT eligible to be passed onward
        # (they enter the recipient's hand only after the simultaneous step).
        players = list(game_state.players)
        n = len(players)

        picks: list[Card | None] = [None] * n
        for idx, p in enumerate(players):
            if not p.hand:
                picks[idx] = None
                continue
            chosen = p.ai.choose_card_to_pass_for_masquerade(
                game_state, p, list(p.hand)
            )
            if chosen is None or chosen not in p.hand:
                # Player must pass if able; default to the worst card.
                # The interface returned None despite a non-empty hand;
                # fall back to the cheapest card.
                chosen = min(p.hand, key=lambda c: (c.cost.coins, c.name))
            p.hand.remove(chosen)
            picks[idx] = chosen

        # Step 2: Resolve passes. Players sit clockwise around the table;
        # "the next player to their left" is the next index in turn order.
        for idx, p in enumerate(players):
            card = picks[idx]
            if card is None:
                continue
            recipient = players[(idx + 1) % n]
            recipient.hand.append(card)
            game_state.log_callback(
                (
                    "action",
                    p.ai.name,
                    f"passes {card.name} to {recipient.ai.name} via Masquerade",
                    {},
                )
            )

        # Step 3: The player who played Masquerade may trash a card from
        # their hand.
        if not player.hand:
            return
        trashed = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if trashed is None or trashed not in player.hand:
            return
        player.hand.remove(trashed)
        game_state.trash_card(player, trashed)
