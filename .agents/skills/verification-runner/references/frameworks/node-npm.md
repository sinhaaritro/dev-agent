# Framework: Node + npm

Canonical commands and failure patterns for Node.js projects managed with npm.

## Detection

`package.json` at the repo root (with a `package-lock.json`) -> this page. Note: if `pnpm-lock.yaml` or `yarn.lock` is present instead, prefer the package manager the lockfile declares - do not mix `npm ci` with a pnpm/yarn lockfile.

## Canonical commands

- Install / sync dependencies: `npm ci` (clean install from package-lock.json; use `npm install` only when adding a new dependency deliberately - a lockfile change is a reviewable event)
- Build: `npm run build` (or the script named in the plan's section 5)
- Test (full suite): `npm test` (or `npm run test`)
- Test (single file): `npx vitest run tests/path/to/file.test.ts` (vitest) or `npx jest tests/path/to/file.test.ts` (jest)
- Lint: `npm run lint` (when the project declares it)
- Type check: `npm run typecheck` or `npx tsc --noEmit`

## Failure patterns & fixes

- `Cannot find module` / ESM/CJS resolution errors: the dependency isn't installed or the module system mismatches - `npm ci`, then re-run; check `"type": "module"` in package.json against the import style.
- Lockfile mismatch: `npm ci` fails when package.json and package-lock.json disagree - run `npm install` (regenerates the lockfile) only if the package.json change was intentional.
- Build passes but tests fail: run the failing test alone first (`npx vitest run <file>`), the isolation usually identifies the culprit faster than a full-suite read.
- Out-of-memory during build: Node's default heap is small - `NODE_OPTIONS=--max-old-space-size=4096` for the build command when the plan's scope is large.
- Engine refused an interactive command: some dev servers pass `--watch` flags - verification must run non-interactively; drop the watch flag for the run.

## Verification checklist

- Install step: `npm ci` (clean, from the lockfile)
- Build step: `npm run build`
- Test step: `npm test` (full suite) or the scoped invocation from the plan's section 5
- Lint step: `npm run lint` when declared