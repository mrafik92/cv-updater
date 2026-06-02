# CV Tailor — UI Style Guide

Tailwind utility recipes used across templates. Compose with `class="..."`.

## Tokens

- **Surface**: `bg-slate-50` (page), `bg-white` (cards/header)
- **Text**: `text-slate-900` (body), `text-slate-600` (muted), `text-slate-400` (meta)
- **Accent**: `text-indigo-600`, `bg-indigo-600` (primary actions, brand)
- **Border**: `border-slate-200` (default), `border-slate-100` (subtle)
- **Radius**: `rounded-lg` (controls), `rounded-xl` (cards)
- **Spacing base**: 4px grid (`px-4`, `py-2`, `gap-6`)
- **Font**: system-ui via `font-sans`

## Recipes

### Card
`rounded-xl bg-white p-6 shadow-sm border border-slate-200`

### Primary button (`btn-primary`)
`inline-block rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700`

### Secondary button (`btn-secondary`)
`inline-block rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50`

### Input (`input`)
`w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500`

### Textarea (`textarea`)
Same as input plus `resize-y min-h-[8rem]`

### Badge (`badge`)
`inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700`

Status variants:
- success: `bg-green-50 text-green-700`
- error: `bg-red-50 text-red-700`
- warning: `bg-amber-50 text-amber-700`

### Flash toast
See `_partials/flash.html`. Auto-dismisses after 4s with opacity fade.
