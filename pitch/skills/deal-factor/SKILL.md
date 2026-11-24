---
name: deal-factor
description: Research the factors that decide whether we win a deal and return sourced findings plus sharp client questions. Use for deal factors, competitive landscape, buying committee, stakeholder mapping, decision criteria, budget signal, forcing events, why-us, win/loss risks, or when a research ticket in a pitch map asks for any of these. Research only; it does not plan the solution or write proposals.
---

Research the deal-winning factors for one client and return sourced findings. Shared rules:
`../../references/rules.md`.

## Factors

- Buying committee, by role.
- Decision criteria, formal or informal.
- Alternatives and competitors, including do-nothing, build in-house and buy off the shelf.
- Budget signal: signalled, unclear or constrained. No amounts.
- Timeline and forcing events.
- Why us: our strengths and weaknesses against their criteria.
- Risks to the win.

## Behavior

- Start from the discovery MoM, the pack's lessons (`gp pack show lessons`) and offerings (`gp pack show
  offerings`) before searching. A missing key means none. Strengths come from approved offerings, weaknesses from
  their `Does not do` lines; a file with no `Approved by:` line counts as absent, and the strengths then read
  "unknown, a human provides".
- Use web search for public information on the client's company and industry, competitors' public capabilities
  and the regulatory context. Prefer primary sources.
- Research **roles, never named private individuals**.
- Tag every finding `from MoM`, `public: <source>`, `inferred` or `human-provided`.
- Treat vendor marketing as a claim, not a fact.
- Never fabricate competitors, criteria or stakeholders. An unknown is a valid finding: write "Unknown" and say
  what would resolve it.
- Flag anything commitment-like for a human.
- If called from a `research` ticket, cover only the factors that ticket asks for, return the findings for the
  ticket's Answer, and do not edit the map.

## Output: `pitch/deal-factors.md`

1. A short summary.
2. One Known / Unknown block per factor, each finding tagged.
3. Questions for the client (two to five per factor at most, plain language, each with why we ask), for a human to
   send.
4. Ranked risks to the win.
5. Suggested tickets for the pitch map.

Deal factors never enter the canonical: they are not requirements.
