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
