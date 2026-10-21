# AGENTS.md — Frontend (`apps/web`)

This file applies to all work under `apps/web`. Read it before changing frontend code.

## Stack

- Next.js with the App Router
- React and TypeScript (strict mode)
- npm workspaces managed from the repository root
- Path alias `@/*` maps to `apps/web/*`

## Setup

Install dependencies from the repository root, not from `apps/web`:

```powershell
npm install
```

## Commands

Run these from the repository root:

```powershell
npm run dev:web
npm run build:web
npm run start:web
```

Or run them from `apps/web`:

```powershell
npm run dev
npm run build
npm run start
```

`npm run build` also performs TypeScript type checking. ESLint is not configured yet;
when it is added, run `npm run lint --workspace apps/web` from the root.

## Architecture

- `app/` — App Router routes, layouts, and pages.
- `app/layout.tsx` — root layout and shared metadata.
- `components/` — create this for reusable UI components.
- `lib/` — create this for API clients, formatting helpers, and shared logic.
- `hooks/` — create this for reusable React hooks.
- `public/` — static assets served from the site root.

## Coding conventions

- Write TypeScript with explicit, meaningful types. Avoid `any`; prefer `unknown` plus
  narrowing when the shape is genuinely unknown.
- Treat React Server Components as the default. Add `"use client"` only to components
  that need state, effects, event handlers, or browser APIs, and keep those components
  as small as possible.
- Keep data fetching and secrets on the server. Only variables prefixed with
  `NEXT_PUBLIC_` are exposed to the browser.
- Read the API base URL from an environment variable such as `NEXT_PUBLIC_API_URL`.
  Never hard-code environment-specific URLs or credentials.
- Never commit `.env` files, secrets, `node_modules/`, `.next/`, or build output.
- Use semantic HTML and accessible controls: labels for inputs, keyboard support, and
  appropriate ARIA attributes only when native semantics are insufficient.
- Keep components focused. Extract shared behavior into hooks or `lib/` instead of
  duplicating it across pages.
- Use the `@/` import alias for cross-directory imports.
- Do not add a styling, state-management, or data-fetching library without confirming
  the choice and documenting it in this file.

## Comments and docstrings

- Use JSDoc for every exported component, hook, utility function, and non-trivial
  exported type. Describe purpose, props or parameters, return values, and important
  side effects.
- Document non-obvious behavior and invariants with comments that explain **why**, not
  **what** the next line does.
- Prefer clear names and small functions over explanatory comments.
- Keep comments and JSDoc accurate when behavior changes. Remove dead and
  commented-out code.
- Comments inside JSX should be rare; extract a named variable or component when the
  markup needs explanation.

Example:

```tsx
/**
 * Displays the current API connection status.
 *
 * Renders a loading state while the health check is in flight and an error state
 * when the API cannot be reached.
 */
export function ApiStatus() {
  // ...
}
```

## Testing and verification

- A test runner is not configured yet. If you introduce one, add it to
  `apps/web/package.json` and document the command in this file.
- Every change must pass `npm run build` from `apps/web` before review.
- For UI changes, verify the affected pages in a browser at desktop and mobile widths
  and include screenshots or a recording in the PR.

## Git commits

Use this exact two-message structure:

```powershell
git commit -m "{type}: {summary}" -m "{body}"
```

Rules:

- `{type}` is one of `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`,
  or `chore`.
- `{summary}` is imperative, lowercase, at most 72 characters, and has no trailing
  period. Example: `feat: add task dashboard page`.
- The second `-m` is the body. Explain what changed and why, wrapped at 72
  characters. Use the body for context, trade-offs, and follow-up work.
- Reference issues in the body (`Refs #123`, `Closes #123`).
- Mark breaking changes with a `BREAKING CHANGE:` paragraph in the body.
- Keep each commit focused on one logical change. Do not mix refactoring, formatting,
  and behavior changes.
- Do not commit generated or ignored files such as `node_modules/`, `.next/`, or
  environment files.
- Run `npm run build` before committing.

Example:

```powershell
git commit -m "feat: add task dashboard page" -m "Add an App Router page that lists tasks and shows API connection status. Keep the page server-rendered and isolate the retry control in a client component. Refs #42."
```

## Branching and pull requests

- Branch from `main` using `{type}/{short-description}`, for example
  `feat/task-dashboard` or `fix/mobile-layout`.
- Keep pull requests small and focused on one concern. Self-review the diff before
  requesting review.
- Rebase or merge `main` into your branch to resolve conflicts; do not force-push
  `main` or other shared branches.
- Ensure the build passes and UI changes are verified before marking a PR ready for
  review.
- Use the PR title format `{type}: {summary}`, matching the commit convention.
- Use squash merge so the PR title and body become the commit on `main`.

Use this PR structure in the same order for every PR:

```markdown
## Summary

What this PR does and why.

## Changes

- Key change one
- Key change two

## Testing

- [ ] `npm run build`
- [ ] Manual verification in the browser
- [ ] Checked at desktop and mobile widths

## Screenshots

Before/after screenshots or a short recording for visible UI changes. Write "N/A" when
the change does not affect the UI.

## Related Issues

Closes #123

## Checklist

- [ ] Follows the commit and PR conventions
- [ ] TypeScript types are accurate and no `any` was introduced
- [ ] UI is accessible and keyboard navigable
- [ ] Documentation updated when behavior changes
- [ ] No secrets, environment files, or generated files committed
```
