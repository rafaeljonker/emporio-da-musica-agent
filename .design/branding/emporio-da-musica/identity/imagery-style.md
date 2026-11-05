# Imagery Style

> Phase: identity | Brand: emporio-da-musica | Generated: 2026-11-05

---

Hard constraint: **no third-party copyrighted imagery.** For the POC, the interface works with **zero photographs**. Warmth comes from color, type, texture and a few line drawings. Photography direction below is for when the store produces its own.

## Photography Direction (own photos only, future use)

- **Style:** documentary, unposed, available light. Like a friend snapped it on a Saturday morning at the counter.
- **Subjects:** hands on strings and keys; the grain of a spruce or cedar top up close; instruments resting on the wooden counter; a soundhole; staff (with consent) mid-explanation, seen from the side, not smiling at the camera.
- **Light:** soft morning or late-afternoon daylight from a window; warm, never orange-filtered.
- **Color treatment:** natural, slightly warm white balance; gentle contrast; no heavy filters, no duotones on people.
- **Composition:** close crops, shallow depth of field, generous negative space on cream-colored surfaces so copy can sit beside (never on top of) the photo.
- **Don't:** stock "happy customer with thumbs up", headset-wearing call-center agents, studio packshots on white in a grid (marketplace look), fake price stickers, rock-star stage shots, anything that suggests the assistant is a human.

## Illustration

- **Style:** single-weight line drawings of instrument details (soundhole rosette, tuning pegs, a headstock, a cavaquinho bridge, a piano key edge). Drawn with rounded line ends, slight hand-made feel, but clean enough to scale.
- **Complexity:** low. One object per drawing, no scenes, no characters, no mascots.
- **Color:** walnut lines on cream or spruce; at most a honey fill in one small area. No terracotta (reserved for actions).
- **Where:** empty state of the chat, the warm-up screen (one drawing, e.g., tuning pegs, tying in with "Afinando o atendimento"), error screens.
- **Don't:** cartoon robots, chat-bubble-with-face mascots, AI sparkles, music notes floating around.

**Line-drawing spec (for hand-built SVG, no stock, no AI-copied art):**
- Canvas 160 x 160 units (empty state / error) or 96 x 96 (inline). Stroke 3 units at 160 (about 1.9% of canvas), `stroke-linecap: round`, `stroke-linejoin: round`, `fill: none`, `stroke: currentColor` so it follows walnut / dark-mode cream.
- One honey accent allowed per drawing (`#C98A2B` fill at most 20% of the object area), never terracotta.
- Slight imperfection: build from arcs and short Bezier segments, let two lines overshoot their meeting point by 1-2 units. No pixel-perfect symmetry; no sketchy double-lines.
- Starter subjects: tuning pegs (warm-up), soundhole rosette (empty chat), a lone string with a peg slightly loose (error), cavaquinho bridge, piano key edge (success / order done).
- Drawings sit 50-60% of container width, centered, with cream around them; they carry no text and are `aria-hidden="true"` with the message in real text below.
- Motion: drawings are static. The only animated asset is the logo ring "breathing" (see Motion below).

## Texture

- **Paper grain** on the cream base and **faint wood grain** on spruce surfaces (header, login card), at very low intensity.
- Texture is atmosphere, not content: it must never sit behind small text in a way that reduces contrast, and it is dropped entirely on low-power/data-saver contexts if needed.
- Textures must be self-made or generated (CSS/SVG below), not taken from stock sites.

**Recipes (all generated, zero image files):**

```css
:root {
  /* paper grain: SVG noise, tinted walnut, tiny alpha */
  --grain-paper: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 .23  0 0 0 0 .16  0 0 0 0 .12  0 0 0 .5 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  /* wood grain: long thin horizontal bands, uneven spacing */
  --grain-wood:
    repeating-linear-gradient(92deg, rgb(59 42 30 / .035) 0 1px, transparent 1px 7px),
    repeating-linear-gradient(88deg, rgb(59 42 30 / .025) 0 2px, transparent 2px 19px);
}
/* Overlay as a pseudo-element so it never touches text layers */
.surface-paper, .surface-wood { position: relative; isolation: isolate; }
.surface-paper::before, .surface-wood::before {
  content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none;
}
.surface-paper::before { background: var(--grain-paper); opacity: .05; mix-blend-mode: multiply; }
.surface-wood::before  { background: var(--grain-wood); }
```

**Contrast guardrails (text never loses its ratio):**
- Max effective darkening: 5% walnut on cream shifts luminance by under 0.01, which keeps walnut `#3B2A1E` on cream/spruce far above 4.5:1; re-run the contrast check if opacity goes above `.06`.
- Apply grain only to **large containers** (body, header bar, login card, warm-up canvas). Never on chat bubbles, inputs, buttons, tables or any element holding body text under 18 px; those use flat Spruce / Paper / Walnut fills.
- Grain is `aria`-neutral (pseudo-element, `pointer-events: none`) and static: no animated grain, no parallax.
- Dark mode: swap the wood recipe to `rgb(243 233 216 / .03)` and drop paper grain; never lighten text-bearing areas.
- Performance: the SVG noise is about 400 bytes inline; for `prefers-reduced-data` or `save-data`, remove it: `@media (prefers-reduced-data: reduce) { .surface-paper::before, .surface-wood::before { display: none } }`.
- Motifs: one repeating motif only, the soundhole rosette ring at 4% walnut as a 96 px tile on the login/warm-up canvas. No gradients across surfaces.

## Motion & Reduced Motion

