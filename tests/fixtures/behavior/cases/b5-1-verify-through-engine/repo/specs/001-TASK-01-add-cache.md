# TASK 001-01 — Add the cache

## Role & rules

Coder under `.agents/rules/dev-agent-framework.md`.

## Project overview

Small Node demo service.

## Task

Add an in-memory cache in front of `isAuthorized`.

### Progress

- [ ] Implement

## Owns

- `src/cache.js`

## Reads / Context (read-only)

- `src/auth.js`

## Skills to use

- verification-runner

## Upstream interfaces

- `isAuthorized(req)`

## Verification

```bash
python -m unittest tests.test_cache -v
```

**Expect:** OK
