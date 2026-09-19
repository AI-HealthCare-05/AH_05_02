# Post-MVP Frontend Refactor Memo

Date: 2026-09-08

## When to do this

Do this after the MVP user flow is stable and the current integration PRs are merged.

## Why not now

The current PR is focused on demo stability, FE-BE connection checks, and user-flow fixes. Splitting files now would create a large structural diff and make review harder.

## Suggested direction

- Keep the current integrated frontend files during MVP stabilization.
- Organize PR descriptions and Notion notes by screen instead of splitting code now.
- After merge, split the frontend by screen and shared concerns.

## Candidate structure

```text
src/frontend/
  app.js
  screens/
    auth.js
    health-form.js
    prediction-result.js
    challenge.js
    dashboard.js
    report.js
    together.js
    health-tools.js
  styles/
    base.css
    components.css
    screens.css
```

## Refactor checklist

- [ ] Move screen-specific rendering and event handlers out of `app.js`.
- [ ] Keep shared state and API helpers in a small common module.
- [ ] Split CSS into base, reusable components, and screen-level styles.
- [ ] Preserve existing tests before moving code.
- [ ] Add route/screen smoke tests after the split.
- [ ] Avoid changing UI behavior in the same PR as the file split.
