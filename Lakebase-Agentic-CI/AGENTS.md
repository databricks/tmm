# Development workflow

This repository uses Git worktrees, Lakebase database branches, and GitHub
pull requests.

Each coding-agent session works on its own Git branch and a matching Lakebase
Postgres branch (a copy-on-write clone of production), then opens a pull
request. When the PR is opened, GitHub Actions automatically deploys a per-PR
preview app to Databricks Apps, backed by a fresh Lakebase branch cloned from
production. Both are torn down automatically when the PR closes.

## Works with any worktree-aware agent

This workflow is agent-agnostic. It is built on Git worktrees plus GitHub
Actions, so it behaves identically no matter which coding agent drives it:

- **Claude Code** — a `SessionStart` hook (`.claude/hooks/setup-lakebase.sh`)
  provisions the per-worktree Lakebase branch automatically.
- **OpenAI Codex** — works the same way thanks to Codex's Git worktree
  support: run each task in its own worktree and Codex maps one branch to one
  environment (see
  https://learn.chatgpt.com/docs/environments/git-worktrees).
- **Google Antigravity** — same model: give each task its own worktree, and
  the per-branch Lakebase + preview-app lifecycle applies unchanged.

Why it "just works" everywhere: the parts that make this workflow function —
the per-branch Lakebase clone naming (`scripts/branch-name.sh`), the preview
deploy/cleanup, and the production migration — are driven by **Git branch
names and GitHub PR events**, not by any one agent. Whichever agent opens the
PR, the `Deploy Lakebase Preview`, `Migrate Lakebase Production`, and
`Cleanup Lakebase Branch` workflows run the same.

**One agent-specific piece:** the automatic per-worktree Lakebase branch
provisioning is wired as a Claude Code `SessionStart` hook. In Codex,
Antigravity, or any other tool, reproduce it either by adding an equivalent
"session start" / setup hook, or by running the script manually from the
worktree root once per session:

    CLAUDE_PROJECT_DIR="$(pwd)" bash .claude/hooks/setup-lakebase.sh

The script is a no-op in the main checkout and only provisions a branch inside
a linked worktree. If your agent doesn't persist the exported `LAKEBASE_*`
variables across commands, export them in your shell (the script prints the
branch and database it resolved). Everything downstream — the PR-triggered
preview and cleanup — is unaffected.

## Feature development

When running inside a worktree, work only on the Git branch assigned to that
worktree.

Do not switch branches.

The environment variable `LAKEBASE_BRANCH` identifies the Lakebase database
branch assigned to this worktree. Only modify that Lakebase branch.

Never connect directly to or modify the production Lakebase branch
(`production`). Never use production database credentials. Never delete
Lakebase branches manually. This worktree's branch is cleaned up
automatically: the `Cleanup Lakebase Branch` GitHub Action deletes it when
its PR is closed, and a 30-day TTL reclaims it as a safety net if no PR is
ever opened.

Never create or delete Databricks Apps manually. The per-PR preview app is
created and deleted only by GitHub Actions (`Deploy Lakebase Preview` and
`Cleanup Lakebase Branch`); do not deploy or delete it by hand.

## Database changes

The schema is defined in code with Drizzle (`app/server/db/schema.ts`) and
applied via ordered migration files in `app/migrations/`. The app never runs
DDL at startup — migrations own all schema changes; the app issues DML only.

When database changes are required:

1. Verify `AGENT_ENV=lakebase-preview`.
2. Verify `LAKEBASE_BRANCH` is defined.
3. Edit `app/server/db/schema.ts`, then from `app/` run `npm run db:generate`
   to produce the SQL migration in `app/migrations/`.
4. Apply and test against this worktree's branch only: `npm run migrate`.
5. Commit the generated migration files together with the application code.

Never apply migrations directly to production (the `Migrate Lakebase Production`
workflow does that on merge).

## Pull requests

For feature work:

1. Implement the requested functionality.
2. Run relevant tests, linting, and type checking.
3. Make a coherent commit.
4. Push the current branch to origin.
5. If the current branch has no pull request, create a draft pull request.
6. Continue working on the same branch and pull request.
7. Push subsequent commits as needed.
8. Once implementation and checks are complete, mark the PR ready for review.

A feature task is not complete until:

- changes are committed
- changes are pushed
- a pull request exists
- automated checks pass
- the pull request is ready for review

Do not merge your own pull request.

### Pull request creation

Use `gh pr view` to determine whether a PR already exists.

If none exists:

    gh pr create --draft --fill

When finished:

    gh pr ready

## Before completion

The application lives in the `app/` directory — run all npm/AppKit commands from
there (`cd app`). The Databricks bundle (`databricks.yml`) stays at the repo
root, so run `databricks` bundle/app commands from the root. Run the project's
standard checks:

    (cd app && npm run typecheck)
    (cd app && npm run lint)
    databricks apps validate --profile <PROFILE>

Review:

    git status
    git diff origin/main...HEAD

Then push all final commits and verify:

    gh pr checks

Report the PR URL when complete. Opening the PR triggers the
`Deploy Lakebase Preview` GitHub Action, which deploys a preview app
(`appkit-lakebase-pr-<number>`) on a fresh `pr-<number>` Lakebase branch and
comments the preview URL on the PR. Closing or merging the PR triggers the
`Cleanup Lakebase Branch` GitHub Action, which deletes the preview app, the
`pr-<number>` branch, and this worktree's Lakebase branch. If a PR is never
opened, each branch's 30-day TTL reclaims it as a backstop.

## Databricks AppKit

This project uses Databricks AppKit packages. For AI assistant guidance on using these packages, refer to:

- **@databricks/appkit** (Backend SDK): [./app/node_modules/@databricks/appkit/CLAUDE.md](./app/node_modules/@databricks/appkit/CLAUDE.md)
- **@databricks/appkit-ui** (UI Integration, Charts, Tables, SSE, and more.): [./app/node_modules/@databricks/appkit-ui/CLAUDE.md](./app/node_modules/@databricks/appkit-ui/CLAUDE.md)

### Databricks Skills

For enhanced AI assistance with Databricks CLI operations, authentication, data exploration, and app development, install the Databricks skills:

```bash
databricks aitools install
```
