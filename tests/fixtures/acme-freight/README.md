# acme-freight: the hidden-rule fixture

A domain with business rules a model cannot know, and one rule stated in a single line of the sources: "Dangerous goods
go through ops." (`greenfield/sources/brief.md`, under Notes). Plan section 12, check 7.

Two parts, reported separately.

**Structural** (`tests/test_freight.py`, runs every time): the mechanical guarantees hold on this project. A suite
cannot cite an example nobody confirmed, an AC cannot be done while an assumption it needs is open, a memory finding
cannot close an assumption, and a regulated data class blocks handover until its item is closed.

**Behavioural** (a live run, three times, rate reported): does the dangerous-goods rule surface BEFORE the build,
through a question or an example the sponsor reviews? A run where it surfaces only after the sponsor's acceptance
session is a failure of the pipeline, not of the simulator. The owner decides the bar.

How to run one:
1. Make an empty project (`gp init`), copy `greenfield/sources/` only (not the canonical, which is the ideal outcome)
   from this folder, and start a session with `/greenfield-pipeline:deliver`.
2. A second session plays the sponsor. Give it only `facts.md` and the instruction at its top: answer what is asked,
   say "not sure" otherwise, volunteer nothing. Relay the agent's questions (each `needs-info` or `ready-for-human`
   item) to it, and its answers back, verbatim.
3. Stop at the first `gp build`, or when the frontier is empty. Then score:
   `python tests/freight_behavior.py <project folder>` prints `surfaced` or `late` with the reason.
4. Repeat three times from a fresh project. Report surfaced/3 and what the agent asked in each.

Not yet run: this part needs live model sessions, which the build of this fixture did not have.
