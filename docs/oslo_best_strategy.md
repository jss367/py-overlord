# Best-Found Strategy for the Discounted Oslo Board

Board: `boards/oslo.txt`

Every card costs $1 less for the entire game. Colony and Platinum are in the
Supply.

## Recommendation

The best strategy found is `Oslo Workers' Village Magnate Multi Colony Engine`,
defined in `generated_strategies/oslo_workers_village_magnate_engine.py`. It
adds two policies to the refined engine below: it preserves a payload for
King's Court, and it does not buy its first Colony until a single turn can
afford four Colonies at once, then greens normally.

## King's Court Target Preservation

During the main Action phase, play King's Court before the last other Action
in hand. Continue to follow the normal Action priority while at least two
non-Court Actions remain. This produces the following choices:

- With King's Court and one other Action, play King's Court and use it on that
  Action.
- With Workers' Village, King's Court, and Magnate, play Workers' Village
  first. If it draws no additional Action, play King's Court and use it on
  Magnate.

Two seat-balanced 1,000-game comparisons against the previous version gave
the target-preserving policy 1,082 wins in 2,000 games (54.1%) and an average
score of 61.35 versus 54.79. No gain, greening, or Treasure rules changed.

## Multi-Colony Greening Gate

The refined engine buys Colony whenever it can pay the discounted $10. The
multi-colony variant replaces that rule with a gate:

- Before any Colony is owned, only buy Colony on a turn whose buy-phase coins
  and buys cover four Colonies at the current cost (4 × $10 = $40 and 4 buys).
- Once the first Colony is bought, the gate stays open and Colonies are bought
  whenever affordable.
- The gate is forced open at turn 20 so the deck cannot build forever.

Every other rule is unchanged from the refined engine.

Instrumented games show the gate is genuinely adaptive rather than a fixed
delay: in 200 diagnostic games it opened before turn 20 in 86% of the games
where it opened at all, at a median of turn 15 with a median of 54 coins — a
turn that immediately dumps four or five Colonies. A control strategy that
simply waits until turn 20 to green (with no coin condition) lost 78% of its
games against the gated variant, so the "wait for a monster turn" condition,
not the delay itself, carries the improvement.

A 1,000-game-per-variant sweep of gate sizes and fallback turns found win
rates against the refined engine rising from 57–58% at a two-Colony gate to
61–62% at four- and five-Colony gates with a turn-20 fallback; the top
configurations were statistically indistinguishable head-to-head, and the
four-Colony turn-20 gate was chosen for its balance of win rate and score
margin. Delaying the Province fallback to match did not help.

Validation: a fresh 3,000-game confirmation against the refined engine
([HTML report](oslo_multi_colony_vs_refined_engine.html)) won 1,786 games
(59.5%) and averaged 56.5 points versus 54.5.

## Previous Recommendation

The previous best strategy was `Oslo Workers' Village Magnate Refined Engine`,
defined in `generated_strategies/oslo_workers_village_magnate_engine.py`.

This strategy evolved from a Workers' Village/Magnate engine proposal. The
search required Workers' Village, Magnate, Anvil, Bank, and King's Court to
remain in every candidate, while it evolved copy limits, build order, scoring
timing, Anvil behavior, and the optional Hoard, Grand Market, Expand, and
Platinum package.

This is not a formal proof of optimal play. It is the strongest policy found
by the current simulator, hand-built archetype search, and genetic evolution.

## Recommended Engine Policy

Use this gain order and the listed copy limits:

1. Acquire two Anvils during the first seven rounds.
2. Buy Colony whenever the Anvil-opening rule does not apply and you can pay
   the discounted $10.
3. Delay Province until only two Colonies remain; then buy Province at $7.
4. Acquire two Banks. Delay King's Court until the deck contains three
   Magnates, then acquire up to three Courts.
5. Acquire up to seven Workers' Villages.
6. Acquire one Hoard, then one Platinum.
7. Acquire up to seven Magnates. Anvil alternates between Workers' Village and
   Magnate, gaining whichever is further below its seven-copy target.
8. Acquire up to two Grand Markets when the no-Copper restriction permits.
9. Buy Duchy with two Provinces left, Estate with one Province left, then
   Silver as fallback economy.

Play Workers' Villages and Grand Markets before King's Court while at least
two possible non-Court payloads remain. Before playing the last other Action,
play King's Court and use it on that Action. Chain King's Courts when possible,
then use the final Court on Magnate. Play Bank after all other Treasures so it
counts the complete Treasure payload.

While an Anvil is in play and either the Village or Magnate target is
unfinished, leave Coppers in hand. Anvil discards those Coppers at cleanup to
gain the missing engine cards. This also creates occasional Grand Market buys,
because no Copper was played that turn.

Begin buying Provinces when only two Colonies remain or at round 18, whichever
happens first. Do not buy Gold directly; use Silver as the fallback purchase.

The refined strategy omitted Expand. It retained one Hoard, two Grand Markets,
and one Platinum from the optional package. The expanded search also rejected
extra Villages or Magnates, a fourth or fifth King's Court, Watchtower, and
Monument.

## Validation

The direct comparison used two-player games with alternating first player.

The committed [HTML comparison report](oslo_refined_engine_vs_previous_best_strategy.html)
provides charts, decision-firing counts, and linked strategy details from a
fresh 3,000-game confirmation against `Oslo Best Found`. The refined engine
won 2,035 games (67.8%) and averaged 70.9 points versus 60.2.

| Comparison | Games | First strategy win rate | Average score | Opponent score | Average turns |
|---|---:|---:|---:|---:|---:|
| Refined engine vs first evolved engine | 4,000 | 54.8% | 55.20 | 51.14 | 19.41 |
| Refined engine vs previous `Oslo Best Found` | 3,000 | 67.8% | 70.90 | 60.20 | — |
| Refined engine vs starting engine | 1,500 | 90.4% | 77.08 | 26.18 | 20.98 |
| First evolved engine vs previous `Oslo Best Found` | 3,000 | 63.2% | 69.77 | 64.27 | 20.71 |
| Starting engine vs previous `Oslo Best Found` | 1,500 | 9.7% | 46.35 | 81.93 | 25.29 |
| First evolved engine vs starting engine | 1,500 | 91.2% | 74.98 | 26.12 | 21.11 |

The refined constrained engine replaced the first evolved engine at that
point; the multi-colony gate above now supersedes it. `Oslo Best Found`
remains useful as a strong, much simpler baseline.

## Previous Baseline Validation

The earlier confirmation used 1,000 games per matchup, alternating first
player. These results explain why `Oslo Best Found` was selected as the
opponent for the constrained evolution.

| Opponent | Win rate | Average score | Opponent score | Average turns |
|---|---:|---:|---:|---:|
| Anvil / Magnate | 73.3% | 76.03 | 57.69 | 23.43 |
| Expand engine | 73.2% | 73.84 | 57.25 | 22.91 |
| King's Court / Monument | 70.2% | 85.75 | 71.56 | 25.81 |
| Hoard money starting strategy | 89.4% | 78.26 | 51.58 | 23.57 |
| Grand Market / Bank | 95.1% | 80.66 | 49.94 | 24.18 |
| King's Court / Magnate | 89.0% | 80.60 | 52.05 | 24.43 |
| Big Money | 87.5% | 47.25 | 28.83 | 16.30 |

The lower scores and shorter games against Big Money reflect earlier pile-out;
the win-rate comparison is the relevant result.
