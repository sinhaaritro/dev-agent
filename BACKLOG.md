# Backlog

A permanent, flat list of issues worth capturing but not yet turned into a spec. Root
placement keeps it outside `specs/temp/`, so the task-cleaner can never purge it.

Each entry answers **who / what / when / where / how** — the complete set. Fill all five
(use `—` when one is unknown) so both a human and an agent can understand the issue
without context:

`- [ ] <when: YYYY-MM-DD> | what: <one-liner> | where: <file/area> | who: <raised-by / owner> | how: <approach / repro>`

In review, an issue the human decides not to fix now is **parked** here as one such
entry; issues that still block route back to Plan/Build. **The human owns the
lifecycle** — agents may add or propose entries, but only the human closes/completes
one. The human later promotes entries into specs (the `how` + `where` seed the new
spec's plan).

## Entries

- [ ] 2026-09-27 | what: vetting (1.5) mechanics are deferred — the `vetting:` flag exists but the critic loop is not built | where: phase-protocol / auto-router | who: framework | how: implement the 1.5-Vetting loop (fresh critic, 3-try cap, gate-log entry) when first needed

- [ ] 2026-09-28 | what: do we need the Task 1, Task 2,... list? The list can be made in the compiled state. We will keep the Outcomes table at all status | where: in the md file | who:  | how:  | when: the status is at drafted state in the file

- [x] 2026-09-28 | what: the check oracle-lint (promote_spec.py line ~326: `expect in verify`) is too strict - it rejects any Expect value that appears as a substring of the Verify command, which blocks the natural `grep -o MARKER` idiom (the marker is in the command) AND the verify engine (verify.py line 929) requires the marker in the output, so `grep -q`/`test`/`! grep` oracles (no output) also fail. Only awkward oracles pass both. | where: .agents/skills/spec-builder/scripts/promote_spec.py (_validate_tasks) + .agents/skills/verification-runner/scripts/verify.py (cmd_run) | who: framework | how: relax the substring rule (e.g. only flag Expect values that are the WHOLE command or an unconditional constant) so a marker the command itself emits (grep -o / grep match output) is allowed; reconcile with the verify engine's exit-0-and-marker rule | when: hit while authoring spec 003 oracles — resolved 2026-10-19: the substring rule was relaxed in `_unfailable_expect` (a marker the command emits, e.g. `grep -o MARKER`, is now a valid oracle); the empty template stubs have been removed.
