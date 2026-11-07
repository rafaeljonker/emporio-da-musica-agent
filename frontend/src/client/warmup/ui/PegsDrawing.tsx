/** Tuning pegs (imagery-style.md): decorative, md+ only. */
export function PegsDrawing() {
  return (
    <svg
      viewBox="0 0 96 96"
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      className="hidden size-24 text-foreground md:block"
    >
      <path d="M34 92V30c0-14 6-24 14-26 8 2 14 12 14 26v62" />
      <path d="M42 92V20M54 92V20" />
      <circle cx="22" cy="36" r="6" />
      <path d="M28 36h6" />
      <circle cx="22" cy="58" r="6" />
      <path d="M28 58h6" />
      <circle cx="74" cy="36" r="6" fill="var(--brand)" fillOpacity=".2" />
      <path d="M68 36h-6" />
      <circle cx="74" cy="58" r="6" />
      <path d="M68 58h-6" />
    </svg>
  )
}
