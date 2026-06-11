# CLAUDE.md — experiments

This repo is public receipts for Product Compass posts. Anyone may read it to check a number. Treat every file as audience-facing.

## Structure

```
README.md                  # Root index (humans): one row per experiment SET, with dates
CLAUDE.md                  # This file
<set-slug>/                # One folder per experiment SET — a theme, not a whole model.
                           #   e.g. fable-5-speed-depth, fable-5-writing-register, gpt-6-tool-use.
                           #   A model can have several sets; name by theme and keep each set focused.
  README.md                # Set index: intro (what the set is about) + numbered table
                           #   (experiment, question, headline result) + shared method notes & caveats
  <NN-slug>/               # One folder per experiment (01-effort-dial, ...)
    README.md              # The experiment write-up (template below)
    <scripts>              # Exact scripts that produced the data
    <logs>                 # Raw, unedited output
```

## Per-experiment README template

Five sections, in order. Keep each tight; the audience is a busy PM/builder skimming for the number.

1. **Question** — one sentence, the claim being tested, ideally quoting the discourse it answers.
2. **Method** — tool, command shape, prompts (verbatim), sample size per cell, what timing includes.
3. **Results** — tables of raw numbers. Show every round, not just means.
4. **Findings** — numbered, one bold headline sentence each, interpretation only after the number.
5. **Caveats** — n, surface, variance observed, what would invalidate the finding. Never skip this section.

## Honesty bar (hard constraints)

- Raw logs are never edited, trimmed for embarrassment, or regenerated until they look right. One ~6s network outlier stays in the data with a variance re-run next to it; that is the model to follow.
- State n for every cell. n=1 is publishable if labeled directional.
- Failed and null results get filed like wins. An experiment that disproves the post's angle is the most valuable file in the repo.
- Wall-clock numbers: say what they include (CLI startup, tool roundtrips). Prefer ratios over absolutes.
- No internal paths, keys, or private-repo content. Prompts quoted verbatim are fine.

## When adding an experiment

1. Pick the set folder. A set is a theme (`fable-5-speed-depth`), not a whole model, so name by theme and keep each set focused.
2. Inside it, create `<NN-slug>/` with the next free number.
3. Write the experiment README from the template; copy in the exact scripts and raw logs.
4. Add the row to that set README's table.
5. If it's a NEW set: create `<set-slug>/README.md` (intro + table) and add the set row to the root README with its date.
6. Headline result = the one sentence you'd put in a tweet. If you can't write it, the experiment isn't done.
