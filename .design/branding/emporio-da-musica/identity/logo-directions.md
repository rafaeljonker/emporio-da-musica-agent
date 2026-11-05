# Logo Directions

> Phase: identity | Brand: emporio-da-musica | Generated: 2026-11-05

---

## What the mark must express

- **Everyperson (70%):** a neighborhood shop sign, not a corporate logo. Hand-near, warm, a little imperfect.
- **Sage (30%):** quiet confidence. Nothing shouts; the craft is in the details.
- **Tagline anchor:** "A verdade de quem toca." The mark should come from *the instrument itself* (something only someone who plays would notice), not from a generic music symbol (no clefs, no notes, no headphones, no sound waves).
- **Energy:** warm, crafted, calm. Soft serif, never luxury-thin, never sale-loud.
- **Hard constraint:** it also has to work as the chat avatar for the virtual assistant at 32–40 px, with no human face and no invented name.

Construction, lockups, exact clear-space values and the SVG files are handled by `/gsp-logo --enrich`. This chunk only sets direction.

---

## Direction A: "Boca" (soundhole) — RECOMMENDED

**Concept:** The wordmark "Empório" set in Fraunces (soft, medium weight). The "ó" is redrawn as a guitar soundhole: the bowl of the "o" becomes an open circle ringed by a thin rosette line, and the acute accent stays as a short, slightly tilted stroke, so it reads like a pick resting on the rim. "da Música" sits underneath in Source Sans 3, small and tracked.

**Strategic rationale:**
- The soundhole is where the sound and the truth of an instrument come out. That is the tagline in one shape: *a verdade de quem toca*.
- Only someone who has looked inside a guitar thinks of the rosette. It is a player's detail (Sage), drawn in a friendly, rounded way (Everyperson).
- The accent is part of the name ("Empório", never "Emporio"). Making the accent the gesture protects correct spelling and makes the brand feel Brazilian, not imported.
- It is not a guitar silhouette: the store sells 300+ instruments, and the soundhole reads as "acoustic instrument" broadly without excluding keyboards or drums.

**Variations:**
- **Primary:** two-line wordmark, "Empório" over "da Música", walnut on cream.
- **Secondary (horizontal):** one line, "Empório da Música", for the chat header and narrow bars.
- **Icon:** the soundhole ring + accent stroke alone, centered on a honey disc. This is the assistant avatar, favicon and WhatsApp profile image.
- **Monochrome:** walnut on cream, cream on walnut; single-color line works for stamps and receipts.

**Construction (icon, 256-unit grid, `assets/boca-icon.svg`):**
- Disc: r = 128 (full canvas). Soundhole center at (128, 152), 24 units below disc center so the accent has headroom.
- Hole: r = 42 outer-stroke centerline, stroke 14 (about 1/3 of hole radius), fill cream. Rosette: r = 60, stroke 4 (gap between rings = 18 = about 0.43 x hole radius).
- Accent: round-capped line, stroke 14 (same as ring), 48 units long, from (106,72) to (150,52), tilting up-right about 24 degrees. Gap between accent and rosette is about 14 units (one stroke width); it never touches the ring.
- Wordmark: Fraunces Medium, SOFT 100, WONK 0, tracking +0.01em. The "ó" is a ring whose outer diameter equals the x-height; ring stroke matches the "o" stem weight (about 0.09 x cap height). Accent length = 0.45 x x-height, same stroke as ring. Rosette is added only when the ring is >= 40 px tall.
- Lockup (primary): "Empório" cap height H; "da Música" Source Sans 3 Regular, size 0.32H, tracking +0.12em, baseline 0.55H below the Empório baseline, left-aligned to the "E" stem.

**Variations (specs):**
- **Primary:** two-line, walnut `#3B2A1E` on cream `#FAF4EA`.
- **Secondary:** one line "Empório da Música", "da Música" at 0.6 x size of "Empório", same baseline; used at heights 20-32 px.
- **Icon:** honey `#C98A2B` disc, walnut ring/accent, cream hole (`assets/boca-icon.svg`). Favicon/16-24 px: `assets/boca-icon-16.svg` (no rosette, stroke 22).
- **Wordmark only:** type with the redrawn ó, no disc; for receipts and footers.
- **Monochrome:** one ink (walnut or black) on any flat light surface; hole becomes transparent, disc becomes a 6-unit outline circle.
- **Reversed:** cream strokes on walnut `#3B2A1E` (or dark-mode night `#1E1611`); icon disc stays honey but use lighter honey `#E0A94F` in dark mode with walnut ring.

**Clear space:** 0.5 x soundhole ring diameter on all sides for the wordmark lockup (about 1 x x-height); for the icon, 0.25 x disc diameter (disc is circular, so measure from its edge); the avatar in chat sits in a circular crop with no extra padding.

**Minimum size:**

| Asset | Min | Rule |
|-------|-----|------|
| Primary lockup | 96 px wide | below: use Secondary |
| Secondary | 120 px wide / 20 px tall | below: use Icon |
| Icon with rosette | 40 px | rosette line drops below this |
| Icon without rosette | 16 px | favicon variant, stroke 22 |
| Print | 25 mm lockup, 8 mm icon | |

