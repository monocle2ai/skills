# Phase 6 — Smoke-test & PR flow

## Locate your Monocle clone

- **Source clone (edit here):** your local checkout of Monocle, e.g. `~/monocle` (git root). Package source:
  `<your-monocle-clone>/apptrace/src/monocle_apptrace/`.
- `origin` should be **your fork** of Monocle. Upstream = `monocle2ai/monocle` (**PR target**).
- The demo's venv has its own installed copy at `<demo>/.venv/.../site-packages/monocle_apptrace`.
- If you don't have a clone yet, `git clone https://github.com/monocle2ai/monocle` (then add your fork as a
  remote) and work from there.

## Step 1 — make the change in the clone

Edit only the targeted files in `<your-monocle-clone>/apptrace/src/monocle_apptrace/instrumentation/metamodel/<fw>/`
(and `wrapper_method.py` if registering a handler). Changes must be **additive and minimal**: add a method entry,
fix an accessor, or correct an output processor — never rewrite or restructure existing code, and don't add verbose
scaffolding. The bar is **zero regression**: existing spans and other frameworks must be unaffected, so sanity-check
you didn't touch a shared code path. The precise symptom from Phase 4 scopes the change.

## Step 2 — smoke test (editable install into the demo venv, re-run, re-grade)

```bash
# install the patched Monocle into the target demo's venv
uv pip install --python <demo>/.venv/bin/python -e <your-monocle-clone>/apptrace

# re-run the SAME question that failed in Phase 3, with file+console exporters
export MONOCLE_EXPORTER=file MONOCLE_CONSOLE=true
# ... run the demo ...
```

Re-grade the new `.monocle/` trace against `good-trace-recipe.md`. Proceed only if the gap is now closed and
nothing else regressed. If it didn't help, iterate in the clone (no reinstall needed — `-e` is editable, just
re-run). If it can't be closed with a small change → stop and report a redesign is needed.

## Step 3 — 🚦 PR (only after user says yes)

Branch + PR conventions:
- **Branch:** `monocle-fix/<feature>` (e.g. `monocle-fix/crewai-tool-output`).
- **PR target:** upstream `monocle2ai/monocle`, base branch `main` (confirm upstream's default).
- **Title (required signature):** prefix `[claude-skill]` so it's clearly skill-generated, then a clear,
  scoped summary — e.g. `[claude-skill] CrewAI: capture tool output in agentic.tool.invocation spans`.
- **DCO sign-off (required):** every commit must be `Signed-off-by:` the user's identity — use `git commit -s`.
  Monocle is a Linux Foundation project and enforces DCO; a PR without sign-off is blocked.
- **Body:** follow Monocle's PR template exactly — the four sections below, in order:
  - `## Proposed changes` — the big picture for maintainers: the symptom (framework + span/field), the root
    cause (which `methods.py` / processor / entity), the fix, and the before/after trace evidence from the
    smoke test. Link any issue it fixes.
  - `## Types of changes` — put an `x` in the box that applies (usually **Bugfix** for a coverage gap,
    **New feature** for a brand-new framework metamodel; **Breaking change** only if existing spans change shape).
  - `## Checklist` — check: read CONTRIBUTING, signed the CLA, lint + unit tests pass locally, added tests that
    prove the fix/feature, added docs if appropriate, dependent changes merged downstream.
  - `## Further comments` — for a structural or complex change, explain why you chose this solution and what
    alternatives you considered.

  End with the attribution footer `🤖 Generated with the monocle-auto-instrument skill`.

```bash
cd <your-monocle-clone>
git checkout -b monocle-fix/<feature>
git add -A
git commit -s -m "$(cat <<'EOF'
[claude-skill] <framework>: <one-line summary>

<what was missing, root cause, the small fix, smoke-test evidence>

🤖 Generated with the monocle-auto-instrument skill
EOF
)"
git push -u origin monocle-fix/<feature>          # pushes to your fork

# PR body MUST follow Monocle's template — fill the < > placeholders and tick the right boxes
cat > /tmp/monocle-pr-body.md <<'EOF'
## Proposed changes

<Big picture for the maintainers: the symptom (framework + span/field), the root cause
(which methods.py / processor / entity), the fix, and before/after trace evidence from the
smoke test. Link any issue this fixes.>

## Types of changes

- [x] Bugfix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation Update (if none of the other choices apply)

## Checklist

- [x] I have read the [CONTRIBUTING](https://github.com/monocle2ai/monocle/blob/main/CONTRIBUTING.md) doc
- [x] I have signed the CLA
- [x] Lint and unit tests pass locally with my changes
- [x] I have added tests that prove my fix is effective or that my feature works
- [ ] I have added the necessary documentation (if appropriate)
- [ ] Any dependent changes have been merged and published in downstream modules

## Further comments

<For a structural or complex change: why you chose this solution and what alternatives you considered.>

🤖 Generated with the monocle-auto-instrument skill
EOF

gh pr create --repo monocle2ai/monocle \
  --head <your-fork>:monocle-fix/<feature> \
  --title "[claude-skill] <framework>: <summary>" \
  --body-file /tmp/monocle-pr-body.md
```

If `gh` lacks permission to PR cross-fork, fall back to printing the branch + a ready-to-paste PR title/body for
the user to open manually. Never open the PR without the Phase-6 🚦 confirmation.
