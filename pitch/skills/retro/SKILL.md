---
name: retro
description: Learn from a finished deal by proposing small changes to the pack and the pitch drafts, so the next pitch is better. Invoke deliberately with /pitch:retro after an outcome (won, lost or parked) is written, or when the same mistake has happened twice across deals.
disable-model-invocation: true
---

Runs only when the user asks. Suggest it in one line when an outcome is written to `pitch/OUTCOME.md`, and when
the same mistake has happened twice. Shared rules: `../../references/rules.md`.

Retro writes the **pack** (or, with the bundled generic pack, the project's own `greenfield/lessons.md`), never
the plugin: an installed plugin folder is a cache that an update overwrites, and a second company must not edit
the first one's core. It never edits `offerings.md`: that file is a human's approved record.

1. `gp retro begin` snapshots the pack's size.
2. **Read:** `pitch/OUTCOME.md` and the human's reason for it (loss reasons come only from a human; if none is
   given, ask rather than guess), the map's reopened and `wontfix` tickets, failed proofs, the proposal and deck
   reports, the corrections a human made to drafts, earlier retro notes, and the lessons (`gp pack show lessons`).
3. **Propose**, one at a time, and let the owner choose:
   - a **check** for a mechanical mistake: a pre-flight line for the drafting contract, shown to catch the real
     past mistake (the owner decides whether it is built; you do not edit the plugin);
   - a **lesson** line for a judgement call (for example: "regulated clients: ask about data residency in the
     first client loop");
   - a **pointer** where the agent searched long;
   - **deletions** of text that changes nothing. Deletions pay for additions.
4. **Limits:** each retro leaves the pack no larger; `lessons.md` holds at most 30 lines, and a new lesson at the
   cap merges with or replaces an old one. Lessons are general (industry, deal shape, roles), never a client name,
   a figure or anything confidential, because a lesson crosses into other clients' pitches. Every change is a
   diff the human accepts; write nothing before that.
5. `gp retro finish` refuses if anything grew, a file is over its cap, or a lesson names a specific. Trim and
   finish again.

Output: one short note to the user: what went well or badly and why, the proposed diffs, and whether any lesson
was merged or dropped to stay under the cap.
