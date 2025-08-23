# Contributing

Thanks for helping improve Vikunja Voice Assistant!

## Ground Rules
- Keep logging minimal (info for success, error for failures). Avoid debug spam.
- No unrelated formatting changes in the same PR.
- Follow existing naming (snake_case for Python, concise file names).
- All UI / behavior changes must include a screenshot or short video.
- Tests (where practical) or manual validation steps described in PR.

## Dev Setup
1. Clone repo inside your Home Assistant `custom_components` dev environment.
2. Restart HA after changes or use the Reload Services / Assist reload where possible.
3. Optional: enable debug locally:
```
logger:
  logs:
    custom_components.vikunja: debug
```

## Submitting a PR
1. Branch from `main`.
2. Ensure no stray prints / leftover debug.
3. Update README / docs if feature surface changes.
4. Fill PR template including video/screenshot.

## Issue Reports
Must include reproduction steps + visual evidence.

## Style
- Line length: be reasonable; prefer readability.
- Imports: stdlib, third-party, local groups.
- Avoid broad except; specify exceptions where feasible.

Appreciate your contributions!
