---
tags: [lowercase-kebab, ...]
---

# [SPEC-ID]: Feature Title

Status: DRAFT | Phase: 1-Plan | Date: YYYY-MM-DD

## 1. Goal & Context

1-2 sentences explaining the business/technical goal.

## 2. Architectural Decisions & Trade-offs

Key technical choices made, alternative options considered, and trade-offs.

## 3. Affected Files & Scope

- Modified: src/auth/service.ts
- Created: src/auth/jwt-strategy.ts
- Deleted: none

## 4. Actionable TODO Checklist

- [ ] Step 1: Create JWT strategy helper in src/auth/jwt-strategy.ts.
- [ ] Step 2: Implement validation method in src/auth/service.ts.
- [ ] Step 3: Add unit tests in tests/auth/service.test.ts.

## 5. Verification Commands

- Build Command: npm run build
- Test Command: npm test -- tests/auth/service.test.ts

## 6. Rollback Strategy

Instructions on reverting edits if verification fails 3 times.

---
Usage: drafted at `docs/temp/draft-plan.md` during Phase 1-Plan; validated with
`promote_spec.py check <draft> --lane <B|A>` (the check also lints the `tags:` field, spec 010 D7); on acceptance promoted to `docs/specs/<id>-<feature>.md` via `promote_spec.py promote <draft> --lane <B|A> --status <APPROVED|PROVISIONAL>`. Lane A mandates the full template; Lane B uses sections 1, 3, 4 only. The `tags:` field is mandatory on committed docs and lives in the YAML frontmatter block at the top of the file (lowercase-kebab, 2-30 chars, max 7); a bare `tags:` line outside frontmatter is accepted for reading and normalized into frontmatter by the engine on promote/adr/tag-rename.
