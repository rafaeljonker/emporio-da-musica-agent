# Install Manifest

> Phase: brief | Project: emporio-chat | Generated: 2026-11-05
> Target: shadcn/ui on Tailwind CSS v4, Vite + React + TypeScript, in `frontend/` (created in phase 5).

Run from the repo root. Versions are left to the build phase (spec section 8).

## 1. App + Tailwind v4

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install tailwindcss @tailwindcss/vite
npm install -D @types/node
```

Then: `@import "tailwindcss";` at the top of `src/index.css`; add `tailwindcss()` to `vite.config.ts` plugins; add the `@/*` → `./src/*` alias in `tsconfig.json`, `tsconfig.app.json` and `vite.config.ts` (`resolve.alias`). shadcn init requires the alias.

## 2. shadcn init + brand theme

```bash
npx shadcn@latest init
npx shadcn@latest add ../.design/branding/emporio-da-musica/patterns/emporio-da-musica.theme.json
```

Equivalent: `/gsp-brand-apply emporio-da-musica`. Then paste the brand extensions and `@theme inline` bridge from [token-mapping.md](../../../branding/emporio-da-musica/patterns/components/token-mapping.md) (sections 4–5) directly after the generated block.

## 3. Components

```bash
npx shadcn@latest add button input label textarea select card avatar badge
```

| Component | Why |
|-----------|-----|
| `button` | every action; cva replaced per [button.md](../../../branding/emporio-da-musica/patterns/components/button.md) |
| `input`, `label` | login form |
| `textarea` | chat composer (auto-grow) |
| `select` | CustomerSelector |
| `card` | login card |
| `avatar` | Boca disc in rail and agent groups |
| `badge` | honest badge on ProductCard |

Not installed, on purpose:

| Component | Reason |
|-----------|--------|
| `scroll-area` | the transcript is a native `overflow-y-auto` `role="log"` with `tabIndex={0}`; Radix ScrollArea wraps the viewport and complicates the live region and keyboard scrolling |
| `sonner` / `toast` | errors are inline (`role="alert"` on login/warm-up, inline retry in the thread) |
| `tooltip` | icon-only buttons carry visible-equivalent `aria-label`s; no hover-only info |
| `collapsible` | MetricsPanel uses native `<details>` |

Add any of these in the design phase only if a screen needs it.

## 4. Icons and fonts

```bash
npm install lucide-react @fontsource/source-sans-3 @fontsource-variable/fraunces
```

Import in `src/main.tsx`: `@fontsource/source-sans-3/400.css`, `@fontsource/source-sans-3/600.css`, `@fontsource-variable/fraunces` (latin + latin-ext only, per STYLE.md). No Google Fonts.

Lucide icons used: `Send`, `UserRound`, `Clock`, `CircleCheck`, `Circle`, `Server`, `Cpu`, `CircleAlert`, `CircleSlash`, `FlaskConical`, `ChevronDown`, `Check`, `LogOut`.

## 5. Verify

```bash
npm run build
```

## Related
- [scope.md](./scope.md) · [target-adaptations.md](./target-adaptations.md)
