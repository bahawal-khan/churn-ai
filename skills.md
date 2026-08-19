# ChurnAI — Development Skills & Workflows

Project-specific workflows to follow as phases are built out.

## Workflow

- Build phase-by-phase: foundation → backend → database → ML → frontend → integration.
- Each phase should be its own set of commits, kept small and reviewable.
- Confirm scope with the user before starting a new phase.

## Backend (Flask, future)

- Keep routes thin; move business logic into service modules.
- Config via environment variables, never hardcoded secrets.

## Frontend (Next.js, future)

- Keep API calls in a dedicated client module, not scattered in components.

## Database (SQLite, future)

- Track schema changes via migrations, not manual edits.
- Never commit the `.db` file itself.

## ML (future)

- Keep data prep, training, and inference as separate, testable steps.
- Record model version/params alongside any saved model artifact.