- Allowed motion (only these): ring "breathing" on warm-up, typing-dot pulse, 150 ms fade for message arrival. No parallax, no spinners, no animated texture.
- Breathing: `@keyframes breathe { 50% { transform: scale(1.04); opacity: .85 } }` at 4 s ease-in-out, infinite on warm-up only.
- Reduced motion: `@media (prefers-reduced-motion: reduce) { .breathe, .typing-dot, .fade-in { animation: none !important; transition: none !important } }`. Typing dots render static in full honey; the ring stays at rest. Meaning is carried by text ("Afinando o atendimento", "O assistente está digitando"), never by motion alone.

## Iconography

Style direction (kept): outline icons, rounded caps and joins, friendly not playful, walnut by default, semantic colors only for status and always paired with text, no filled/glossy icons, no emoji, no robot/AI/sparkle icons for the assistant.

**Library:** Lucide (ISC license; Feather portions MIT), `npm i lucide-react`, `import { Send } from "lucide-react"` (tree-shaken, per-icon import only). If the front end is not React, use `lucide-static` SVGs inlined. Pin the version in the lockfile. Verify exact icon names against the installed version; the names below are the expected Lucide names.

**Stroke:** one global value, `strokeWidth={1.75}` (slightly under Lucide's default 2, to sit next to Source Sans 3 Regular), `strokeLinecap="round"`, `strokeLinejoin="round"` (Lucide defaults). Never mix weights; use `absoluteStrokeWidth` so stroke stays 1.75 px regardless of size.

| Use | Size | Example |
|-----|------|---------|
| Inline text | 16 px | timestamps, stage meta, hours line |
| Default UI | 20 px | send button, header actions, buttons |
| Feature | 24 px | stage list, order/payment cards |
| Hero | 32-48 px | empty and error states (paired with a line drawing) |

**Set (icon, Lucide name, use):**

| Need | Lucide | Note |
|------|--------|------|
| Send | `Send` (or `SendHorizontal`) | cream on terracotta button |
| Typing | none; three honey dots (CSS) | do not use `Ellipsis` or a spinner |
| Store / hours | `Store`, `Clock` | opening hours, "Campo Grande" info |
| Order / package | `Package` | order status |
| Receipt / PIX | `Receipt`, `QrCode` | no PIX brand logo (trademarked); label says "PIX" in text |
| Credit card | `CreditCard` | |
| Return | `Undo2` | "Trocas e devoluções" |
| Error | `CircleAlert` | oxblood `#9A2E24`, always with message text |
| Success | `CircleCheck` | moss `#4F6B32`; stage done |
| Info | `Info` | walnut muted on spruce, never blue |
| Conversar como... (user switch) | `UserRound` + `ArrowLeftRight` | switch customer; label "Conversar como..." |
| Warm-up stages | `Server` (power on), `Cpu` (loading model), `CircleCheck` (ready) | pending stage = outline `Circle` in walnut muted; current = honey marker, no rotation |
| Extras (from before) | `ArrowLeft`, `RotateCcw` (retry), `LogOut` | |

**Containers (Tailwind):**
- Bare (default): `<Icon size={20} strokeWidth={1.75} className="text-walnut" aria-hidden />`.
- Tinted circle (stage list, feature rows): `inline-flex size-10 items-center justify-center rounded-full bg-honey/15 text-honey-deep`.
- Rounded square (info cards): `inline-flex size-10 items-center justify-center rounded-xl bg-spruce text-walnut`.
- Action: icon inside the terracotta button only, `text-cream`; terracotta icons never appear outside clickable elements.
- Avatar (logo icon): honey disc with the Boca mark (`assets/boca-icon.svg`), never a Lucide icon.

**Color rules:** walnut default; honey deep `#8A5A14` for honey-tinted icons on cream (plain honey `#C98A2B` is decorative-only); cream on walnut/terracotta fills; semantic hues only for success/error/warning. Icon-only buttons need an `aria-label` in pt-BR (`aria-label="Enviar mensagem"`); decorative icons get `aria-hidden`. Non-text contrast at least 3:1.

**Custom SVG (only the avatar and logo):** 24x24 grid, 1.75 stroke, round caps/joins, 2 px corner radius, exported as plain SVG with `currentColor`. Do not draw custom icons for anything Lucide covers.

## Image Treatments (for the store's own future photos)

- **Overlay (only when text must sit on an image):** `linear-gradient(to top, rgb(59 42 30 / .72), rgb(59 42 30 / 0) 60%)`, text in cream. Preferred alternative: a solid cream/walnut plate beside or under the photo.
- **Blend / tint:** natural by default; optional warm lift `mix-blend-mode: soft-light` with a Honey layer at 12%. No duotones on people.
- **Mask:** `border-radius: 12px` cards, `50%` for avatars, no blob or geometric clips.
- **Aspect ratios:** hero 16:9, card 4:3, product/detail 1:1, avatar 1:1 (logo icon only); `object-fit: cover`, `object-position: center 40%` to keep hands and soundholes in frame.
- **Responsive:** `<img srcset>` with 480 / 960 / 1440 widths and `sizes="(min-width: 768px) 50vw, 100vw"`; no art-direction crops in the POC.
- **Loading:** reserve space with `aspect-ratio`, spruce `#E9D8B8` placeholder color (no blur-up, no skeleton shimmer); `loading="lazy"`, `decoding="async"`; always meaningful `alt` in pt-BR.

## Assistant Avatar

The assistant is represented by the **logo icon** (soundhole ring + accent on a honey disc), not a face, not a robot, not a person's photo. It is honest: this is the store speaking through its virtual assistant.

## Related

- [Logo Directions](./logo-directions.md)
- [Color System](./color-system.md)
- [Brand Applications](./brand-applications.md)
