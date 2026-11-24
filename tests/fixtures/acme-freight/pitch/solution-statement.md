# Solution Statement: acme-freight
Status: DRAFT, needs human review
Pitch date: 2026-12-15

## Outcome
Staff can get a consistent freight price for any ordinary shipment in under a minute by the end of the pilot, measured by quote time and by disagreements between two staff on the same shipment. Baseline: TBD. Target: TBD.

## Problem statement
- P1 Slow quoting: staff quote from a printed tariff by hand (discovery call, 2026-11-10) [stated]
- P2 Inconsistent prices: two staff quote different prices for the same shipment (discovery call, 2026-11-10) [stated]
- P3 Dangerous goods mishandled: a tool must never quote them (discovery call, 2026-11-10) [stated]

## Domain
### Terms
- heavy tier: the tariff band for shipments over 100 kg | source: client-document | confirmed: yes
- remote zone: a delivery zone priced at the zone A price plus a surcharge | source: client | confirmed: yes
### Rules
- R1 Weight tariff: up to 100 kg is 50 per started 10 kg, over 100 kg is 45 per started 10 kg | source: client-document | confirmed: yes
- R2 Round up: a price is rounded up to the next whole number | source: client | confirmed: yes
- R3 Dangerous goods: never quoted, routed to ops | source: client | confirmed: yes
- R4 Fuel levy: unknown | source: memory | confirmed: no

## Worked examples
- EX1 Heavy tier: rule R1 | given: 120 kg to zone A | expect: price 540 | confirmed by client operations lead, 2026-11-10 | serves: E1
- EX2 Round up: rule R2 | given: 10 kg to the remote zone | expect: price 58 | confirmed by client finance lead, 2026-11-10 | serves: E1
- EX3 Dangerous goods: rule R3 | given: 10 kg to zone A, dangerous | expect: refusal naming ops | confirmed by client operations lead, 2026-11-10 | serves: E2

## Solution elements
### E1 Quote calculator
- Solves: P1, P2
- Need: a staff member can read one price from a weight and a zone, the same every time
- Element: a command-line calculator that applies the confirmed tariff and rounding
- Surface: quote-cli (cli) (plates)
- Fit: replaces the rigid off-the-shelf option the client rejected
- Proof requirement: The calculator MUST print the heavy-tier price for 120 kg to zone A | acceptance: the observer sees 540 | (plates)
- Proof evidence: demonstrated (attested by our solution architect, 2026-12-01, demo-notes link)
- Decided in: Which tariff rules apply?

### E2 Dangerous-goods refusal
- Solves: P3
- Need: dangerous goods never receive a quote and reach ops
- Element: the calculator refuses a dangerous shipment and names ops
- Surface: quote-cli (cli) (plates)
- Fit: matches the client's stated rule
- Proof requirement: The calculator MUST refuse a dangerous shipment and name ops | acceptance: the observer sees a refusal that says ops |
- Proof evidence: pending
- Decided in: Which goods go through ops?

## Why us
- Consistent quotes without a rigid tool | criterion: replace the rejected off-the-shelf option | delivered by: E1 | basis: O1 | human (our sales lead, 2026-11-12)

## Assumptions
- A1 Staff-only use: the tool runs on a staff laptop and never stores customer data | owner: our solution architect | validate by: ask the client operations lead, 2026-11-20 | client must confirm: yes

## Data and regulation
Data handled: financial
Regimes named by the client: none. We make no compliance claim.

## Scope boundaries
In: a quote calculator for staff, refusal of dangerous goods
Out: booking, invoicing, carrier selection (not asked for)

## Commitments
(none approved)

## Gaps (internal, never client-facing)
- R4 Fuel levy: a rule resting on memory with no confirmed example; ask the client
- The six-week request is an unapproved commitment candidate

## Traceability index
| Problem | Need | Element | Proof requirement | Proof evidence |
|---|---|---|---|---|
| P1, P2 | one consistent price | E1 Quote calculator | 540 for 120 kg to zone A | demonstrated |
| P3 | dangerous goods reach ops | E2 Dangerous-goods refusal | refusal names ops | pending |
