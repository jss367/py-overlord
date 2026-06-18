# Lisbon Board Strategy Search

Board: `boards/lisbon.txt`

Kingdom:

- Watchtower
- Clerk
- Gardens
- Investment
- Workers' Village
- City
- Collection
- Festival
- Expand
- Peddler
- Colony
- Platinum

## Recommendation

The best strategy found for this board is published as `Lisbon Best Found`,
defined in `generated_strategies/lisbon_best_found.py`.

That strategy intentionally mirrors the existing `Lisbon City Crusher` gain
policy from `generated_strategies/lisbon_city_crusher.py`. The published file
omits Crusher's dead Watchtower action rule because this strategy does not buy
Watchtower; in normal games, that rule is not part of the plan.

This is not a formal proof of optimal play. It is the best strategy found by
the current simulator, existing strategy library, and focused local search.

## Why This Strategy Wins

`Lisbon Best Found` leans into the board's fastest shared pressure point:
emptying City, then forcing Clerk depletion while pivoting into points. The
gain order is:

1. City
2. Colony
3. Clerk
4. Province
5. Duchy
6. Gardens
7. Peddler
8. Silver

The important idea is that City is not just an engine piece here. It is also a
pile-pressure tool. Once City and Clerk are low or empty, the game can end
before slower payload engines convert their extra components into enough Colony
points.

## Validation

The search compared the known Lisbon strategies, then tested focused variants
around the two strongest families:

- City/Clerk pile pressure, represented by `Lisbon City Crusher`
- Clerk/Collection/Colony engine, represented by `ClerkCollectionColony`

The higher-confidence confirmation tournament used 1,000 games per matchup
with alternating first player. Top-table result:

| Strategy | Average win rate |
|---|---:|
| Lisbon City Crusher | 67.0% |
| ClerkCollectionColony | 66.2% |
| Lisbon City Engine | 52.3% |
| City Pile Engine | 47.9% |
| BigMoney | 2.2% |

Key head-to-heads from that run:

| Matchup | Result |
|---|---:|
| Lisbon City Crusher vs ClerkCollectionColony | 48.4% |
| Lisbon City Crusher vs Lisbon City Engine | 64.7% |
| Lisbon City Crusher vs City Pile Engine | 71.0% |
| Lisbon City Crusher vs BigMoney | 98.7% |

`ClerkCollectionColony` is slightly favored in the direct matchup, but
`Lisbon City Crusher` has the better average result across the top table.
That makes Crusher the most robust recommendation found in this search.

## Failed Finalist

A finalist variant that kept the same gain order but changed action ordering
looked promising in a smaller local round-robin. It did not survive the
1,000-game confirmation run:

| Strategy | Average win rate |
|---|---:|
| Lisbon City Crusher | 67.0% |
| ClerkCollectionColony | 66.2% |
| Peddler-before-Clerk variant | 64.4% |

The variant was discarded rather than added as a generated strategy.
