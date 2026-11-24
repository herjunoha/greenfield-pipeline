---
name: catchup
description: Show the owner what waits on them, the decisions made since the last catch-up and the Attention flags rex raised, in a few lines of pointers. Use for "catch me up", "what is waiting on me", "/greenfield-pipeline:catchup", and after a long afk stretch.
---

# catchup: what waits on the owner

1. Run `gp catchup`. It prints what waits (`ready-for-human` and `needs-info` items), decisions since the last
   catch-up, Attention flags from the evidence READMEs, AC counts by state, any ceiling reached, and the ladder in
   force. Running it moves the since-marker; `--keep` does not.
2. Say it in a few lines, most urgent first: a ceiling reached, then a one-way door waiting, then the rest. Point at
   item ids; do not retell their briefs. Offer to take the items one at a time (each is a full brief).
3. If the owner answers an item: a `ready-for-human` item closes only on their accepted line (`gp accept-line I-n`,
   then `gp close I-n --why "..."`). You never accept for them.
4. The ladder is the owner's. If they say "watch build today", that is `gp level build hitl` for this session
   (logged, ends with the session). A permanent change is their edit of `fence.yaml`. Never infer a level from
   how well the work has gone.
