---
name: handover
description: Produce the sponsor-facing handover documents of a greenfield-pipeline project, including the limits page, after the work is verified. Use for "write the handover", "prepare the acceptance documents", "generate the UAT pack", or when gp acs shows ACs done and the owner wants something to hand to the sponsor.
---

# handover: documents, drafted and local

Nothing leaves the machine from this part. The owner reviews, signs and sends.

1. `gp acs`: the ACs and what stops each from being done. Handover does not require every AC done, but the limits page
   must say which are not and why.
2. `gp quickstart`: the README quickstart must pass from a fresh clone of the recorded build. If it fails, the README
   is a build item to fix first (ed), not a note.
3. `gp handover` renders the eight generic markdown documents from `gp handover-data` into
   `greenfield/handover/`. It refuses while a regulated-data item is open (the owner names the regime or confirms
   none applies; then `gp accept-line`, `gp close`).
4. Brief **dora-the-doc-author** to improve wording, or to render through the pack's document skills if the pack maps
   them. Facts stay as the data states them.
5. rex reads the limits page against the project: does it say everything that is unproven?
6. Tell the owner what to do next, as one message (`gp notify "<what>" --action "<what to do>"`, one per turn, no
   sponsor data): review the documents, sign the certificate, send. Never send or sign for them. A document number
   is issued by the owner (`gp number acceptance`): it cannot be deleted.

`greenfield-pipeline` never claims compliance. If the sponsor named a regime, the limits page names it and says the pipeline
did not assess it.
