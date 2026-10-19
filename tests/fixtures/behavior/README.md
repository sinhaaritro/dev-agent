# Behavior fixtures

Two layers, one contract:

- **`fixtures/<name>/`** — a named input state.
  - `fixture.json`: `profile`, `setup` (bootstrap + skills to install), and a
    description.
  - `repo/` (optional): the consumer overlay on top of
    `profiles/<profile>/repo/`.
- **`cases/<case>/case.json`** — one directory per TEST-PLAN id, named
  `<id>-<slug>` (e.g. `b4-1-compile-then-stop`). A case owns one prompt +
  assertions.
  - `fixture`: which named state to seed.
  - `category`: the TEST-PLAN `2.x` group.
  - `case_id` (`B4.1`) and `title`: the visible scenario label.
  - `given` / `when` / `then`: the human scenario description. `then` is the
    list of observable outcomes the artifacts should prove.
  - `expected_artifacts`: the machine checks (the actual test).
  - `steps[]` is still supported for a genuine multi-prompt scenario, but the
    catalog is flat so every id is visible as its own directory.

`then` is documentation, not an assertion. Keep it honest: each `then` item
should be backed by at least one `expected_artifacts` entry.

Cases that name the same fixture are prepared once per config, then copied —
one fixture can run many prompts (in parallel with `--jobs`). Each prompt still
carries its own artifact checks, so one fixture can prove several constraints.

```bash
python tools/behavior_eval.py coverage        # TEST-PLAN ids vs catalog
python tools/behavior_eval.py list            # fixtures + ids + skills
python tools/behavior_eval.py list --verbose  # + Given / When / Then
python tools/behavior_eval.py batch --run-id <id> --skill auto-router --jobs 4 --open
python tools/behavior_eval.py feedback --run-dir <batch-dir>
```

The trusted review copy lands in `.behavior-review/` (gitignored). The vendored
viewer is not edited; the harness only supplies its workspace + metadata.
