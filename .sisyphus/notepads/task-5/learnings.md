# T5 learnings

- Tailwind standalone v4.3 is downloaded from latest GitHub release; v3 directives (@tailwind base/components/utilities) still compile via the v4 CLI.
- Tailwind v4 auto-detects content paths; `tailwind.config.js` is kept (per spec) for the `content` glob, font stack, and accent color.
- Starlette/FastAPI on this stack uses the new `templates.TemplateResponse(request, name)` signature — passing a dict as 2nd positional arg crashes with `unhashable type: 'dict'` due to internal cache key tuple.
- Existing `cv_tailor/templates/` and `cv_tailor/static/` were already created (presumably by T1); only had to populate.
