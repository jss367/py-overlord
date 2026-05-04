"""Implementation of the Bandit attack."""

from ..base_card import Card, CardCost, CardStats, CardType


class Bandit(Card):
    """Action - Attack ($5):

    Gain a Gold. Each other player reveals the top 2 cards of their deck,
    trashes a revealed Treasure other than Copper, and discards the rest.
    """

    def __init__(self):
        super().__init__(
            name="Bandit",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        # Gain a Gold.
        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))

        def attack_target(target):
            revealed = []
            for _ in range(2):
                if not target.deck and target.discard:
                    target.shuffle_discard_into_deck()
                if not target.deck:
                    break
                revealed.append(target.deck.pop())

            if not revealed:
                return

            game_state.log_callback(
                (
                    "action",
                    target.ai.name,
                    f"reveals top of deck for Bandit: {[c.name for c in revealed]}",
                    {"revealed": [c.name for c in revealed]},
                )
            )

            # Identify trashable Treasures (anything except Copper).
            trashable = [
                c for c in revealed if c.is_treasure and c.name != "Copper"
            ]

            if trashable:
                # The attacker chooses which one to trash. Default to highest
                # coin cost (e.g. Gold over Silver).
                if len(trashable) == 1:
                    to_trash = trashable[0]
                else:
                    to_trash = player.ai.choose_treasure_to_trash_with_bandit(
                        game_state, player, target, list(trashable)
                    )
                    if to_trash not in trashable:
                        to_trash = max(
                            trashable,
                            key=lambda c: (c.cost.coins, c.name),
                        )
                revealed.remove(to_trash)
                game_state.trash_card(target, to_trash)
                game_state.log_callback(
                    (
                        "action",
                        target.ai.name,
                        f"trashes {to_trash} due to Bandit",
                        {"trashed": to_trash.name},
                    )
                )

            # Discard everything else.
            for card in revealed:
                game_state.discard_card(target, card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
