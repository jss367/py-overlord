from ..base_card import Card, CardCost, CardStats, CardType


class PirateShip(Card):
    """Action-Attack ($4): Choose one:
      (1) Each other player reveals the top 2 cards of their deck, trashes a
          revealed Treasure that you choose, discards the rest, and if anyone
          had a Treasure trashed this way, you take a Coin token.
      (2) +$1 per Coin token on this Pirate Ship mat.

    Note: in this codebase the "mat" is modeled as a per-player counter on the
    PlayerState (`pirate_ship_tokens`) so all of the player's Pirate Ships share
    the same pool, matching the published rule.
    """

    def __init__(self):
        super().__init__(
            name="Pirate Ship",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        tokens = getattr(player, "pirate_ship_tokens", 0)
        mode = player.ai.choose_pirate_ship_mode(game_state, player, tokens)

        if mode == "coins":
            player.coins += tokens
            return

        # Attack mode: each other player reveals 2, you trash one Treasure.
        any_trashed = [False]

        def attack_target(target):
            revealed = []
            for _ in range(2):
                if not target.deck and target.discard:
                    target.shuffle_discard_into_deck()
                if not target.deck:
                    break
                revealed.append(target.deck.pop())

            treasures = [c for c in revealed if c.is_treasure]
            if treasures:
                # Attacker chooses which treasure to trash.
                choice = player.ai.choose_treasure_to_trash_with_pirate_ship(
                    game_state, player, target, treasures
                )
                if choice is None or choice not in treasures:
                    choice = max(treasures, key=lambda c: (c.cost.coins, c.name))
                revealed.remove(choice)
                game_state.trash_card(target, choice)
                any_trashed[0] = True

            for c in revealed:
                game_state.discard_card(target, c)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

        if any_trashed[0]:
            player.pirate_ship_tokens = getattr(player, "pirate_ship_tokens", 0) + 1
