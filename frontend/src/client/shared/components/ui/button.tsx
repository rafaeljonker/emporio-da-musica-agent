import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"
import { Slot } from "radix-ui"

// Brand override (patterns/components/button.md): solid hover, walnut focus outline, 44px targets.
const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-full font-sans text-base font-semibold whitespace-nowrap transition-[color,background-color,transform] duration-150 ease-brand select-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:pointer-events-none disabled:bg-muted disabled:text-muted-foreground aria-disabled:cursor-not-allowed aria-disabled:bg-muted aria-disabled:text-muted-foreground aria-disabled:hover:bg-muted aria-disabled:active:scale-100 [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground hover:bg-primary-hover focus-visible:shadow-[0_0_0_2px_var(--background)] active:scale-[0.98] active:bg-primary-hover",
        secondary: "border border-input bg-secondary text-foreground hover:bg-card",
        outline: "border border-input bg-secondary text-foreground hover:bg-card",
        ghost: "text-foreground hover:bg-muted",
        link: "h-auto px-0 text-foreground underline decoration-1 underline-offset-3 hover:decoration-2",
        destructive: "bg-destructive text-primary-foreground hover:bg-destructive/90",
      },
      size: {
        default: "h-11 px-6",
        sm: "h-9 px-4",
        icon: "size-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
