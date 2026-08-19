# [SPEC-ID]: Feature Title

Status: DRAFT | Phase: 1-Plan | Author: AI Agent | Date: YYYY-MM-DD

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
Usage: drafted at `docs/temp/draft-plan.md` during Phase 1-Plan; validated with `promote_spec.py check <draft> --lane <B|A>`; on acceptance promoted to `docs/specs/<id>-<feature>.md` via `promote_spec.py promote <draft> --lane <B|A> --status <APPROVED|PROVISIONAL>`. Lane A mandates the full template; Lane B uses sections 1, 3, 4 only.
