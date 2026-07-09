# Copilot Instructions

## Project status

This repository currently contains **no application source code** — it is a
fresh checkout scaffolded with [GitHub Spec Kit](https://github.com/github/spec-kit)
(speckit), Python variant, version `0.12.8` (see `.specify/init-options.json`).
There is no README, no build tooling, and no tests yet. Do not assume a tech
stack (language/framework) until one is actually introduced in the repo —
check `.specify/memory/constitution.md` and any `specs/` directory (created by
the workflow below) for the latest project intent before making assumptions.

## Spec Kit workflow

This repo is driven by the Spec-Driven Development workflow implemented as a
set of custom chat agents/prompts under `.github/agents/` and `.github/prompts/`,
backed by scripts/templates in `.specify/`. Use these agents in order for any
new feature work, since each stage's agent expects artifacts produced by the
previous stage:

1. `speckit.constitution` — establish/update project principles in
   `.specify/memory/constitution.md` (currently just an unfilled template —
   fill this in when the project's actual purpose/stack is decided).
2. `speckit.specify` — turn a feature description into a spec
   (uses `.specify/templates/spec-template.md`, creates a numbered
   `specs/NNN-feature-name/` directory via `.specify/scripts/`).
3. `speckit.clarify` — resolve ambiguities in the spec before planning.
4. `speckit.plan` — produce an implementation plan
   (`.specify/templates/plan-template.md`).
5. `speckit.tasks` — break the plan into dependency-ordered tasks
   (`.specify/templates/tasks-template.md`).
6. `speckit.analyze` — cross-check spec/plan/tasks for consistency
   (read-only, non-destructive).
7. `speckit.checklist` — optionally generate a custom quality checklist.
8. `speckit.implement` — execute `tasks.md` to build the feature.
9. `speckit.converge` — after implementation, diff the codebase against
   spec/plan/tasks and append any missed work as new tasks.
10. `speckit.taskstoissues` — convert tasks into GitHub issues if needed.

Feature numbering is sequential (`init-options.json`: `feature_numbering:
sequential`); new feature directories/branches are created by
`.specify/scripts/powershell/create-new-feature.ps1` (invoked by the
`speckit.specify` agent).

## Key conventions

- Do not hand-edit files under `.specify/integrations/*.manifest.json` —
  these track installed speckit/copilot integration versions and file
  checksums for the toolchain itself, not the project.
- When the constitution (`.specify/memory/constitution.md`) is filled in,
  treat it as the source of truth for project-wide principles; the
  `speckit.plan` and `speckit.tasks` agents check work against it.
- Once real source code, a README, or build/test commands are added, update
  this file with concrete build/lint/test instructions and architecture notes.
