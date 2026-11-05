# Input, Textarea, composer — override spec (shadcn `input`, `textarea`, `label`)

> Tier 2 | Brand: emporio-da-musica | Source: `.yml` `patterns.input`, `tokens.color.input`

## Why override

- shadcn `input` uses `bg-transparent` and `border-input`; the brand fill is paper (`bg-popover`) and `--input` is walnut muted (6.45 on cream, 5.03 on spruce, 6.89 on paper; dark 4.14 / 3.58). The decorative `--border` (1.58) must never be a field boundary (SC 1.4.11).
- shadcn focus changes the border color and adds a 3px half-opacity ring; the brand keeps the border unchanged and adds a 2px walnut outline with 2px offset.
- shadcn uses `md:text-sm`; the brand floor is 16px everywhere (also prevents iOS zoom).

## Anatomy

1. `Label` above the field — walnut, 16px, 600. Never placeholder-only.
2. Field — `h-11 rounded-md border border-input bg-popover px-3 text-base text-foreground`.
3. Helper / error line below — 14px `text-muted-foreground`, or `text-destructive` + `CircleAlert` 20px + words.

## States

| State | Treatment |
|---|---|
| rest | 1px `--input` border, paper fill |
| hover | no change (fields are not hover targets) |
| focus-visible | `outline-2 outline-ring outline-offset-2`; border unchanged |
| invalid | `aria-invalid="true"`, border stays `--input`, error line in oxblood with icon, linked via `aria-describedby` |
| disabled | `bg-muted text-muted-foreground cursor-not-allowed` |
| placeholder | `placeholder:text-muted-foreground` (6.89 on paper); never the only label |

## Chat composer

- `rounded-full` textarea (auto-grow, 1 to 5 lines) + send icon button (see [button.md](./button.md)).
- `aria-label="Mensagem"`; placeholder "Escreve sua mensagem".
- Enter sends, Shift+Enter breaks a line. Send button disabled (muted tokens) while the field is empty or a reply is streaming.
- Sticky to the bottom with `pb-[env(safe-area-inset-bottom)]`.

## Code hint

```tsx
<Label htmlFor="email" className="text-base font-semibold text-foreground">E-mail</Label>
<Input id="email" type="email" autoComplete="email" aria-describedby="login-erro"
  className="h-11 rounded-md border-input bg-popover text-base focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2 focus-visible:ring-0" />
<p id="login-erro" role="alert" className="flex gap-2 text-destructive">
  <CircleAlert size={20} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
  E-mail ou senha não bateram. Confere e tenta de novo.
</p>
```

## Copy (pt-BR)

Labels "E-mail", "Senha". Demo note under the form: "Ambiente de demonstração. Use as credenciais do case."