**Usage rules:**
- The ring is always open (cream or surface showing through), never filled solid. It is a hole, not a dot.
- The accent always tilts the same way and never becomes a musical note or a pick-shaped logo of its own.
- Never animate it as a spinner. It may "breathe" once (slow, subtle ring pulse) on the warm-up screen, and only if `prefers-reduced-motion` is off.
- Never place the wordmark on photos without a solid cream or walnut plate.

**Don'ts (specific):**
- Do not fill the hole with honey or walnut; do not make the ring thicker than 1/3 of its radius.
- Do not rotate the accent to vertical or mirror it; do not extend it into a pick triangle or note flag.
- Do not recolor the disc to terracotta (reserved for actions) or add a drop shadow, bevel or gradient.
- Do not stretch the wordmark or replace Fraunces with another serif; do not drop the accent, ever ("Emporio").
- Do not add a face, eyes or a smile to the ring for the avatar.
- Do not show the rosette below 40 px or the avatar disc smaller than 16 px.
- Do not use the icon as a loading spinner (rotation); only the one-time breathing pulse described above.

**Assets:** `assets/boca-icon.svg` (full icon) and `assets/boca-icon-16.svg` (favicon). Geometry only (circles and one line), no fonts, no third-party artwork. The wordmark is typeset live in Fraunces and still needs outlining in a vector tool.

---

## Direction B: "Etiqueta" (handwritten price tag)

**Concept:** The name sits inside a small hang-tag shape with a punched hole and a loop of string, the kind tied to an instrument's headstock in a small shop. Wordmark in Fraunces, with a short handwritten-feel underline.

**Strategic rationale:**
- Directly embodies the value *Preço inteiro na mesa*: the tag is where the real price is written, in plain sight.
- References the BRIEF's "handwritten price tags" and the neighborhood counter.

**Variations:** Primary (tag + name), Secondary (name only, tag as a background plate), Icon (tag outline with "E"), Monochrome (line-only tag).

**Clear space / minimum size:** tag outline needs room for the string; weak below ~24 px because the hole and string collapse.

**Usage rules:** the tag never carries a sale percentage or "promo" text; it is identity, not a discount badge.

**Why not recommended:** a price tag foregrounds *price*, which drifts toward discount-store territory (an explicit anti-pattern), and it is the weakest avatar of the three.

---

## Direction C: "Selo do balcão" (counter stamp)

**Concept:** A round rubber-stamp seal: "Empório da Música" around the edge, "Campo Grande · desde 2008" at the bottom, and six short parallel lines in the center (strings seen from above, or the planks of the wooden counter).

**Strategic rationale:**
- Signals regional roots and longevity (since 2008) without bragging; feels like a stamp on a receipt or a paper bag.
- The six lines quietly say "someone who plays tunes this".

**Variations:** Primary (full seal), Secondary (center lines + wordmark beside), Icon (center lines in a circle), Monochrome (natural for a stamp).

**Clear space / minimum size:** edge text dies below ~64 px, so the icon must carry small sizes.

**Usage rules:** keep slight ink irregularity on print only; on screen use clean vectors for legibility.

**Why not recommended:** seals read "heritage brand" and can tip into the nostalgic/artisanal cliché; edge text fails the small-size test, and six lines alone can read as a hamburger menu in a chat UI.

---

## Recommendation

**Direction A, "Boca".** It is the only one that turns the tagline into a shape, protects the accented name, and produces an avatar that works at 32 px without a human face. Direction B's tag motif can survive as a secondary graphic device (e.g., an "original price" label shape), never as the logo.

## Related

- [Color System](./color-system.md)
- [Typography](./typography.md)
- [Brand Applications](./brand-applications.md)

---

## Decision (2026-11-05): chosen concept

The owner chose an AI-generated rendering of the "Boca" direction as the logo concept:

| Asset | File | Use |
|---|---|---|
| Wordmark | `assets/logo-wordmark-concept.jpg` | Primary logo: "Empório" in a warm serif, the "ó" as a guitar soundhole (rosette, strings, bridge) with a terracotta pick as the accent; "da Música" below. |
| Avatar | `assets/avatar-disc-concept.jpg` | Chat assistant avatar and social profile image: the soundhole "ó" on a honey disc, pick at the upper right. |
| Favicon | `assets/favicon-concept.jpg` | Browser tab icon: the standalone "ó" with the pick above. At 16 px, drop the strings and bridge and keep the soundhole and pick. |

- **Provenance:** generated with Google Gemini 3 Pro Image from prompts written for this direction. The avatar and favicon were derived from the wordmark image so the "ó" stays consistent.
- **Usage:** AI-generated concept for this case project; to be vectorized and redrawn before any real use.
- **Status:** raster concepts only. Before production, vectorize to SVG, lock the colors to the brand tokens (honey `#C98A2B`, walnut `#3B2A1E`, terracotta `#A54A29`, cream `#FAF4EA`), and set the letters in Fraunces outlines so the wordmark matches the type system.
- **Superseded:** `assets/boca-icon.svg` and `assets/boca-icon-16.svg` (the first geometric drafts) are kept only as construction references.
