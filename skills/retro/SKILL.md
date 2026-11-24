---
name: retro
description: Look back over a greenfield-pipeline project, propose small durable improvements to the pack and the project, and leave the pack no larger. Use on demand, or when the same mistake happened twice. Never edits the plugin itself.
---

# retro: smaller, not bigger

Retro writes the pack and the project, never the plugin: an installed plugin folder is a cache that an update
overwrites. With the bundled generic pack it works on the project's own `greenfield/lessons.md` and
`greenfield/standards.md`; the fence asks before any write into the plugin.

1. `gp retro begin` snapshots the pack's size. Read `decisions.tsv`, the evidence READMEs' Attention sections and
   the findings rex raised more than once.
2. Propose, one at a time, and let the owner choose:
   - a **mechanical** mistake becomes a `gp check` rule proposal, shown to fail on the real past mistake (the
     owner decides whether it is built; you do not edit the engine);
   - a **judgement** call becomes one line in `standards.md`;
   - a place the agent searched for a long time becomes a pointer;
   - text that changes nothing is **deleted**. Deletions pay for additions.
3. Lessons are general. No project name, glossary term, person, phone number, email or token. They are a few lines
   each; `lessons.md` and `standards.md` are at most 30 lines.
4. `gp retro finish` refuses if anything grew, a file is over its cap, or a lesson names a specific. Trim and
   finish again. A first retro that cannot be made no larger is a retro that proposes nothing.
